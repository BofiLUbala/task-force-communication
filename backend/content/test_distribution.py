"""Audience targeting and multi-channel distribution.

These tests exist to prove the two claims the product rests on: that a
publication reaches exactly the people it was addressed to, and that each
channel succeeds or fails on its own without dragging the others with it.

No provider is contacted. LinkedIn, YouTube and the WhatsApp bridge are
patched at their network boundary, because a test that really posted to
LinkedIn would be a test that cannot be run twice.
"""
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User

from .channels import distribute
from .models import (
    PublicationDelivery,
    PublicationRead,
    PublicMedia,
    PublicPost,
    RecipientDelivery,
    SocialAccount,
    SocialPostAttempt,
)


def make_user(username, role=User.Role.AGENT, **extra):
    return User.objects.create_user(
        username=username,
        password='motdepasse-solide-1',
        email=extra.pop('email', f'{username}@taskforce.cd'),
        role=role,
        status=User.AccountStatus.ACTIVE,
        **extra,
    )


def make_post(**extra):
    extra.setdefault('title', 'Opération d’assainissement')
    extra.setdefault('slug', extra['title'].lower().replace(' ', '-').replace('’', ''))
    extra.setdefault('category', PublicPost.Category.COMMUNIQUE)
    extra.setdefault('body', '<p>Le déploiement commence lundi.</p>')
    extra.setdefault('is_published', True)
    return PublicPost.objects.create(**extra)


class AudienceResolutionTests(TestCase):
    """Who a publication resolves to, per audience mode."""

    @classmethod
    def setUpTestData(cls):
        cls.chief = make_user('chief', User.Role.HIERARCHY)
        cls.kin = make_user('kin_agent', unit='Kinshasa')
        cls.lub = make_user('lub_agent', unit='Lubumbashi')
        cls.no_contact = make_user('quiet_agent', email='', unit='Kinshasa')

    def test_everyone_reaches_all_active_accounts(self):
        post = make_post(audience=PublicPost.Audience.EVERYONE)
        from .audience import resolve_users

        self.assertEqual(resolve_users(post).count(), 4)

    def test_all_agents_excludes_the_hierarchy(self):
        post = make_post(audience=PublicPost.Audience.ALL_AGENTS)
        from .audience import resolve_users

        names = set(resolve_users(post).values_list('username', flat=True))
        self.assertEqual(names, {'kin_agent', 'lub_agent', 'quiet_agent'})

    def test_hierarchy_only_excludes_every_agent(self):
        post = make_post(audience=PublicPost.Audience.HIERARCHY_ONLY)
        from .audience import resolve_users

        self.assertEqual(
            set(resolve_users(post).values_list('username', flat=True)), {'chief'},
        )

    def test_specific_group_matches_the_unit(self):
        post = make_post(
            audience=PublicPost.Audience.SPECIFIC_GROUP, audience_unit='Kinshasa',
        )
        from .audience import resolve_users

        self.assertEqual(
            set(resolve_users(post).values_list('username', flat=True)),
            {'kin_agent', 'quiet_agent'},
        )

    def test_specific_users_matches_only_the_named_accounts(self):
        post = make_post(audience=PublicPost.Audience.SPECIFIC_USERS)
        post.audience_users.set([self.lub])
        from .audience import resolve_users

        self.assertEqual(
            set(resolve_users(post).values_list('username', flat=True)), {'lub_agent'},
        )

    def test_inactive_accounts_are_never_targeted(self):
        self.lub.is_active = False
        self.lub.save(update_fields=('is_active',))
        post = make_post(audience=PublicPost.Audience.ALL_AGENTS)
        from .audience import resolve_users

        self.assertNotIn('lub_agent', set(resolve_users(post).values_list('username', flat=True)))


