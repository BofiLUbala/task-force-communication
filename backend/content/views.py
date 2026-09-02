from django.utils import timezone
from django.utils.text import slugify
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from notifications.services import notify_hierarchy_new_report, notify_agent_report_reviewed

from .models import PublicPost, Report, ReportMedia
from .permissions import IsHierarchy, IsOwnerAgent
from .serializers import (
    PublicPostSerializer,
    ReportMediaSerializer,
    ReportReviewSerializer,
    ReportSerializer,
)


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
        return (permissions.IsAuthenticated(), IsHierarchy())

    def get_queryset(self):
        qs = PublicPost.objects.all().prefetch_related('gallery')
        if self.action in ('list', 'retrieve') and not (
            self.request.user.is_authenticated and self.request.user.is_hierarchy
        ):
            qs = qs.filter(is_published=True)
        category = self.request.query_params.get('category')
        return qs.filter(category=category) if category else qs

    def perform_create(self, serializer):
        title = serializer.validated_data.get('title', '')
        serializer.save(published_by=self.request.user, slug=slugify(title))

    @action(detail=True, methods=['post'], permission_classes=(permissions.IsAuthenticated, IsHierarchy))
    def publish(self, request, slug=None):
        post = self.get_object()
        post.is_published = True
        post.published_at = timezone.now()
        post.published_by = request.user
        post.save()
        return Response(PublicPostSerializer(post).data)
