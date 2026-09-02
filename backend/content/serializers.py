from rest_framework import serializers

from .models import (
    EditorImage,
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
        fields = ('id', 'file', 'media_type', 'caption')
        read_only_fields = ('id',)


class PublicPostSerializer(serializers.ModelSerializer):
    gallery = PublicMediaSerializer(many=True, read_only=True)
    published_by_name = serializers.CharField(source='published_by.get_full_name', read_only=True)

    class Meta:
        model = PublicPost
        fields = (
            'id', 'title', 'slug', 'category', 'excerpt', 'body', 'cover_image', 'attachment',
            'source_report', 'published_by', 'published_by_name', 'is_published',
            'published_at', 'created_at', 'gallery',
        )
        read_only_fields = ('id', 'slug', 'published_by', 'published_by_name', 'published_at', 'created_at', 'gallery')


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