class FeedVisibilityTests(TestCase):
    """The feed is where audience stops being a label and becomes a rule."""

    def setUp(self):
        self.chief = make_user('chief', User.Role.HIERARCHY)
        self.agent = make_user('agent', unit='Kinshasa')
        self.other = make_user('other', unit='Matadi')
        self.client = APIClient()

        self.public = make_post(
            title='Communiqué public', slug='communique-public',
            audience=PublicPost.Audience.EVERYONE, published_by=self.chief,
        )
        self.secret = make_post(
            title='Note interne', slug='note-interne',
            audience=PublicPost.Audience.HIERARCHY_ONLY, published_by=self.chief,
        )
        self.kinshasa = make_post(
            title='Consigne Kinshasa', slug='consigne-kinshasa',
            audience=PublicPost.Audience.SPECIFIC_GROUP, audience_unit='Kinshasa',
            published_by=self.chief,
        )

    def feed_slugs(self, user):
        self.client.force_authenticate(user)
        response = self.client.get('/api/publications/feed/')
        self.assertEqual(response.status_code, 200)
        return {row['slug'] for row in response.data['results']}

    def test_agent_never_sees_a_hierarchy_only_publication(self):
        slugs = self.feed_slugs(self.agent)
        self.assertIn('communique-public', slugs)
        self.assertNotIn('note-interne', slugs)

    def test_agent_sees_a_publication_aimed_at_their_unit(self):
        self.assertIn('consigne-kinshasa', self.feed_slugs(self.agent))

    def test_agent_from_another_unit_does_not(self):
        self.assertNotIn('consigne-kinshasa', self.feed_slugs(self.other))

    def test_hierarchy_sees_everything(self):
        slugs = self.feed_slugs(self.chief)
        self.assertEqual(slugs, {'communique-public', 'note-interne', 'consigne-kinshasa'})

    def test_specific_user_targeting_reaches_exactly_that_user(self):
        targeted = make_post(
            title='Convocation', slug='convocation',
            audience=PublicPost.Audience.SPECIFIC_USERS, published_by=self.chief,
        )
        targeted.audience_users.set([self.other])
        self.assertIn('convocation', self.feed_slugs(self.other))
        self.assertNotIn('convocation', self.feed_slugs(self.agent))

    def test_hierarchy_only_detail_is_refused_not_merely_hidden(self):
        """The protection must survive someone calling the endpoint directly."""
        self.client.force_authenticate(self.agent)
        response = self.client.get('/api/publications/note-interne/')
        self.assertEqual(response.status_code, 404)

    def test_anonymous_public_site_only_sees_everyone_publications(self):
        self.client.force_authenticate(None)
        response = self.client.get('/api/posts/')
        slugs = {row['slug'] for row in response.data['results']}
        self.assertEqual(slugs, {'communique-public'})

    def test_drafts_never_appear_in_the_feed(self):
        make_post(
            title='Brouillon', slug='brouillon', is_published=False,
            audience=PublicPost.Audience.EVERYONE, published_by=self.chief,
        )
        self.assertNotIn('brouillon', self.feed_slugs(self.agent))


class ReadStateTests(TestCase):
    def setUp(self):
        self.agent = make_user('agent')
        self.post = make_post(audience=PublicPost.Audience.EVERYONE)
        self.client = APIClient()
        self.client.force_authenticate(self.agent)

    def test_feed_reports_unread_then_read(self):
        response = self.client.get('/api/publications/feed/')
        self.assertEqual(response.data['unread_count'], 1)
        self.assertFalse(response.data['results'][0]['is_read'])

        self.client.post(f'/api/publications/{self.post.slug}/mark-read/')
        response = self.client.get('/api/publications/feed/')
        self.assertEqual(response.data['unread_count'], 0)
        self.assertTrue(response.data['results'][0]['is_read'])

    def test_marking_read_twice_creates_one_row(self):
        self.client.post(f'/api/publications/{self.post.slug}/mark-read/')
        self.client.post(f'/api/publications/{self.post.slug}/mark-read/')
        self.assertEqual(PublicationRead.objects.filter(post=self.post).count(), 1)

    def test_unread_filter_hides_what_was_already_opened(self):
        self.client.post(f'/api/publications/{self.post.slug}/mark-read/')
        response = self.client.get('/api/publications/feed/?unread=1')
        self.assertEqual(response.data['results'], [])


