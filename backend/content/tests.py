from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from accounts.models import User
from .models import PublicMedia, PublicPost, SocialMediaLink


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
            {'file': video, 'media_type': 'VIDEO', 'caption': 'Démonstration'},
            format='multipart',
        )
        self.assertEqual(upload.status_code, 201)
        self.assertTrue(PublicMedia.objects.filter(post=post, media_type='VIDEO').exists())

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
