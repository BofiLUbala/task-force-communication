import logging
import secrets

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.services import notify_hierarchy_new_report, notify_agent_report_reviewed

from .audience import can_view, feed_queryset, visibility_filter
from .channels import (
    distribute,
    normalise_channels,
    overall_status as channel_overall,
    with_automatic_social,
)
from .models import (
    EditorImage,
    PublicationDelivery,
    PublicationRead,
    NewsletterDelivery,
    NewsletterSubscriber,
    PublicMedia,
    PublicPost,
    Report,
    ReportMedia,
    SocialAccount,
    SocialMediaLink,
    SocialPostAttempt,
)
from .newsletter import send_test, send_to_subscribers
from .permissions import IsHierarchy, IsOwnerAgent, IsOwnerOrHierarchy
from .serializers import (
    ContactMessageSerializer,
    PublicationDeliverySerializer,
    RecipientDeliverySerializer,
    EditorImageSerializer,
    NewsletterDeliverySerializer,
    NewsletterSubscriberSerializer,
    PublicMediaSerializer,
    PublicPostSerializer,
    ReportMediaSerializer,
    ReportReviewSerializer,
    ReportSerializer,
    SocialAccountSerializer,
    SocialMediaLinkSerializer,
    SocialPostAttemptSerializer,
)
from .social import oauth as social_oauth
from .social.capabilities import (
    ALL_CHANNELS,
    EMAIL,
    WEB,
    WEBSITE,
    available_channels,
    plan_publication,
)
from .social.publishers import publish_to_account, publish_to_all_accounts
from .social.tokens import record_expiry
from .validators import guess_media_type, validate_attachment


logger = logging.getLogger(__name__)

CATEGORY_PATHS = {
    'COMMUNIQUE': 'actualites',
    'ACTUALITE': 'actualites',
    'ACTIVITE': 'activites',
    'NEWSLETTER': 'newsletter',
}

SOCIAL_TARGETS = ('LINKEDIN', 'YOUTUBE', 'FACEBOOK', 'TIKTOK')


def public_post_url(post):
    """Canonical page for a publication — the link that travels with shares."""
    return f'{settings.FRONTEND_URL}/publications/{post.slug}'


def connected_platforms():
    return set(
        SocialAccount.objects.filter(is_active=True).values_list('platform', flat=True)
    )


def requested_targets(request):
    """Destinations the user ticked, defaulting to every connected platform."""
    raw = request.data.get('targets')
    if raw in (None, ''):
        return None
    if isinstance(raw, str):
        raw = [item.strip() for item in raw.split(',') if item.strip()]
    return [str(item).upper() for item in raw]


def parse_datetime_field(raw):
    """Parse an ISO datetime from the composer, always timezone-aware."""
    from django.utils.dateparse import parse_datetime

    if not raw:
        return None
    parsed = parse_datetime(str(raw))
    if parsed is None:
        return None
    return timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed


def default_channels(post):
    """What "publish" means when the caller named no channel.

    The apps, plus the social platforms that are added automatically anyway.
    E-mail and WhatsApp are deliberately excluded: writing to thousands of
    inboxes and phones is never something to do by default.
    """
    if post.channels:
        return normalise_channels(post.channels)
    return with_automatic_social([WEB, 'MOBILE'])


def legacy_results(post, deliveries):
    """The pre-delivery-model response shape, still served to older clients.

    A mobile build already installed in the field reads `results` with a
    `WEBSITE` row; dropping it would break those installs on the next deploy.
    """
    rows = []
    for delivery in deliveries:
        if delivery.channel != WEB:
            continue
        rows.append({
            'platform': WEBSITE,
            'platform_display': 'Site Task Force',
            'status': 'SENT' if delivery.status == PublicationDelivery.Status.SUCCESS else delivery.status,
            'detail': delivery.detail,
            'external_url': public_post_url(post),
        })
    rows.extend(
        SocialPostAttemptSerializer(
            post.social_attempts.select_related('account'), many=True,
        ).data
    )
    return rows