class InternalChannelTests(TestCase):
    def setUp(self):
        self.chief = make_user('chief', User.Role.HIERARCHY)
        make_user('agent_one')
        make_user('agent_two')
        self.post = make_post(
            is_published=False, audience=PublicPost.Audience.ALL_AGENTS,
            published_by=self.chief,
        )

    def test_web_and_mobile_publish_and_count_the_audience(self):
        deliveries = distribute(self.post, ['WEB', 'MOBILE'], 'http://x/p/1', self.chief)
        self.post.refresh_from_db()

        self.assertTrue(self.post.is_published)
        self.assertEqual(self.post.status, PublicPost.Status.PUBLISHED)
        for delivery in deliveries:
            self.assertEqual(delivery.status, PublicationDelivery.Status.SUCCESS)
            self.assertEqual(delivery.recipient_count, 2)

    def test_status_is_correct_even_when_deliveries_were_prefetched(self):
        """Publishing through the API must not report a published post as a draft.

        The viewset prefetches `deliveries` to build its response, which fills
        the related manager's cache before any delivery exists. Reading the
        status back out of that cache made a successful publication look like
        a draft on the dashboard.
        """
        client = APIClient()
        client.force_authenticate(self.chief)
        response = client.post(
            f'/api/publications/{self.post.slug}/publish/',
            {'channels': ['WEB', 'MOBILE']}, format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['overall_status'], PublicPost.Status.PUBLISHED)
        self.post.refresh_from_db()
        self.assertEqual(self.post.status, PublicPost.Status.PUBLISHED)

    def test_running_twice_does_not_duplicate_deliveries(self):
        distribute(self.post, ['WEB'], 'http://x/p/1', self.chief)
        distribute(self.post, ['WEB'], 'http://x/p/1', self.chief)
        self.assertEqual(self.post.deliveries.filter(channel='WEB').count(), 1)


class EmailChannelTests(TestCase):
    def setUp(self):
        self.chief = make_user('chief', User.Role.HIERARCHY, email='chef@taskforce.cd')
        self.agent = make_user('agent', email='agent@taskforce.cd')
        make_user('unreachable', email='')
        self.post = make_post(audience=PublicPost.Audience.ALL_AGENTS, published_by=self.chief)

    def test_email_reaches_only_the_audience(self):
        delivery = distribute(self.post, ['EMAIL'], 'http://x/p/1')[0]

        self.assertEqual(delivery.status, PublicationDelivery.Status.SUCCESS)
        self.assertEqual(delivery.success_count, 1)
        self.assertEqual([m.to for m in mail.outbox], [['agent@taskforce.cd']])

    def test_an_account_without_an_address_is_not_counted(self):
        delivery = distribute(self.post, ['EMAIL'], 'http://x/p/1')[0]
        self.assertEqual(delivery.recipient_count, 1)

    def test_a_second_run_does_not_mail_anyone_twice(self):
        distribute(self.post, ['EMAIL'], 'http://x/p/1')
        mail.outbox.clear()
        distribute(self.post, ['EMAIL'], 'http://x/p/1')
        self.assertEqual(mail.outbox, [])

    def test_email_body_carries_the_publication_link(self):
        distribute(self.post, ['EMAIL'], 'http://x/p/1')
        body = mail.outbox[0].body
        self.assertIn(self.post.slug, body)

    def test_smtp_failure_is_recorded_per_recipient(self):
        with patch(
            'django.core.mail.EmailMultiAlternatives.send',
            side_effect=OSError('relais SMTP indisponible'),
        ):
            delivery = distribute(self.post, ['EMAIL'], 'http://x/p/1')[0]

        self.assertEqual(delivery.status, PublicationDelivery.Status.FAILED)
        row = delivery.recipients.get()
        self.assertEqual(row.status, RecipientDelivery.Status.FAILED)
        self.assertIn('SMTP', row.error_code)

    def test_hierarchy_only_publication_never_reaches_public_subscribers(self):
        from .models import NewsletterSubscriber

        NewsletterSubscriber.objects.create(email='public@exemple.cd')
        self.post.audience = PublicPost.Audience.HIERARCHY_ONLY
        self.post.save(update_fields=('audience',))

        distribute(self.post, ['EMAIL'], 'http://x/p/1')
        recipients = {address for message in mail.outbox for address in message.to}
        self.assertNotIn('public@exemple.cd', recipients)


