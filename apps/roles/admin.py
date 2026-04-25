"""Admin configuration for roles app."""

from django.contrib import admin

from .models import Permission, Role, RolePermission


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    """Admin interface for Permission model."""
    
    list_display = ['codename', 'name', 'category']
    list_filter = ['category']
    search_fields = ['codename', 'name', 'description']
    ordering = ['category', 'codename']


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Admin interface for Role model."""
    
    list_display = ['name', 'codename', 'role_type', 'is_system_role', 'created_at']
    list_filter = ['role_type', 'is_system_role']
    search_fields = ['name', 'codename', 'description']
    ordering = ['role_type', 'name']
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'codename', 'description')
        }),
        ('Typ', {
            'fields': ('role_type', 'is_system_role')
        }),
        ('Zeitstempel', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    """Admin interface for RolePermission model."""
    
    list_display = ['role', 'permission', 'assigned_at']
    list_filter = ['role__role_type', 'permission__category']
    search_fields = ['role__name', 'permission__name']
    ordering = ['role', 'permission']
    
    readonly_fields = ['assigned_at']