def newsletter_permission_error(post, channels, user):
    """Guard the one action the roles genuinely disagree about.

    Anyone may draft a newsletter and publish it to the apps. Actually mailing
    an official newsletter out is a hierarchy act, refused here on the server —
    hiding the button in React would leave the endpoint open to any agent.
    """
    if post.category != PublicPost.Category.NEWSLETTER:
        return None
    if EMAIL not in normalise_channels(channels):
        return None
    if user.is_authenticated and (user.is_hierarchy or user.is_super_admin):
        return None
    return {
        'detail': 'Seule la hiérarchie peut envoyer une newsletter officielle par e-mail.',
        'code': 'NEWSLETTER_FORBIDDEN',
    }


def overall_status(results):
    """PARTIAL_SUCCESS is the honest answer when destinations disagree."""
    states = {result['status'] for result in results}
    if not states or states <= {'SKIPPED'}:
        return 'SKIPPED'
    if 'FAILED' in states and ('SENT' in states or 'SKIPPED' in states):
        return 'PARTIAL_SUCCESS'
    if 'FAILED' in states:
        return 'FAILED'
    return 'SUCCESS'


def run_social_publication(post, targets=None):
    """Publish to each selected social destination, isolated from one another."""
    accounts = {
        account.platform: account
        for account in SocialAccount.objects.filter(is_active=True)
    }
    chosen = [
        platform for platform in (targets or accounts.keys())
        if platform in SOCIAL_TARGETS
    ]
    plans = plan_publication(post, connected_platforms(), targets=chosen)
    post_url = public_post_url(post)

    attempts = []
    for platform in chosen:
        account = accounts.get(platform)
        plan = plans.get(platform)
        if account is None:
            attempts.append(SocialPostAttempt.objects.create(
                post=post, account=None, platform=platform,
                status=SocialPostAttempt.Status.SKIPPED,
                detail=f'Aucun compte {platform} connecté.',
                error_code='NOT_CONNECTED',
            ))
            continue
        attempts.append(publish_to_account(post, account, post_url, plan=plan))
    return attempts


