from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    InvitationAcceptView,
    InvitationDetailView,
    InvitationView,
    LoginView,
    ManagedUserViewSet,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterPushTokenView,
    RegisterView,
    RegistrationStatusView,
    TokenRefreshView,
    VerifyEmailView,
)

router = DefaultRouter()
router.register('users', ManagedUserViewSet, basename='managed-user')

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('login/refresh/', TokenRefreshView.as_view(), name='login-refresh'),
    path('registration-status/', RegistrationStatusView.as_view(), name='registration-status'),
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('invitations/', InvitationView.as_view(), name='invitation-create'),
    path('invitations/detail/', InvitationDetailView.as_view(), name='invitation-detail'),
    path('invitations/accept/', InvitationAcceptView.as_view(), name='invitation-accept'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('me/', MeView.as_view(), name='me'),
    path('me/push-token/', RegisterPushTokenView.as_view(), name='me-push-token'),
] + router.urls
