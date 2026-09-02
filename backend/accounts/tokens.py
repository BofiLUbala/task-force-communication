import hashlib
import secrets
from datetime import timedelta
from email.mime.image import MIMEImage
from html import escape
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from .models import OneTimeToken


def _send_branded_email(subject, recipient, heading, message, button_label, link, notice):
    logo_path = Path(settings.BASE_DIR).parent / 'web-app' / 'public' / 'logo-taskforce.jpg'
    logo_source = 'cid:taskforce-logo' if logo_path.exists() else f'{settings.FRONTEND_URL}/logo-taskforce.jpg'
    plain_text = f'{heading}\n\n{message}\n\n{button_label}: {link}\n\n{notice}'
    html = f'''<!doctype html>
<html lang="fr"><body style="margin:0;background:#f2f5fb;font-family:Arial,sans-serif;color:#14233b">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f2f5fb;padding:32px 12px">
    <tr><td align="center">
      <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="max-width:600px;width:100%;background:#ffffff;border-radius:14px;overflow:hidden;box-shadow:0 8px 30px rgba(0,47,106,.12)">
        <tr><td align="center" style="background:#eef4ff;padding:24px"><img src="{logo_source}" width="320" alt="Task Force Présidentielle" style="display:block;max-width:100%;height:auto"></td></tr>
        <tr><td style="padding:34px 38px">
          <h1 style="margin:0 0 16px;color:#003b7a;font-size:25px;line-height:1.25">{escape(heading)}</h1>
          <p style="margin:0 0 26px;color:#4a5870;font-size:16px;line-height:1.65">{escape(message)}</p>
          <table role="presentation" cellspacing="0" cellpadding="0"><tr><td style="border-radius:8px;background:#f4cf00">
            <a href="{escape(link)}" style="display:inline-block;padding:14px 24px;color:#003b7a;text-decoration:none;font-size:16px;font-weight:bold">{escape(button_label)}</a>
          </td></tr></table>
          <p style="margin:26px 0 0;color:#738097;font-size:13px;line-height:1.55">Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :<br><a href="{escape(link)}" style="color:#0759a8;word-break:break-all">{escape(link)}</a></p>
        </td></tr>
        <tr><td style="padding:20px 38px;background:#003b7a;color:#d9e5f5;font-size:12px;line-height:1.5">{escape(notice)}<br><strong>Task Force Présidentielle — RDC</strong></td></tr>
      </table>
    </td></tr>
  </table>
</body></html>'''
    email = EmailMultiAlternatives(subject, plain_text, settings.DEFAULT_FROM_EMAIL, [recipient])
    email.attach_alternative(html, 'text/html')
    if logo_path.exists():
        with logo_path.open('rb') as logo_file:
            logo = MIMEImage(logo_file.read(), _subtype='jpeg')
        logo.add_header('Content-ID', '<taskforce-logo>')
        logo.add_header('Content-Disposition', 'inline', filename='logo-taskforce.jpg')
        email.attach(logo)
    email.send(fail_silently=False)


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
    name = user.first_name or user.last_name or 'Agent'
    _send_branded_email(
        'Activez votre compte Task Force Présidentielle', user.email,
        f'Bienvenue, {name}',
        'Votre compte agent a bien été créé. Confirmez maintenant votre adresse e-mail pour activer votre accès. Ce lien est valable pendant 48 heures et ne fonctionne qu’une seule fois.',
        'Activer mon compte', link,
        'Vous n’êtes pas à l’origine de cette inscription ? Ignorez simplement ce message.',
    )


def send_password_reset_email(user):
    raw_token = create_one_time_token(user, OneTimeToken.Purpose.PASSWORD_RESET, timedelta(hours=1))
    link = f"{settings.FRONTEND_URL}/nouveau-mot-de-passe?token={raw_token}"
    _send_branded_email(
        'Réinitialisation de votre mot de passe', user.email,
        'Réinitialisez votre mot de passe',
        'Nous avons reçu une demande de modification du mot de passe de votre compte. Utilisez le bouton ci-dessous dans un délai d’une heure. Le lien ne fonctionne qu’une seule fois.',
        'Choisir un nouveau mot de passe', link,
        'Vous n’avez pas demandé cette modification ? Ignorez ce message ; votre mot de passe actuel reste inchangé.',
    )
