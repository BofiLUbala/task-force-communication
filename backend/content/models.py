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
        NEWSLETTER = 'NEWSLETTER', 'Newsletter'

    class Audience(models.TextChoices):
        EVERYONE = 'EVERYONE', 'Tout le monde'
        ALL_AGENTS = 'ALL_AGENTS', 'Tous les agents'
        HIERARCHY_ONLY = 'HIERARCHY_ONLY', 'Hiérarchie uniquement'
        SPECIFIC_GROUP = 'SPECIFIC_GROUP', 'Une unité précise'
        SPECIFIC_USERS = 'SPECIFIC_USERS', 'Des personnes précises'

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Brouillon'
        SCHEDULED = 'SCHEDULED', 'Programmée'
        PROCESSING = 'PROCESSING', 'Diffusion en cours'
        PUBLISHED = 'PUBLISHED', 'Publiée'
        PARTIAL = 'PARTIAL_SUCCESS', 'Publiée partiellement'
        FAILED = 'FAILED', 'Échec de diffusion'

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    category = models.CharField(max_length=20, choices=Category.choices)
    excerpt = models.CharField(max_length=500, blank=True)
    body = models.TextField()
    cover_image = models.ImageField(upload_to='covers/', null=True, blank=True)
    attachment = models.FileField(upload_to='communiques/', null=True, blank=True)
    newsletter_subject = models.CharField(max_length=255, blank=True)
    newsletter_preview_text = models.CharField(max_length=255, blank=True)
    newsletter_sender_name = models.CharField(max_length=150, blank=True)
    newsletter_sent_at = models.DateTimeField(null=True, blank=True)
    newsletter_recipient_count = models.PositiveIntegerField(default=0)

    # Who the publication is for. EVERYONE is the historical behaviour and
    # stays the default, so posts created before targeting existed keep being
    # visible exactly as they were.
    audience = models.CharField(
        max_length=20, choices=Audience.choices, default=Audience.EVERYONE,
    )
    #: Used when audience is SPECIFIC_GROUP — matched against `User.unit`.
    audience_unit = models.CharField(max_length=100, blank=True)
    audience_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name='targeted_publications',
    )
    #: Channels the author asked for, kept so a retry knows the original intent.
    channels = models.JSONField(default=list, blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    source_report = models.ForeignKey(
        Report, on_delete=models.SET_NULL, null=True, blank=True, related_name='publications',
    )
    # Deleting a staff account purges everything they produced, published
    # content included — the platform's agreed retention rule.
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, related_name='publications',
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
    needs_reconnect = models.BooleanField(default=False)
    last_error = models.CharField(max_length=500, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
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
    """Audit trail of one publication pushed to one destination.

    `platform` is denormalised so the history survives an account being
    disconnected and deleted — an attempt is a record of what happened, and
    must stay readable afterwards.
    """

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'En attente'
        PROCESSING = 'PROCESSING', 'En cours'
        SENT = 'SENT', 'Envoyé'
        FAILED = 'FAILED', 'Échec'
        SKIPPED = 'SKIPPED', 'Ignoré'

    post = models.ForeignKey(PublicPost, on_delete=models.CASCADE, related_name='social_attempts')
    account = models.ForeignKey(
        SocialAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name='post_attempts',
    )
    platform = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices)
    detail = models.CharField(max_length=500, blank=True)
    external_url = models.URLField(max_length=500, blank=True)

    provider_post_id = models.CharField(max_length=255, blank=True)
    provider_media_id = models.CharField(max_length=255, blank=True)
    error_code = models.CharField(max_length=60, blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.platform} - {self.post.title} - {self.status}'

    def save(self, *args, **kwargs):
        if not self.platform and self.account_id:
            self.platform = self.account.platform
        super().save(*args, **kwargs)

    @property
    def platform_display(self):
        try:
            return SocialAccount.Platform(self.platform).label
        except ValueError:
            return self.platform or 'Site web'


class PublicMedia(models.Model):
    """An attachment carried by a publication.

    Historically photos and videos only; documents and audio were added so a
    single post can hold the full mix (text + images + video + PDF + links)
    that the social adapters then trim down per destination.
    """

    class MediaType(models.TextChoices):
        PHOTO = 'PHOTO', 'Photo'
        VIDEO = 'VIDEO', 'Vidéo'
        DOCUMENT = 'DOCUMENT', 'Document'
        AUDIO = 'AUDIO', 'Audio'

    post = models.ForeignKey(PublicPost, on_delete=models.CASCADE, related_name='gallery')
    file = models.FileField(upload_to=public_upload_path)
    media_type = models.CharField(max_length=20, choices=MediaType.choices)
    title = models.CharField(max_length=255, blank=True)
    caption = models.CharField(max_length=255, blank=True)
    alt_text = models.CharField(max_length=255, blank=True)
    social_links = models.JSONField(default=list, blank=True)

    original_filename = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)
    file_size = models.PositiveBigIntegerField(default=0)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    thumbnail = models.ImageField(upload_to='thumbnails/', null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        ordering = ('order', 'id')

    def __str__(self):
        return f'{self.media_type} - {self.post.title}'

    @property
    def is_image(self):
        return self.media_type == self.MediaType.PHOTO

    @property
    def is_video(self):
        return self.media_type == self.MediaType.VIDEO

    @property
    def is_document(self):
        return self.media_type == self.MediaType.DOCUMENT


class PostLink(models.Model):
    """An external URL carried by a publication (site, article, resource)."""

    post = models.ForeignKey(PublicPost, on_delete=models.CASCADE, related_name='links')
    url = models.URLField(max_length=1000)
    label = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('order', 'id')

    def __str__(self):
        return self.label or self.url


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150, blank=True)
    unsubscribe_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('-subscribed_at',)

    def __str__(self):
        return self.email


