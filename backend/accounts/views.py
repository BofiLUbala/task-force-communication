from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView as BaseTokenRefreshView

from .models import OneTimeToken
from .permissions import CanManageAccounts
from .provisioning import (
    capacity_error,
    open_registration_role,
    remaining_seats,
    role_post_is_vacant,
)
from .serializers import (
    EmailTokenSerializer,
    ExpoPushTokenSerializer,
    InvitationAcceptSerializer,
    InvitationCreateSerializer,
    ManagedUserSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    TaskForceTokenObtainPairSerializer,
    TaskForceTokenRefreshSerializer,
    UserSerializer,
)
from .tokens import (
    consume_one_time_token,
    peek_one_time_token,
    send_invitation_email,
    send_password_reset_email,
    send_verification_email,
)

User = get_user_model()

CLOSED_REGISTRATION_MESSAGE = (
    'Les inscriptions publiques sont fermées. Les comptes sont désormais créés '
    'uniquement sur invitation de votre responsable.'
)


def revoke_sessions(user):
    """Blacklist every refresh token still held by `user`.

    Access tokens are already rejected as soon as `is_active` flips, since
    SimpleJWT re-checks the flag on every request; this closes the refresh path.
    """
    from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)


class LoginView(TokenObtainPairView):
    """Login for every role — the role is embedded in the JWT."""
    serializer_class = TaskForceTokenObtainPairSerializer


class TokenRefreshView(BaseTokenRefreshView):
    """Refresh endpoint that survives an account being purged mid-session."""
    serializer_class = TaskForceTokenRefreshSerializer


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user


