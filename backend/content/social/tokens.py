"""OAuth token lifecycle for connected social accounts.

Access tokens expire — Google's after an hour — so without this the first
publication works and every later one fails with an opaque 401. Refreshing
happens server-side only; no token ever reaches the browser.
"""
import logging
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

#: Refresh a little early rather than racing the provider's clock.
EXPIRY_MARGIN = timedelta(minutes=5)


class TokenError(Exception):
    """Raised when an account can no longer authenticate and must reconnect."""

    def __init__(self, message, code='RECONNECT_REQUIRED'):
        super().__init__(message)
        self.code = code


def record_expiry(account, payload):
    """Store `expires_in` from an OAuth exchange as an absolute instant."""
    expires_in = payload.get('expires_in')
    if expires_in:
        try:
            account.token_expires_at = timezone.now() + timedelta(seconds=int(expires_in))
        except (TypeError, ValueError):
            account.token_expires_at = None
    return account


def is_expired(account):
    if not account.token_expires_at:
        return False  # unknown lifetime: let the provider be the judge
    return account.token_expires_at <= timezone.now() + EXPIRY_MARGIN


def _refresh_google(account):
    return requests.post(
        'https://oauth2.googleapis.com/token',
        data={
            'grant_type': 'refresh_token',
            'refresh_token': account.refresh_token,
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
        },
        timeout=15,
    )


def _refresh_linkedin(account):
    # Only apps approved for programmatic refresh receive a usable refresh
    # token; otherwise LinkedIn answers 400 and the member must reconnect.
    return requests.post(
        'https://www.linkedin.com/oauth/v2/accessToken',
        data={
            'grant_type': 'refresh_token',
            'refresh_token': account.refresh_token,
            'client_id': settings.LINKEDIN_CLIENT_ID,
            'client_secret': settings.LINKEDIN_CLIENT_SECRET,
        },
        timeout=15,
    )


REFRESHERS = {
    'YOUTUBE': _refresh_google,
    'LINKEDIN': _refresh_linkedin,
}


def mark_reconnect_required(account, message):
    account.needs_reconnect = True
    account.last_error = message[:500]
    account.save(update_fields=('needs_reconnect', 'last_error'))


def ensure_fresh_token(account):
    """Return a usable access token for `account`, refreshing it if needed.

    Raises `TokenError` when the account must be reconnected by a human.
    """
    if not account.access_token:
        mark_reconnect_required(account, 'Aucun jeton d’accès enregistré.')
        raise TokenError(f'Le compte {account.platform} doit être reconnecté.')

    if not is_expired(account):
        return account.access_token

    refresher = REFRESHERS.get(account.platform)
    if not refresher or not account.refresh_token:
        mark_reconnect_required(
            account, 'Jeton expiré et aucun rafraîchissement possible pour cette plateforme.',
        )
        raise TokenError(
            f'Le jeton {account.platform} a expiré. Reconnectez le compte.', 'TOKEN_EXPIRED',
        )

    try:
        response = refresher(account)
    except requests.RequestException as exc:
        logger.warning('Token refresh network failure for %s: %s', account.platform, exc)
        raise TokenError(f'Réseau indisponible pour rafraîchir le jeton {account.platform}.', 'NETWORK_ERROR')

    if not response.ok:
        # Never log the body verbatim: refresh responses can echo secrets.
        logger.warning('Token refresh rejected for %s (HTTP %s)', account.platform, response.status_code)
        mark_reconnect_required(account, f'Rafraîchissement refusé par le fournisseur (HTTP {response.status_code}).')
        raise TokenError(
            f'Le fournisseur {account.platform} a refusé le rafraîchissement. Reconnectez le compte.',
            'REFRESH_FAILED',
        )

    payload = response.json()
    account.access_token = payload.get('access_token', account.access_token)
    if payload.get('refresh_token'):
        account.refresh_token = payload['refresh_token']
    record_expiry(account, payload)
    account.needs_reconnect = False
    account.last_error = ''
    account.save(update_fields=(
        'access_token', 'refresh_token', 'token_expires_at', 'needs_reconnect', 'last_error',
    ))
    logger.info('Refreshed %s access token', account.platform)
    return account.access_token


def account_health(account):
    """Connection state for the back-office, with no secret in sight."""
    if not account.is_active:
        return 'DISCONNECTED'
    if account.needs_reconnect:
        return 'RECONNECT_REQUIRED'
    if is_expired(account) and not account.refresh_token:
        return 'RECONNECT_REQUIRED'
    return 'CONNECTED'
