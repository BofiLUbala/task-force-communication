import json

from rest_framework import serializers

from .models import (
    EditorImage,
    PublicationDelivery,
    RecipientDelivery,
    NewsletterDelivery,
    NewsletterSubscriber,
    PostLink,
    PublicMedia,
    PublicPost,
    Report,
    ReportMedia,
    SocialAccount,
    SocialMediaLink,
    SocialPostAttempt,
)


class ReportMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportMedia
        fields = ('id', 'file', 'media_type', 'uploaded_at')
        read_only_fields = ('id', 'uploaded_at')


class ReportSerializer(serializers.ModelSerializer):
    media_files = ReportMediaSerializer(many=True, read_only=True)
    submitted_by_name = serializers.CharField(source='submitted_by.get_full_name', read_only=True)

    class Meta:
        model = Report
        fields = (
            'id', 'client_uuid', 'title', 'description', 'incident_type', 'location',
            'occurred_at', 'status', 'review_comment', 'reviewed_at',
            'submitted_by', 'submitted_by_name', 'media_files', 'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'status', 'review_comment', 'reviewed_at', 'submitted_by',
            'submitted_by_name', 'media_files', 'created_at', 'updated_at',
        )

    def create(self, validated_data):
        validated_data['submitted_by'] = self.context['request'].user
        return super().create(validated_data)


class ReportReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=('VALIDATE', 'REJECT'))
    comment = serializers.CharField(required=False, allow_blank=True)


class PublicMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicMedia
        fields = (
            'id', 'file', 'media_type', 'title', 'caption', 'alt_text', 'social_links',
            'original_filename', 'mime_type', 'file_size', 'width', 'height',
            'duration_seconds', 'thumbnail', 'order',
        )
        read_only_fields = (
            'id', 'original_filename', 'mime_type', 'file_size', 'width', 'height',
            'duration_seconds',
        )

    def validate_social_links(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('Les liens sociaux doivent être une liste.')
        cleaned = []
        for link in value:
            if not isinstance(link, dict) or not link.get('url'):
                continue
            url = serializers.URLField().run_validation(link['url'])
            cleaned.append({
                'platform': str(link.get('platform', '')).strip() or 'Lien',
                'url': url,
            })
        return cleaned


class PostLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostLink
        fields = ('id', 'url', 'label', 'order')
        read_only_fields = ('id',)


class PublicationDeliverySerializer(serializers.ModelSerializer):
    """One channel's outcome, as the dashboard and detail page show it."""

    channel_label = serializers.CharField(read_only=True)
    is_retryable = serializers.BooleanField(read_only=True)

    class Meta:
        model = PublicationDelivery
        fields = (
            'id', 'channel', 'channel_label', 'status', 'provider', 'external_id',
            'external_url', 'error_code', 'error_message', 'detail',
            'recipient_count', 'success_count', 'failure_count',
            'started_at', 'completed_at', 'retry_count', 'is_retryable',
        )
        read_only_fields = fields


class RecipientDeliverySerializer(serializers.ModelSerializer):
    recipient_name = serializers.SerializerMethodField()

    class Meta:
        model = RecipientDelivery
        fields = ('id', 'address', 'recipient_name', 'status', 'error_code', 'error', 'sent_at')
        read_only_fields = fields

    def get_recipient_name(self, row):
        if row.user_id:
            return row.user.get_full_name() or row.user.username
        return row.subscriber.name if row.subscriber_id else ''


class PublicPostSerializer(serializers.ModelSerializer):
    gallery = PublicMediaSerializer(many=True, read_only=True)
    links = PostLinkSerializer(many=True, read_only=True)
    published_by_name = serializers.CharField(source='published_by.get_full_name', read_only=True)
    platform_links = serializers.SerializerMethodField()
    # Write-only mirror of `links`: the composer sends the whole list at once.
    links_payload = serializers.JSONField(write_only=True, required=False)

    deliveries = PublicationDeliverySerializer(many=True, read_only=True)
    audience_display = serializers.SerializerMethodField()
    audience_size = serializers.SerializerMethodField()
    audience_user_ids = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    # The composer posts the targeted accounts as a plain id list, including
    # through multipart forms where a JSON body is not available.
    audience_users_payload = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model = PublicPost
        fields = (
            'id', 'title', 'slug', 'category', 'category_display', 'excerpt', 'body',
            'cover_image', 'attachment',
            'newsletter_subject', 'newsletter_preview_text', 'newsletter_sender_name',
            'newsletter_sent_at', 'newsletter_recipient_count',
            'audience', 'audience_unit', 'audience_display', 'audience_size',
            'audience_user_ids', 'audience_users_payload',
            'channels', 'scheduled_for', 'status', 'deliveries', 'is_read',
            'source_report', 'published_by', 'published_by_name', 'is_published',
            'published_at', 'created_at', 'gallery', 'platform_links', 'links', 'links_payload',
        )
        read_only_fields = (
            'id', 'slug', 'published_by', 'published_by_name', 'published_at', 'created_at',
            'gallery', 'platform_links', 'links', 'newsletter_sent_at', 'newsletter_recipient_count',
            'deliveries', 'status', 'audience_display', 'audience_size', 'audience_user_ids',
            'is_read', 'category_display',
        )

    def get_audience_display(self, post):
        from .audience import audience_description
        return audience_description(post)

    def get_audience_size(self, post):
        from .audience import audience_size
        return audience_size(post)

    def get_audience_user_ids(self, post):
        return list(post.audience_users.values_list('id', flat=True))

    def get_is_read(self, post):
        """Whether the requesting user has opened this publication.

        `read_post_ids` is put on the context by the feed endpoint so a
        50-item feed costs one extra query rather than fifty.
        """
        request = self.context.get('request')
        if not (request and request.user.is_authenticated):
            return False
        known = self.context.get('read_post_ids')
        if known is not None:
            return post.pk in known
        return post.reads.filter(user=request.user).exists()

    def validate_audience_users_payload(self, value):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                raise serializers.ValidationError('Liste de destinataires illisible.')
        if value in (None, ''):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('Les destinataires doivent être une liste.')
        try:
            return [int(item) for item in value]
        except (TypeError, ValueError):
            raise serializers.ValidationError('Identifiant de destinataire invalide.')

    def get_platform_links(self, post):
        attempts = getattr(post, 'social_attempts', None)
        if attempts is None:
            return []
        return [
            {
                'platform': attempt.platform,
                'platform_display': attempt.platform_display,
                'url': attempt.external_url,
            }
            for attempt in attempts.all()
            if attempt.status == SocialPostAttempt.Status.SENT and attempt.external_url
        ]

    def validate_links_payload(self, value):
        """Validate every URL, but never fail a publication over a label."""
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                raise serializers.ValidationError('Liste de liens illisible.')
        if value in (None, ''):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('Les liens doivent être une liste.')

        cleaned = []
        for index, entry in enumerate(value):
            raw = entry.get('url') if isinstance(entry, dict) else entry
            if not raw:
                continue
            url = serializers.URLField(max_length=1000).run_validation(str(raw).strip())
            label = str(entry.get('label', '')).strip()[:255] if isinstance(entry, dict) else ''
            cleaned.append({'url': url, 'label': label, 'order': index})
        return cleaned

    def _sync_links(self, post, links):
        post.links.all().delete()
        PostLink.objects.bulk_create([PostLink(post=post, **link) for link in links])

    def _sync_audience(self, post, user_ids):
        """Only real, active accounts can be targeted.

        Ids that do not resolve are dropped rather than rejected: a stale id in
        the composer must not block a publication, and silently *adding* a
        recipient would be the dangerous direction, not removing one.
        """
        from accounts.models import User

        post.audience_users.set(User.objects.filter(id__in=user_ids, is_active=True))

    def create(self, validated_data):
        links = validated_data.pop('links_payload', None)
        audience_users = validated_data.pop('audience_users_payload', None)
        post = super().create(validated_data)
        if links is not None:
            self._sync_links(post, links)
        if audience_users is not None:
            self._sync_audience(post, audience_users)
        return post

    def update(self, instance, validated_data):
        links = validated_data.pop('links_payload', None)
        audience_users = validated_data.pop('audience_users_payload', None)
        post = super().update(instance, validated_data)
        if links is not None:
            self._sync_links(post, links)
        if audience_users is not None:
            self._sync_audience(post, audience_users)
        return post


class NewsletterSubscriberSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsletterSubscriber
        fields = ('id', 'email', 'name', 'is_active', 'subscribed_at')
        read_only_fields = ('id', 'is_active', 'subscribed_at')
        extra_kwargs = {'email': {'validators': []}}
        extra_kwargs = {'email': {'validators': []}}


class NewsletterDeliverySerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='subscriber.email', read_only=True)

    class Meta:
        model = NewsletterDelivery
        fields = ('id', 'email', 'status', 'error', 'sent_at')
        read_only_fields = fields


class ContactMessageSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    subject = serializers.CharField(max_length=200)
    message = serializers.CharField(max_length=5000)


class EditorImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = EditorImage
        fields = ('id', 'file', 'created_at')
        read_only_fields = ('id', 'created_at')


class SocialMediaLinkSerializer(serializers.ModelSerializer):
    added_by_name = serializers.CharField(source='added_by.get_full_name', read_only=True)

    class Meta:
        model = SocialMediaLink
        fields = ('id', 'name', 'url', 'is_active', 'order', 'added_by', 'added_by_name', 'created_at')
        read_only_fields = ('id', 'added_by', 'added_by_name', 'created_at')


class SocialAccountSerializer(serializers.ModelSerializer):
    """Connection state for the back-office.

    Access and refresh tokens are deliberately absent: they must never leave
    the server.
    """

    platform_display = serializers.CharField(source='get_platform_display', read_only=True)
    connected_by_name = serializers.CharField(source='connected_by.get_full_name', read_only=True)
    health = serializers.SerializerMethodField()

    class Meta:
        model = SocialAccount
        fields = (
            'id', 'platform', 'platform_display', 'account_name', 'external_account_id',
            'is_active', 'needs_reconnect', 'last_error', 'last_used_at', 'token_expires_at',
            'health', 'connected_by', 'connected_by_name', 'connected_at',
        )
        read_only_fields = fields

    def get_health(self, account):
        from .social.tokens import account_health
        return account_health(account)


class SocialPostAttemptSerializer(serializers.ModelSerializer):
    platform_display = serializers.CharField(read_only=True)

    class Meta:
        model = SocialPostAttempt
        fields = (
            'id', 'platform', 'platform_display', 'status', 'detail', 'external_url',
            'provider_post_id', 'error_code', 'retry_count', 'started_at', 'completed_at',
            'created_at',
        )
        read_only_fields = fields
