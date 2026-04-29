"""Apps configuration for resolutions app."""

from django.apps import AppConfig


class ResolutionsConfig(AppConfig):
    """Configuration for resolutions app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.resolutions'
    verbose_name = 'Beschlüsse'
