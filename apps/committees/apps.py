"""Committees app configuration."""

from django.apps import AppConfig


class CommitteesConfig(AppConfig):
    """Configuration for committees app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.committees'
    verbose_name = 'Gremienverwaltung'
    
    def ready(self):
        """Import signal handlers when app is ready."""
        import apps.committees.signals  # noqa: F401
