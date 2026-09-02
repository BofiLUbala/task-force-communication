from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password

from .models import User


class TaskForceTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['full_name'] = user.get_full_name() or user.username
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['role'] = self.user.role
        data['full_name'] = self.user.get_full_name() or self.user.username
        data['user_id'] = self.user.id
        return data


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id', 'username', 'first_name', 'last_name', 'email',
            'role', 'matricule', 'phone_number', 'unit', 'is_active_agent',
        )
        read_only_fields = ('id', 'role')


class ExpoPushTokenSerializer(serializers.Serializer):
    expo_push_token = serializers.CharField(max_length=255)


class RegisterSerializer(serializers.ModelSerializer):
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
        user = User(
            username=email,
            role=User.Role.AGENT,
            is_active=False,
            is_active_agent=False,
            **validated_data,
        )
        user.set_password(password)
        user.save()
        return user


class EmailTokenSerializer(serializers.Serializer):
    token = serializers.CharField()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(EmailTokenSerializer):
    password = serializers.CharField(write_only=True, min_length=8, validators=[validate_password])
