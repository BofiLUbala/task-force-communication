"""Push a published PublicPost to a connected social account.

LinkedIn accepts text (+ optional image) shares. YouTube and TikTok only
accept video content, so posts without a video attachment are skipped for
those two platforms.
"""
import mimetypes

import requests
from django.conf import settings

from ..models import SocialPostAttempt


def _video_file(post):
    video = post.gallery.filter(media_type='VIDEO').first()
    if video:
        return video.file
    if post.attachment and (mimetypes.guess_type(post.attachment.name)[0] or '').startswith('video'):
        return post.attachment
    return None


def _record(post, account, status, detail='', external_url=''):
    return SocialPostAttempt.objects.create(
        post=post, account=account, status=status, detail=detail[:500], external_url=external_url,
    )


def publish_to_linkedin(post, account, post_url):
    if settings.LINKEDIN_ORGANIZATION_URN:
        author = f'urn:li:organization:{settings.LINKEDIN_ORGANIZATION_URN}'
    elif account.external_account_id:
        author = f'urn:li:person:{account.external_account_id}'
    else:
        return _record(
            post, account, SocialPostAttempt.Status.FAILED,
            detail='Identité LinkedIn introuvable — reconnectez le compte.',
        )
    body = {
        'author': author,
        'lifecycleState': 'PUBLISHED',
        'specificContent': {
            'com.linkedin.ugc.ShareContent': {
                'shareCommentary': {'text': f'{post.title}\n\n{post.excerpt or post.body[:400]}\n\n{post_url}'},
                'shareMediaCategory': 'NONE',
            },
        },
        'visibility': {'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC'},
    }
    resp = requests.post(
        'https://api.linkedin.com/v2/ugcPosts',
        json=body,
        headers={
            'Authorization': f'Bearer {account.access_token}',
            'X-Restli-Protocol-Version': '2.0.0',
        },
        timeout=20,
    )
    if resp.ok:
        return _record(post, account, SocialPostAttempt.Status.SENT, detail=resp.text[:300])
    return _record(post, account, SocialPostAttempt.Status.FAILED, detail=resp.text[:500])


def publish_to_youtube(post, account, post_url):
    video = _video_file(post)
    if not video:
        return _record(post, account, SocialPostAttempt.Status.SKIPPED, detail='Aucune vidéo à publier sur YouTube.')

    metadata = {
        'snippet': {
            'title': post.title[:100],
            'description': f'{post.excerpt or post.body[:400]}\n\n{post_url}',
        },
        'status': {'privacyStatus': 'public'},
    }
    video.open('rb')
    try:
        resp = requests.post(
            'https://www.googleapis.com/upload/youtube/v3/videos'
            '?uploadType=multipart&part=snippet,status',
            headers={'Authorization': f'Bearer {account.access_token}'},
            files={
                'metadata': ('metadata.json', __import__('json').dumps(metadata), 'application/json'),
                'file': (video.name, video, 'video/*'),
            },
            timeout=120,
        )
    finally:
        video.close()

    if resp.ok:
        video_id = resp.json().get('id', '')
        return _record(
            post, account, SocialPostAttempt.Status.SENT,
            detail=resp.text[:300],
            external_url=f'https://www.youtube.com/watch?v={video_id}' if video_id else '',
        )
    return _record(post, account, SocialPostAttempt.Status.FAILED, detail=resp.text[:500])


def publish_to_tiktok(post, account, post_url):
    video = _video_file(post)
    if not video:
        return _record(post, account, SocialPostAttempt.Status.SKIPPED, detail='Aucune vidéo à publier sur TikTok.')

    video.open('rb')
    try:
        video_bytes = video.read()
    finally:
        video.close()

    init_resp = requests.post(
        'https://open.tiktokapis.com/v2/post/publish/video/init/',
        json={
            'post_info': {
                'title': post.title[:150],
                'privacy_level': 'SELF_ONLY',
            },
            'source_info': {
                'source': 'FILE_UPLOAD',
                'video_size': len(video_bytes),
                'chunk_size': len(video_bytes),
                'total_chunk_count': 1,
            },
        },
        headers={
            'Authorization': f'Bearer {account.access_token}',
            'Content-Type': 'application/json',
        },
        timeout=30,
    )
    if not init_resp.ok:
        return _record(post, account, SocialPostAttempt.Status.FAILED, detail=init_resp.text[:500])

    upload_url = init_resp.json().get('data', {}).get('upload_url')
    if not upload_url:
        return _record(post, account, SocialPostAttempt.Status.FAILED, detail=init_resp.text[:500])

    upload_resp = requests.put(
        upload_url,
        data=video_bytes,
        headers={
            'Content-Type': 'video/mp4',
            'Content-Range': f'bytes 0-{len(video_bytes) - 1}/{len(video_bytes)}',
        },
        timeout=120,
    )
    if upload_resp.ok:
        return _record(
            post, account, SocialPostAttempt.Status.SENT,
            detail='Envoyé en brouillon privé (app TikTok non encore auditée pour la publication publique).',
        )
    return _record(post, account, SocialPostAttempt.Status.FAILED, detail=upload_resp.text[:500])


def publish_to_facebook(post, account, post_url):
    resp = requests.post(
        f'https://graph.facebook.com/v21.0/{account.external_account_id}/feed',
        data={
            'message': f'{post.title}\n\n{post.excerpt or post.body[:400]}\n\n{post_url}',
            'access_token': account.access_token,
        },
        timeout=20,
    )
    if resp.ok:
        post_id = resp.json().get('id', '')
        return _record(
            post, account, SocialPostAttempt.Status.SENT,
            detail=resp.text[:300],
            external_url=f'https://www.facebook.com/{post_id}' if post_id else '',
        )
    return _record(post, account, SocialPostAttempt.Status.FAILED, detail=resp.text[:500])


PUBLISHERS = {
    'LINKEDIN': publish_to_linkedin,
    'YOUTUBE': publish_to_youtube,
    'TIKTOK': publish_to_tiktok,
    'FACEBOOK': publish_to_facebook,
}


def publish_to_all_accounts(post, post_url):
    """Push `post` to every active connected account. Never raises —
    failures are recorded as SocialPostAttempt rows instead."""
    from ..models import SocialAccount

    attempts = []
    for account in SocialAccount.objects.filter(is_active=True):
        publisher = PUBLISHERS.get(account.platform)
        if not publisher:
            continue
        try:
            attempts.append(publisher(post, account, post_url))
        except Exception as exc:  # noqa: BLE001 - never let one platform break the others
            attempts.append(_record(post, account, SocialPostAttempt.Status.FAILED, detail=str(exc)))
    return attempts
