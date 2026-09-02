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
