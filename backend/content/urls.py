from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    EditorImageUploadView,
    PublicPostViewSet,
    ReportViewSet,
    SocialAccountViewSet,
    SocialMediaLinkViewSet,
    SocialOAuthCallbackView,
    SocialOAuthStartView,
)

router = DefaultRouter()
router.register('reports', ReportViewSet, basename='report')
router.register('posts', PublicPostViewSet, basename='post')
router.register('social-links', SocialMediaLinkViewSet, basename='social-link')
router.register('social-accounts', SocialAccountViewSet, basename='social-account')

urlpatterns = router.urls + [
    path('social-accounts/oauth/<str:platform>/start/', SocialOAuthStartView.as_view(), name='social-oauth-start'),
    path('social-accounts/oauth/<str:platform>/callback/', SocialOAuthCallbackView.as_view(), name='social-oauth-callback'),
    path('editor-images/', EditorImageUploadView.as_view(), name='editor-image-upload'),
]
