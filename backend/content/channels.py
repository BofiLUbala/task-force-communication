"""One publication, distributed to every channel the author selected.

This is the "create once, distribute everywhere" engine. It owns three rules
that the rest of the application depends on:

1. **Isolation.** Each channel runs inside its own try/except and writes its
   own `PublicationDelivery`. YouTube refusing an upload never un-sends the
   e-mails, never un-publishes the website and never rolls back LinkedIn.
2. **Honesty.** A delivery is SUCCESS only once the thing actually happened —
   a provider returned an identifier, or a message left the SMTP server. The
   compatibility engine decides beforehand what a channel cannot carry, and
   that becomes an explicit SKIPPED with a reason rather than a silent drop.
3. **No double send.** Recipient rows are unique per address, and a channel
   that already succeeded is never re-run.
"""
import logging

from django.utils import timezone

from .audience import audience_size, email_recipients, whatsapp_recipients
from .models import PublicationDelivery, PublicPost, RecipientDelivery, SocialPostAttempt
from .social.capabilities import (
    ALL_CHANNELS,
    EMAIL,
    MOBILE,
    WEB,
    WEBSITE,
    WHATSAPP,
    available_channels,
    plan_destination,
    whatsapp_message,
)

logger = logging.getLogger(__name__)

SOCIAL_CHANNELS = ('LINKEDIN', 'YOUTUBE')


def automatic_social_channels():
    """Social platforms every publication is offered to, without being asked.

    An author chooses *what* to publish and *who* it is for; deciding which
    connected provider can carry it is the compatibility engine's job, not a
    checklist the author re-ticks on every post. Any platform the back-office
    has ever connected is included — a since-disconnected one then reports
    NOT_CONNECTED through `deliver_social` instead of vanishing silently,
    while a platform that was never set up stays out of the result entirely.
    """
    from .models import SocialAccount

    known = set(
        SocialAccount.objects.filter(platform__in=SOCIAL_CHANNELS)
        .values_list('platform', flat=True)
    )
    return [channel for channel in SOCIAL_CHANNELS if channel in known]


def with_automatic_social(channels):
    """The author's channels plus every automatic social one, order preserved.

    Broadcast channels (e-mail, WhatsApp) are deliberately *not* added here:
    mailing thousands of people is an explicit act, so it stays an explicit
    choice.
    """
    merged = list(channels)
    for channel in automatic_social_channels():
        if channel not in merged:
            merged.append(channel)
    return merged

#: How `SocialPostAttempt.status` maps onto the unified delivery vocabulary.
ATTEMPT_STATUS = {
    SocialPostAttempt.Status.SENT: PublicationDelivery.Status.SUCCESS,
    SocialPostAttempt.Status.FAILED: PublicationDelivery.Status.FAILED,
    SocialPostAttempt.Status.SKIPPED: PublicationDelivery.Status.SKIPPED,
    SocialPostAttempt.Status.PENDING: PublicationDelivery.Status.PENDING,
    SocialPostAttempt.Status.PROCESSING: PublicationDelivery.Status.PROCESSING,
}


def normalise_channels(raw):
    """Accept WEBSITE, lowercase and comma-joined input; return known channels."""
    if raw in (None, ''):
        return []
    if isinstance(raw, str):
        raw = [item.strip() for item in raw.split(',') if item.strip()]
    cleaned = []
    for item in raw:
        name = str(item).upper().strip()
        if name == WEBSITE:
            name = WEB
        if name in ALL_CHANNELS and name not in cleaned:
            cleaned.append(name)
    return cleaned


def start_delivery(post, channel):
    delivery, _ = PublicationDelivery.objects.get_or_create(post=post, channel=channel)
    delivery.status = PublicationDelivery.Status.PROCESSING
    delivery.started_at = timezone.now()
    delivery.completed_at = None
    delivery.error_code = ''
    delivery.error_message = ''
    delivery.save()
    return delivery


def finish_delivery(delivery, status, detail='', **fields):
    delivery.status = status
    delivery.detail = (detail or '')[:500]
    delivery.completed_at = timezone.now()
    for key, value in fields.items():
        setattr(delivery, key, value)
    delivery.save()
    return delivery


def skip(delivery, reason, code='INCOMPATIBLE'):
    return finish_delivery(
        delivery, PublicationDelivery.Status.SKIPPED, reason,
        error_code=code, error_message=reason[:500],
    )


# --------------------------------------------------------------------------
# Self-hosted channels: the web app and the mobile app
# --------------------------------------------------------------------------

