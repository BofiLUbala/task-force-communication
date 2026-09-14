"""Sign-in accepts either the username or the account's e-mail address."""
from rest_framework.test import APITestCase

from .models import User

STRONG_PASSWORD = 'A-Strong-pass-482!'


class LoginIdentifierTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='admin', email='Chief@taskforce.rdc.cd',
            password=STRONG_PASSWORD, role=User.Role.HIERARCHY,
        )

    def login(self, identifier, password=STRONG_PASSWORD):
        return self.client.post(
            '/api/auth/login/', {'username': identifier, 'password': password}, format='json',
        )

    def test_username_still_works(self):
        response = self.login('admin')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['role'], 'HIERARCHY')

    def test_email_is_accepted_and_case_insensitive(self):
        for identifier in ('Chief@taskforce.rdc.cd', 'chief@taskforce.rdc.cd', '  CHIEF@TASKFORCE.RDC.CD  '):
            with self.subTest(identifier=identifier):
                self.assertEqual(self.login(identifier).status_code, 200)

    def test_wrong_password_is_still_refused(self):
        self.assertEqual(self.login('chief@taskforce.rdc.cd', 'not-the-password').status_code, 401)

    def test_unknown_email_is_refused(self):
        self.assertEqual(self.login('nobody@taskforce.rdc.cd').status_code, 401)

    def test_username_wins_over_another_account_email(self):
        """An address used as one account's username must not sign in another."""
        User.objects.create_user(
            username='shared@taskforce.rdc.cd', email='other@taskforce.rdc.cd',
            password=STRONG_PASSWORD, role=User.Role.AGENT,
        )
        self.user.email = 'shared@taskforce.rdc.cd'
        self.user.save(update_fields=['email'])

        response = self.login('shared@taskforce.rdc.cd')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['user_id'], User.objects.get(username='shared@taskforce.rdc.cd').id)

    def test_ambiguous_email_is_refused(self):
        """`email` has no unique constraint — never guess between two accounts."""
        User.objects.create_user(
            username='deputy', email='chief@taskforce.rdc.cd',
            password=STRONG_PASSWORD, role=User.Role.AGENT,
        )
        self.assertEqual(self.login('chief@taskforce.rdc.cd').status_code, 401)

    def test_inactive_account_is_refused(self):
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])
        self.assertEqual(self.login('chief@taskforce.rdc.cd').status_code, 401)
