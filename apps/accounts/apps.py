"""Application configuration for accounts app."""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Configuration for accounts application."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = 'Benutzerverwaltung'
