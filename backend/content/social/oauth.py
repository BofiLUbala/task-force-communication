"""OAuth authorize/exchange helpers for each connected social platform.

Each platform requires its own developer app (client id/secret) configured
via environment variables — see config/settings.py. A platform whose
credentials are empty is reported as unavailable and cannot be connected.
"""
from urllib.parse import urlencode

import requests
from django.conf import settings


class OAuthError(Exception):
    pass


def _redirect_uri(platform):
    return f'{settings.SOCIAL_AUTH_REDIRECT_BASE}/api/social-accounts/oauth/{platform.lower()}/callback/'


LINKEDIN_SCOPES = 'openid profile w_member_social'
GOOGLE_SCOPES = 'https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly'
TIKTOK_SCOPES = 'video.publish video.upload user.info.basic'
FACEBOOK_SCOPES = 'pages_show_list,pages_manage_posts,pages_read_engagement'
FACEBOOK_API_VERSION = 'v21.0'


def is_configured(platform):
    return {
        'LINKEDIN': bool(settings.LINKEDIN_CLIENT_ID and settings.LINKEDIN_CLIENT_SECRET),
        'YOUTUBE': bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET),
        'TIKTOK': bool(settings.TIKTOK_CLIENT_KEY and settings.TIKTOK_CLIENT_SECRET),
        'FACEBOOK': bool(settings.FACEBOOK_APP_ID and settings.FACEBOOK_APP_SECRET),
    }.get(platform, False)


def authorize_url(platform, state):
    if not is_configured(platform):
        raise OAuthError(f'{platform} n’est pas configuré (clés API manquantes).')

    if platform == 'LINKEDIN':
        params = {
            'response_type': 'code',
            'client_id': settings.LINKEDIN_CLIENT_ID,
            'redirect_uri': _redirect_uri(platform),
            'state': state,
            'scope': LINKEDIN_SCOPES,
        }
        return f'https://www.linkedin.com/oauth/v2/authorization?{urlencode(params)}'

    if platform == 'YOUTUBE':
        params = {
            'response_type': 'code',
            'client_id': settings.GOOGLE_CLIENT_ID,
            'redirect_uri': _redirect_uri(platform),
            'state': state,
            'scope': GOOGLE_SCOPES,
            'access_type': 'offline',
            'prompt': 'consent',
        }
        return f'https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}'

    if platform == 'TIKTOK':
        params = {
            'response_type': 'code',
            'client_key': settings.TIKTOK_CLIENT_KEY,
            'redirect_uri': _redirect_uri(platform),
            'state': state,
            'scope': TIKTOK_SCOPES,
        }
        return f'https://www.tiktok.com/v2/auth/authorize/?{urlencode(params)}'

    if platform == 'FACEBOOK':
        params = {
            'response_type': 'code',
            'client_id': settings.FACEBOOK_APP_ID,
            'redirect_uri': _redirect_uri(platform),
            'state': state,
            'scope': FACEBOOK_SCOPES,
        }
        return f'https://www.facebook.com/{FACEBOOK_API_VERSION}/dialog/oauth?{urlencode(params)}'

    raise OAuthError(f'Plateforme inconnue: {platform}')


def exchange_code(platform, code):
    """Exchange an authorization code for tokens. Returns a dict with at
    least access_token, and optionally refresh_token / expires_in."""

    if platform == 'LINKEDIN':
        resp = requests.post('https://www.linkedin.com/oauth/v2/accessToken', data={
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': _redirect_uri(platform),
            'client_id': settings.LINKEDIN_CLIENT_ID,
            'client_secret': settings.LINKEDIN_CLIENT_SECRET,
        }, timeout=15)
    elif platform == 'YOUTUBE':
        resp = requests.post('https://oauth2.googleapis.com/token', data={
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': _redirect_uri(platform),
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
        }, timeout=15)
    elif platform == 'TIKTOK':
        resp = requests.post('https://open.tiktokapis.com/v2/oauth/token/', data={
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': _redirect_uri(platform),
            'client_key': settings.TIKTOK_CLIENT_KEY,
            'client_secret': settings.TIKTOK_CLIENT_SECRET,
        }, headers={'Content-Type': 'application/x-www-form-urlencoded'}, timeout=15)
    elif platform == 'FACEBOOK':
        resp = requests.get(f'https://graph.facebook.com/{FACEBOOK_API_VERSION}/oauth/access_token', params={
            'client_id': settings.FACEBOOK_APP_ID,
            'client_secret': settings.FACEBOOK_APP_SECRET,
            'redirect_uri': _redirect_uri(platform),
            'code': code,
        }, timeout=15)
    else:
        raise OAuthError(f'Plateforme inconnue: {platform}')

    if not resp.ok:
        raise OAuthError(f'Échec de l’échange du code {platform}: {resp.text[:300]}')
    return resp.json()


def get_facebook_page(user_access_token):
    """Facebook publishes as a Page, not the logged-in user, so the user
    token from the OAuth exchange must be swapped for that Page's own
    access token. Returns (page_id, page_name, page_access_token)."""
    resp = requests.get(
        f'https://graph.facebook.com/{FACEBOOK_API_VERSION}/me/accounts',
        params={'access_token': user_access_token},
        timeout=15,
    )
    if not resp.ok:
        return '', '', ''
    pages = resp.json().get('data', [])
    if not pages:
        return '', '', ''
    page = pages[0]
    return page.get('id', ''), page.get('name', ''), page.get('access_token', '')


def get_linkedin_identity(access_token):
    """Fetch the connected member's id/name via OpenID Connect userinfo,
    used as the ugcPosts author URN when posting as the person rather than
    an organization page."""
    resp = requests.get(
        'https://api.linkedin.com/v2/userinfo',
        headers={'Authorization': f'Bearer {access_token}'},
        timeout=15,
    )
    if not resp.ok:
        return '', ''
    data = resp.json()
    return data.get('sub', ''), data.get('name', '')
