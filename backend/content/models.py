import uuid

from django.conf import settings
from django.db import models


def report_upload_path(instance, filename):
    return f'reports/{instance.report.id}/{filename}'


def public_upload_path(instance, filename):
    return f'public/{instance.post.id}/{filename}'


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