class RegisterPushTokenView(APIView):
    """Field agents register their Expo push token here after login."""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = ExpoPushTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.expo_push_token = serializer.validated_data['expo_push_token']
        request.user.save(update_fields=['expo_push_token'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class RegistrationStatusView(APIView):
    """Tells the signup page whether it is open, and for which post."""
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        role = open_registration_role()
        if role is None:
            return Response({
                'open': False, 'role': None, 'role_label': '',
                'detail': CLOSED_REGISTRATION_MESSAGE,
            })
        return Response({
            'open': True,
            'role': role,
            'role_label': User.Role(role).label,
            'detail': '',
        })


class RegisterView(APIView):
    """Public signup, restricted to whichever staff post still has a free seat."""
    permission_classes = (permissions.AllowAny,)

    @transaction.atomic
    def post(self, request):
        role = open_registration_role()
        if role is None:
            return Response({'detail': CLOSED_REGISTRATION_MESSAGE}, status=status.HTTP_403_FORBIDDEN)

        serializer = RegisterSerializer(data=request.data, context={'role': role})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        send_verification_email(user)
        return Response(
            {
                'role': user.role,
                'role_label': user.get_role_display(),
                'detail': (
                    f'Compte « {user.get_role_display()} » créé. Consultez votre e-mail pour '
                    'l’activer dans les 48 heures.'
                ),
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    permission_classes = (permissions.AllowAny,)

    @transaction.atomic
    def post(self, request):
        serializer = EmailTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = consume_one_time_token(
            serializer.validated_data['token'],
            OneTimeToken.Purpose.EMAIL_VERIFICATION,
        )
        if user is None:
            return Response(
                {'detail': 'Ce lien est invalide, expiré ou a déjà été utilisé.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.mark_active()
        return Response({'detail': 'Votre compte est activé. Vous pouvez maintenant vous connecter.'})


class InvitationView(APIView):
    """Create an account for someone else and e-mail them an activation link.

    The invited role is derived from the inviter's post, never from the
    request: a super admin staffs the hierarchy, the hierarchy staffs the field.
    """

    permission_classes = (permissions.IsAuthenticated, CanManageAccounts)

    @transaction.atomic
    def post(self, request):
        role = request.user.manageable_roles[0]
        full = capacity_error(role)
        if full:
            return Response({'detail': full, 'code': 'ROLE_FULL'},
                            status=status.HTTP_400_BAD_REQUEST)

        serializer = InvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        user = User(
            username=email,
            email=email,
            first_name=serializer.validated_data.get('first_name', ''),
            last_name=serializer.validated_data.get('last_name', ''),
            role=role,
            status=User.AccountStatus.INVITED,
            invited_by=request.user,
            is_active=False,
            is_active_agent=False,
        )
        user.set_unusable_password()
        user.save()
        send_invitation_email(user, request.user)
        return Response(ManagedUserSerializer(user).data, status=status.HTTP_201_CREATED)


class InvitationDetailView(APIView):
    """Read an invitation without consuming it, so the activation page can
    greet the invitee and fail early on a dead link."""

    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        raw_token = request.query_params.get('token', '')
        token = peek_one_time_token(raw_token, OneTimeToken.Purpose.INVITATION) if raw_token else None
        if token is None:
            return Response(
                {'detail': 'Cette invitation est invalide, expirée ou a déjà été utilisée.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({
            'email': token.user.email,
            'first_name': token.user.first_name,
            'last_name': token.user.last_name,
            'role': token.user.role,
            'role_label': token.user.get_role_display(),
            'invited_by': token.user.invited_by.get_full_name() if token.user.invited_by else '',
        })


class InvitationAcceptView(APIView):
    """The invitee sets their own password here; that activates the account."""

    permission_classes = (permissions.AllowAny,)

    @transaction.atomic
    def post(self, request):
        serializer = InvitationAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = consume_one_time_token(data['token'], OneTimeToken.Purpose.INVITATION)
        if user is None:
            return Response(
                {'detail': 'Cette invitation est invalide, expirée ou a déjà été utilisée.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.first_name = data.get('first_name') or user.first_name
        user.last_name = data.get('last_name') or user.last_name
        user.phone_number = data.get('phone_number') or user.phone_number
        user.set_password(data['password'])
        user.save(update_fields=('first_name', 'last_name', 'phone_number', 'password'))
        user.mark_active()
        return Response({'detail': 'Votre compte est activé. Vous pouvez maintenant vous connecter.'})


class ManagedUserViewSet(viewsets.ReadOnlyModelViewSet):
    """Account management restricted to the roles the caller owns."""

    serializer_class = ManagedUserSerializer
    permission_classes = (permissions.IsAuthenticated, CanManageAccounts)

    def get_queryset(self):
        return (
            User.objects.filter(role__in=self.request.user.manageable_roles)
            .select_related('invited_by')
            .order_by('-date_joined')
        )

    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Counts backing the management dashboards."""
        from content.models import PublicPost, Report

        managed_role = request.user.manageable_roles[0]
        managed = self.get_queryset()
        return Response({
            'managed_role': managed_role,
            'managed_role_label': User.Role(managed_role).label,
            'total': managed.count(),
            'by_status': {
                state.value: managed.filter(status=state).count()
                for state in User.AccountStatus
            },
            'post_is_vacant': role_post_is_vacant(managed_role),
            # Seats let the dashboard say "1 place restante" instead of only
            # disabling the button once the post is already full.
            'post_capacity': User.ROLE_CAPACITY.get(managed_role),
            'post_occupied': User.objects.filter(role=managed_role).count(),
            'post_remaining': remaining_seats(managed_role),
            'platform': {
                'agents': User.objects.filter(role=User.Role.AGENT).count(),
                'hierarchy': User.objects.filter(role=User.Role.HIERARCHY).count(),
                'reports': Report.objects.count(),
                'publications': PublicPost.objects.count(),
            },
        })

    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        user = self.get_object()
        if user.status != User.AccountStatus.ACTIVE:
            return Response(
                {'detail': 'Seul un compte actif peut être révoqué.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.is_active = False
        user.is_active_agent = False
        user.status = User.AccountStatus.REVOKED
        user.save(update_fields=('is_active', 'is_active_agent', 'status'))
        revoke_sessions(user)
        return Response(ManagedUserSerializer(user).data)

    @action(detail=True, methods=['post'])
    def reactivate(self, request, pk=None):
        user = self.get_object()
        if user.status != User.AccountStatus.REVOKED:
            return Response(
                {'detail': 'Seul un compte révoqué peut être réactivé.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.mark_active()
        return Response(ManagedUserSerializer(user).data)

    @action(detail=True, methods=['post'], url_path='resend-invitation')
    def resend_invitation(self, request, pk=None):
        user = self.get_object()
        if user.status != User.AccountStatus.INVITED:
            return Response(
                {'detail': 'Ce compte n’est pas en attente d’invitation.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        send_invitation_email(user, request.user)
        return Response({'detail': f'Invitation renvoyée à {user.email}.'})

    @action(detail=True, methods=['delete'], url_path='purge')
    def purge(self, request, pk=None):
        """Hard-delete the account and everything it produced — field reports
        and public publications alike, per the platform's retention rule."""
        user = self.get_object()
        revoke_sessions(user)
        email = user.email
        user.delete()
        return Response({'detail': f'Le compte {email} et toutes ses données ont été supprimés.'})


class PasswordResetRequestView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=serializer.validated_data['email'], is_active=True).first()
        if user:
            send_password_reset_email(user)
        return Response({'detail': 'Si cette adresse correspond à un compte actif, un e-mail a été envoyé.'})


class PasswordResetConfirmView(APIView):
    permission_classes = (permissions.AllowAny,)

    @transaction.atomic
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = consume_one_time_token(
            serializer.validated_data['token'],
            OneTimeToken.Purpose.PASSWORD_RESET,
        )
        if user is None:
            return Response(
                {'detail': 'Ce lien est invalide, expiré ou a déjà été utilisé.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(serializer.validated_data['password'])
        user.save(update_fields=('password',))
        return Response({'detail': 'Votre mot de passe a été modifié.'})
