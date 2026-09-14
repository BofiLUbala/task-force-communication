from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import OneTimeToken, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'get_full_name', 'role', 'status', 'unit', 'matricule', 'is_active')
    list_filter = ('role', 'status', 'unit', 'is_active_agent', 'is_active')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Task Force', {'fields': (
            'role', 'status', 'invited_by', 'matricule', 'phone_number', 'unit',
            'expo_push_token', 'is_active_agent',
        )}),
    )


@admin.register(OneTimeToken)
class OneTimeTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'purpose', 'created_at', 'expires_at', 'used_at')
    list_filter = ('purpose', 'used_at')
    search_fields = ('user__email', 'user__username')
    readonly_fields = ('user', 'purpose', 'token_hash', 'created_at', 'expires_at', 'used_at')
