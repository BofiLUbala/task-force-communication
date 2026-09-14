from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer

from .models import User


class TaskForceTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['full_name'] = user.get_full_name() or user.username
        return token

    @staticmethod
    def resolve_identifier(identifier):
        """Map an e-mail address onto the username it belongs to.

        The sign-in form asks for "e-mail address or username", so honour both.
        Accounts created by invitation already use the address as their
        username, but `admin` and any account made with `createsuperuser` do
        not, and were being refused.

        A username match always wins: it is the field the account is keyed on.
        `email` carries no unique constraint at the database level, so an
        address shared by several accounts resolves to nothing at all rather
        than to an arbitrary one of them.
        """
        identifier = (identifier or '').strip()
        if '@' not in identifier:
            return identifier
        if User.objects.filter(username=identifier).exists():
            return identifier
        matches = list(User.objects.filter(email__iexact=identifier)[:2])
        if len(matches) == 1:
            return matches[0].username
        return identifier

    def validate(self, attrs):
        attrs[self.username_field] = self.resolve_identifier(attrs.get(self.username_field))
        data = super().validate(attrs)
        data['role'] = self.user.role
        data['full_name'] = self.user.get_full_name() or self.user.username
        data['user_id'] = self.user.id
        return data


class TaskForceTokenRefreshSerializer(TokenRefreshSerializer):
    """Refuse a refresh token whose account no longer exists.

    SimpleJWT looks the user up with `.get()` and lets `DoesNotExist` escape
    as a 500. Purging an account is a first-class action on this platform, so
    that path is routine: it must answer 401 like any other dead token.
    """

    def validate(self, attrs):
        try:
            return super().validate(attrs)
        except User.DoesNotExist:
            raise AuthenticationFailed(
                self.error_messages['no_active_account'], 'no_active_account',
            )


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id', 'username', 'first_name', 'last_name', 'email',
            'role', 'status', 'matricule', 'phone_number', 'unit', 'is_active_agent',
        )
        read_only_fields = ('id', 'role', 'status')


class ExpoPushTokenSerializer(serializers.Serializer):
    expo_push_token = serializers.CharField(max_length=255)


class ManagedUserSerializer(serializers.ModelSerializer):
    """An account as shown in the super admin / hierarchy management tables."""

    full_name = serializers.SerializerMethodField()
    role_label = serializers.CharField(source='get_role_display', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    invited_by_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'full_name', 'first_name', 'last_name', 'email', 'phone_number',
            'role', 'role_label', 'status', 'status_label',
            'invited_by_name', 'date_joined', 'last_login',
        )

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_invited_by_name(self, obj):
        if not obj.invited_by:
            return ''
        return obj.invited_by.get_full_name() or obj.invited_by.username


class RegisterSerializer(serializers.ModelSerializer):
    """Public signup — only ever used to fill a vacant singleton post.

    The role comes from the view (via ``context['role']``), never from the
    request body, so nobody can pick their own privileges.
    """

    password = serializers.CharField(write_only=True, min_length=8, validators=[validate_password])

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone_number', 'password')

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('Un compte utilise déjà cette adresse e-mail.')
        return email

    def create(self, validated_data):
        password = validated_data.pop('password')
        email = validated_data['email']
        role = self.context['role']
        user = User(
            username=email,
            role=role,
            status=User.AccountStatus.PENDING_EMAIL,
            is_active=False,
            is_active_agent=False,
            **validated_data,
        )
        user.set_password(password)
        user.save()
        return user


class InvitationCreateSerializer(serializers.Serializer):
    """The inviter supplies an e-mail address; the invitee fills in the rest."""

    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('Un compte utilise déjà cette adresse e-mail.')
        return email


class InvitationAcceptSerializer(serializers.Serializer):
    token = serializers.CharField()
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    phone_number = serializers.CharField(max_length=30, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=8, validators=[validate_password])


class EmailTokenSerializer(serializers.Serializer):
    token = serializers.CharField()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(EmailTokenSerializer):
    password = serializers.CharField(write_only=True, min_length=8, validators=[validate_password])
