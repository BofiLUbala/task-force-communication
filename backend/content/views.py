import secrets

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.services import notify_hierarchy_new_report, notify_agent_report_reviewed

from .models import EditorImage, PublicPost, Report, ReportMedia, SocialAccount, SocialMediaLink
from .permissions import IsHierarchy, IsOwnerAgent
from .serializers import (
    EditorImageSerializer,
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
from .social.publishers import publish_to_all_accounts


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
        if self.action in ('create', 'upload_media'):
            return (permissions.IsAuthenticated(),)
        return (permissions.IsAuthenticated(), IsHierarchy())

    def get_queryset(self):
        qs = PublicPost.objects.all().prefetch_related('gallery', 'social_attempts__account')
        if self.action in ('list', 'retrieve') and not (
            self.request.user.is_authenticated and self.request.user.is_hierarchy
        ):
            qs = qs.filter(is_published=True)
        category = self.request.query_params.get('category')
        return qs.filter(category=category) if category else qs

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
        )

    @action(
        detail=True,
        methods=['post'],
        url_path='upload-media',
        parser_classes=(MultiPartParser, FormParser),
        permission_classes=(permissions.IsAuthenticated,),
    )
    def upload_media(self, request, slug=None):
        post = self.get_object()
        serializer = PublicMediaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(post=post)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=(permissions.IsAuthenticated, IsHierarchy))
    def publish(self, request, slug=None):
        post = self.get_object()
        post.is_published = True
        post.published_at = timezone.now()
        post.published_by = request.user
        post.save()

        category_paths = {
            'COMMUNIQUE': 'actualites',
            'ACTUALITE': 'actualites',
            'ACTIVITE': 'activites',
        }
        post_url = f'{settings.FRONTEND_URL}/{category_paths.get(post.category, "actualites")}'
        publish_to_all_accounts(post, post_url)

        return Response(PublicPostSerializer(post).data)

    @action(detail=True, methods=['get'], permission_classes=(permissions.IsAuthenticated, IsHierarchy))
    def social_attempts(self, request, slug=None):
        post = self.get_object()
        attempts = post.social_attempts.select_related('account')
        return Response(SocialPostAttemptSerializer(attempts, many=True).data)

    @action(detail=True, methods=['post'], url_path='push-social', permission_classes=(permissions.IsAuthenticated,))
    def push_social(self, request, slug=None):
        """Push an already-published post to connected social accounts.
        Called by the frontend once a post (and its media, if any) is fully
        uploaded, so video posts have their file available for YouTube/TikTok."""
        post = self.get_object()
        if not post.is_published:
            return Response({'detail': 'Ce post n’est pas publié.'}, status=status.HTTP_400_BAD_REQUEST)

        category_paths = {'COMMUNIQUE': 'actualites', 'ACTUALITE': 'actualites', 'ACTIVITE': 'activites'}
        post_url = f'{settings.FRONTEND_URL}/{category_paths.get(post.category, "actualites")}'
        attempts = publish_to_all_accounts(post, post_url)
        return Response(SocialPostAttemptSerializer(attempts, many=True).data)


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
        serializer.save(added_by=self.request.user)


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
        connected = {a.platform: a for a in SocialAccount.objects.filter(is_active=True)}
        data = [
            {
                'platform': platform,
                'label': label,
                'configured': social_oauth.is_configured(platform),
                'connected': platform in connected,
                'account_name': connected[platform].account_name if platform in connected else '',
            }
            for platform, label in SocialAccount.Platform.choices
        ]
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
        elif platform == 'FACEBOOK':
            external_account_id, account_name, page_token = social_oauth.get_facebook_page(access_token)
            if page_token:
                access_token = page_token

        SocialAccount.objects.update_or_create(
            platform=platform,
            defaults={
                'access_token': access_token,
                'refresh_token': tokens.get('refresh_token', ''),
                'external_account_id': external_account_id,
                'account_name': account_name,
                'is_active': True,
                'connected_by': request.user if request.user.is_authenticated else None,
            },
        )
        return HttpResponseRedirect(f'{dashboard_url}?social_connected={platform}')