def deliver_internal(post, channel, request_user=None):
    """Make the publication visible in the app feeds.

    There is no remote provider here: publishing means making the post visible
    and recording how many concerned accounts the audience resolves to.
    Filtering per user happens at read time, in `audience.feed_queryset`.
    """
    delivery = start_delivery(post, channel)
    if not post.is_published:
        post.is_published = True
        post.published_at = post.published_at or timezone.now()
        if request_user is not None and post.published_by_id is None:
            post.published_by = request_user
        post.save(update_fields=('is_published', 'published_at', 'published_by'))

    count = audience_size(post)
    label = 'application mobile' if channel == MOBILE else 'application web'
    return finish_delivery(
        delivery, PublicationDelivery.Status.SUCCESS,
        f'Visible par {count} utilisateur(s) concerne(s) dans l’{label}.',
        recipient_count=count, success_count=count, provider='TASKFORCE',
    )


# --------------------------------------------------------------------------
# E-mail
# --------------------------------------------------------------------------

def deliver_email(post, post_url):
    """Send the e-mail version to everyone the audience resolves to.

    Addresses already written to for this publication are skipped, so running
    this twice completes a partial send instead of mailing the first half of
    the list a second time.
    """
    from .newsletter import build_message

    delivery = start_delivery(post, EMAIL)
    recipients = email_recipients(post)
    if not recipients:
        return skip(
            delivery, 'Aucun destinataire avec une adresse e-mail valide.', 'NO_RECIPIENT',
        )

    already = set(
        delivery.recipients.filter(status=RecipientDelivery.Status.SUCCESS)
        .values_list('address', flat=True)
    )
    sent = failed = 0
    for address, user, subscriber in recipients:
        if address in already:
            continue
        token = subscriber.unsubscribe_token if subscriber else None
        try:
            message, html = build_message(post, address, token)
            message.attach_alternative(html, 'text/html')
            message.send(fail_silently=False)
        except Exception as exc:  # SMTP errors differ per backend and provider
            failed += 1
            RecipientDelivery.objects.update_or_create(
                delivery=delivery, address=address,
                defaults={
                    'user': user, 'subscriber': subscriber,
                    'status': RecipientDelivery.Status.FAILED,
                    'error_code': 'SMTP_ERROR', 'error': str(exc)[:500],
                },
            )
            continue
        sent += 1
        RecipientDelivery.objects.update_or_create(
            delivery=delivery, address=address,
            defaults={
                'user': user, 'subscriber': subscriber,
                'status': RecipientDelivery.Status.SUCCESS, 'error_code': '', 'error': '',
            },
        )

    status = (
        PublicationDelivery.Status.FAILED if sent == 0
        else PublicationDelivery.Status.SUCCESS
    )
    detail = f'{sent} e-mail(s) envoye(s)'
    detail += f', {failed} echec(s).' if failed else '.'
    return finish_delivery(
        delivery, status, detail, provider='SMTP',
        recipient_count=len(recipients), success_count=sent, failure_count=failed,
        error_code='SMTP_ERROR' if sent == 0 else '',
    )


# --------------------------------------------------------------------------
# WhatsApp
# --------------------------------------------------------------------------

def deliver_whatsapp(post, post_url):
    """Send the WhatsApp adaptation: short text plus the full-publication link.

    Attachments are never pushed through the bridge — the provider does not
    reliably accept them — but nothing is lost, because the link that always
    closes the message leads to the complete publication.
    """
    from notifications.services import send_whatsapp_message

    delivery = start_delivery(post, WHATSAPP)
    if WHATSAPP not in available_channels():
        return skip(
            delivery, 'La passerelle WhatsApp n’est pas configuree sur ce serveur.',
            'PROVIDER_DISABLED',
        )

    recipients, missing = whatsapp_recipients(post)
    for user, code in missing:
        RecipientDelivery.objects.update_or_create(
            delivery=delivery, address=f'user:{user.pk}',
            defaults={
                'user': user, 'status': RecipientDelivery.Status.SKIPPED,
                'error_code': code, 'error': 'Aucun numero de telephone enregistre.',
            },
        )
    if not recipients:
        return skip(
            delivery, 'Aucun destinataire ne dispose d’un numero WhatsApp.', 'NO_RECIPIENT',
        )

    text = whatsapp_message(post, post_url)
    already = set(
        delivery.recipients.filter(status=RecipientDelivery.Status.SUCCESS)
        .values_list('address', flat=True)
    )
    sent = failed = 0
    last_code = ''
    for phone, user in recipients:
        if phone in already:
            continue
        ok, code, error = send_whatsapp_message(phone, text)
        if ok:
            sent += 1
        else:
            failed += 1
            last_code = code
        RecipientDelivery.objects.update_or_create(
            delivery=delivery, address=phone,
            defaults={
                'user': user,
                'status': (
                    RecipientDelivery.Status.SUCCESS if ok
                    else RecipientDelivery.Status.FAILED
                ),
                'error_code': code, 'error': error[:500],
            },
        )

    status = (
        PublicationDelivery.Status.FAILED if sent == 0
        else PublicationDelivery.Status.SUCCESS
    )
    detail = f'{sent} message(s) WhatsApp envoye(s)'
    detail += f', {failed} echec(s).' if failed else '.'
    if missing:
        detail += f' {len(missing)} destinataire(s) sans numero.'
    return finish_delivery(
        delivery, status, detail, provider='OPENWA',
        recipient_count=len(recipients), success_count=sent, failure_count=failed,
        error_code=last_code if sent == 0 else '',
    )


