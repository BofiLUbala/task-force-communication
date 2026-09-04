from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    EditorImageUploadView,
    ContactMessageView,
    NewsletterSubscribeView,
    NewsletterUnsubscribeView,
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
    path('contact/', ContactMessageView.as_view(), name='contact-message'),
    path('social-accounts/oauth/<str:platform>/start/', SocialOAuthStartView.as_view(), name='social-oauth-start'),
    path('social-accounts/oauth/<str:platform>/callback/', SocialOAuthCallbackView.as_view(), name='social-oauth-callback'),
    path('editor-images/', EditorImageUploadView.as_view(), name='editor-image-upload'),
    path('newsletter/subscribe/', NewsletterSubscribeView.as_view(), name='newsletter-subscribe'),
    path('newsletter/unsubscribe/<uuid:token>/', NewsletterUnsubscribeView.as_view(), name='newsletter-unsubscribe'),
]
