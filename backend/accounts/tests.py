from datetime import timedelta
import hashlib
from urllib.parse import parse_qs, urlparse

from django.core import mail
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import OneTimeToken, User


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AccountActivationTests(APITestCase):
    def test_registration_requires_one_time_email_confirmation(self):
        response = self.client.post('/api/auth/register/', {
            'first_name': 'Jean',
            'last_name': 'Agent',
            'email': 'jean@example.com',
            'phone_number': '+243810000000',
            'password': 'A-Strong-pass-482!',
        })
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email='jean@example.com')
        self.assertFalse(user.is_active)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(len(mail.outbox[0].alternatives), 1)
        self.assertIn('Activer mon compte', mail.outbox[0].alternatives[0].content)
        self.assertTrue(any(attachment.get('Content-ID') == '<taskforce-logo>' for attachment in mail.outbox[0].attachments))

        link = next(line for line in mail.outbox[0].body.splitlines() if 'confirmation-email?token=' in line)
        token = parse_qs(urlparse(link).query)['token'][0]
        first_use = self.client.post('/api/auth/verify-email/', {'token': token})
        second_use = self.client.post('/api/auth/verify-email/', {'token': token})

        self.assertEqual(first_use.status_code, 200)
        self.assertEqual(second_use.status_code, 400)
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_expired_confirmation_is_rejected(self):
        user = User.objects.create_user(username='expired@example.com', email='expired@example.com', is_active=False)
        raw_token = 'expired-token'
        OneTimeToken.objects.create(
            user=user,
            purpose=OneTimeToken.Purpose.EMAIL_VERIFICATION,
            token_hash=hashlib.sha256(raw_token.encode('utf-8')).hexdigest(),
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        response = self.client.post('/api/auth/verify-email/', {'token': raw_token})
        self.assertEqual(response.status_code, 400)
        user.refresh_from_db()
        self.assertFalse(user.is_active)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class PasswordResetTests(APITestCase):
    def test_password_reset_link_is_single_use(self):
        user = User.objects.create_user(username='agent@example.com', email='agent@example.com', password='Old-pass-482!')
        request = self.client.post('/api/auth/password-reset/', {'email': user.email})
        self.assertEqual(request.status_code, 200)
        self.assertIn('Choisir un nouveau mot de passe', mail.outbox[0].alternatives[0].content)
        link = next(line for line in mail.outbox[0].body.splitlines() if 'nouveau-mot-de-passe?token=' in line)
        token = parse_qs(urlparse(link).query)['token'][0]

        first_use = self.client.post('/api/auth/password-reset/confirm/', {'token': token, 'password': 'New-pass-593!'})
        second_use = self.client.post('/api/auth/password-reset/confirm/', {'token': token, 'password': 'Another-pass-604!'})

        self.assertEqual(first_use.status_code, 200)
        self.assertEqual(second_use.status_code, 400)
        user.refresh_from_db()
        self.assertTrue(user.check_password('New-pass-593!'))

# Create your tests here.
