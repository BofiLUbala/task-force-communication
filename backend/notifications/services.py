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


def send_whatsapp(phone_number, message):
    if not settings.OPENWA_ENABLED:
        return
    try:
        requests.post(
            f'{settings.OPENWA_API_URL}/sendText',
            json={'to': phone_number, 'content': message},
            headers={'Authorization': f'Bearer {settings.OPENWA_API_KEY}'},
            timeout=10,
        )
    except requests.RequestException:
        logger.exception('Échec envoi WhatsApp (open-wa)')


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
