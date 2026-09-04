from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from accounts.models import User
from .models import NewsletterDelivery, NewsletterSubscriber, PublicMedia, PublicPost, SocialMediaLink


class PublicationTests(APITestCase):
    def setUp(self):
        self.hierarchy = User.objects.create_user(
            username='hierarchy', password='test-password', role=User.Role.HIERARCHY,
        )
        self.client.force_authenticate(self.hierarchy)

    def test_hierarchy_can_publish_and_attach_video(self):
        response = self.client.post('/api/posts/', {
            'title': 'Vidéo officielle',
            'category': 'ACTIVITE',
            'excerpt': 'Suivi des travaux',
            'body': 'Présentation vidéo de l’avancement.',
            'is_published': True,
        })
        self.assertEqual(response.status_code, 201)
        post = PublicPost.objects.get(pk=response.data['id'])
        self.assertTrue(post.is_published)
        self.assertIsNotNone(post.published_at)

        video = SimpleUploadedFile('demo.mp4', b'video-content', content_type='video/mp4')
        upload = self.client.post(
            f'/api/posts/{post.slug}/upload-media/',
            {
                'file': video,
                'media_type': 'VIDEO',
                'title': 'Travaux à Kinshasa',
                'caption': 'Démonstration',
                'social_links': '[{"platform":"YouTube","url":"https://youtube.com/watch?v=demo"}]',
            },
            format='multipart',
        )
        self.assertEqual(upload.status_code, 201)
        media = PublicMedia.objects.get(post=post, media_type='VIDEO')
        self.assertEqual(media.title, 'Travaux à Kinshasa')
        self.assertEqual(media.social_links[0]['platform'], 'YouTube')

    def test_agent_can_create_publication(self):
        agent = User.objects.create_user(username='agent', password='test-password', role=User.Role.AGENT)
        self.client.force_authenticate(agent)
        response = self.client.post('/api/posts/', {
            'title': 'Actualité de terrain',
            'category': 'ACTUALITE',
            'excerpt': 'Information officielle',
            'body': 'Contenu publié depuis le tableau de bord agent.',
            'is_published': True,
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(PublicPost.objects.get(pk=response.data['id']).published_by, agent)

    def test_newsletter_is_published_in_its_own_feed(self):
        newsletter = PublicPost.objects.create(
            title='Message hebdomadaire', slug='message-hebdomadaire', category='NEWSLETTER',
            excerpt='Les actions de la semaine', body='Contenu de la newsletter.',
            published_by=self.hierarchy, is_published=True,
        )
        own_feed = self.client.get('/api/posts/', {'category': 'NEWSLETTER'})
        own_items = own_feed.data.get('results', own_feed.data)
        self.assertEqual([item['id'] for item in own_items], [newsletter.id])

        news_feed = self.client.get('/api/posts/', {'exclude_category': 'NEWSLETTER'})
        news_items = news_feed.data.get('results', news_feed.data)
        self.assertNotIn(newsletter.id, [item['id'] for item in news_items])


class SocialMediaLinkTests(APITestCase):
    def test_agent_can_add_a_social_link(self):
        agent = User.objects.create_user(username='agent2', password='test-password', role=User.Role.AGENT)
        self.client.force_authenticate(agent)
        response = self.client.post('/api/social-links/', {'name': 'Facebook', 'url': 'https://facebook.com/taskforce'})
        self.assertEqual(response.status_code, 201)
        link = SocialMediaLink.objects.get(pk=response.data['id'])
        self.assertEqual(link.added_by, agent)
        self.assertTrue(link.is_active)

    def test_public_list_only_shows_active_links(self):
        SocialMediaLink.objects.create(name='Facebook', url='https://facebook.com/taskforce', is_active=True)
        SocialMediaLink.objects.create(name='Old Page', url='https://example.com/old', is_active=False)
        response = self.client.get('/api/social-links/')
        self.assertEqual(response.status_code, 200)
        names = [item['name'] for item in response.data['results']] if 'results' in response.data else [item['name'] for item in response.data]
        self.assertIn('Facebook', names)
        self.assertNotIn('Old Page', names)

    def test_only_hierarchy_can_delete_a_link(self):
        link = SocialMediaLink.objects.create(name='Facebook', url='https://facebook.com/taskforce')
        agent = User.objects.create_user(username='agent3', password='test-password', role=User.Role.AGENT)
        self.client.force_authenticate(agent)
        forbidden = self.client.delete(f'/api/social-links/{link.id}/')
        self.assertEqual(forbidden.status_code, 403)

        hierarchy = User.objects.create_user(username='hierarchy2', password='test-password', role=User.Role.HIERARCHY)
        self.client.force_authenticate(hierarchy)
        allowed = self.client.delete(f'/api/social-links/{link.id}/')
        self.assertEqual(allowed.status_code, 204)
        self.assertFalse(SocialMediaLink.objects.filter(pk=link.id).exists())


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class NewsletterTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='newsletter-editor', password='password', role=User.Role.AGENT)

    def test_public_can_subscribe_unsubscribe_and_reactivate(self):
        response = self.client.post('/api/newsletter/subscribe/', {'email': 'Reader@Example.com', 'name': 'Lecteur'})
        self.assertEqual(response.status_code, 201)
        subscriber = NewsletterSubscriber.objects.get(email='reader@example.com')
        self.assertTrue(subscriber.is_active)

        response = self.client.post(f'/api/newsletter/unsubscribe/{subscriber.unsubscribe_token}/')
        self.assertEqual(response.status_code, 200)
        subscriber.refresh_from_db()
        self.assertFalse(subscriber.is_active)

        response = self.client.post('/api/newsletter/subscribe/', {'email': 'reader@example.com'})
        self.assertEqual(response.status_code, 200)
        subscriber.refresh_from_db()
        self.assertTrue(subscriber.is_active)

    def test_editor_can_test_then_send_newsletter(self):
        subscriber = NewsletterSubscriber.objects.create(email='subscriber@example.com')
        post = PublicPost.objects.create(
            title='Info salubrité', slug='info-salubrite', category='NEWSLETTER',
            excerpt='Résumé', body='<p>Message officiel</p>', published_by=self.user,
            newsletter_subject='Objet officiel', is_published=False,
        )
        self.client.force_authenticate(self.user)

        draft_feed = self.client.get('/api/posts/', {'category': 'NEWSLETTER'})
        self.assertEqual(draft_feed.data.get('results', draft_feed.data), [])

        test_response = self.client.post(f'/api/posts/{post.slug}/test-newsletter/', {'email': 'test@example.com'}, format='json')
        self.assertEqual(test_response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        send_response = self.client.post(f'/api/posts/{post.slug}/send-newsletter/', {}, format='json')
        self.assertEqual(send_response.status_code, 200)
        self.assertEqual(send_response.data['sent'], 1)
        post.refresh_from_db()
        self.assertTrue(post.is_published)
        self.assertIsNotNone(post.newsletter_sent_at)
        self.assertTrue(NewsletterDelivery.objects.filter(post=post, subscriber=subscriber, status='SENT').exists())
        self.assertIn(str(subscriber.unsubscribe_token), mail.outbox[-1].alternatives[0].content)
        published_feed = self.client.get('/api/posts/', {'category': 'NEWSLETTER'})
        published_items = published_feed.data.get('results', published_feed.data)
        self.assertEqual(published_items[0]['slug'], post.slug)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='site@example.com', CONTACT_EMAIL='contact@example.com',
)
class ContactMessageTests(APITestCase):
    def test_public_visitor_can_send_contact_message(self):
        response = self.client.post('/api/contact/', {
            'name': 'Visiteur', 'email': 'visitor@example.com',
            'subject': 'Question salubrité', 'message': 'Bonjour, voici ma question.',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(mail.outbox[0].to, ['contact@example.com'])
        self.assertEqual(mail.outbox[0].reply_to, ['visitor@example.com'])
