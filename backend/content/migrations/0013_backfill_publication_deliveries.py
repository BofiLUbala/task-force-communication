"""Give publications that predate the delivery model an honest history.

Before this change a publication recorded only `is_published` plus, for the
social networks, a `SocialPostAttempt`. The dashboard now reads
`PublicationDelivery`, so without a backfill every existing publication would
render as "never distributed" — which is untrue and would invite someone to
re-send a newsletter that has already gone out.

The backfill only restates what the old columns already asserted. It invents
no success: a channel is written as SUCCESS only where the legacy data says it
happened (`is_published`, `newsletter_sent_at`, an attempt marked SENT).
"""
from django.db import migrations


def backfill(apps, schema_editor):
    PublicPost = apps.get_model('content', 'PublicPost')
    PublicationDelivery = apps.get_model('content', 'PublicationDelivery')
    SocialPostAttempt = apps.get_model('content', 'SocialPostAttempt')

    attempt_status = {'SENT': 'SUCCESS', 'FAILED': 'FAILED', 'SKIPPED': 'SKIPPED'}
    rows = []

    for post in PublicPost.objects.all().iterator():
        channels = []
        post_rows = []

        if post.is_published:
            channels.append('WEB')
            post_rows.append(PublicationDelivery(
                post=post, channel='WEB', status='SUCCESS', provider='TASKFORCE',
                detail='Publication visible sur le site (diffusion historique).',
                completed_at=post.published_at or post.created_at,
            ))

        if post.newsletter_sent_at:
            channels.append('EMAIL')
            post_rows.append(PublicationDelivery(
                post=post, channel='EMAIL', status='SUCCESS', provider='SMTP',
                detail='Newsletter envoyée aux abonnés (diffusion historique).',
                recipient_count=post.newsletter_recipient_count,
                success_count=post.newsletter_recipient_count,
                completed_at=post.newsletter_sent_at,
            ))

        # One row per channel: keep the most recent attempt for each platform,
        # matching the unique (post, channel) constraint.
        latest = {}
        for attempt in SocialPostAttempt.objects.filter(post=post).order_by('created_at'):
            if attempt.platform in ('LINKEDIN', 'YOUTUBE'):
                latest[attempt.platform] = attempt
        for platform, attempt in latest.items():
            channels.append(platform)
            post_rows.append(PublicationDelivery(
                post=post, channel=platform,
                status=attempt_status.get(attempt.status, 'PENDING'),
                provider=platform,
                detail=attempt.detail or '',
                external_id=attempt.provider_post_id or '',
                external_url=attempt.external_url or '',
                error_code=attempt.error_code or '',
                retry_count=attempt.retry_count,
                started_at=attempt.started_at,
                completed_at=attempt.completed_at,
                metadata={'attempt_id': attempt.pk},
            ))

        rows.extend(post_rows)
        statuses = {row.status for row in post_rows}
        if not statuses:
            post.status = 'DRAFT'
        elif statuses == {'SUCCESS'}:
            post.status = 'PUBLISHED'
        elif 'SUCCESS' in statuses:
            post.status = 'PARTIAL_SUCCESS'
        else:
            post.status = 'FAILED'
        post.channels = channels
        post.save(update_fields=('status', 'channels'))

    PublicationDelivery.objects.bulk_create(rows, ignore_conflicts=True)


def unbackfill(apps, schema_editor):
    apps.get_model('content', 'PublicationDelivery').objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0012_publicpost_audience_publicpost_audience_unit_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill, unbackfill),
    ]
