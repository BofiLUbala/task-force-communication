from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        AGENT = 'AGENT', 'Agent terrain'
        HIERARCHY = 'HIERARCHY', 'Hiérarchie'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.AGENT)
    matricule = models.CharField(max_length=50, unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=30, blank=True)
    unit = models.CharField(max_length=100, blank=True)
    expo_push_token = models.CharField(max_length=255, blank=True)
    is_active_agent = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.get_full_name() or self.username} ({self.get_role_display()})'

    @property
    def is_hierarchy(self):
        return self.role == self.Role.HIERARCHY


class OneTimeToken(models.Model):
    class Purpose(models.TextChoices):
        EMAIL_VERIFICATION = 'EMAIL_VERIFICATION', "Confirmation d’adresse e-mail"
        PASSWORD_RESET = 'PASSWORD_RESET', 'Réinitialisation du mot de passe'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='one_time_tokens')
    purpose = models.CharField(max_length=30, choices=Purpose.choices)
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=('purpose', 'token_hash'), name='accounts_on_purpose_02cdec_idx')]

    @property
    def is_used(self):
        return self.used_at is not None
