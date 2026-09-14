"""Signup slots, invitations, revocation and account purging."""
from urllib.parse import parse_qs, urlparse

from django.core import mail
from django.test import override_settings
from rest_framework.test import APITestCase

from content.models import PublicPost, Report

from .models import User

STRONG_PASSWORD = 'A-Strong-pass-482!'


def invitation_token(message):
    link = next(line for line in message.body.splitlines() if 'activation-compte?token=' in line)
    return parse_qs(urlparse(link).query)['token'][0]


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class PublicSignupSlotTests(APITestCase):
    def register(self, email):
        return self.client.post('/api/auth/register/', {
            'first_name': 'Test', 'last_name': 'User', 'email': email,
            'password': STRONG_PASSWORD,
        })

    def test_signup_fills_one_super_admin_then_two_hierarchies_then_closes(self):
        self.assertEqual(self.client.get('/api/auth/registration-status/').data['role'], 'SUPER_ADMIN')

        first = self.register('boss@example.com')
        self.assertEqual(first.status_code, 201)
        self.assertEqual(User.objects.get(email='boss@example.com').role, User.Role.SUPER_ADMIN)

        # The super admin post holds a single seat; the next one is a lead.
        self.assertEqual(self.client.get('/api/auth/registration-status/').data['role'], 'HIERARCHY')

        second = self.register('chief@example.com')
        self.assertEqual(second.status_code, 201)
        self.assertEqual(User.objects.get(email='chief@example.com').role, User.Role.HIERARCHY)

        # Two operational leads, so the field is never left unstaffed.
        self.assertEqual(self.client.get('/api/auth/registration-status/').data['role'], 'HIERARCHY')

        third = self.register('deputy@example.com')
        self.assertEqual(third.status_code, 201)
        self.assertEqual(User.objects.get(email='deputy@example.com').role, User.Role.HIERARCHY)

        status_now = self.client.get('/api/auth/registration-status/').data
        self.assertFalse(status_now['open'])

        fourth = self.register('someone@example.com')
        self.assertEqual(fourth.status_code, 403)
        self.assertFalse(User.objects.filter(email='someone@example.com').exists())

    def test_the_platform_never_holds_more_than_three_staff_accounts(self):
        self.register('boss@example.com')
        self.register('chief@example.com')
        self.register('deputy@example.com')
        self.register('intruder@example.com')

        staff = User.objects.filter(role__in=User.STAFF_ROLES)
        self.assertEqual(staff.count(), 3)
        self.assertEqual(staff.filter(role=User.Role.SUPER_ADMIN).count(), 1)
        self.assertEqual(staff.filter(role=User.Role.HIERARCHY).count(), 2)

    def test_self_registered_account_stays_pending_until_email_confirmed(self):
        self.register('boss@example.com')
        user = User.objects.get(email='boss@example.com')
        self.assertEqual(user.status, User.AccountStatus.PENDING_EMAIL)
        self.assertFalse(user.is_active)

    def test_hierarchy_slot_reopens_once_the_account_is_deleted(self):
        self.register('boss@example.com')
        self.register('chief@example.com')
        User.objects.get(email='chief@example.com').delete()
        self.assertEqual(self.client.get('/api/auth/registration-status/').data['role'], 'HIERARCHY')


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class InvitationTests(APITestCase):
    def setUp(self):
        self.super_admin = User.objects.create_user(
            username='boss@example.com', email='boss@example.com', password=STRONG_PASSWORD,
            role=User.Role.SUPER_ADMIN, status=User.AccountStatus.ACTIVE, first_name='Grand', last_name='Patron',
        )
        self.hierarchy = User.objects.create_user(
            username='chief@example.com', email='chief@example.com', password=STRONG_PASSWORD,
            role=User.Role.HIERARCHY, status=User.AccountStatus.ACTIVE, first_name='Responsable', last_name='Un',
        )

    def test_hierarchy_invites_an_agent_who_sets_their_own_password(self):
        self.client.force_authenticate(self.hierarchy)
        response = self.client.post('/api/auth/invitations/', {'email': 'agent@example.com'})
        self.assertEqual(response.status_code, 201)

        invited = User.objects.get(email='agent@example.com')
        self.assertEqual(invited.role, User.Role.AGENT)
        self.assertEqual(invited.status, User.AccountStatus.INVITED)
        self.assertFalse(invited.is_active)
        self.assertFalse(invited.has_usable_password())
        self.assertEqual(invited.invited_by, self.hierarchy)

        token = invitation_token(mail.outbox[-1])
        self.client.force_authenticate(None)

        preview = self.client.get('/api/auth/invitations/detail/', {'token': token})
        self.assertEqual(preview.data['email'], 'agent@example.com')

        accepted = self.client.post('/api/auth/invitations/accept/', {
            'token': token, 'first_name': 'Jean', 'last_name': 'Terrain', 'password': STRONG_PASSWORD,
        })
        self.assertEqual(accepted.status_code, 200)

        invited.refresh_from_db()
        self.assertTrue(invited.is_active)
        self.assertEqual(invited.status, User.AccountStatus.ACTIVE)
        self.assertEqual(invited.first_name, 'Jean')

        login = self.client.post('/api/auth/login/', {'username': 'agent@example.com', 'password': STRONG_PASSWORD})
        self.assertEqual(login.status_code, 200)

        replay = self.client.post('/api/auth/invitations/accept/', {'token': token, 'password': STRONG_PASSWORD})
        self.assertEqual(replay.status_code, 400)

    def test_super_admin_may_invite_a_second_hierarchy_but_not_a_third(self):
        self.client.force_authenticate(self.super_admin)

        second = self.client.post('/api/auth/invitations/', {'email': 'deputy@example.com'})
        self.assertEqual(second.status_code, 201, second.data)
        self.assertEqual(User.objects.get(email='deputy@example.com').role, User.Role.HIERARCHY)

        third = self.client.post('/api/auth/invitations/', {'email': 'other-chief@example.com'})
        self.assertEqual(third.status_code, 400)
        self.assertEqual(third.data['code'], 'ROLE_FULL')
        self.assertFalse(User.objects.filter(email='other-chief@example.com').exists())

        # Freeing a seat reopens exactly one place.
        self.hierarchy.delete()
        allowed = self.client.post('/api/auth/invitations/', {'email': 'other-chief@example.com'})
        self.assertEqual(allowed.status_code, 201)
        self.assertEqual(User.objects.filter(role=User.Role.HIERARCHY).count(), 2)

    def test_a_pending_invitation_holds_its_seat(self):
        """Two people must never be invited onto the same post and find out
        about the clash only when the second one activates."""
        self.client.force_authenticate(self.super_admin)
        self.client.post('/api/auth/invitations/', {'email': 'deputy@example.com'})

        invited = User.objects.get(email='deputy@example.com')
        self.assertEqual(invited.status, User.AccountStatus.INVITED)
        self.assertFalse(invited.is_active)

        refused = self.client.post('/api/auth/invitations/', {'email': 'third@example.com'})
        self.assertEqual(refused.status_code, 400)
        self.assertEqual(refused.data['code'], 'ROLE_FULL')

    def test_the_dashboard_reports_the_remaining_seats(self):
        self.client.force_authenticate(self.super_admin)
        stats = self.client.get('/api/auth/users/overview/').data
        self.assertEqual(stats['post_capacity'], 2)
        self.assertEqual(stats['post_occupied'], 1)
        self.assertEqual(stats['post_remaining'], 1)
        self.assertTrue(stats['post_is_vacant'])

        self.client.post('/api/auth/invitations/', {'email': 'deputy@example.com'})
        full = self.client.get('/api/auth/users/overview/').data
        self.assertEqual(full['post_remaining'], 0)
        self.assertFalse(full['post_is_vacant'])

    def test_agents_cannot_invite_anyone(self):
        agent = User.objects.create_user(
            username='agent@example.com', email='agent@example.com', password=STRONG_PASSWORD,
            role=User.Role.AGENT, status=User.AccountStatus.ACTIVE,
        )
        self.client.force_authenticate(agent)
        self.assertEqual(self.client.post('/api/auth/invitations/', {'email': 'x@example.com'}).status_code, 403)
        self.assertEqual(self.client.get('/api/auth/users/').status_code, 403)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AccountManagementTests(APITestCase):
    def setUp(self):
        self.super_admin = User.objects.create_user(
            username='boss@example.com', email='boss@example.com', password=STRONG_PASSWORD,
            role=User.Role.SUPER_ADMIN, status=User.AccountStatus.ACTIVE,
        )
        self.hierarchy = User.objects.create_user(
            username='chief@example.com', email='chief@example.com', password=STRONG_PASSWORD,
            role=User.Role.HIERARCHY, status=User.AccountStatus.ACTIVE,
        )
        self.agent = User.objects.create_user(
            username='agent@example.com', email='agent@example.com', password=STRONG_PASSWORD,
            role=User.Role.AGENT, status=User.AccountStatus.ACTIVE,
        )

    def test_each_post_only_sees_the_accounts_it_owns(self):
        self.client.force_authenticate(self.hierarchy)
        listed = {row['email'] for row in self.client.get('/api/auth/users/').data['results']}
        self.assertEqual(listed, {'agent@example.com'})

        self.client.force_authenticate(self.super_admin)
        listed = {row['email'] for row in self.client.get('/api/auth/users/').data['results']}
        self.assertEqual(listed, {'chief@example.com'})

    def test_revoking_an_agent_blocks_login_until_reactivated(self):
        self.client.force_authenticate(self.hierarchy)
        self.assertEqual(self.client.post(f'/api/auth/users/{self.agent.id}/revoke/').status_code, 200)

        self.agent.refresh_from_db()
        self.assertEqual(self.agent.status, User.AccountStatus.REVOKED)
        self.assertFalse(self.agent.is_active)

        self.client.force_authenticate(None)
        blocked = self.client.post('/api/auth/login/', {'username': 'agent@example.com', 'password': STRONG_PASSWORD})
        self.assertEqual(blocked.status_code, 401)

        self.client.force_authenticate(self.hierarchy)
        self.assertEqual(self.client.post(f'/api/auth/users/{self.agent.id}/reactivate/').status_code, 200)

        self.client.force_authenticate(None)
        restored = self.client.post('/api/auth/login/', {'username': 'agent@example.com', 'password': STRONG_PASSWORD})
        self.assertEqual(restored.status_code, 200)

    def test_purging_an_agent_removes_their_reports_and_publications(self):
        Report.objects.create(submitted_by=self.agent, title='Incident Gombe')
        PublicPost.objects.create(
            title='Communiqué', slug='communique', category=PublicPost.Category.COMMUNIQUE,
            body='Texte', published_by=self.agent, is_published=True,
        )

        self.client.force_authenticate(self.hierarchy)
        response = self.client.delete(f'/api/auth/users/{self.agent.id}/purge/')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email='agent@example.com').exists())
        self.assertEqual(Report.objects.count(), 0)
        self.assertEqual(PublicPost.objects.count(), 0)

    def test_hierarchy_cannot_touch_the_super_admin(self):
        self.client.force_authenticate(self.hierarchy)
        self.assertEqual(self.client.post(f'/api/auth/users/{self.super_admin.id}/revoke/').status_code, 404)
        self.assertEqual(self.client.delete(f'/api/auth/users/{self.super_admin.id}/purge/').status_code, 404)
        self.assertTrue(User.objects.filter(email='boss@example.com').exists())

    def test_super_admin_can_revoke_the_hierarchy(self):
        self.client.force_authenticate(self.super_admin)
        self.assertEqual(self.client.post(f'/api/auth/users/{self.hierarchy.id}/revoke/').status_code, 200)
        self.hierarchy.refresh_from_db()
        self.assertEqual(self.hierarchy.status, User.AccountStatus.REVOKED)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class PurgedAccountSessionTests(APITestCase):
    """A browser left open by someone whose account was purged must be told
    to sign in again, not met with a server error."""

    def test_refreshing_a_purged_account_returns_401(self):
        agent = User.objects.create_user(
            username='agent@example.com', email='agent@example.com', password=STRONG_PASSWORD,
            role=User.Role.AGENT, status=User.AccountStatus.ACTIVE,
        )
        tokens = self.client.post(
            '/api/auth/login/', {'username': 'agent@example.com', 'password': STRONG_PASSWORD},
        ).data
        agent.delete()

        response = self.client.post('/api/auth/login/refresh/', {'refresh': tokens['refresh']})
        self.assertEqual(response.status_code, 401)

    def test_refreshing_a_revoked_account_returns_401(self):
        agent = User.objects.create_user(
            username='agent@example.com', email='agent@example.com', password=STRONG_PASSWORD,
            role=User.Role.AGENT, status=User.AccountStatus.ACTIVE,
        )
        tokens = self.client.post(
            '/api/auth/login/', {'username': 'agent@example.com', 'password': STRONG_PASSWORD},
        ).data
        agent.is_active = False
        agent.save(update_fields=('is_active',))

        response = self.client.post('/api/auth/login/refresh/', {'refresh': tokens['refresh']})
        self.assertEqual(response.status_code, 401)