@override_settings(OPENWA_ENABLED=True)
class WhatsAppChannelTests(TestCase):
    def setUp(self):
        self.chief = make_user('chief', User.Role.HIERARCHY, phone_number='+243900000001')
        self.agent = make_user('agent', phone_number='+243900000002')
        self.silent = make_user('silent', phone_number='')
        self.post = make_post(audience=PublicPost.Audience.ALL_AGENTS, published_by=self.chief)

    def test_message_is_sent_to_agents_with_a_number(self):
        with patch('notifications.services.send_whatsapp_message', return_value=(True, '', '')) as send:
            delivery = distribute(self.post, ['WHATSAPP'], 'http://x/p/1')[0]

        self.assertEqual(delivery.status, PublicationDelivery.Status.SUCCESS)
        self.assertEqual(delivery.success_count, 1)
        self.assertEqual(send.call_args[0][0], '+243900000002')

    def test_message_carries_the_full_publication_link(self):
        with patch('notifications.services.send_whatsapp_message', return_value=(True, '', '')) as send:
            distribute(self.post, ['WHATSAPP'], 'http://x/publication/42')
        self.assertIn('http://x/publication/42', send.call_args[0][1])

    def test_recipient_without_a_number_is_recorded_as_skipped(self):
        with patch('notifications.services.send_whatsapp_message', return_value=(True, '', '')):
            delivery = distribute(self.post, ['WHATSAPP'], 'http://x/p/1')[0]

        skipped = delivery.recipients.filter(status=RecipientDelivery.Status.SKIPPED)
        self.assertEqual(skipped.count(), 1)
        self.assertEqual(skipped.get().error_code, 'NO_PHONE_NUMBER')

    def test_provider_error_is_recorded_not_swallowed(self):
        with patch(
            'notifications.services.send_whatsapp_message',
            return_value=(False, 'PROVIDER_UNAVAILABLE', 'Passerelle injoignable.'),
        ):
            delivery = distribute(self.post, ['WHATSAPP'], 'http://x/p/1')[0]

        self.assertEqual(delivery.status, PublicationDelivery.Status.FAILED)
        self.assertEqual(delivery.error_code, 'PROVIDER_UNAVAILABLE')

    @override_settings(OPENWA_ENABLED=False)
    def test_unconfigured_gateway_skips_rather_than_fails(self):
        delivery = distribute(self.post, ['WHATSAPP'], 'http://x/p/1')[0]
        self.assertEqual(delivery.status, PublicationDelivery.Status.SKIPPED)
        self.assertEqual(delivery.error_code, 'PROVIDER_DISABLED')


class SocialChannelTests(TestCase):
    def setUp(self):
        self.chief = make_user('chief', User.Role.HIERARCHY)
        self.post = make_post(published_by=self.chief)
        SocialAccount.objects.create(
            platform='LINKEDIN', access_token='tok', external_account_id='abc', is_active=True,
        )

    def test_youtube_without_a_video_is_skipped_with_a_reason(self):
        SocialAccount.objects.create(platform='YOUTUBE', access_token='tok', is_active=True)
        delivery = distribute(self.post, ['YOUTUBE'], 'http://x/p/1')[0]

        self.assertEqual(delivery.status, PublicationDelivery.Status.SKIPPED)
        self.assertEqual(delivery.error_code, 'INCOMPATIBLE')
        self.assertIn('vidéo', delivery.detail.lower())

    def test_unconnected_platform_is_skipped(self):
        delivery = distribute(self.post, ['YOUTUBE'], 'http://x/p/1')[0]
        self.assertEqual(delivery.status, PublicationDelivery.Status.SKIPPED)
        self.assertEqual(delivery.error_code, 'NOT_CONNECTED')

    def test_successful_provider_post_is_recorded_with_its_identifier(self):
        # PUBLISHERS holds a direct function reference, so the dict entry is
        # what has to be replaced — patching the module attribute would leave
        # the real adapter, and a real network call, in place.
        publisher = lambda *a, **k: {  # noqa: E731
            'status': SocialPostAttempt.Status.SENT,
            'detail': 'Publié sur LinkedIn.',
            'provider_post_id': 'urn:li:share:999',
            'external_url': 'https://linkedin.com/feed/update/999',
        }
        with patch.dict('content.social.publishers.PUBLISHERS', {'LINKEDIN': publisher}):
            delivery = distribute(self.post, ['LINKEDIN'], 'http://x/p/1')[0]

        self.assertEqual(delivery.status, PublicationDelivery.Status.SUCCESS)
        self.assertEqual(delivery.external_id, 'urn:li:share:999')
        self.assertTrue(delivery.external_url)