class ReportViewSet(viewsets.ModelViewSet):
    """
    Agents: create reports, see only their own.
    Hierarchy: see all reports, validate/reject.
    """
    serializer_class = ReportSerializer
    permission_classes = (permissions.IsAuthenticated, IsOwnerAgent)

    def get_queryset(self):
        user = self.request.user
        qs = Report.objects.all().prefetch_related('media_files')
        if user.is_hierarchy:
            status_filter = self.request.query_params.get('status')
            return qs.filter(status=status_filter) if status_filter else qs
        return qs.filter(submitted_by=user)

    def perform_create(self, serializer):
        report = serializer.save()
        notify_hierarchy_new_report(report)

    @action(detail=True, methods=['post'], parser_classes=(MultiPartParser, FormParser))
    def upload_media(self, request, pk=None):
        report = self.get_object()
        if report.status != Report.Status.PENDING:
            return Response(
                {'detail': 'Impossible d’ajouter un fichier à un rapport déjà traité.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = ReportMediaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(report=report)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=(permissions.IsAuthenticated, IsHierarchy))
    def review(self, request, pk=None):
        report = self.get_object()
        serializer = ReportReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report.status = (
            Report.Status.VALIDATED
            if serializer.validated_data['action'] == 'VALIDATE'
            else Report.Status.REJECTED
        )
        report.review_comment = serializer.validated_data.get('comment', '')
        report.reviewed_by = request.user
        report.reviewed_at = timezone.now()
        report.save()

        notify_agent_report_reviewed(report)
        return Response(ReportSerializer(report).data)


class PublicPostViewSet(viewsets.ModelViewSet):
    """
    Public: anyone can list/retrieve published posts (read-only, no auth).
    Hierarchy: full CRUD, including publishing.
    """
    serializer_class = PublicPostSerializer
    lookup_field = 'slug'

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return (permissions.AllowAny(),)
        if self.action in (
            'create', 'upload_media', 'delete_media', 'push_social', 'publication_plan',
            'feed', 'mark_read', 'deliveries', 'stats', 'audience_options',
        ):
            return (permissions.IsAuthenticated(),)
        # Sending an official newsletter is a hierarchy act, enforced here and
        # not merely by hiding a button in React.
        if self.action in ('send_newsletter', 'newsletter_stats'):
            return (permissions.IsAuthenticated(), IsHierarchy())
        if self.action in (
            'update', 'partial_update', 'destroy', 'publish', 'schedule',
            'retry_delivery', 'test_newsletter',
        ):
            return (permissions.IsAuthenticated(), IsOwnerOrHierarchy())
        return (permissions.IsAuthenticated(), IsHierarchy())

    def get_queryset(self):
        from django.db.models import Q

        qs = PublicPost.objects.all().prefetch_related(
            'gallery', 'links', 'deliveries', 'social_attempts__account',
        )
        user = self.request.user

        # Audience is enforced here, in the queryset, so no endpoint can
        # accidentally serve a hierarchy-only publication to an agent.
        if self.action == 'list':
            qs = qs.filter(is_published=True).filter(visibility_filter(user)).distinct()
        elif self.action == 'retrieve' and not (user.is_authenticated and user.is_hierarchy):
            # Drafts stay visible to their own author, who is still writing them.
            visible = Q(is_published=True) & visibility_filter(user)
            if user.is_authenticated:
                visible |= Q(published_by_id=user.id)
            qs = qs.filter(visible).distinct()

        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        exclude_category = self.request.query_params.get('exclude_category')
        return qs.exclude(category=exclude_category) if exclude_category else qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.setdefault('read_post_ids', getattr(self, '_read_post_ids', None))
        return context

    def perform_create(self, serializer):
        title = serializer.validated_data.get('title', '')
        base_slug = slugify(title) or 'publication'
        slug = base_slug
        suffix = 2
        while PublicPost.objects.filter(slug=slug).exists():
            slug = f'{base_slug}-{suffix}'
            suffix += 1
        is_published = serializer.validated_data.get('is_published', False)
        serializer.save(
            published_by=self.request.user,
            slug=slug,
            published_at=timezone.now() if is_published else None,
            # A publication starts as a draft and only becomes PUBLISHED once a
            # channel has actually delivered it — see `channels.distribute`.
            status=PublicPost.Status.PUBLISHED if is_published else PublicPost.Status.DRAFT,
        )

    @action(
        detail=True,
        methods=['post'],
        url_path='upload-media',
        parser_classes=(MultiPartParser, FormParser),
        permission_classes=(permissions.IsAuthenticated,),
    )
    def upload_media(self, request, slug=None):
        """Attach one file. Content is sniffed, not trusted from its name."""
        post = self.get_object()
        upload = request.data.get('file')
        if not upload:
            return Response({'detail': 'Aucun fichier reçu.'}, status=status.HTTP_400_BAD_REQUEST)

        media_type = (request.data.get('media_type') or '').upper() or guess_media_type(upload)
        try:
            mime_type, size, safe_name = validate_attachment(upload, media_type)
        except DjangoValidationError as exc:
            return Response(
                {'detail': exc.messages[0], 'code': 'INVALID_ATTACHMENT'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Keep the QueryDict type: DRF only JSON-decodes string fields such as
        # `social_links` when the input still looks like an HTML form payload.
        payload = request.data.copy()
        payload['media_type'] = media_type
        serializer = PublicMediaSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        next_order = post.gallery.count()
        serializer.save(
            post=post,
            original_filename=safe_name,
            mime_type=mime_type,
            file_size=size,
            order=serializer.validated_data.get('order') or next_order,
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path='media/(?P<media_id>[0-9]+)',
            permission_classes=(permissions.IsAuthenticated, IsOwnerOrHierarchy))
    def delete_media(self, request, slug=None, media_id=None):
        post = self.get_object()
        deleted, _ = PublicMedia.objects.filter(post=post, pk=media_id).delete()
        if not deleted:
            return Response({'detail': 'Pièce jointe introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], url_path='publication-plan',
            permission_classes=(permissions.IsAuthenticated,))
    def publication_plan(self, request, slug=None):
        """What each destination would receive — drives the composer preview.

        Availability comes from `available_channels()`, not from the connected
        social accounts alone: e-mail and WhatsApp are configured through
        settings rather than OAuth, and reporting them as "not connected"
        would grey out channels that in fact deliver.
        """
        post = self.get_object()
        plans = plan_publication(post, available_channels())
        return Response({
            'post': post.slug,
            'destinations': [plan.as_dict() for plan in plans.values()],
        })

    @action(detail=True, methods=['post'], url_path='retry-social',
            permission_classes=(permissions.IsAuthenticated, IsHierarchy))
    def retry_social(self, request, slug=None):
        """Re-run a failed destination without duplicating a successful one."""
        post = self.get_object()
        attempt_id = request.data.get('attempt')
        attempt = post.social_attempts.filter(pk=attempt_id).first() if attempt_id else None
        if attempt is None:
            return Response({'detail': 'Tentative introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        if attempt.provider_post_id:
            return Response(
                {'detail': 'Cette publication a déjà abouti chez le fournisseur.', 'code': 'ALREADY_PUBLISHED'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if attempt.account is None or not attempt.account.is_active:
            return Response(
                {'detail': f'Le compte {attempt.platform} n’est plus connecté.', 'code': 'NOT_CONNECTED'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        refreshed = publish_to_account(
            post, attempt.account, public_post_url(post), attempt=attempt,
        )
        return Response(SocialPostAttemptSerializer(refreshed).data)

    @action(detail=True, methods=['post'])
    def publish(self, request, slug=None):
        """Distribute one publication to the author's channels and, always, to
        the connected social accounts.

        Social platforms are never part of the caller's selection: publish
        once and every connected provider that can carry the content receives
        it, while the ones that cannot record a SKIPPED reason. Each channel
        is run in isolation and records its own delivery, so a LinkedIn
        refusal never un-publishes the web feed or un-sends the e-mails that
        already left.
        """
        post = self.get_object()
        # `targets` is the historical field name; `channels` is the new one.
        raw = request.data.get('channels')
        if raw in (None, ''):
            raw = request.data.get('targets')
        channels = with_automatic_social(
            normalise_channels(raw) or default_channels(post),
        )

        denial = newsletter_permission_error(post, channels, request.user)
        if denial:
            return Response(denial, status=status.HTTP_403_FORBIDDEN)

        deliveries = distribute(post, channels, public_post_url(post), request.user)
        post.refresh_from_db()
        return Response({
            'overall_status': channel_overall(deliveries),
            'deliveries': PublicationDeliverySerializer(deliveries, many=True).data,
            'results': legacy_results(post, deliveries),
            'post': PublicPostSerializer(post, context=self.get_serializer_context()).data,
        })

    @action(detail=True, methods=['post'])
    def schedule(self, request, slug=None):
        """Park a publication for a future date without distributing it yet."""
        post = self.get_object()
        when = parse_datetime_field(request.data.get('scheduled_for'))
        if when is None:
            return Response(
                {'detail': 'Date de programmation invalide.', 'code': 'INVALID_DATE'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if when <= timezone.now():
            return Response(
                {'detail': 'La date de programmation doit être dans le futur.', 'code': 'PAST_DATE'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        channels = normalise_channels(request.data.get('channels')) or post.channels
        denial = newsletter_permission_error(post, channels, request.user)
        if denial:
            return Response(denial, status=status.HTTP_403_FORBIDDEN)

        post.scheduled_for = when
        post.channels = channels
        post.status = PublicPost.Status.SCHEDULED
        post.is_published = False
        post.save(update_fields=('scheduled_for', 'channels', 'status', 'is_published'))
        return Response(PublicPostSerializer(post, context=self.get_serializer_context()).data)

    @action(detail=False, methods=['get'])
    def feed(self, request):
        """The internal feed: only what this user's audience entitles them to.

        Web and mobile both read this endpoint, so the two apps can never
        disagree about who is concerned by a publication.
        """
        queryset = feed_queryset(request.user)
        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        if request.query_params.get('unread') in ('1', 'true', 'True'):
            queryset = queryset.exclude(reads__user=request.user)

        page = self.paginate_queryset(queryset)
        rows = page if page is not None else list(queryset)
        # One query for the whole page instead of one per publication.
        self._read_post_ids = set(
            PublicationRead.objects.filter(user=request.user, post__in=rows)
            .values_list('post_id', flat=True)
        )
        serializer = self.get_serializer(rows, many=True)
        if page is not None:
            response = self.get_paginated_response(serializer.data)
            response.data['unread_count'] = queryset.exclude(reads__user=request.user).count()
            return response
        return Response({
            'count': len(rows),
            'unread_count': queryset.exclude(reads__user=request.user).count(),
            'results': serializer.data,
        })

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, slug=None):
        """Record that this user has opened the publication."""
        post = self.get_object()
        if not can_view(post, request.user):
            return Response({'detail': 'Action non autorisée.'}, status=status.HTTP_403_FORBIDDEN)
        PublicationRead.objects.get_or_create(post=post, user=request.user)
        return Response({'detail': 'Publication marquée comme lue.'})

    @action(detail=True, methods=['get'])
    def deliveries(self, request, slug=None):
        """Per-channel results, with the recipient breakdown where one exists."""
        post = self.get_object()
        if not (request.user.is_hierarchy or post.published_by_id == request.user.id):
            return Response({'detail': 'Action non autorisée.'}, status=status.HTTP_403_FORBIDDEN)

        rows = []
        for delivery in post.deliveries.prefetch_related('recipients__user'):
            data = PublicationDeliverySerializer(delivery).data
            if delivery.channel in (EMAIL, 'WHATSAPP'):
                data['recipients'] = RecipientDeliverySerializer(
                    delivery.recipients.all()[:200], many=True,
                ).data
            rows.append(data)
        return Response({
            'overall_status': post.status,
            'audience': PublicPostSerializer(
                post, context=self.get_serializer_context(),
            ).data['audience_display'],
            'deliveries': rows,
        })

    @action(detail=True, methods=['post'], url_path='deliveries/(?P<delivery_id>[0-9]+)/retry')
    def retry_delivery(self, request, slug=None, delivery_id=None):
        """Re-run one failed channel. Never re-runs one that already worked."""
        post = self.get_object()
        delivery = post.deliveries.filter(pk=delivery_id).first()
        if delivery is None:
            return Response({'detail': 'Diffusion introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        if delivery.status == PublicationDelivery.Status.SUCCESS:
            return Response(
                {'detail': 'Ce canal a déjà abouti ; le relancer enverrait le contenu en double.',
                 'code': 'ALREADY_DELIVERED'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if delivery.external_id:
            return Response(
                {'detail': 'Le fournisseur a déjà créé cette publication.', 'code': 'ALREADY_PUBLISHED'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        denial = newsletter_permission_error(post, [delivery.channel], request.user)
        if denial:
            return Response(denial, status=status.HTTP_403_FORBIDDEN)

        refreshed = distribute(post, [delivery.channel], public_post_url(post), request.user)
        return Response(PublicationDeliverySerializer(refreshed[0]).data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Counters for the publications dashboard."""
        from django.db.models import Count, Q

        qs = PublicPost.objects.all()
        if not request.user.is_hierarchy:
            qs = qs.filter(published_by=request.user)
        return Response({
            'published': qs.filter(is_published=True).count(),
            'drafts': qs.filter(is_published=False, status=PublicPost.Status.DRAFT).count(),
            'scheduled': qs.filter(status=PublicPost.Status.SCHEDULED).count(),
            'failed_deliveries': PublicationDelivery.objects.filter(
                post__in=qs, status=PublicationDelivery.Status.FAILED,
            ).count(),
            'by_category': list(
                qs.values('category').annotate(total=Count('id')).order_by('-total')
            ),
        })

    @action(detail=False, methods=['get'], url_path='audience-options')
    def audience_options(self, request):
        """The pickers the composer needs: units and selectable accounts."""
        from accounts.models import User

        users = User.objects.filter(
            is_active=True, status=User.AccountStatus.ACTIVE,
        ).order_by('first_name', 'username')
        return Response({
            'units': sorted(
                {unit for unit in users.values_list('unit', flat=True) if unit}
            ),
            'users': [
                {
                    'id': user.id,
                    'name': user.get_full_name() or user.username,
                    'role': user.role,
                    'unit': user.unit,
                    'has_email': bool(user.email),
                    'has_phone': bool(user.phone_number),
                }
                for user in users
            ],
            'channels': [
                {'channel': channel, 'available': channel in available_channels() or channel in (WEB, 'MOBILE')}
                for channel in ALL_CHANNELS
            ],
        })

    @action(detail=True, methods=['get'], permission_classes=(permissions.IsAuthenticated, IsHierarchy))
    def social_attempts(self, request, slug=None):
        post = self.get_object()
        attempts = post.social_attempts.select_related('account')
        return Response(SocialPostAttemptSerializer(attempts, many=True).data)

    @action(detail=True, methods=['post'], url_path='push-social', permission_classes=(permissions.IsAuthenticated,))
    def push_social(self, request, slug=None):
        """Push an already-published post to the selected social accounts.

        Called once the post and all its attachments are uploaded, so video
        destinations actually have a file to send.
        """
        post = self.get_object()
        if not post.is_published:
            return Response({'detail': 'Ce post n’est pas publié.'}, status=status.HTTP_400_BAD_REQUEST)

        attempts = run_social_publication(post, requested_targets(request))
        results = SocialPostAttemptSerializer(attempts, many=True).data
        return Response({'overall_status': overall_status(results), 'results': results})

    @action(detail=True, methods=['post'], url_path='send-newsletter',
            permission_classes=(permissions.IsAuthenticated, IsHierarchy))
    def send_newsletter(self, request, slug=None):
        post = self.get_object()
        if post.category != PublicPost.Category.NEWSLETTER:
            return Response({'detail': 'Cette publication n’est pas une newsletter.'}, status=status.HTTP_400_BAD_REQUEST)
        if post.newsletter_sent_at:
            return Response({'detail': 'Cette newsletter a déjà été envoyée.'}, status=status.HTTP_400_BAD_REQUEST)
        sent, failed = send_to_subscribers(post)
        post.is_published = True
        post.published_at = post.published_at or timezone.now()
        post.newsletter_sent_at = timezone.now()
        post.newsletter_recipient_count = sent
        post.save(update_fields=('is_published', 'published_at', 'newsletter_sent_at', 'newsletter_recipient_count'))
        return Response({'sent': sent, 'failed': failed, 'post': PublicPostSerializer(post).data})

    @action(detail=True, methods=['post'], url_path='test-newsletter',
            permission_classes=(permissions.IsAuthenticated, IsOwnerOrHierarchy))
    def test_newsletter(self, request, slug=None):
        """Send the e-mail version of any publication to one address.

        This is the author's preview of what the EMAIL channel will produce,
        so it is no longer restricted to the NEWSLETTER category. Mailing an
        *official newsletter* to the real list stays hierarchy-only, and so
        does testing one, since that is still an official e-mail leaving the
        platform under the newsletter's sender identity.
        """
        post = self.get_object()
        denial = newsletter_permission_error(post, [EMAIL], request.user)
        if denial:
            return Response(denial, status=status.HTTP_403_FORBIDDEN)
        email = request.data.get('email', '').strip()
        if not email:
            return Response({'detail': 'Une adresse e-mail de test est requise.'}, status=status.HTTP_400_BAD_REQUEST)
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        try:
            validate_email(email)
            send_test(post, email)
        except ValidationError:
            return Response({'detail': 'Adresse e-mail invalide.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({'detail': f'Échec de l’envoi test : {exc}'}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({'detail': 'E-mail de test envoyé.'})

    @action(detail=True, methods=['get'], url_path='newsletter-stats',
            permission_classes=(permissions.IsAuthenticated, IsHierarchy))
    def newsletter_stats(self, request, slug=None):
        post = self.get_object()
        if not request.user.is_hierarchy and post.published_by_id != request.user.id:
            return Response({'detail': 'Action non autorisée.'}, status=status.HTTP_403_FORBIDDEN)
        deliveries = post.newsletter_deliveries.select_related('subscriber')
        return Response({
            'recipient_count': post.newsletter_recipient_count,
            'sent': deliveries.filter(status=NewsletterDelivery.Status.SENT).count(),
            'failed': deliveries.filter(status=NewsletterDelivery.Status.FAILED).count(),
            'deliveries': NewsletterDeliverySerializer(deliveries, many=True).data,
        })


class ContactMessageView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        from django.core.mail import EmailMultiAlternatives

        serializer = ContactMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        email = EmailMultiAlternatives(
            subject=f'[Contact site] {data["subject"]}',
            body=f'Nom : {data["name"]}\nE-mail : {data["email"]}\n\n{data["message"]}',
            from_email=settings.DEFAULT_FROM_EMAIL or settings.CONTACT_EMAIL,
            to=[settings.CONTACT_EMAIL],
            reply_to=[data['email']],
        )
        try:
            email.send(fail_silently=False)
        except Exception:
            return Response({'detail': 'Le message n’a pas pu être envoyé. Réessayez plus tard.'}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({'detail': 'Votre message a bien été envoyé.'}, status=status.HTTP_201_CREATED)


class NewsletterSubscribeView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = NewsletterSubscriberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscriber, created = NewsletterSubscriber.objects.get_or_create(
            email=serializer.validated_data['email'].lower(),
            defaults={'name': serializer.validated_data.get('name', '')},
        )
        if not created:
            subscriber.name = serializer.validated_data.get('name', subscriber.name)
            subscriber.is_active = True
            subscriber.unsubscribed_at = None
            subscriber.save(update_fields=('name', 'is_active', 'unsubscribed_at'))
        return Response({'detail': 'Inscription confirmée.'}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class NewsletterUnsubscribeView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, token):
        from django.shortcuts import get_object_or_404
        subscriber = get_object_or_404(NewsletterSubscriber, unsubscribe_token=token)
        subscriber.is_active = False
        subscriber.unsubscribed_at = timezone.now()
        subscriber.save(update_fields=('is_active', 'unsubscribed_at'))
        return Response({'detail': 'Désabonnement confirmé.'})


class EditorImageUploadView(APIView):
    """Upload an image from the rich-text editor toolbar; returns its URL
    for immediate insertion into the editor content."""
    permission_classes = (permissions.IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        serializer = EditorImageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(uploaded_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SocialMediaLinkViewSet(viewsets.ModelViewSet):
    """
    Public: anyone can list the active social media links (shown on the homepage).
    Agents and hierarchy: can add a link. Only hierarchy can edit/deactivate/delete.
    """
    serializer_class = SocialMediaLinkSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return (permissions.AllowAny(),)
        if self.action == 'create':
            return (permissions.IsAuthenticated(),)
        return (permissions.IsAuthenticated(), IsHierarchy())

    def get_queryset(self):
        qs = SocialMediaLink.objects.all()
        if self.action in ('list', 'retrieve') and not (
            self.request.user.is_authenticated and self.request.user.is_hierarchy
        ):
            qs = qs.filter(is_active=True)
        return qs

    def perform_create(self, serializer):
        serializer.save(added_by=self.request.user, is_active=True)


class SocialAccountViewSet(viewsets.ReadOnlyModelViewSet):
    """Connected accounts used to auto-publish to social networks. Any
    authenticated user (agent or hierarchy) can manage connections, since
    only a handful of people use this app; connecting/disconnecting happens
    through the OAuth views below."""
    serializer_class = SocialAccountSerializer
    permission_classes = (permissions.IsAuthenticated,)
    queryset = SocialAccount.objects.all()

    @action(detail=False, methods=['get'])
    def platforms(self, request):
        from .social.tokens import account_health

        connected = {a.platform: a for a in SocialAccount.objects.filter(is_active=True)}
        data = []
        for platform, label in SocialAccount.Platform.choices:
            account = connected.get(platform)
            data.append({
                'platform': platform,
                'label': label,
                'configured': social_oauth.is_configured(platform),
                'connected': account is not None,
                'account_name': account.account_name if account else '',
                'external_account_id': account.external_account_id if account else '',
                'connected_at': account.connected_at if account else None,
                'last_used_at': account.last_used_at if account else None,
                'token_expires_at': account.token_expires_at if account else None,
                # Health tells the operator whether a reconnection is due
                # *before* the next publication fails.
                'health': account_health(account) if account else 'DISCONNECTED',
                'last_error': account.last_error if account else '',
            })
        return Response(data)

    @action(detail=True, methods=['post'])
    def disconnect(self, request, pk=None):
        account = self.get_object()
        account.is_active = False
        account.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SocialOAuthStartView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, platform):
        platform = platform.upper()
        state = secrets.token_urlsafe(24)
        # Stored in the server-side cache rather than the session: the SPA
        # (port 5173) and API (port 8000) are different origins in dev, and
        # browsers don't reliably round-trip a session cookie through the
        # provider's top-level redirect back in that setup.
        cache.set(f'social_oauth_state:{state}', platform, timeout=600)
        try:
            url = social_oauth.authorize_url(platform, state)
        except social_oauth.OAuthError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'authorize_url': url})


class SocialOAuthCallbackView(APIView):
    """Public redirect target for the provider's OAuth callback. Validated
    via the state token stored server-side when the flow started."""
    permission_classes = (permissions.AllowAny,)

    def get(self, request, platform):
        platform = platform.upper()
        code = request.query_params.get('code')
        state = request.query_params.get('state')
        cache_key = f'social_oauth_state:{state}' if state else None
        expected_platform = cache.get(cache_key) if cache_key else None
        dashboard_url = f'{settings.FRONTEND_URL}/espace/reseaux-sociaux'

        if not code or not state or expected_platform != platform:
            return HttpResponseRedirect(f'{dashboard_url}?social_error=state')
        cache.delete(cache_key)

        try:
            tokens = social_oauth.exchange_code(platform, code)
        except social_oauth.OAuthError:
            return HttpResponseRedirect(f'{dashboard_url}?social_error=exchange')

        access_token = tokens.get('access_token', '')
        external_account_id, account_name = '', ''
        if platform == 'LINKEDIN':
            external_account_id, account_name = social_oauth.get_linkedin_identity(access_token)
        elif platform == 'YOUTUBE':
            external_account_id, account_name = social_oauth.get_youtube_channel(access_token)
        elif platform == 'FACEBOOK':
            external_account_id, account_name, page_token = social_oauth.get_facebook_page(access_token)
            if page_token:
                access_token = page_token

        # Google only returns a refresh token on the consent grant; a
        # re-authorisation that skips consent returns none, and overwriting
        # with '' would silently strip the account's only way to stay alive.
        existing = SocialAccount.objects.filter(platform=platform).first()
        refresh_token = tokens.get('refresh_token') or (existing.refresh_token if existing else '')

        account, _ = SocialAccount.objects.update_or_create(
            platform=platform,
            defaults={
                'access_token': access_token,
                'refresh_token': refresh_token,
                'external_account_id': external_account_id,
                'account_name': account_name,
                'is_active': True,
                'needs_reconnect': False,
                'last_error': '',
                'connected_by': request.user if request.user.is_authenticated else None,
            },
        )
        # Without the expiry, the first refresh would only be attempted after a
        # publication had already failed.
        record_expiry(account, tokens)
        account.save(update_fields=('token_expires_at',))
        logger.info('Connected social account platform=%s', platform)
        return HttpResponseRedirect(f'{dashboard_url}?social_connected={platform}')
