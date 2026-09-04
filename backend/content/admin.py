from django.contrib import admin

from .models import NewsletterDelivery, NewsletterSubscriber, SocialAccount, SocialMediaLink, SocialPostAttempt


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'is_active', 'subscribed_at', 'unsubscribed_at')
    list_filter = ('is_active',)
    search_fields = ('email', 'name')


@admin.register(NewsletterDelivery)
class NewsletterDeliveryAdmin(admin.ModelAdmin):
    list_display = ('post', 'subscriber', 'status', 'sent_at')
    list_filter = ('status',)


@admin.register(SocialMediaLink)
class SocialMediaLinkAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'is_active', 'order', 'added_by', 'created_at')
    list_editable = ('is_active', 'order')


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ('platform', 'account_name', 'is_active', 'connected_by', 'connected_at')
    list_editable = ('is_active',)


@admin.register(SocialPostAttempt)
class SocialPostAttemptAdmin(admin.ModelAdmin):
    list_display = ('post', 'account', 'status', 'created_at')
    list_filter = ('status',)