class ProviderFailureIsolationTests(TestCase):
    """The central promise: one channel's failure stays inside that channel."""

    def setUp(self):
        self.chief = make_user('chief', User.Role.HIERARCHY, email='chef@taskforce.cd')
        make_user('agent', email='agent@taskforce.cd')
        self.post = make_post(
            audience=PublicPost.Audience.EVERYONE, published_by=self.chief, is_published=False,
        )
        SocialAccount.objects.create(platform='LINKEDIN', access_token='tok', is_active=True)

    def test_linkedin_failure_leaves_web_mobile_and_email_intact(self):
        with patch(
            'content.social.publishers.publish_to_linkedin',
            side_effect=RuntimeError('LinkedIn est tombé'),
        ):
            deliveries = distribute(
                self.post, ['WEB', 'MOBILE', 'EMAIL', 'LINKEDIN'], 'http://x/p/1', self.chief,
            )

        by_channel = {d.channel: d for d in deliveries}
        self.assertEqual(by_channel['WEB'].status, PublicationDelivery.Status.SUCCESS)
        self.assertEqual(by_channel['MOBILE'].status, PublicationDelivery.Status.SUCCESS)
        self.assertEqual(by_channel['EMAIL'].status, PublicationDelivery.Status.SUCCESS)
        self.assertEqual(by_channel['LINKEDIN'].status, PublicationDelivery.Status.FAILED)

        self.post.refresh_from_db()
        self.assertTrue(self.post.is_published, 'the web publication must not be rolled back')
        self.assertEqual(self.post.status, PublicPost.Status.PARTIAL)
        self.assertEqual(len(mail.outbox), 2, 'sent e-mails must not be undone')

    def test_an_unexpected_crash_is_contained_as_a_failed_delivery(self):
        with patch('content.channels.deliver_email', side_effect=RuntimeError('boum')):
            deliveries = distribute(self.post, ['WEB', 'EMAIL'], 'http://x/p/1', self.chief)

        by_channel = {d.channel: d for d in deliveries}
        self.assertEqual(by_channel['WEB'].status, PublicationDelivery.Status.SUCCESS)
        self.assertEqual(by_channel['EMAIL'].status, PublicationDelivery.Status.FAILED)
        self.assertEqual(by_channel['EMAIL'].error_code, 'UNEXPECTED_ERROR')


