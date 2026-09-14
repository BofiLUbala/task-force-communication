"""Multimedia publication, destination compatibility and provider adapters.

Provider HTTP calls are faked at the `requests` boundary so the adapters'
real request shapes, response parsing and failure isolation are exercised
without touching LinkedIn or YouTube. What these tests do *not* prove is that
the live providers accept the payloads — see the report for that distinction.
"""
from unittest import mock

from django.core.cache import cache
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase

from accounts.models import User

from .models import (
    PublicationDelivery,
    PublicMedia,
    PublicPost,
    SocialAccount,
    SocialPostAttempt,
)
from .social import capabilities
from .social.capabilities import build_inventory, html_to_text, plan_destination
from .social.tokens import TokenError, account_health, ensure_fresh_token

def _real_png():
    """Django validates ImageField uploads with Pillow, so cover images must
    be genuine PNG bytes rather than a plausible-looking header."""
    import io

    from PIL import Image

    buffer = io.BytesIO()
    Image.new('RGB', (4, 4), (0, 47, 106)).save(buffer, format='PNG')
    return buffer.getvalue()


PNG = _real_png()
PDF = b'%PDF-1.4' + b'0' * 64
MP4 = b'\x00\x00\x00\x18ftypisom' + b'0' * 64


def png(name='photo.png'):
    return SimpleUploadedFile(name, PNG, content_type='image/png')


def pdf(name='communique.pdf'):
    return SimpleUploadedFile(name, PDF, content_type='application/pdf')


def mp4(name='clip.mp4'):
    return SimpleUploadedFile(name, MP4, content_type='video/mp4')


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, headers=None, text=''):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.headers = headers or {}
        self.text = text or ''

    @property
    def ok(self):
        return 200 <= self.status_code < 300

    def json(self):
        return self._json


class FakeRequests:
    """Stands in for `requests` inside the publishers, recording every call."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []
        # Exception classes the adapters catch by name.
        import requests as real_requests
        self.Timeout = real_requests.Timeout
        self.RequestException = real_requests.RequestException

    def _dispatch(self, method, url, **kwargs):
        self.calls.append({'method': method, 'url': url, **kwargs})
        for fragment, response in self.routes.items():
            if fragment in url:
                return response(**kwargs) if callable(response) else response
        raise AssertionError(f'Unexpected {method} to {url}')

    def post(self, url, **kwargs):
        return self._dispatch('POST', url, **kwargs)

    def put(self, url, **kwargs):
        return self._dispatch('PUT', url, **kwargs)

    def get(self, url, **kwargs):
        return self._dispatch('GET', url, **kwargs)


LINKEDIN_OK = {
    'assets?action=registerUpload': FakeResponse(200, {
        'value': {
            'asset': 'urn:li:digitalmediaAsset:ABC123',
            'uploadMechanism': {
                'com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest': {
                    'uploadUrl': 'https://upload.linkedin.example/stream',
                },
            },
        },
    }),
    'upload.linkedin.example': FakeResponse(201),
    '/v2/ugcPosts': FakeResponse(201, {'id': 'urn:li:share:987'},
                                 headers={'x-restli-id': 'urn:li:share:987'}),
}

YOUTUBE_OK = {
    'uploadType=resumable': FakeResponse(
        200, {}, headers={'Location': 'https://upload.youtube.example/session'},
    ),
    'upload.youtube.example': FakeResponse(200, {'id': 'yt-video-42'}),
    'thumbnails/set': FakeResponse(200, {}),
}


class PublicationBase(APITestCase):
    def setUp(self):
        self.hierarchy = User.objects.create_user(
            username='chief', password='pw', role=User.Role.HIERARCHY,
        )
        self.client.force_authenticate(self.hierarchy)

    def create_post(self, **overrides):
        payload = {
            'title': 'Communiqué officiel',
            'category': 'ACTUALITE',
            'excerpt': 'Résumé court',
            'body': '<p>Texte <strong>officiel</strong> de la Task Force.</p>',
            'is_published': True,
        }
        payload.update(overrides)
        response = self.client.post('/api/posts/', payload, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        return PublicPost.objects.get(pk=response.data['id'])

    def attach(self, post, upload, media_type, **extra):
        response = self.client.post(
            f'/api/posts/{post.slug}/upload-media/',
            {'file': upload, 'media_type': media_type, **extra},
            format='multipart',
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def connect(self, platform, **overrides):
        defaults = {
            'account_name': f'{platform} officiel',
            'external_account_id': 'ext-1',
            'access_token': 'token-value',
            'is_active': True,
        }
        defaults.update(overrides)
        return SocialAccount.objects.create(platform=platform, **defaults)


class ContentTypeTests(PublicationBase):
    """The composer must handle every documented content combination."""

    def test_text_only_post(self):
        post = self.create_post()
        inventory = build_inventory(post)
        self.assertTrue(inventory.has_text)
        self.assertEqual(inventory.images, [])
        self.assertIn('officiel', inventory.text)
        self.assertNotIn('<strong>', inventory.text)

    def test_single_image_post(self):
        post = self.create_post()
        self.attach(post, png(), 'PHOTO', alt_text='Vue du chantier')
        inventory = build_inventory(post)
        self.assertEqual(len(inventory.images), 1)
        self.assertEqual(inventory.images[0].alt_text, 'Vue du chantier')
        self.assertEqual(inventory.images[0].mime_type, 'image/png')
        self.assertGreater(inventory.images[0].file_size, 0)

    def test_multiple_images_keep_their_order(self):
        post = self.create_post()
        for index in range(3):
            self.attach(post, png(f'photo{index}.png'), 'PHOTO', title=f'Image {index}')
        inventory = build_inventory(post)
        self.assertEqual(len(inventory.images), 3)
        self.assertEqual([m.order for m in inventory.images], [0, 1, 2])

    def test_video_attachment(self):
        post = self.create_post()
        self.attach(post, mp4(), 'VIDEO')
        inventory = build_inventory(post)
        self.assertEqual(len(inventory.videos), 1)
        self.assertEqual(inventory.primary_video.mime_type, 'video/mp4')

    def test_pdf_document_attachment(self):
        post = self.create_post()
        self.attach(post, pdf(), 'DOCUMENT', title='Communiqué n°12')
        inventory = build_inventory(post)
        self.assertEqual(len(inventory.documents), 1)
        self.assertEqual(inventory.documents[0].mime_type, 'application/pdf')

    def test_external_links_are_validated_and_stored(self):
        response = self.client.post('/api/posts/', {
            'title': 'Avec liens', 'category': 'ACTUALITE', 'excerpt': 'r', 'body': '<p>b</p>',
            'is_published': True,
            'links_payload': '[{"url":"https://presidence.cd","label":"Présidence"},'
                             '{"url":"https://example.org/rapport"}]',
        }, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        post = PublicPost.objects.get(pk=response.data['id'])
        self.assertEqual(post.links.count(), 2)
        self.assertEqual(post.links.first().label, 'Présidence')

    def test_invalid_link_is_rejected_without_creating_the_post(self):
        response = self.client.post('/api/posts/', {
            'title': 'Lien cassé', 'category': 'ACTUALITE', 'excerpt': 'r', 'body': '<p>b</p>',
            'links_payload': '[{"url":"pas-une-url"}]',
        }, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(PublicPost.objects.filter(title='Lien cassé').exists())

    def test_mixed_multimedia_post(self):
        post = self.create_post(
            links_payload='[{"url":"https://presidence.cd","label":"Présidence"}]',
        )
        self.attach(post, png('a.png'), 'PHOTO')
        self.attach(post, png('b.png'), 'PHOTO')
        self.attach(post, mp4(), 'VIDEO')
        self.attach(post, pdf(), 'DOCUMENT')

        inventory = build_inventory(post)
        self.assertEqual(len(inventory.images), 2)
        self.assertEqual(len(inventory.videos), 1)
        self.assertEqual(len(inventory.documents), 1)
        self.assertEqual(len(inventory.links), 1)

    def test_attachment_can_be_removed(self):
        post = self.create_post()
        media = self.attach(post, png(), 'PHOTO')
        response = self.client.delete(f'/api/posts/{post.slug}/media/{media["id"]}/')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(post.gallery.count(), 0)


class AttachmentSecurityTests(PublicationBase):
    def test_script_disguised_as_an_image_is_refused(self):
        post = self.create_post()
        malicious = SimpleUploadedFile('photo.png', b'<?php system($_GET["c"]); ?>', content_type='image/png')
        response = self.client.post(
            f'/api/posts/{post.slug}/upload-media/',
            {'file': malicious, 'media_type': 'PHOTO'}, format='multipart',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(post.gallery.count(), 0)

    def test_pdf_uploaded_as_a_photo_is_refused(self):
        post = self.create_post()
        response = self.client.post(
            f'/api/posts/{post.slug}/upload-media/',
            {'file': pdf(), 'media_type': 'PHOTO'}, format='multipart',
        )
        self.assertEqual(response.status_code, 400)

    def test_empty_upload_is_refused(self):
        post = self.create_post()
        empty = SimpleUploadedFile('vide.png', b'', content_type='image/png')
        response = self.client.post(
            f'/api/posts/{post.slug}/upload-media/',
            {'file': empty, 'media_type': 'PHOTO'}, format='multipart',
        )
        self.assertEqual(response.status_code, 400)

    def test_executable_extension_is_refused(self):
        post = self.create_post()
        script = SimpleUploadedFile('note.php', b'%PDF-1.4 harmless looking', content_type='application/pdf')
        response = self.client.post(
            f'/api/posts/{post.slug}/upload-media/',
            {'file': script, 'media_type': 'DOCUMENT'}, format='multipart',
        )
        self.assertEqual(response.status_code, 400)


class CompatibilityTests(PublicationBase):
    def test_youtube_is_unavailable_without_a_video(self):
        post = self.create_post()
        plan = plan_destination(post, 'YOUTUBE', connected=True)
        self.assertFalse(plan.available)
        self.assertIn('nécessite une vidéo', plan.reason)

    def test_youtube_is_unavailable_for_an_image_only_post(self):
        post = self.create_post()
        self.attach(post, png(), 'PHOTO')
        plan = plan_destination(post, 'YOUTUBE', connected=True)
        self.assertFalse(plan.available)
        self.assertTrue(any('image' in excluded['item'] for excluded in plan.excluded))

    def test_youtube_is_available_with_a_video(self):
        post = self.create_post()
        self.attach(post, mp4(), 'VIDEO')
        plan = plan_destination(post, 'YOUTUBE', connected=True)
        self.assertTrue(plan.available)
        self.assertIn('1 vidéo', plan.included)

    def test_linkedin_keeps_text_images_and_links_but_flags_the_document(self):
        post = self.create_post(links_payload='[{"url":"https://presidence.cd"}]')
        self.attach(post, png('a.png'), 'PHOTO')
        self.attach(post, pdf(), 'DOCUMENT')

        plan = plan_destination(post, 'LINKEDIN', connected=True)

        self.assertTrue(plan.available)
        self.assertIn('texte', plan.included)
        self.assertIn('1 image(s)', plan.included)
        self.assertIn('1 lien(s)', plan.included)
        excluded_items = ' '.join(item['item'] for item in plan.excluded)
        self.assertIn('document', excluded_items)

    def test_linkedin_caps_the_number_of_images(self):
        post = self.create_post()
        for index in range(capabilities.LINKEDIN_MAX_IMAGES + 2):
            self.attach(post, png(f'p{index}.png'), 'PHOTO')
        plan = plan_destination(post, 'LINKEDIN', connected=True)
        self.assertIn(f'{capabilities.LINKEDIN_MAX_IMAGES} image(s)', plan.included)
        self.assertTrue(any('supplémentaire' in item['item'] for item in plan.excluded))

    def test_website_accepts_everything(self):
        post = self.create_post(links_payload='[{"url":"https://presidence.cd"}]')
        self.attach(post, png(), 'PHOTO')
        self.attach(post, mp4(), 'VIDEO')
        self.attach(post, pdf(), 'DOCUMENT')
        plan = plan_destination(post, capabilities.WEBSITE)
        self.assertTrue(plan.available)
        self.assertEqual(plan.excluded, [])

    def test_disconnected_platform_is_unavailable(self):
        post = self.create_post()
        plan = plan_destination(post, 'LINKEDIN', connected=False)
        self.assertFalse(plan.available)
        self.assertIn('Aucun compte', plan.reason)

    def test_publication_plan_endpoint_lists_every_destination(self):
        post = self.create_post()
        self.connect('LINKEDIN')
        response = self.client.get(f'/api/posts/{post.slug}/publication-plan/')
        self.assertEqual(response.status_code, 200)
        by_platform = {row['platform']: row for row in response.data['destinations']}
        # The plan now covers every distribution channel, not just the web
        # site and the social networks. WEB is the canonical name for what
        # used to be called WEBSITE; the old spelling is still accepted as
        # input (see `channels.normalise_channels`).
        self.assertTrue(by_platform['WEB']['available'])
        self.assertTrue(by_platform['MOBILE']['available'])
        self.assertTrue(by_platform['LINKEDIN']['available'])
        self.assertFalse(by_platform['YOUTUBE']['available'])

    def test_rich_text_is_flattened_for_plain_text_providers(self):
        html = '<h2>Titre</h2><p>Ligne un</p><ul><li>Point</li></ul><p>Fin&nbsp;!</p>'
        text = html_to_text(html)
        self.assertNotIn('<', text)
        self.assertIn('Point', text)
        self.assertIn('Titre', text)


class LinkedInPublisherTests(PublicationBase):
    def test_text_post_is_published_and_recorded(self):
        post = self.create_post()
        account = self.connect('LINKEDIN')
        fake = FakeRequests(LINKEDIN_OK)

        with mock.patch('content.social.publishers.requests', fake):
            response = self.client.post(f'/api/posts/{post.slug}/push-social/', {}, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['overall_status'], 'SUCCESS')
        attempt = SocialPostAttempt.objects.get(post=post, platform='LINKEDIN')
        self.assertEqual(attempt.status, SocialPostAttempt.Status.SENT)
        self.assertEqual(attempt.provider_post_id, 'urn:li:share:987')
        self.assertIn('linkedin.com/feed/update', attempt.external_url)
        self.assertIsNotNone(attempt.completed_at)
        account.refresh_from_db()
        self.assertIsNotNone(account.last_used_at)

    def test_text_post_carries_title_body_and_links(self):
        post = self.create_post(links_payload='[{"url":"https://presidence.cd"}]')
        self.connect('LINKEDIN')
        fake = FakeRequests(LINKEDIN_OK)

        with mock.patch('content.social.publishers.requests', fake):
            self.client.post(f'/api/posts/{post.slug}/push-social/', {}, format='json')

        ugc = next(call for call in fake.calls if 'ugcPosts' in call['url'])
        share = ugc['json']['specificContent']['com.linkedin.ugc.ShareContent']
        commentary = share['shareCommentary']['text']
        self.assertIn('Communiqué officiel', commentary)
        self.assertIn('https://presidence.cd', commentary)
        self.assertEqual(share['shareMediaCategory'], 'ARTICLE')

    def test_image_post_registers_uploads_then_shares_them(self):
        post = self.create_post()
        self.attach(post, png('a.png'), 'PHOTO')
        self.attach(post, png('b.png'), 'PHOTO')
        self.connect('LINKEDIN')
        fake = FakeRequests(LINKEDIN_OK)

        with mock.patch('content.social.publishers.requests', fake):
            self.client.post(f'/api/posts/{post.slug}/push-social/', {}, format='json')

        registrations = [call for call in fake.calls if 'registerUpload' in call['url']]
        uploads = [call for call in fake.calls if 'upload.linkedin.example' in call['url']]
        self.assertEqual(len(registrations), 2)
        self.assertEqual(len(uploads), 2)

        ugc = next(call for call in fake.calls if 'ugcPosts' in call['url'])
        share = ugc['json']['specificContent']['com.linkedin.ugc.ShareContent']
        self.assertEqual(share['shareMediaCategory'], 'IMAGE')
        self.assertEqual(len(share['media']), 2)

    def test_video_post_uses_the_video_recipe(self):
        post = self.create_post()
        self.attach(post, mp4(), 'VIDEO')
        self.connect('LINKEDIN')
        fake = FakeRequests(LINKEDIN_OK)

        with mock.patch('content.social.publishers.requests', fake):
            self.client.post(f'/api/posts/{post.slug}/push-social/', {'targets': ['LINKEDIN']}, format='json')

        registration = next(call for call in fake.calls if 'registerUpload' in call['url'])
        recipes = registration['json']['registerUploadRequest']['recipes']
        self.assertEqual(recipes, ['urn:li:digitalmediaRecipe:feedshare-video'])
        ugc = next(call for call in fake.calls if 'ugcPosts' in call['url'])
        self.assertEqual(
            ugc['json']['specificContent']['com.linkedin.ugc.ShareContent']['shareMediaCategory'],
            'VIDEO',
        )

    def test_documents_are_not_sent_and_the_post_link_travels_instead(self):
        post = self.create_post()
        self.attach(post, pdf(), 'DOCUMENT')
        self.connect('LINKEDIN')
        fake = FakeRequests(LINKEDIN_OK)

        with mock.patch('content.social.publishers.requests', fake):
            self.client.post(f'/api/posts/{post.slug}/push-social/', {}, format='json')

        self.assertFalse(any('registerUpload' in call['url'] for call in fake.calls))
        ugc = next(call for call in fake.calls if 'ugcPosts' in call['url'])
        commentary = ugc['json']['specificContent']['com.linkedin.ugc.ShareContent']['shareCommentary']['text']
        self.assertIn(f'/publications/{post.slug}', commentary)

    def test_provider_rejection_is_recorded_as_a_failure(self):
        post = self.create_post()
        self.connect('LINKEDIN')
        fake = FakeRequests({
            '/v2/ugcPosts': FakeResponse(403, {'message': 'Not enough permissions'}),
        })

        with mock.patch('content.social.publishers.requests', fake):
            response = self.client.post(f'/api/posts/{post.slug}/push-social/', {}, format='json')

        self.assertEqual(response.data['overall_status'], 'FAILED')
        attempt = SocialPostAttempt.objects.get(post=post, platform='LINKEDIN')
        self.assertEqual(attempt.status, SocialPostAttempt.Status.FAILED)
        self.assertEqual(attempt.error_code, 'PERMISSION_DENIED')
        self.assertIn('Not enough permissions', attempt.detail)
        self.assertEqual(attempt.provider_post_id, '')

    def test_media_upload_failure_does_not_report_success(self):
        post = self.create_post()
        self.attach(post, png(), 'PHOTO')
        self.connect('LINKEDIN')
        fake = FakeRequests({
            'assets?action=registerUpload': LINKEDIN_OK['assets?action=registerUpload'],
            'upload.linkedin.example': FakeResponse(500, text='upstream error'),
        })

        with mock.patch('content.social.publishers.requests', fake):
            self.client.post(f'/api/posts/{post.slug}/push-social/', {}, format='json')

        attempt = SocialPostAttempt.objects.get(post=post, platform='LINKEDIN')
        self.assertEqual(attempt.status, SocialPostAttempt.Status.FAILED)
        self.assertEqual(attempt.error_code, 'PROVIDER_UNAVAILABLE')
        self.assertFalse(any('ugcPosts' in call['url'] for call in fake.calls))

    def test_missing_provider_id_is_not_treated_as_success(self):
        post = self.create_post()
        self.connect('LINKEDIN')
        fake = FakeRequests({'/v2/ugcPosts': FakeResponse(201, {})})

        with mock.patch('content.social.publishers.requests', fake):
            self.client.post(f'/api/posts/{post.slug}/push-social/', {}, format='json')

        attempt = SocialPostAttempt.objects.get(post=post, platform='LINKEDIN')
        self.assertEqual(attempt.status, SocialPostAttempt.Status.FAILED)
        self.assertEqual(attempt.error_code, 'NO_PROVIDER_ID')


class YouTubePublisherTests(PublicationBase):
    def test_video_upload_stores_the_video_id(self):
        post = self.create_post()
        self.attach(post, mp4(), 'VIDEO')
        self.connect('YOUTUBE')
        fake = FakeRequests(YOUTUBE_OK)

        with mock.patch('content.social.publishers.requests', fake):
            response = self.client.post(f'/api/posts/{post.slug}/push-social/', {}, format='json')

        self.assertEqual(response.data['overall_status'], 'SUCCESS')
        attempt = SocialPostAttempt.objects.get(post=post, platform='YOUTUBE')
        self.assertEqual(attempt.status, SocialPostAttempt.Status.SENT)
        self.assertEqual(attempt.provider_post_id, 'yt-video-42')
        self.assertEqual(attempt.external_url, 'https://www.youtube.com/watch?v=yt-video-42')

    def test_upload_is_resumable_and_description_is_plain_text(self):
        post = self.create_post(links_payload='[{"url":"https://presidence.cd"}]')
        self.attach(post, mp4(), 'VIDEO')
        self.connect('YOUTUBE')
        fake = FakeRequests(YOUTUBE_OK)

        with mock.patch('content.social.publishers.requests', fake):
            self.client.post(f'/api/posts/{post.slug}/push-social/', {}, format='json')

        start = next(call for call in fake.calls if 'uploadType=resumable' in call['url'])
        snippet = start['json']['snippet']
        self.assertEqual(snippet['title'], 'Communiqué officiel')
        self.assertNotIn('<', snippet['description'])
        self.assertIn('https://presidence.cd', snippet['description'])
        self.assertIn('X-Upload-Content-Length', start['headers'])
        # The bytes go to the session URL returned by the provider, not inline.
        self.assertTrue(any('upload.youtube.example' in call['url'] for call in fake.calls))

    def test_cover_image_is_sent_as_a_thumbnail(self):
        post = self.create_post(cover_image=png('cover.png'))
        self.attach(post, mp4(), 'VIDEO')
        self.connect('YOUTUBE')
        fake = FakeRequests(YOUTUBE_OK)

        with mock.patch('content.social.publishers.requests', fake):
            self.client.post(f'/api/posts/{post.slug}/push-social/', {}, format='json')

        self.assertTrue(any('thumbnails/set' in call['url'] for call in fake.calls))
        attempt = SocialPostAttempt.objects.get(post=post, platform='YOUTUBE')
        self.assertEqual(attempt.status, SocialPostAttempt.Status.SENT)
        self.assertIn('Miniature', attempt.detail)

    def test_thumbnail_failure_does_not_undo_the_video(self):
        post = self.create_post(cover_image=png('cover.png'))
        self.attach(post, mp4(), 'VIDEO')
        self.connect('YOUTUBE')
        fake = FakeRequests({**YOUTUBE_OK, 'thumbnails/set': FakeResponse(403, {'message': 'no'})})

        with mock.patch('content.social.publishers.requests', fake):
            self.client.post(f'/api/posts/{post.slug}/push-social/', {}, format='json')

        attempt = SocialPostAttempt.objects.get(post=post, platform='YOUTUBE')
        self.assertEqual(attempt.status, SocialPostAttempt.Status.SENT)
        self.assertEqual(attempt.provider_post_id, 'yt-video-42')

    def test_text_only_post_is_skipped(self):
        post = self.create_post()
        self.connect('YOUTUBE')
        fake = FakeRequests({})

        with mock.patch('content.social.publishers.requests', fake):
            response = self.client.post(f'/api/posts/{post.slug}/push-social/', {}, format='json')

        attempt = SocialPostAttempt.objects.get(post=post, platform='YOUTUBE')
        self.assertEqual(attempt.status, SocialPostAttempt.Status.SKIPPED)
        self.assertEqual(attempt.error_code, 'VIDEO_REQUIRED')
        self.assertIn('nécessite une vidéo', attempt.detail)
        self.assertEqual(fake.calls, [])
        self.assertEqual(response.data['overall_status'], 'SKIPPED')

    def test_image_only_post_is_skipped(self):
        post = self.create_post()
        self.attach(post, png(), 'PHOTO')
        self.connect('YOUTUBE')
        fake = FakeRequests({})

        with mock.patch('content.social.publishers.requests', fake):
            self.client.post(f'/api/posts/{post.slug}/push-social/', {}, format='json')

        attempt = SocialPostAttempt.objects.get(post=post, platform='YOUTUBE')
        self.assertEqual(attempt.status, SocialPostAttempt.Status.SKIPPED)

    def test_pdf_only_post_is_never_uploaded_as_a_video(self):
        post = self.create_post()
        self.attach(post, pdf(), 'DOCUMENT')
        self.connect('YOUTUBE')
        fake = FakeRequests({})

        with mock.patch('content.social.publishers.requests', fake):
            self.client.post(f'/api/posts/{post.slug}/push-social/', {}, format='json')

        self.assertEqual(fake.calls, [])
        attempt = SocialPostAttempt.objects.get(post=post, platform='YOUTUBE')
        self.assertEqual(attempt.status, SocialPostAttempt.Status.SKIPPED)

    def test_upload_failure_is_recorded_with_its_code(self):
        post = self.create_post()
        self.attach(post, mp4(), 'VIDEO')
        self.connect('YOUTUBE')
        fake = FakeRequests({
            'uploadType=resumable': YOUTUBE_OK['uploadType=resumable'],
            'upload.youtube.example': FakeResponse(500, {'message': 'backend error'}),
        })

        with mock.patch('content.social.publishers.requests', fake):
            self.client.post(f'/api/posts/{post.slug}/push-social/', {}, format='json')

        attempt = SocialPostAttempt.objects.get(post=post, platform='YOUTUBE')
        self.assertEqual(attempt.status, SocialPostAttempt.Status.FAILED)
        self.assertEqual(attempt.error_code, 'PROVIDER_UNAVAILABLE')
        self.assertEqual(attempt.provider_post_id, '')

    def test_only_the_first_video_is_uploaded(self):
        post = self.create_post()
        self.attach(post, mp4('one.mp4'), 'VIDEO')
        self.attach(post, mp4('two.mp4'), 'VIDEO')
        self.connect('YOUTUBE')
        fake = FakeRequests(YOUTUBE_OK)

        with mock.patch('content.social.publishers.requests', fake):
            self.client.post(f'/api/posts/{post.slug}/push-social/', {}, format='json')

        starts = [call for call in fake.calls if 'uploadType=resumable' in call['url']]
        self.assertEqual(len(starts), 1)
        plan = plan_destination(post, 'YOUTUBE', connected=True)
        self.assertTrue(any('supplémentaire' in item['item'] for item in plan.excluded))


class FailureIsolationTests(PublicationBase):
    def test_one_provider_failing_leaves_the_other_intact(self):
        post = self.create_post()
        self.attach(post, mp4(), 'VIDEO')
        self.connect('LINKEDIN')
        self.connect('YOUTUBE')
        fake = FakeRequests({
            **LINKEDIN_OK,
            'uploadType=resumable': FakeResponse(500, {'message': 'youtube down'}),
        })

        with mock.patch('content.social.publishers.requests', fake):
            response = self.client.post(f'/api/posts/{post.slug}/push-social/', {}, format='json')

        self.assertEqual(response.data['overall_status'], 'PARTIAL_SUCCESS')
        linkedin = SocialPostAttempt.objects.get(post=post, platform='LINKEDIN')
        youtube = SocialPostAttempt.objects.get(post=post, platform='YOUTUBE')
        self.assertEqual(linkedin.status, SocialPostAttempt.Status.SENT)
        self.assertEqual(youtube.status, SocialPostAttempt.Status.FAILED)

    def test_website_publication_survives_every_provider_failing(self):
        post = self.create_post(is_published=False)
        self.connect('LINKEDIN')
        fake = FakeRequests({'/v2/ugcPosts': FakeResponse(500, {'message': 'down'})})

        with mock.patch('content.social.publishers.requests', fake):
            response = self.client.post(f'/api/posts/{post.slug}/publish/', {}, format='json')

        post.refresh_from_db()
        self.assertTrue(post.is_published)
        self.assertIsNotNone(post.published_at)
        self.assertEqual(response.data['overall_status'], 'PARTIAL_SUCCESS')
        website = next(r for r in response.data['results'] if r['platform'] == 'WEBSITE')
        self.assertEqual(website['status'], 'SENT')

    def test_unexpected_publisher_crash_is_contained(self):
        post = self.create_post()
        self.connect('LINKEDIN')

        # PUBLISHERS holds a direct function reference, so patching the module
        # attribute would leave the real adapter — and a real network call — in place.
        crashing = mock.Mock(side_effect=RuntimeError('boom'))
        with mock.patch.dict('content.social.publishers.PUBLISHERS', {'LINKEDIN': crashing}):
            response = self.client.post(f'/api/posts/{post.slug}/push-social/', {}, format='json')

        self.assertEqual(response.status_code, 200)
        attempt = SocialPostAttempt.objects.get(post=post, platform='LINKEDIN')
        self.assertEqual(attempt.status, SocialPostAttempt.Status.FAILED)
        self.assertEqual(attempt.error_code, 'UNEXPECTED_ERROR')

    def test_targets_limit_which_destinations_run(self):
        post = self.create_post()
        self.connect('LINKEDIN')
        self.connect('YOUTUBE')
        fake = FakeRequests(LINKEDIN_OK)

        with mock.patch('content.social.publishers.requests', fake):
            self.client.post(f'/api/posts/{post.slug}/push-social/', {'targets': ['LINKEDIN']}, format='json')

        self.assertEqual(SocialPostAttempt.objects.filter(post=post).count(), 1)
        self.assertEqual(SocialPostAttempt.objects.get(post=post).platform, 'LINKEDIN')

    def test_disconnected_target_is_skipped_not_crashed(self):
        post = self.create_post()
        response = self.client.post(
            f'/api/posts/{post.slug}/push-social/', {'targets': ['LINKEDIN']}, format='json',
        )
        attempt = SocialPostAttempt.objects.get(post=post, platform='LINKEDIN')
        self.assertEqual(attempt.status, SocialPostAttempt.Status.SKIPPED)
        self.assertEqual(attempt.error_code, 'NOT_CONNECTED')
        self.assertEqual(response.data['overall_status'], 'SKIPPED')


class AutomaticSocialDistributionTests(PublicationBase):
    """Publish once: every connected social account decides for itself.

    The author picks the audience and the in-house channels; nobody re-ticks
    LinkedIn and YouTube on every post. What each provider does with the
    content is the compatibility engine's answer, not a checkbox.
    """

    def deliveries(self, post):
        return {row.channel: row for row in post.deliveries.all()}

    def test_text_and_image_reaches_linkedin_and_skips_youtube(self):
        post = self.create_post(is_published=False)
        self.attach(post, png(), 'PHOTO')
        self.connect('LINKEDIN')
        self.connect('YOUTUBE')

        with mock.patch('content.social.publishers.requests', FakeRequests(LINKEDIN_OK)):
            # The author asked for the web app only — the social accounts are added anyway.
            self.client.post(
                f'/api/posts/{post.slug}/publish/', {'channels': ['WEB']}, format='json',
            )

        rows = self.deliveries(post)
        self.assertEqual(rows['WEB'].status, PublicationDelivery.Status.SUCCESS)
        self.assertEqual(rows['LINKEDIN'].status, PublicationDelivery.Status.SUCCESS)
        self.assertEqual(rows['YOUTUBE'].status, PublicationDelivery.Status.SKIPPED)
        self.assertEqual(rows['YOUTUBE'].error_code, 'INCOMPATIBLE')

    def test_text_and_video_reaches_both_providers(self):
        post = self.create_post(is_published=False)
        self.attach(post, mp4(), 'VIDEO')
        self.connect('LINKEDIN')
        self.connect('YOUTUBE')

        with mock.patch(
            'content.social.publishers.requests', FakeRequests({**LINKEDIN_OK, **YOUTUBE_OK}),
        ):
            self.client.post(
                f'/api/posts/{post.slug}/publish/', {'channels': ['WEB']}, format='json',
            )

        rows = self.deliveries(post)
        self.assertEqual(rows['LINKEDIN'].status, PublicationDelivery.Status.SUCCESS)
        self.assertEqual(rows['YOUTUBE'].status, PublicationDelivery.Status.SUCCESS)
        self.assertEqual(rows['YOUTUBE'].external_url, 'https://www.youtube.com/watch?v=yt-video-42')

    def test_disconnected_provider_is_skipped_without_blocking_the_rest(self):
        post = self.create_post(is_published=False)
        self.attach(post, mp4(), 'VIDEO')
        self.connect('LINKEDIN')
        self.connect('YOUTUBE', is_active=False)

        with mock.patch('content.social.publishers.requests', FakeRequests(LINKEDIN_OK)):
            self.client.post(
                f'/api/posts/{post.slug}/publish/', {'channels': ['WEB']}, format='json',
            )

        rows = self.deliveries(post)
        self.assertEqual(rows['WEB'].status, PublicationDelivery.Status.SUCCESS)
        self.assertEqual(rows['LINKEDIN'].status, PublicationDelivery.Status.SUCCESS)
        self.assertEqual(rows['YOUTUBE'].status, PublicationDelivery.Status.SKIPPED)
        self.assertEqual(rows['YOUTUBE'].error_code, 'NOT_CONNECTED')

    def test_a_failing_provider_never_blocks_another_channel(self):
        post = self.create_post(is_published=False)
        self.attach(post, mp4(), 'VIDEO')
        self.connect('LINKEDIN')
        self.connect('YOUTUBE')
        broken = FakeRequests({
            **YOUTUBE_OK,
            '/v2/ugcPosts': FakeResponse(500, {'message': 'linkedin down'}),
            'assets?action=registerUpload': FakeResponse(500, {'message': 'linkedin down'}),
        })

        with mock.patch('content.social.publishers.requests', broken):
            self.client.post(
                f'/api/posts/{post.slug}/publish/', {'channels': ['WEB']}, format='json',
            )

        rows = self.deliveries(post)
        self.assertEqual(rows['LINKEDIN'].status, PublicationDelivery.Status.FAILED)
        self.assertEqual(rows['WEB'].status, PublicationDelivery.Status.SUCCESS)
        self.assertEqual(rows['YOUTUBE'].status, PublicationDelivery.Status.SUCCESS)

    def test_a_never_connected_platform_produces_no_row(self):
        post = self.create_post(is_published=False)
        self.connect('LINKEDIN')

        with mock.patch('content.social.publishers.requests', FakeRequests(LINKEDIN_OK)):
            self.client.post(
                f'/api/posts/{post.slug}/publish/', {'channels': ['WEB']}, format='json',
            )

        self.assertNotIn('YOUTUBE', self.deliveries(post))

    def test_mass_mailing_is_never_added_automatically(self):
        post = self.create_post(is_published=False)
        self.connect('LINKEDIN')

        with mock.patch('content.social.publishers.requests', FakeRequests(LINKEDIN_OK)):
            self.client.post(
                f'/api/posts/{post.slug}/publish/', {'channels': ['WEB']}, format='json',
            )

        rows = self.deliveries(post)
        self.assertIn('LINKEDIN', rows)
        self.assertNotIn('EMAIL', rows)
        self.assertNotIn('WHATSAPP', rows)


class ScheduledPublicationTests(PublicationBase):
    """A parked publication must actually leave on its own.

    `schedule()` only ever set a date; nothing came back for it, so scheduled
    publications sat untouched forever. These cover the command that closes
    that loop.
    """

    def schedule_post(self, when, channels=None):
        post = self.create_post(is_published=False)
        post.status = PublicPost.Status.SCHEDULED
        post.scheduled_for = when
        post.channels = channels or ['WEB']
        post.save(update_fields=('status', 'scheduled_for', 'channels'))
        return post

    def test_a_due_publication_is_distributed(self):
        post = self.schedule_post(timezone.now() - timedelta(minutes=1))

        call_command('run_scheduled_publications')

        post.refresh_from_db()
        self.assertEqual(post.status, PublicPost.Status.PUBLISHED)
        self.assertTrue(post.is_published)
        self.assertIsNotNone(post.published_at)
        self.assertEqual(
            post.deliveries.get(channel='WEB').status, PublicationDelivery.Status.SUCCESS,
        )

    def test_a_future_publication_is_left_alone(self):
        post = self.schedule_post(timezone.now() + timedelta(hours=3))

        call_command('run_scheduled_publications')

        post.refresh_from_db()
        self.assertEqual(post.status, PublicPost.Status.SCHEDULED)
        self.assertFalse(post.is_published)
        self.assertEqual(post.deliveries.count(), 0)

    def test_running_twice_does_not_publish_twice(self):
        post = self.schedule_post(timezone.now() - timedelta(minutes=1))

        call_command('run_scheduled_publications')
        first = post.deliveries.get(channel='WEB').completed_at
        call_command('run_scheduled_publications')

        post.refresh_from_db()
        self.assertEqual(post.deliveries.count(), 1)
        self.assertEqual(post.deliveries.get(channel='WEB').completed_at, first)

    def test_dry_run_changes_nothing(self):
        post = self.schedule_post(timezone.now() - timedelta(minutes=1))

        call_command('run_scheduled_publications', '--dry-run')

        post.refresh_from_db()
        self.assertEqual(post.status, PublicPost.Status.SCHEDULED)
        self.assertEqual(post.deliveries.count(), 0)


class RetryTests(PublicationBase):
    def test_a_failed_attempt_can_be_retried_and_then_succeeds(self):
        post = self.create_post()
        self.connect('LINKEDIN')
        failing = FakeRequests({'/v2/ugcPosts': FakeResponse(503, {'message': 'try later'})})

        with mock.patch('content.social.publishers.requests', failing):
            self.client.post(f'/api/posts/{post.slug}/push-social/', {}, format='json')

        attempt = SocialPostAttempt.objects.get(post=post, platform='LINKEDIN')
        self.assertEqual(attempt.status, SocialPostAttempt.Status.FAILED)

        with mock.patch('content.social.publishers.requests', FakeRequests(LINKEDIN_OK)):
            response = self.client.post(
                f'/api/posts/{post.slug}/retry-social/', {'attempt': attempt.id}, format='json',
            )

        self.assertEqual(response.status_code, 200)
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, SocialPostAttempt.Status.SENT)
        self.assertEqual(attempt.retry_count, 1)
        # The retry reuses the row: no duplicate provider post is created.
        self.assertEqual(SocialPostAttempt.objects.filter(post=post, platform='LINKEDIN').count(), 1)

    def test_an_already_published_attempt_is_never_reposted(self):
        post = self.create_post()
        account = self.connect('LINKEDIN')
        attempt = SocialPostAttempt.objects.create(
            post=post, account=account, platform='LINKEDIN',
            status=SocialPostAttempt.Status.SENT, provider_post_id='urn:li:share:1',
        )
        response = self.client.post(
            f'/api/posts/{post.slug}/retry-social/', {'attempt': attempt.id}, format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['code'], 'ALREADY_PUBLISHED')

    def test_retry_is_restricted_to_hierarchy(self):
        post = self.create_post()
        agent = User.objects.create_user(username='agent', password='pw', role=User.Role.AGENT)
        self.client.force_authenticate(agent)
        response = self.client.post(
            f'/api/posts/{post.slug}/retry-social/', {'attempt': 1}, format='json',
        )
        self.assertEqual(response.status_code, 403)


class SocialAccountSecurityTests(PublicationBase):
    def test_tokens_are_never_exposed_by_the_api(self):
        self.connect('LINKEDIN', access_token='super-secret', refresh_token='refresh-secret')
        response = self.client.get('/api/social-accounts/')
        payload = str(response.data)
        self.assertNotIn('super-secret', payload)
        self.assertNotIn('refresh-secret', payload)
        self.assertIn('health', response.data['results'][0])

    def test_anonymous_users_cannot_read_or_start_a_connection(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/social-accounts/').status_code, 401)
        self.assertEqual(
            self.client.get('/api/social-accounts/oauth/linkedin/start/').status_code, 401,
        )

    def test_anonymous_users_cannot_publish_or_read_a_plan(self):
        post = self.create_post()
        self.client.force_authenticate(None)
        self.assertEqual(
            self.client.post(f'/api/posts/{post.slug}/push-social/', {}, format='json').status_code, 401,
        )
        self.assertEqual(
            self.client.get(f'/api/posts/{post.slug}/publication-plan/').status_code, 401,
        )

    @override_settings(LINKEDIN_CLIENT_ID='id', LINKEDIN_CLIENT_SECRET='secret')
    def test_oauth_callback_stores_the_account_and_its_expiry(self):
        cache.set('social_oauth_state:state-123', 'LINKEDIN', timeout=600)
        with mock.patch(
            'content.social.oauth.exchange_code',
            return_value={'access_token': 'tok', 'refresh_token': 'ref', 'expires_in': 3600},
        ), mock.patch(
            'content.social.oauth.get_linkedin_identity', return_value=('member-1', 'Task Force'),
        ):
            response = self.client.get(
                '/api/social-accounts/oauth/linkedin/callback/',
                {'code': 'auth-code', 'state': 'state-123'},
            )

        self.assertEqual(response.status_code, 302)
        account = SocialAccount.objects.get(platform='LINKEDIN')
        self.assertEqual(account.account_name, 'Task Force')
        self.assertTrue(account.is_active)
        self.assertFalse(account.needs_reconnect)
        self.assertIsNotNone(account.token_expires_at)

    @override_settings(GOOGLE_CLIENT_ID='id', GOOGLE_CLIENT_SECRET='secret')
    def test_youtube_callback_stores_the_connected_channel_identity(self):
        cache.set('social_oauth_state:state-yt', 'YOUTUBE', timeout=600)
        with mock.patch(
            'content.social.oauth.exchange_code',
            return_value={'access_token': 'tok', 'refresh_token': 'ref', 'expires_in': 3600},
        ), mock.patch(
            'content.social.oauth.get_youtube_channel', return_value=('UC-chan-1', 'Task Force TV'),
        ):
            response = self.client.get(
                '/api/social-accounts/oauth/youtube/callback/',
                {'code': 'auth-code', 'state': 'state-yt'},
            )

        self.assertEqual(response.status_code, 302)
        account = SocialAccount.objects.get(platform='YOUTUBE')
        self.assertEqual(account.external_account_id, 'UC-chan-1')
        self.assertEqual(account.account_name, 'Task Force TV')
        self.assertFalse(account.needs_reconnect)

    @override_settings(GOOGLE_CLIENT_ID='id', GOOGLE_CLIENT_SECRET='secret')
    def test_reconnect_without_a_new_refresh_token_keeps_the_stored_one(self):
        SocialAccount.objects.create(
            platform='YOUTUBE', access_token='old', refresh_token='keep-me', needs_reconnect=True,
        )
        cache.set('social_oauth_state:state-yt2', 'YOUTUBE', timeout=600)
        with mock.patch(
            'content.social.oauth.exchange_code',
            return_value={'access_token': 'fresh', 'expires_in': 3600},
        ), mock.patch(
            'content.social.oauth.get_youtube_channel', return_value=('UC-chan-1', 'Task Force TV'),
        ):
            self.client.get(
                '/api/social-accounts/oauth/youtube/callback/',
                {'code': 'auth-code', 'state': 'state-yt2'},
            )

        account = SocialAccount.objects.get(platform='YOUTUBE')
        self.assertEqual(account.access_token, 'fresh')
        self.assertEqual(account.refresh_token, 'keep-me')

    def test_oauth_callback_rejects_an_unknown_state(self):
        response = self.client.get(
            '/api/social-accounts/oauth/linkedin/callback/',
            {'code': 'auth-code', 'state': 'forged'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('social_error=state', response['Location'])
        self.assertFalse(SocialAccount.objects.exists())


class TokenLifecycleTests(PublicationBase):
    def test_a_valid_token_is_used_as_is(self):
        account = self.connect(
            'YOUTUBE', access_token='still-good',
            token_expires_at=timezone.now() + timedelta(hours=2),
        )
        self.assertEqual(ensure_fresh_token(account), 'still-good')
        self.assertEqual(account_health(account), 'CONNECTED')

    def test_an_expired_token_is_refreshed_server_side(self):
        account = self.connect(
            'YOUTUBE', access_token='stale', refresh_token='refresh-me',
            token_expires_at=timezone.now() - timedelta(minutes=1),
        )
        with mock.patch(
            'content.social.tokens.requests.post',
            return_value=FakeResponse(200, {'access_token': 'fresh', 'expires_in': 3600}),
        ):
            token = ensure_fresh_token(account)

        self.assertEqual(token, 'fresh')
        account.refresh_from_db()
        self.assertEqual(account.access_token, 'fresh')
        self.assertGreater(account.token_expires_at, timezone.now())
        self.assertFalse(account.needs_reconnect)

    def test_a_rejected_refresh_marks_the_account_for_reconnection(self):
        account = self.connect(
            'YOUTUBE', access_token='stale', refresh_token='revoked',
            token_expires_at=timezone.now() - timedelta(minutes=1),
        )
        with mock.patch(
            'content.social.tokens.requests.post', return_value=FakeResponse(400, {'error': 'invalid_grant'}),
        ):
            with self.assertRaises(TokenError):
                ensure_fresh_token(account)

        account.refresh_from_db()
        self.assertTrue(account.needs_reconnect)
        self.assertEqual(account_health(account), 'RECONNECT_REQUIRED')

    def test_expired_token_without_refresh_capability_requires_reconnection(self):
        account = self.connect(
            'LINKEDIN', access_token='stale', refresh_token='',
            token_expires_at=timezone.now() - timedelta(minutes=1),
        )
        with self.assertRaises(TokenError):
            ensure_fresh_token(account)
        account.refresh_from_db()
        self.assertTrue(account.needs_reconnect)

    def test_publication_reports_reconnection_instead_of_a_generic_failure(self):
        post = self.create_post()
        self.connect(
            'LINKEDIN', access_token='stale', refresh_token='',
            token_expires_at=timezone.now() - timedelta(minutes=1),
        )
        with mock.patch('content.social.publishers.requests', FakeRequests({})):
            self.client.post(f'/api/posts/{post.slug}/push-social/', {}, format='json')

        attempt = SocialPostAttempt.objects.get(post=post, platform='LINKEDIN')
        self.assertEqual(attempt.status, SocialPostAttempt.Status.FAILED)
        self.assertEqual(attempt.error_code, 'TOKEN_EXPIRED')


class BackwardCompatibilityTests(PublicationBase):
    """Posts created before the attachment model must keep working."""

    def test_legacy_cover_and_attachment_still_publish(self):
        post = PublicPost.objects.create(
            title='Ancien communiqué', slug='ancien-communique', category='COMMUNIQUE',
            excerpt='Résumé', body='<p>Corps</p>', published_by=self.hierarchy,
            is_published=True,
            cover_image=SimpleUploadedFile('old-cover.png', PNG, content_type='image/png'),
            attachment=SimpleUploadedFile('old.pdf', PDF, content_type='application/pdf'),
        )
        self.assertEqual(post.gallery.count(), 0)

        inventory = build_inventory(post)
        self.assertIsNotNone(inventory.cover)
        self.assertIsNotNone(inventory.legacy_attachment)

        plan = plan_destination(post, 'LINKEDIN', connected=True)
        self.assertTrue(plan.available)
        self.assertTrue(any('document' in item['item'] for item in plan.excluded))

    def test_legacy_post_is_still_served_on_its_public_url(self):
        PublicPost.objects.create(
            title='Ancienne actualité', slug='ancienne-actualite', category='ACTUALITE',
            excerpt='Résumé', body='<p>Contenu historique</p>', published_by=self.hierarchy,
            is_published=True, published_at=timezone.now(),
        )
        self.client.force_authenticate(None)
        response = self.client.get('/api/posts/ancienne-actualite/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['title'], 'Ancienne actualité')
        self.assertIn('Contenu historique', response.data['body'])
        self.assertEqual(response.data['gallery'], [])
        self.assertEqual(response.data['links'], [])

    def test_public_feed_still_lists_every_category(self):
        for index, category in enumerate(('ACTUALITE', 'COMMUNIQUE', 'ACTIVITE')):
            PublicPost.objects.create(
                title=f'Publication {category}', slug=f'pub-{index}', category=category,
                excerpt='r', body='<p>b</p>', published_by=self.hierarchy,
                is_published=True, published_at=timezone.now(),
            )
        self.client.force_authenticate(None)
        response = self.client.get('/api/posts/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 3)

    def test_attempt_history_survives_the_account_being_deleted(self):
        post = self.create_post()
        account = self.connect('LINKEDIN')
        SocialPostAttempt.objects.create(
            post=post, account=account, platform='LINKEDIN',
            status=SocialPostAttempt.Status.SENT,
            external_url='https://www.linkedin.com/feed/update/urn:li:share:1',
        )
        account.delete()

        self.client.force_authenticate(None)
        response = self.client.get(f'/api/posts/{post.slug}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['platform_links'][0]['platform'], 'LINKEDIN')
        self.assertEqual(response.data['platform_links'][0]['platform_display'], 'LinkedIn')
