import logging

import requests
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _hierarchy_emails():
    from accounts.models import User
    return list(
        User.objects.filter(role=User.Role.HIERARCHY, is_active=True)
        .exclude(email='')
        .values_list('email', flat=True)
    )


def _hierarchy_phone_numbers():
    from accounts.models import User
    return list(
        User.objects.filter(role=User.Role.HIERARCHY, is_active=True)
        .exclude(phone_number='')
        .values_list('phone_number', flat=True)
    )


def send_expo_push(expo_token, title, body):
    if not expo_token:
        return
    try:
        requests.post(
            settings.EXPO_PUSH_URL,
            json={'to': expo_token, 'title': title, 'body': body, 'sound': 'default'},
            timeout=10,
        )
    except requests.RequestException:
        logger.exception('Échec envoi push Expo')


def send_whatsapp_message(phone_number, message, timeout=15):
    """Send one WhatsApp message and report what happened.

    Returns `(ok, error_code, error_message)`. Publication delivery needs the
    outcome per recipient, so unlike the fire-and-forget notification helper
    below this one never swallows the failure.
    """
    if not settings.OPENWA_ENABLED:
        return False, 'PROVIDER_DISABLED', 'La passerelle WhatsApp n’est pas activée.'
    if not phone_number:
        return False, 'NO_PHONE_NUMBER', 'Aucun numéro de téléphone.'

    try:
        response = requests.post(
            f'{settings.OPENWA_API_URL}/sendText',
            json={'to': phone_number, 'content': message},
            headers={'Authorization': f'Bearer {settings.OPENWA_API_KEY}'},
            timeout=timeout,
        )
    except requests.Timeout:
        return False, 'TIMEOUT', 'La passerelle WhatsApp n’a pas répondu à temps.'
    except requests.RequestException as exc:
        logger.warning('WhatsApp network failure: %s', exc)
        return False, 'PROVIDER_UNAVAILABLE', 'Passerelle WhatsApp injoignable.'

    if response.status_code >= 500:
        return False, 'PROVIDER_UNAVAILABLE', f'Passerelle WhatsApp en erreur (HTTP {response.status_code}).'
    if response.status_code in (400, 404, 422):
        return False, 'INVALID_RECIPIENT', f'Destinataire refusé par la passerelle (HTTP {response.status_code}).'
    if response.status_code >= 400:
        return False, 'PROVIDER_ERROR', f'Envoi WhatsApp refusé (HTTP {response.status_code}).'
    return True, '', ''


def send_whatsapp(phone_number, message):
    """Fire-and-forget notification send; failures are logged, never raised."""
    ok, _, error = send_whatsapp_message(phone_number, message, timeout=10)
    if not ok and error:
        logger.info('WhatsApp notification not delivered: %s', error)
    return ok


def notify_hierarchy_new_report(report):
    subject = f'Nouveau rapport en attente : {report.title}'
    message = (
        f'{report.submitted_by.get_full_name() or report.submitted_by.username} '
        f'a soumis un nouveau rapport "{report.title}" à valider.'
    )
    emails = _hierarchy_emails()
    if emails:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, emails, fail_silently=True)

    for phone in _hierarchy_phone_numbers():
        send_whatsapp(phone, message)


def notify_agent_report_reviewed(report):
    agent = report.submitted_by
    verb = 'validé' if report.status == report.Status.VALIDATED else 'rejeté'
    subject = f'Votre rapport "{report.title}" a été {verb}'
    message = f'Votre rapport "{report.title}" a été {verb} par la hiérarchie.'
    if report.review_comment:
        message += f'\nCommentaire : {report.review_comment}'

    if agent.email:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [agent.email], fail_silently=True)

    send_expo_push(agent.expo_push_token, subject, message)
    send_whatsapp(agent.phone_number, message)