class NewsletterPermissionTests(TestCase):
    """An agent may draft a newsletter; only the hierarchy may mail it out."""

    def setUp(self):
        self.chief = make_user('chief', User.Role.HIERARCHY, email='chef@taskforce.cd')
        self.agent = make_user('agent', email='agent@taskforce.cd')
        self.post = make_post(
            title='Newsletter hebdomadaire', slug='newsletter-hebdo',
            category=PublicPost.Category.NEWSLETTER, is_published=False,
            audience=PublicPost.Audience.EVERYONE, published_by=self.agent,
        )
        self.client = APIClient()

    def test_agent_cannot_send_an_official_newsletter_by_email(self):
        self.client.force_authenticate(self.agent)
        response = self.client.post(
            f'/api/publications/{self.post.slug}/publish/', {'channels': ['EMAIL']}, format='json',
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data['code'], 'NEWSLETTER_FORBIDDEN')
        self.assertEqual(mail.outbox, [])

    def test_agent_may_still_publish_the_newsletter_to_the_apps(self):
        self.client.force_authenticate(self.agent)
        response = self.client.post(
            f'/api/publications/{self.post.slug}/publish/', {'channels': ['WEB']}, format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.post.refresh_from_db()
        self.assertTrue(self.post.is_published)

    def test_hierarchy_can_send_it(self):
        self.client.force_authenticate(self.chief)
        response = self.client.post(
            f'/api/publications/{self.post.slug}/publish/', {'channels': ['EMAIL']}, format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(mail.outbox)

    def test_a_client_claiming_the_hierarchy_role_is_ignored(self):
        """Authorisation comes from the authenticated account, never the body."""
        self.client.force_authenticate(self.agent)
        response = self.client.post(
            f'/api/publications/{self.post.slug}/publish/',
            {'channels': ['EMAIL'], 'role': 'HIERARCHY', 'is_hierarchy': True},
            format='json',
        )
        self.assertEqual(response.status_code, 403)


class DeliveryEndpointTests(TestCase):
    def setUp(self):
        self.chief = make_user('chief', User.Role.HIERARCHY)
        self.post = make_post(published_by=self.chief)
        self.client = APIClient()
        self.client.force_authenticate(self.chief)

    def test_deliveries_endpoint_reports_every_channel(self):
        distribute(self.post, ['WEB', 'MOBILE'], 'http://x/p/1', self.chief)
        response = self.client.get(f'/api/publications/{self.post.slug}/deliveries/')

        self.assertEqual(response.status_code, 200)
        channels = {row['channel'] for row in response.data['deliveries']}
        self.assertEqual(channels, {'WEB', 'MOBILE'})

    def test_a_successful_channel_cannot_be_retried(self):
        distribute(self.post, ['WEB'], 'http://x/p/1', self.chief)
        delivery = self.post.deliveries.get(channel='WEB')
        response = self.client.post(
            f'/api/publications/{self.post.slug}/deliveries/{delivery.pk}/retry/',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['code'], 'ALREADY_DELIVERED')

    def test_a_provider_that_already_published_cannot_be_retried(self):
        delivery = PublicationDelivery.objects.create(
            post=self.post, channel='LINKEDIN',
            status=PublicationDelivery.Status.FAILED, external_id='urn:li:share:1',
        )
        response = self.client.post(
            f'/api/publications/{self.post.slug}/deliveries/{delivery.pk}/retry/',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['code'], 'ALREADY_PUBLISHED')

    def test_stats_endpoint_counts_drafts_and_failures(self):
        make_post(title='Brouillon', slug='brouillon-x', is_published=False, published_by=self.chief)
        PublicationDelivery.objects.create(
            post=self.post, channel='LINKEDIN', status=PublicationDelivery.Status.FAILED,
        )
        response = self.client.get('/api/publications/stats/')

        self.assertEqual(response.data['drafts'], 1)
        self.assertEqual(response.data['failed_deliveries'], 1)

    def test_schedule_refuses_a_date_in_the_past(self):
        response = self.client.post(
            f'/api/publications/{self.post.slug}/schedule/',
            {'scheduled_for': '2020-01-01T10:00:00Z'}, format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['code'], 'PAST_DATE')

    def test_schedule_parks_the_publication(self):
        from django.utils import timezone
        from datetime import timedelta

        when = (timezone.now() + timedelta(days=1)).isoformat()
        response = self.client.post(
            f'/api/publications/{self.post.slug}/schedule/',
            {'scheduled_for': when, 'channels': ['WEB', 'EMAIL']}, format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.post.refresh_from_db()
        self.assertEqual(self.post.status, PublicPost.Status.SCHEDULED)
        self.assertFalse(self.post.is_published)


class PublicationPlanTests(TestCase):
    """The composer's preview must agree with what distribution actually does."""

    def setUp(self):
        self.chief = make_user('chief', User.Role.HIERARCHY)
        self.post = make_post(published_by=self.chief)
        self.client = APIClient()
        self.client.force_authenticate(self.chief)

    def plan(self):
        response = self.client.get(f'/api/publications/{self.post.slug}/publication-plan/')
        self.assertEqual(response.status_code, 200)
        return {row['platform']: row for row in response.data['destinations']}

    def test_plan_covers_every_channel(self):
        self.assertEqual(
            set(self.plan()), {'WEB', 'MOBILE', 'EMAIL', 'WHATSAPP', 'LINKEDIN', 'YOUTUBE'},
        )

    def test_email_is_available_when_mail_is_configured(self):
        """Availability comes from the mail settings, not from OAuth accounts.

        Reporting e-mail as "not connected" because no *social* account exists
        would grey out a channel that in fact delivers.
        """
        self.assertTrue(self.plan()['EMAIL']['available'])

    @override_settings(OPENWA_ENABLED=False)
    def test_whatsapp_is_unavailable_when_the_gateway_is_off(self):
        self.assertFalse(self.plan()['WHATSAPP']['available'])

    @override_settings(OPENWA_ENABLED=True)
    def test_whatsapp_is_available_once_the_gateway_is_on(self):
        self.assertTrue(self.plan()['WHATSAPP']['available'])


class LinkedInAuthorErrorTests(TestCase):
    """A rejected author URN must name the real problem."""

    @override_settings(LINKEDIN_ORGANIZATION_URN='144829980')
    def test_author_rejection_explains_the_permission_cause(self):
        from content.social import publishers

        chief = make_user('chief', User.Role.HIERARCHY)
        post = make_post(published_by=chief)
        account = SocialAccount.objects.create(
            platform='LINKEDIN', access_token='tok', external_account_id='abc', is_active=True,
        )

        class Rejection:
            ok = False
            status_code = 422

            @staticmethod
            def json():
                return {'message': 'Field Value validation failed in REQUEST_BODY: '
                                   'Data Processing Exception while processing fields [/author]'}

        with patch.object(publishers, 'ensure_fresh_token', return_value='tok'), \
             patch.object(publishers.requests, 'post', return_value=Rejection()):
            with self.assertRaises(publishers.PublishError) as caught:
                publishers.publish_to_linkedin(post, account, 'http://x/p/1')

        self.assertEqual(caught.exception.code, 'AUTHOR_NOT_PERMITTED')
        self.assertIn('administrateur', str(caught.exception))
        self.assertIn('w_organization_social', str(caught.exception))


class MixedMediaPublicationTests(TestCase):
    """A single publication carrying every supported kind of content."""

    def setUp(self):
        self.chief = make_user('chief', User.Role.HIERARCHY)
        self.client = APIClient()
        self.client.force_authenticate(self.chief)

    def create(self, **extra):
        payload = {
            'title': 'Publication mixte',
            'category': PublicPost.Category.COMMUNIQUE,
            'excerpt': 'Résumé',
            'body': '<p>Contenu riche</p>',
            'audience': PublicPost.Audience.ALL_AGENTS,
            **extra,
        }
        response = self.client.post('/api/publications/', payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def test_text_only_publication(self):
        data = self.create()
        self.assertEqual(data['status'], PublicPost.Status.DRAFT)
        self.assertEqual(data['audience'], PublicPost.Audience.ALL_AGENTS)

    def test_publication_with_links(self):
        data = self.create(links_payload=[
            {'url': 'https://presidence.cd', 'label': 'Présidence'},
            {'url': 'https://taskforce.cd/rapport.html'},
        ])
        self.assertEqual(len(data['links']), 2)

    def test_publication_targeting_named_users(self):
        target = make_user('cible')
        data = self.create(
            audience=PublicPost.Audience.SPECIFIC_USERS,
            audience_users_payload=[target.id],
        )
        self.assertEqual(data['audience_user_ids'], [target.id])
        self.assertEqual(data['audience_size'], 1)

    def test_the_same_engine_serves_every_publication_type(self):
        for category in PublicPost.Category.values:
            data = self.create(title=f'Type {category}', category=category)
            self.assertEqual(data['category'], category)
        self.assertEqual(PublicPost.objects.count(), len(PublicPost.Category.values))


class LegacyDataTests(TestCase):
    """Publications created before targeting existed must keep working."""

    def test_a_post_without_an_audience_defaults_to_everyone(self):
        post = PublicPost.objects.create(
            title='Ancien communiqué', slug='ancien-communique',
            category=PublicPost.Category.COMMUNIQUE, body='<p>Texte</p>', is_published=True,
        )
        self.assertEqual(post.audience, PublicPost.Audience.EVERYONE)

    def test_legacy_post_is_still_readable_on_the_public_site(self):
        PublicPost.objects.create(
            title='Ancien communiqué', slug='ancien-communique',
            category=PublicPost.Category.COMMUNIQUE, body='<p>Texte</p>', is_published=True,
        )
        client = APIClient()
        response = client.get('/api/posts/ancien-communique/')
        self.assertEqual(response.status_code, 200)

    def test_legacy_single_file_attachment_still_reaches_the_adapters(self):
        from .social.capabilities import build_inventory

        post = PublicPost.objects.create(
            title='Communiqué PDF', slug='communique-pdf',
            category=PublicPost.Category.COMMUNIQUE, body='<p>Texte</p>', is_published=True,
        )
        post.attachment.name = 'communiques/officiel.pdf'
        post.save(update_fields=('attachment',))

        inventory = build_inventory(post)
        self.assertIsNotNone(inventory.legacy_attachment)
