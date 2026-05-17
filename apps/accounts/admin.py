"""Admin configuration for accounts app."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import TwoFactorRecoveryCode, User, UserProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for User model."""
    
    list_display = [
        'email',
        'first_name',
        'last_name',
        'gender',
        'is_active',
        'date_joined'
    ]
    
    list_filter = [
        'is_active',
        'is_staff',
        'gender',
        'two_factor_enabled'
    ]
    
    search_fields = [
        'email',
        'first_name',
        'last_name'
    ]
    
    ordering = ['last_name', 'first_name']
    
    fieldsets = (
        (None, {
            'fields': ('email', 'password')
        }),
        ('Persönliche Daten', {
            'fields': ('first_name', 'last_name', 'gender', 'phone')
        }),
        ('Berechtigungen', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('2FA', {
            'fields': ('two_factor_enabled', 'two_factor_method')
        }),
        ('Wichtige Daten', {
            'fields': ('date_joined', 'last_login')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email',
                'first_name',
                'last_name',
                'gender',
                'password1',
                'password2'
            )
        }),
    )
    
    readonly_fields = ['date_joined', 'last_login']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin interface for UserProfile model."""
    
    list_display = ['user', 'department', 'employee_id']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'department', 'employee_id']
    list_filter = ['department']
    
    fieldsets = (
        (None, {
            'fields': ('user',)
        }),
        ('Berufliche Informationen', {
            'fields': ('department', 'employee_id')
        }),
        ('Einstellungen', {
            'fields': ('notification_preferences',)
        }),
        ('Profilbild', {
            'fields': ('avatar',)
        }),
    )
    
    readonly_fields = []


@admin.register(TwoFactorRecoveryCode)
class TwoFactorRecoveryCodeAdmin(admin.ModelAdmin):
    """Admin interface for TwoFactorRecoveryCode model."""
    
    list_display = ['user', 'is_used', 'created_at', 'used_at']
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {
            'fields': ('user', 'code')
        }),
        ('Status', {
            'fields': ('is_used', 'created_at', 'used_at')
        }),
    )
    
    readonly_fields = ['created_at', 'used_at']
    
    def has_add_permission(self, request):
        """Prevent manual creation of recovery codes via admin."""
        return False
