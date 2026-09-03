import uuid

from django.conf import settings
from django.db import models


def report_upload_path(instance, filename):
    return f'reports/{instance.report.id}/{filename}'


def public_upload_path(instance, filename):
    return f'public/{instance.post.id}/{filename}'


def editor_upload_path(instance, filename):
    return f'editor/{instance.uploaded_by_id}/{filename}'


class EditorImage(models.Model):
    """An image inserted inline into a rich-text editor (news body, etc.)."""

    file = models.ImageField(upload_to=editor_upload_path)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='editor_images',
    )
    created_at = models.DateTimeField(auto_now_add=True)


class Report(models.Model):
    """A field report submitted by an agent, awaiting hierarchy validation."""

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'En attente'
        VALIDATED = 'VALIDATED', 'Validé'
        REJECTED = 'REJECTED', 'Rejeté'

    client_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports',
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    incident_type = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=255, blank=True)
    occurred_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_reports',
    )
    review_comment = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.title} ({self.get_status_display()})'


class ReportMedia(models.Model):
    class MediaType(models.TextChoices):
        PHOTO = 'PHOTO', 'Photo'
        VIDEO = 'VIDEO', 'Vidéo'
        DOCUMENT = 'DOCUMENT', 'Document'

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='media_files')
    file = models.FileField(upload_to=report_upload_path)
    media_type = models.CharField(max_length=20, choices=MediaType.choices)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.media_type} - {self.report.title}'


class PublicPost(models.Model):
    """Official content published on the public showcase site."""

    class Category(models.TextChoices):
        COMMUNIQUE = 'COMMUNIQUE', 'Communiqué'
        ACTUALITE = 'ACTUALITE', 'Actualité'
        ACTIVITE = 'ACTIVITE', 'Activité'

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    category = models.CharField(max_length=20, choices=Category.choices)
    excerpt = models.CharField(max_length=500, blank=True)
    body = models.TextField()
    cover_image = models.ImageField(upload_to='covers/', null=True, blank=True)
    attachment = models.FileField(upload_to='communiques/', null=True, blank=True)

    source_report = models.ForeignKey(
        Report, on_delete=models.SET_NULL, null=True, blank=True, related_name='publications',
    )
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='publications',
    )
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-published_at', '-created_at')

    def __str__(self):
        return self.title


class SocialMediaLink(models.Model):
    """A social network link shown prominently on the public homepage."""

    name = models.CharField(max_length=100)
    url = models.URLField(max_length=500)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='social_links',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('order', 'created_at')

    def __str__(self):
        return self.name


class SocialAccount(models.Model):
    """An OAuth-connected social network account used for auto-publishing."""

    class Platform(models.TextChoices):
        LINKEDIN = 'LINKEDIN', 'LinkedIn'
        YOUTUBE = 'YOUTUBE', 'YouTube'
        TIKTOK = 'TIKTOK', 'TikTok'
        FACEBOOK = 'FACEBOOK', 'Facebook'

    platform = models.CharField(max_length=20, choices=Platform.choices)
    account_name = models.CharField(max_length=255, blank=True)
    external_account_id = models.CharField(max_length=255, blank=True)
    access_token = models.TextField()
    refresh_token = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    connected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='social_accounts',
    )
    connected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('platform',)

    def __str__(self):
        return f'{self.get_platform_display()} - {self.account_name or self.external_account_id}'


class SocialPostAttempt(models.Model):
    """Records the result of pushing a PublicPost to a connected social account."""

    class Status(models.TextChoices):
        SENT = 'SENT', 'Envoyé'
        FAILED = 'FAILED', 'Échec'
        SKIPPED = 'SKIPPED', 'Ignoré'

    post = models.ForeignKey(PublicPost, on_delete=models.CASCADE, related_name='social_attempts')
    account = models.ForeignKey(SocialAccount, on_delete=models.CASCADE, related_name='post_attempts')
    status = models.CharField(max_length=20, choices=Status.choices)
    detail = models.CharField(max_length=500, blank=True)
    external_url = models.URLField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.account.platform} - {self.post.title} - {self.status}'


class PublicMedia(models.Model):
    class MediaType(models.TextChoices):
        PHOTO = 'PHOTO', 'Photo'
        VIDEO = 'VIDEO', 'Vidéo'

    post = models.ForeignKey(PublicPost, on_delete=models.CASCADE, related_name='gallery')
    file = models.FileField(upload_to=public_upload_path)
    media_type = models.CharField(max_length=20, choices=MediaType.choices)
    caption = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f'{self.media_type} - {self.post.title}'
