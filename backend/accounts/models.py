from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super administrateur'
        HIERARCHY = 'HIERARCHY', 'Hiérarchie'
        AGENT = 'AGENT', 'Agent terrain'

    class AccountStatus(models.TextChoices):
        INVITED = 'INVITED', 'Invitation envoyée'
        PENDING_EMAIL = 'PENDING_EMAIL', 'E-mail à confirmer'
        ACTIVE = 'ACTIVE', 'Actif'
        REVOKED = 'REVOKED', 'Accès révoqué'

    #: How many accounts each staff post may hold. Everything not listed
    #: here (the field agents) is unlimited.
    #:
    #: One technical owner, and two operational leads so the field is never
    #: left unstaffed when one of them is unavailable — both invite agents.
    ROLE_CAPACITY = {
        Role.SUPER_ADMIN: 1,
        Role.HIERARCHY: 2,
    }

    #: Posts with a limited number of seats.
    STAFF_ROLES = tuple(ROLE_CAPACITY)

    #: Posts that exist exactly once. Kept as its own name because "the single
    #: super admin" is a different idea from "a capped post".
    SINGLETON_ROLES = tuple(
        role for role, seats in ROLE_CAPACITY.items() if seats == 1
    )

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.AGENT)
    status = models.CharField(
        max_length=20, choices=AccountStatus.choices, default=AccountStatus.ACTIVE,
    )
    invited_by = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='invited_users',
    )
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

    @property
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN

    @property
    def manageable_roles(self):
        """Roles whose accounts this user may invite, revoke or delete.

        The super admin only ever provisions the single hierarchy account —
        staffing the field is the hierarchy's job, not a technical one.
        """
        if self.is_super_admin:
            return (self.Role.HIERARCHY,)
        if self.is_hierarchy:
            return (self.Role.AGENT,)
        return ()

    def can_manage(self, other):
        return other.role in self.manageable_roles and other.pk != self.pk

    def mark_active(self):
        self.is_active = True
        self.status = self.AccountStatus.ACTIVE
        if self.role == self.Role.AGENT:
            self.is_active_agent = True
        self.save(update_fields=('is_active', 'status', 'is_active_agent'))


class OneTimeToken(models.Model):
    class Purpose(models.TextChoices):
        EMAIL_VERIFICATION = 'EMAIL_VERIFICATION', "Confirmation d’adresse e-mail"
        PASSWORD_RESET = 'PASSWORD_RESET', 'Réinitialisation du mot de passe'
        INVITATION = 'INVITATION', 'Invitation à rejoindre la plateforme'

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
