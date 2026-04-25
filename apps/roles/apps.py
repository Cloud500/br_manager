"""Application configuration for roles app."""

from django.apps import AppConfig


class RolesConfig(AppConfig):
    """Configuration for roles application."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.roles'
    verbose_name = 'Rollen & Berechtigungen'
