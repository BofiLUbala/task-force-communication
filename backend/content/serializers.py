from rest_framework import serializers

from .models import (
    EditorImage,
    NewsletterDelivery,
    NewsletterSubscriber,
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
        fields = ('id', 'file', 'media_type', 'title', 'caption', 'social_links')
        read_only_fields = ('id',)

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


class PublicPostSerializer(serializers.ModelSerializer):
    gallery = PublicMediaSerializer(many=True, read_only=True)
    published_by_name = serializers.CharField(source='published_by.get_full_name', read_only=True)
    platform_links = serializers.SerializerMethodField()

    class Meta:
        model = PublicPost
        fields = (
            'id', 'title', 'slug', 'category', 'excerpt', 'body', 'cover_image', 'attachment',
            'newsletter_subject', 'newsletter_preview_text', 'newsletter_sender_name',
            'newsletter_sent_at', 'newsletter_recipient_count',
            'source_report', 'published_by', 'published_by_name', 'is_published',
            'published_at', 'created_at', 'gallery', 'platform_links',
        )
        read_only_fields = (
            'id', 'slug', 'published_by', 'published_by_name', 'published_at', 'created_at',
            'gallery', 'platform_links', 'newsletter_sent_at', 'newsletter_recipient_count',
        )

    def get_platform_links(self, post):
        attempts = getattr(post, 'social_attempts', None)
        if attempts is None:
            return []
        return [
            {
                'platform': attempt.account.platform,
                'platform_display': attempt.account.get_platform_display(),
                'url': attempt.external_url,
            }
            for attempt in attempts.all()
            if attempt.status == SocialPostAttempt.Status.SENT and attempt.external_url
        ]


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
    platform_display = serializers.CharField(source='get_platform_display', read_only=True)
    connected_by_name = serializers.CharField(source='connected_by.get_full_name', read_only=True)

    class Meta:
        model = SocialAccount
        fields = (
            'id', 'platform', 'platform_display', 'account_name', 'is_active',
            'connected_by', 'connected_by_name', 'connected_at',
        )
        read_only_fields = fields


class SocialPostAttemptSerializer(serializers.ModelSerializer):
    platform = serializers.CharField(source='account.platform', read_only=True)
    platform_display = serializers.CharField(source='account.get_platform_display', read_only=True)

    class Meta:
        model = SocialPostAttempt
        fields = ('id', 'platform', 'platform_display', 'status', 'detail', 'external_url', 'created_at')
        read_only_fields = fields
