import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import OneTimeToken


def _hash_token(raw_token):
    return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()


def create_one_time_token(user, purpose, lifetime):
    OneTimeToken.objects.filter(user=user, purpose=purpose, used_at__isnull=True).update(used_at=timezone.now())
    raw_token = secrets.token_urlsafe(48)
    OneTimeToken.objects.create(
        user=user,
        purpose=purpose,
        token_hash=_hash_token(raw_token),
        expires_at=timezone.now() + lifetime,
    )
    return raw_token


def consume_one_time_token(raw_token, purpose):
    try:
        token = OneTimeToken.objects.select_for_update().select_related('user').get(
            token_hash=_hash_token(raw_token),
            purpose=purpose,
            used_at__isnull=True,
        )
    except OneTimeToken.DoesNotExist:
        return None

    if token.expires_at <= timezone.now():
        return None

    token.used_at = timezone.now()
    token.save(update_fields=('used_at',))
    return token.user


def send_verification_email(user):
    raw_token = create_one_time_token(user, OneTimeToken.Purpose.EMAIL_VERIFICATION, timedelta(hours=48))
    link = f"{settings.FRONTEND_URL}/confirmation-email?token={raw_token}"
    send_mail(
        'Activez votre compte Task Force Présidentielle',
        f"Bonjour {user.first_name or user.last_name or 'Agent'},\n\n"
        "Confirmez votre adresse e-mail en utilisant le lien ci-dessous. "
        "Ce lien expire dans 48 heures et ne peut être utilisé qu’une seule fois.\n\n"
        f"{link}\n\nSi vous n’êtes pas à l’origine de cette inscription, ignorez ce message.",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )


def send_password_reset_email(user):
    raw_token = create_one_time_token(user, OneTimeToken.Purpose.PASSWORD_RESET, timedelta(hours=1))
    link = f"{settings.FRONTEND_URL}/nouveau-mot-de-passe?token={raw_token}"
    send_mail(
        'Réinitialisation de votre mot de passe',
        "Une demande de réinitialisation a été reçue pour votre compte. "
        "Ce lien expire dans une heure et ne peut être utilisé qu’une seule fois.\n\n"
        f"{link}\n\nSi vous n’avez pas fait cette demande, ignorez ce message.",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )
