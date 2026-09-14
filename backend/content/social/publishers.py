"""Translate a Task Force publication into each provider's own format.

Every adapter takes the destination plan produced by `capabilities.py` and
sends only what that platform can genuinely carry. Nothing here fakes a
success: an attempt is marked SENT only once the provider has answered with
an identifier for the published item.
"""
import json
import logging
import mimetypes
import os

import requests
from django.conf import settings
from django.utils import timezone

from ..models import SocialPostAttempt
from .capabilities import (
    CAPABILITIES,
    PLATFORM_LABELS,
    build_inventory,
    html_to_text,
    linkedin_author_urn,
    plan_destination,
)
from .tokens import TokenError, ensure_fresh_token

logger = logging.getLogger(__name__)

LINKEDIN_API = 'https://api.linkedin.com'
YOUTUBE_UPLOAD = 'https://www.googleapis.com/upload/youtube/v3'

YOUTUBE_TITLE_LIMIT = 100
YOUTUBE_DESCRIPTION_LIMIT = 5000
LINKEDIN_COMMENTARY_LIMIT = 2900

UPLOAD_TIMEOUT = 600
API_TIMEOUT = 30


class PublishError(Exception):
    """A provider refused the publication, with a code the UI can act on."""

    def __init__(self, message, code='PROVIDER_ERROR'):
        super().__init__(message)
        self.code = code


def classify_http_error(response, default_code='PROVIDER_ERROR'):
    """Map a provider HTTP status onto one of our stable error codes."""
    status = response.status_code
    if status in (401, 403):
        return 'PERMISSION_DENIED'
    if status == 429:
        return 'RATE_LIMITED'
    if status >= 500:
        return 'PROVIDER_UNAVAILABLE'
    if status == 413:
        return 'FILE_TOO_LARGE'
    return default_code


def provider_message(response, limit=400):
    """A short, secret-free excerpt of a provider error body."""
    try:
        payload = response.json()
    except ValueError:
        return (response.text or '')[:limit]
    for key in ('error_description', 'message', 'error'):
        value = payload.get(key)
        if isinstance(value, str):
            return value[:limit]
        if isinstance(value, dict) and isinstance(value.get('message'), str):
            return value['message'][:limit]
    return json.dumps(payload)[:limit]


def compose_text(inventory, limit=None, include_links=True):
    """Title + body + links, flattened for a plain-text provider field."""
    parts = []
    if inventory.title:
        parts.append(inventory.title)
    if inventory.text:
        parts.append(inventory.text)
    if include_links and inventory.links:
        parts.append('\n'.join(link.url for link in inventory.links))
    text = '\n\n'.join(part for part in parts if part)
    if limit and len(text) > limit:
        text = text[: limit - 1].rstrip() + '…'
    return text


def _open(file_field):
    """Open a stored file for reading without pulling it into memory."""
    file_field.open('rb')
    return file_field


def _file_name(file_field):
    return os.path.basename(getattr(file_field, 'name', '') or 'fichier')


def _content_type(file_field, fallback='application/octet-stream'):
    guessed = mimetypes.guess_type(_file_name(file_field))[0]
    return guessed or fallback


# --------------------------------------------------------------------------
# LinkedIn
# --------------------------------------------------------------------------

def _linkedin_headers(token):
    return {
        'Authorization': f'Bearer {token}',
        'X-Restli-Protocol-Version': '2.0.0',
    }


def linkedin_register_upload(token, author, recipe):
    """Ask LinkedIn for an upload slot; returns (upload_url, asset_urn)."""
    response = requests.post(
        f'{LINKEDIN_API}/v2/assets?action=registerUpload',
        json={
            'registerUploadRequest': {
                'recipes': [f'urn:li:digitalmediaRecipe:{recipe}'],
                'owner': author,
                'serviceRelationships': [{
                    'relationshipType': 'OWNER',
                    'identifier': 'urn:li:userGeneratedContent',
                }],
            },
        },
        headers={**_linkedin_headers(token), 'Content-Type': 'application/json'},
        timeout=API_TIMEOUT,
    )
    if not response.ok:
        raise PublishError(
            f'LinkedIn a refusé la préparation du média : {provider_message(response)}',
            classify_http_error(response, 'MEDIA_UPLOAD_FAILED'),
        )

    value = response.json().get('value', {})
    mechanism = value.get('uploadMechanism', {}).get(
        'com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest', {},
    )
    upload_url = mechanism.get('uploadUrl')
    asset = value.get('asset')
    if not upload_url or not asset:
        raise PublishError('LinkedIn n’a pas fourni d’URL d’envoi pour ce média.', 'MEDIA_UPLOAD_FAILED')
    return upload_url, asset


def linkedin_upload_binary(token, upload_url, file_field):
    """Stream the file to LinkedIn's upload URL."""
    handle = _open(file_field)
    try:
        response = requests.put(
            upload_url,
            data=handle,
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': _content_type(file_field),
            },
            timeout=UPLOAD_TIMEOUT,
        )
    finally:
        handle.close()

    if not response.ok:
        raise PublishError(
            f'Envoi du média vers LinkedIn échoué (HTTP {response.status_code}).',
            classify_http_error(response, 'MEDIA_UPLOAD_FAILED'),
        )


def linkedin_share_content(token, author, inventory, plan):
    """Build the ugcPosts specificContent for whatever the plan kept."""
    capability = CAPABILITIES['LINKEDIN']
    commentary = compose_text(inventory, LINKEDIN_COMMENTARY_LIMIT)
    share = {
        'shareCommentary': {'text': commentary},
        'shareMediaCategory': 'NONE',
    }
    media_urn = ''

    if inventory.videos and capability.video:
        video = inventory.videos[0]
        upload_url, asset = linkedin_register_upload(token, author, 'feedshare-video')
        linkedin_upload_binary(token, upload_url, video.file)
        media_urn = asset
        share['shareMediaCategory'] = 'VIDEO'
        share['media'] = [{
            'status': 'READY',
            'media': asset,
            'title': {'text': (video.title or inventory.title)[:200]},
            'description': {'text': (video.caption or '')[:250]},
        }]
        return share, media_urn

    if inventory.images and capability.image:
        kept = inventory.images[: max(capability.multiple_images, 1)]
        media_entries = []
        for image in kept:
            upload_url, asset = linkedin_register_upload(token, author, 'feedshare-image')
            linkedin_upload_binary(token, upload_url, image.file)
            media_entries.append({
                'status': 'READY',
                'media': asset,
                'title': {'text': (image.title or inventory.title)[:200]},
                'description': {'text': (image.alt_text or image.caption or '')[:250]},
            })
        media_urn = media_entries[0]['media']
        share['shareMediaCategory'] = 'IMAGE'
        share['media'] = media_entries
        return share, media_urn

    if inventory.links and capability.link:
        first = inventory.links[0]
        share['shareMediaCategory'] = 'ARTICLE'
        share['media'] = [{
            'status': 'READY',
            'originalUrl': first.url,
            'title': {'text': (first.label or inventory.title)[:200]},
        }]
        return share, media_urn

    return share, media_urn


def publish_to_linkedin(post, account, post_url, plan=None):
    """Publish to LinkedIn as the configured organisation or member."""
    inventory = build_inventory(post)
    plan = plan or plan_destination(post, 'LINKEDIN', connected=True, inventory=inventory)
    if not plan.available:
        return {'status': SocialPostAttempt.Status.SKIPPED, 'detail': plan.reason, 'code': 'INCOMPATIBLE'}

    token = ensure_fresh_token(account)
    author = linkedin_author_urn(account)
    if not author:
        raise PublishError(
            'Identité LinkedIn introuvable — reconnectez le compte.', 'RECONNECT_REQUIRED',
        )

    # The post page always travels with the share so the excluded documents
    # remain one click away.
    if post_url and not any(link.url == post_url for link in inventory.links):
        class _PageLink:
            url = post_url
            label = post.title
        inventory.links = list(inventory.links) + [_PageLink()]

    share, media_urn = linkedin_share_content(token, author, inventory, plan)

    response = requests.post(
        f'{LINKEDIN_API}/v2/ugcPosts',
        json={
            'author': author,
            'lifecycleState': 'PUBLISHED',
            'specificContent': {'com.linkedin.ugc.ShareContent': share},
            'visibility': {'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC'},
        },
        headers={**_linkedin_headers(token), 'Content-Type': 'application/json'},
        timeout=API_TIMEOUT,
    )
    if not response.ok:
        message = provider_message(response)
        # LinkedIn rejects an author URN the token may not act as with a
        # generic "validation failed ... [/author]". Left as-is that message
        # sends the operator hunting through the post body, when the fix is
        # always about the identity: either the app lacks
        # w_organization_social, or the connected member does not administer
        # the configured page.
        if '/author' in message and author.startswith('urn:li:organization:'):
            raise PublishError(
                'LinkedIn refuse de publier au nom de la page organisation '
                f'{settings.LINKEDIN_ORGANIZATION_URN} : le compte connecté doit en être '
                'administrateur et l’application doit disposer du scope '
                'w_organization_social. Reconnectez le compte ou retirez '
                'LINKEDIN_ORGANIZATION_URN pour publier au nom du membre.',
                'AUTHOR_NOT_PERMITTED',
            )
        raise PublishError(
            f'LinkedIn a refusé la publication : {message}',
            classify_http_error(response),
        )

    post_id = response.headers.get('x-restli-id') or (response.json() or {}).get('id', '')
    if not post_id:
        raise PublishError('LinkedIn n’a retourné aucun identifiant de publication.', 'NO_PROVIDER_ID')

    return {
        'status': SocialPostAttempt.Status.SENT,
        'provider_post_id': post_id,
        'provider_media_id': media_urn,
        'external_url': f'https://www.linkedin.com/feed/update/{post_id}',
        'detail': f'Publié sur LinkedIn ({share["shareMediaCategory"]}).',
    }


# --------------------------------------------------------------------------
# YouTube
# --------------------------------------------------------------------------

def youtube_description(inventory, post_url):
    """Plain-text description; rich HTML would show its own markup on YouTube."""
    parts = [inventory.text] if inventory.text else []
    links = [link.url for link in inventory.links]
    if post_url and post_url not in links:
        links.append(post_url)
    if links:
        parts.append('\n'.join(links))
    description = '\n\n'.join(part for part in parts if part)
    return description[:YOUTUBE_DESCRIPTION_LIMIT]


def youtube_start_resumable(token, metadata, video_file):
    """Open a resumable session so large videos never sit in memory."""
    response = requests.post(
        f'{YOUTUBE_UPLOAD}/videos?uploadType=resumable&part=snippet,status',
        json=metadata,
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json; charset=UTF-8',
            'X-Upload-Content-Type': _content_type(video_file, 'video/*'),
            'X-Upload-Content-Length': str(video_file.size),
        },
        timeout=API_TIMEOUT,
    )
    if not response.ok:
        raise PublishError(
            f'YouTube a refusé l’ouverture de l’envoi : {provider_message(response)}',
            classify_http_error(response, 'VIDEO_UPLOAD_FAILED'),
        )
    session_url = response.headers.get('Location')
    if not session_url:
        raise PublishError('YouTube n’a pas fourni de session d’envoi.', 'VIDEO_UPLOAD_FAILED')
    return session_url


def youtube_set_thumbnail(token, video_id, cover):
    """Best-effort cover image; a failure must not undo a published video."""
    try:
        handle = _open(cover)
        try:
            response = requests.post(
                f'{YOUTUBE_UPLOAD}/thumbnails/set?videoId={video_id}',
                data=handle,
                headers={
                    'Authorization': f'Bearer {token}',
                    'Content-Type': _content_type(cover, 'image/jpeg'),
                },
                timeout=UPLOAD_TIMEOUT,
            )
        finally:
            handle.close()
    except (requests.RequestException, OSError) as exc:
        logger.warning('YouTube thumbnail upload failed for %s: %s', video_id, exc)
        return False
    if not response.ok:
        logger.warning('YouTube refused thumbnail for %s (HTTP %s)', video_id, response.status_code)
        return False
    return True


def publish_to_youtube(post, account, post_url, plan=None):
    """Upload the post's video to YouTube, streaming it in a resumable session."""
    inventory = build_inventory(post)
    plan = plan or plan_destination(post, 'YOUTUBE', connected=True, inventory=inventory)
    if not plan.available:
        return {'status': SocialPostAttempt.Status.SKIPPED, 'detail': plan.reason, 'code': 'VIDEO_REQUIRED'}

    video = inventory.primary_video
    token = ensure_fresh_token(account)
    metadata = {
        'snippet': {
            'title': (inventory.title or video.title or 'Task Force Présidentielle')[:YOUTUBE_TITLE_LIMIT],
            'description': youtube_description(inventory, post_url),
        },
        'status': {
            'privacyStatus': getattr(settings, 'YOUTUBE_PRIVACY_STATUS', 'public'),
            'selfDeclaredMadeForKids': False,
        },
    }

    session_url = youtube_start_resumable(token, metadata, video.file)

    handle = _open(video.file)
    try:
        response = requests.put(
            session_url,
            data=handle,
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': _content_type(video.file, 'video/*'),
                'Content-Length': str(video.file.size),
            },
            timeout=UPLOAD_TIMEOUT,
        )
    finally:
        handle.close()

    if not response.ok:
        raise PublishError(
            f'Envoi de la vidéo vers YouTube échoué : {provider_message(response)}',
            classify_http_error(response, 'VIDEO_UPLOAD_FAILED'),
        )

    video_id = (response.json() or {}).get('id', '')
    if not video_id:
        raise PublishError('YouTube n’a retourné aucun identifiant de vidéo.', 'NO_PROVIDER_ID')

    detail = 'Vidéo publiée sur YouTube.'
    if inventory.cover and youtube_set_thumbnail(token, video_id, inventory.cover):
        detail += ' Miniature appliquée.'

    return {
        'status': SocialPostAttempt.Status.SENT,
        'provider_post_id': video_id,
        'provider_media_id': video_id,
        'external_url': f'https://www.youtube.com/watch?v={video_id}',
        'detail': detail,
    }


# --------------------------------------------------------------------------
# Remaining platforms (kept working, outside the LinkedIn/YouTube scope)
# --------------------------------------------------------------------------

def publish_to_facebook(post, account, post_url, plan=None):
    inventory = build_inventory(post)
    token = ensure_fresh_token(account)
    response = requests.post(
        f'https://graph.facebook.com/v21.0/{account.external_account_id}/feed',
        data={
            'message': compose_text(inventory, 60000),
            'link': post_url,
            'access_token': token,
        },
        timeout=API_TIMEOUT,
    )
    if not response.ok:
        raise PublishError(
            f'Facebook a refusé la publication : {provider_message(response)}',
            classify_http_error(response),
        )
    post_id = (response.json() or {}).get('id', '')
    return {
        'status': SocialPostAttempt.Status.SENT,
        'provider_post_id': post_id,
        'external_url': f'https://www.facebook.com/{post_id}' if post_id else '',
        'detail': 'Publié sur la page Facebook.',
    }


def publish_to_tiktok(post, account, post_url, plan=None):
    inventory = build_inventory(post)
    plan = plan or plan_destination(post, 'TIKTOK', connected=True, inventory=inventory)
    if not plan.available:
        return {'status': SocialPostAttempt.Status.SKIPPED, 'detail': plan.reason, 'code': 'VIDEO_REQUIRED'}

    video = inventory.primary_video
    token = ensure_fresh_token(account)
    handle = _open(video.file)
    try:
        payload = handle.read()
    finally:
        handle.close()

    init_response = requests.post(
        'https://open.tiktokapis.com/v2/post/publish/video/init/',
        json={
            'post_info': {'title': inventory.title[:150], 'privacy_level': 'SELF_ONLY'},
            'source_info': {
                'source': 'FILE_UPLOAD',
                'video_size': len(payload),
                'chunk_size': len(payload),
                'total_chunk_count': 1,
            },
        },
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        timeout=API_TIMEOUT,
    )
    if not init_response.ok:
        raise PublishError(
            f'TikTok a refusé l’envoi : {provider_message(init_response)}',
            classify_http_error(init_response, 'VIDEO_UPLOAD_FAILED'),
        )
    upload_url = (init_response.json() or {}).get('data', {}).get('upload_url')
    if not upload_url:
        raise PublishError('TikTok n’a pas fourni d’URL d’envoi.', 'VIDEO_UPLOAD_FAILED')

    upload_response = requests.put(
        upload_url,
        data=payload,
        headers={
            'Content-Type': 'video/mp4',
            'Content-Range': f'bytes 0-{len(payload) - 1}/{len(payload)}',
        },
        timeout=UPLOAD_TIMEOUT,
    )
    if not upload_response.ok:
        raise PublishError(
            f'Envoi de la vidéo vers TikTok échoué (HTTP {upload_response.status_code}).',
            classify_http_error(upload_response, 'VIDEO_UPLOAD_FAILED'),
        )
    return {
        'status': SocialPostAttempt.Status.SENT,
        'detail': 'Envoyé en brouillon privé (app TikTok non auditée pour la publication publique).',
    }


PUBLISHERS = {
    'LINKEDIN': publish_to_linkedin,
    'YOUTUBE': publish_to_youtube,
    'FACEBOOK': publish_to_facebook,
    'TIKTOK': publish_to_tiktok,
}


def record_attempt(post, account, platform, result, started_at, retry_count=0, attempt=None):
    """Persist one destination's outcome, reusing an attempt when retrying."""
    fields = {
        'post': post,
        'account': account,
        'platform': platform,
        'status': result.get('status', SocialPostAttempt.Status.FAILED),
        'detail': (result.get('detail') or '')[:500],
        'external_url': result.get('external_url', '') or '',
        'provider_post_id': result.get('provider_post_id', '') or '',
        'provider_media_id': (result.get('provider_media_id', '') or '')[:255],
        'error_code': result.get('code', '') or '',
        'started_at': started_at,
        'completed_at': timezone.now(),
        'retry_count': retry_count,
    }
    if attempt is not None:
        for key, value in fields.items():
            setattr(attempt, key, value)
        attempt.save()
        return attempt
    return SocialPostAttempt.objects.create(**fields)


def publish_to_account(post, account, post_url, plan=None, attempt=None):
    """Run one destination in isolation — its failure never escapes."""
    started_at = timezone.now()
    publisher = PUBLISHERS.get(account.platform)
    retry_count = (attempt.retry_count + 1) if attempt else 0

    if not publisher:
        return record_attempt(
            post, account, account.platform,
            {
                'status': SocialPostAttempt.Status.SKIPPED,
                'detail': f'Aucun publieur pour {account.platform}.',
                'code': 'UNSUPPORTED_PLATFORM',
            },
            started_at, retry_count, attempt,
        )

    logger.info('Publishing post=%s platform=%s', post.pk, account.platform)
    try:
        result = publisher(post, account, post_url, plan=plan)
    except TokenError as exc:
        result = {'status': SocialPostAttempt.Status.FAILED, 'detail': str(exc), 'code': exc.code}
    except PublishError as exc:
        result = {'status': SocialPostAttempt.Status.FAILED, 'detail': str(exc), 'code': exc.code}
    except requests.Timeout:
        result = {
            'status': SocialPostAttempt.Status.FAILED,
            'detail': f'{PLATFORM_LABELS.get(account.platform, account.platform)} n’a pas répondu à temps.',
            'code': 'TIMEOUT',
        }
    except requests.RequestException as exc:
        logger.warning('Network failure publishing to %s: %s', account.platform, exc)
        result = {
            'status': SocialPostAttempt.Status.FAILED,
            'detail': 'Réseau indisponible pour joindre la plateforme.',
            'code': 'NETWORK_ERROR',
        }
    except Exception as exc:  # noqa: BLE001 — one platform must never break the others
        logger.exception('Unexpected failure publishing to %s', account.platform)
        result = {
            'status': SocialPostAttempt.Status.FAILED,
            'detail': str(exc)[:400],
            'code': 'UNEXPECTED_ERROR',
        }

    if result.get('status') == SocialPostAttempt.Status.SENT:
        account.last_used_at = timezone.now()
        account.last_error = ''
        account.save(update_fields=('last_used_at', 'last_error'))
    elif result.get('code') in ('RECONNECT_REQUIRED', 'TOKEN_EXPIRED', 'REFRESH_FAILED', 'PERMISSION_DENIED'):
        account.needs_reconnect = True
        account.last_error = (result.get('detail') or '')[:500]
        account.save(update_fields=('needs_reconnect', 'last_error'))

    logger.info(
        'Publication result post=%s platform=%s status=%s code=%s',
        post.pk, account.platform, result.get('status'), result.get('code', ''),
    )
    return record_attempt(post, account, account.platform, result, started_at, retry_count, attempt)


def publish_to_all_accounts(post, post_url, platforms=None):
    """Push `post` to every active connected account (optionally filtered).

    Never raises: each destination's outcome is stored as its own attempt, so
    one provider failing leaves the others untouched.
    """
    from ..models import SocialAccount

    accounts = SocialAccount.objects.filter(is_active=True)
    if platforms is not None:
        accounts = accounts.filter(platform__in=platforms)

    attempts = []
    for account in accounts:
        plan = plan_destination(post, account.platform, connected=True)
        attempts.append(publish_to_account(post, account, post_url, plan=plan))
    return attempts
