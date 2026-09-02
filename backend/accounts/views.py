from django.db import transaction
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import OneTimeToken
from .serializers import (
    EmailTokenSerializer,
    ExpoPushTokenSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    TaskForceTokenObtainPairSerializer,
    UserSerializer,
)
from .tokens import consume_one_time_token, send_password_reset_email, send_verification_email

User = get_user_model()


class LoginView(TokenObtainPairView):
    """Login for both agents and hierarchy — role is embedded in the JWT."""
    serializer_class = TaskForceTokenObtainPairSerializer


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


class RegisterView(APIView):
    permission_classes = (permissions.AllowAny,)

    @transaction.atomic
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        send_verification_email(user)
        return Response(
            {'detail': 'Compte créé. Consultez votre e-mail pour l’activer dans les 48 heures.'},
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
        user.is_active = True
        user.is_active_agent = True
        user.save(update_fields=('is_active', 'is_active_agent'))
        return Response({'detail': 'Votre compte est activé. Vous pouvez maintenant vous connecter.'})


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