class NewsletterDelivery(models.Model):
    class Status(models.TextChoices):
        SENT = 'SENT', 'Envoyé'
        FAILED = 'FAILED', 'Échec'

    post = models.ForeignKey(PublicPost, on_delete=models.CASCADE, related_name='newsletter_deliveries')
    subscriber = models.ForeignKey(NewsletterSubscriber, on_delete=models.CASCADE, related_name='deliveries')
    status = models.CharField(max_length=10, choices=Status.choices)
    error = models.CharField(max_length=500, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-sent_at',)
        constraints = [models.UniqueConstraint(fields=('post', 'subscriber'), name='unique_newsletter_delivery')]


class PublicationDelivery(models.Model):
    """One publication's outcome on one distribution channel.

    This is the per-channel roll-up the dashboard reads. The blow-by-blow
    detail still lives where it always did: `SocialPostAttempt` for the social
    providers, `RecipientDelivery` for the per-person channels. Keeping the
    roll-up separate is what lets a publication say "Email: 2 340 delivered,
    LinkedIn: failed, YouTube: skipped" without scanning thousands of rows.
    """

    class Channel(models.TextChoices):
        WEB = 'WEB', 'Site / App Web'
        MOBILE = 'MOBILE', 'Application mobile'
        EMAIL = 'EMAIL', 'E-mail'
        WHATSAPP = 'WHATSAPP', 'WhatsApp'
        LINKEDIN = 'LINKEDIN', 'LinkedIn'
        YOUTUBE = 'YOUTUBE', 'YouTube'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'En attente'
        PROCESSING = 'PROCESSING', 'En cours'
        SUCCESS = 'SUCCESS', 'Réussi'
        FAILED = 'FAILED', 'Échec'
        SKIPPED = 'SKIPPED', 'Ignoré'

    post = models.ForeignKey(PublicPost, on_delete=models.CASCADE, related_name='deliveries')
    channel = models.CharField(max_length=20, choices=Channel.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    provider = models.CharField(max_length=50, blank=True)
    external_id = models.CharField(max_length=255, blank=True)
    external_url = models.URLField(max_length=500, blank=True)
    error_code = models.CharField(max_length=60, blank=True)
    error_message = models.CharField(max_length=500, blank=True)
    detail = models.CharField(max_length=500, blank=True)

    recipient_count = models.PositiveIntegerField(default=0)
    success_count = models.PositiveIntegerField(default=0)
    failure_count = models.PositiveIntegerField(default=0)

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('channel',)
        constraints = [
            models.UniqueConstraint(fields=('post', 'channel'), name='unique_publication_delivery'),
        ]

    def __str__(self):
        return f'{self.channel} - {self.post.title} - {self.status}'

    @property
    def channel_label(self):
        try:
            return self.Channel(self.channel).label
        except ValueError:
            return self.channel

    @property
    def is_retryable(self):
        """A retry is only safe where nothing has already reached a person.

        A successful channel is never re-run: re-sending 2 000 e-mails or
        duplicating a LinkedIn post is worse than the failure it would fix.
        """
        return self.status == self.Status.FAILED and not self.external_id


class RecipientDelivery(models.Model):
    """Per-person outcome for the channels that address people individually.

    `address` (an e-mail or a phone number) carries the uniqueness rather than
    the user, because a publication can reach public newsletter subscribers who
    have no account at all — and because it is the address that must not be
    written to twice.
    """

    class Status(models.TextChoices):
        SUCCESS = 'SUCCESS', 'Envoyé'
        FAILED = 'FAILED', 'Échec'
        SKIPPED = 'SKIPPED', 'Ignoré'

    delivery = models.ForeignKey(
        PublicationDelivery, on_delete=models.CASCADE, related_name='recipients',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='publication_receipts',
    )
    subscriber = models.ForeignKey(
        'NewsletterSubscriber', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='publication_receipts',
    )
    address = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=Status.choices)
    error_code = models.CharField(max_length=60, blank=True)
    error = models.CharField(max_length=500, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-sent_at',)
        constraints = [
            models.UniqueConstraint(fields=('delivery', 'address'), name='unique_recipient_delivery'),
        ]

    def __str__(self):
        return f'{self.address} - {self.status}'


class PublicationRead(models.Model):
    """Marks that a user has opened a publication in the web or mobile app."""

    post = models.ForeignKey(PublicPost, on_delete=models.CASCADE, related_name='reads')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='publication_reads',
    )
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-read_at',)
        constraints = [
            models.UniqueConstraint(fields=('post', 'user'), name='unique_publication_read'),
        ]

    def __str__(self):
        return f'{self.user} a lu {self.post.title}'