# --------------------------------------------------------------------------
# Social providers
# --------------------------------------------------------------------------

def deliver_social(post, channel, post_url, attempt=None):
    """Run one social provider and mirror its attempt into the delivery row.

    The attempt keeps the provider-level detail it has always recorded; the
    delivery is the single per-channel summary every dashboard reads.
    """
    from .models import SocialAccount
    from .social.publishers import publish_to_account

    delivery = start_delivery(post, channel)
    account = SocialAccount.objects.filter(platform=channel, is_active=True).first()
    if account is None:
        SocialPostAttempt.objects.create(
            post=post, account=None, platform=channel,
            status=SocialPostAttempt.Status.SKIPPED,
            detail=f'Aucun compte {channel} connecte.', error_code='NOT_CONNECTED',
        )
        return skip(delivery, f'Aucun compte {channel} connecte.', 'NOT_CONNECTED')

    plan = plan_destination(post, channel, connected=True)
    if not plan.available:
        SocialPostAttempt.objects.create(
            post=post, account=account, platform=channel,
            status=SocialPostAttempt.Status.SKIPPED,
            detail=plan.reason, error_code='INCOMPATIBLE',
        )
        return skip(delivery, plan.reason, 'INCOMPATIBLE')

    result = publish_to_account(post, account, post_url, plan=plan, attempt=attempt)
    succeeded = result.status == SocialPostAttempt.Status.SENT
    return finish_delivery(
        delivery,
        ATTEMPT_STATUS.get(result.status, PublicationDelivery.Status.FAILED),
        result.detail,
        provider=channel,
        external_id=result.provider_post_id or '',
        external_url=result.external_url or '',
        error_code=result.error_code or '',
        error_message='' if succeeded else (result.detail or '')[:500],
        recipient_count=1 if succeeded else 0,
        success_count=1 if succeeded else 0,
        failure_count=1 if result.status == SocialPostAttempt.Status.FAILED else 0,
        retry_count=result.retry_count,
        metadata={'attempt_id': result.pk},
    )


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------

def overall_status(deliveries):
    """The honest summary of a mixed result set."""
    states = {delivery.status for delivery in deliveries}
    success = PublicationDelivery.Status.SUCCESS in states
    failed = PublicationDelivery.Status.FAILED in states
    skipped = PublicationDelivery.Status.SKIPPED in states

    if not states:
        return PublicPost.Status.DRAFT
    if not success:
        return PublicPost.Status.FAILED
    if failed or skipped:
        return PublicPost.Status.PARTIAL
    return PublicPost.Status.PUBLISHED


def run_one(post, channel, post_url, request_user=None):
    """Dispatch a single channel. Never raises — the failure *is* the result."""
    try:
        if channel in (WEB, MOBILE):
            return deliver_internal(post, channel, request_user)
        if channel == EMAIL:
            return deliver_email(post, post_url)
        if channel == WHATSAPP:
            return deliver_whatsapp(post, post_url)
        if channel in SOCIAL_CHANNELS:
            return deliver_social(post, channel, post_url)
        delivery = start_delivery(post, channel)
        return skip(delivery, f'Canal {channel} non pris en charge.', 'UNSUPPORTED_CHANNEL')
    except Exception as exc:  # noqa: BLE001 — one channel must never break the others
        logger.exception('Channel %s failed for post=%s', channel, post.pk)
        delivery, _ = PublicationDelivery.objects.get_or_create(post=post, channel=channel)
        return finish_delivery(
            delivery, PublicationDelivery.Status.FAILED, str(exc)[:400],
            error_code='UNEXPECTED_ERROR', error_message=str(exc)[:500],
        )


def distribute(post, channels, post_url, request_user=None):
    """Run every selected channel, each isolated from the others.

    Channels that already succeeded are left alone, so calling this twice
    completes a partial publication instead of duplicating it.
    """
    channels = normalise_channels(channels) or [WEB, MOBILE]
    done = set(
        post.deliveries.filter(status=PublicationDelivery.Status.SUCCESS)
        .values_list('channel', flat=True)
    )

    results = []
    for channel in channels:
        if channel in done:
            results.append(post.deliveries.get(channel=channel))
            continue
        results.append(run_one(post, channel, post_url, request_user))

    post.channels = channels
    # Deliberately a fresh queryset rather than `post.deliveries.all()`: the
    # viewset prefetches `deliveries` before publishing, so the related
    # manager's cache still holds the state from *before* this run and would
    # report a freshly published post as a draft.
    post.status = overall_status(PublicationDelivery.objects.filter(post=post))
    post.save(update_fields=('channels', 'status'))
    return results
