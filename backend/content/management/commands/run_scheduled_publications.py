"""Distribute the publications whose scheduled time has arrived.

`schedule()` parks a publication with `status=SCHEDULED` and a future
`scheduled_for`, but nothing ever came back for it — a scheduled publication
stayed parked forever. This command is that missing half, meant to be run on a
short interval (a platform cron, or `*/5 * * * *`), and is deliberately the
smallest thing that works: no broker, no worker, no extra infrastructure.

Safe to run concurrently with itself. Claiming a publication is a conditional
UPDATE, so two overlapping runs can never distribute the same one twice.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from ...channels import distribute, overall_status
from ...models import PublicPost


class Command(BaseCommand):
    help = 'Publish every scheduled publication whose time has come.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='List what would be published without distributing anything.',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=20,
            help='Most publications to handle in one run (default: 20).',
        )

    def handle(self, *args, **options):
        from django.conf import settings

        now = timezone.now()
        due = PublicPost.objects.filter(
            status=PublicPost.Status.SCHEDULED,
            scheduled_for__isnull=False,
            scheduled_for__lte=now,
        ).order_by('scheduled_for')[: options['limit']]

        due = list(due)
        if not due:
            self.stdout.write('Aucune publication programmée à diffuser.')
            return

        if options['dry_run']:
            for post in due:
                self.stdout.write(f'[dry-run] {post.slug} — prévue pour {post.scheduled_for}')
            return

        for post in due:
            # Claim it first: the UPDATE only matches while the row is still
            # SCHEDULED, so a second run started a minute later finds nothing
            # and cannot publish the same thing twice.
            claimed = PublicPost.objects.filter(
                pk=post.pk, status=PublicPost.Status.SCHEDULED,
            ).update(status=PublicPost.Status.PROCESSING)
            if not claimed:
                continue

            post.refresh_from_db()
            try:
                deliveries = distribute(
                    post,
                    post.channels,
                    f'{settings.FRONTEND_URL}/publications/{post.slug}',
                )
            except Exception as exc:  # noqa: BLE001 — one post must not stop the run
                PublicPost.objects.filter(pk=post.pk).update(
                    status=PublicPost.Status.FAILED,
                )
                self.stderr.write(f'{post.slug} — échec de diffusion : {exc}')
                continue

            post.refresh_from_db()
            if not post.is_published:
                post.is_published = True
                post.published_at = post.published_at or timezone.now()
                post.save(update_fields=('is_published', 'published_at'))

            self.stdout.write(
                f'{post.slug} — {overall_status(deliveries)} '
                f'({len(deliveries)} canal/canaux)'
            )
