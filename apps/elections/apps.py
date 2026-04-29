"""Elections app configuration."""

from django.apps import AppConfig


class ElectionsConfig(AppConfig):
    """Configuration for elections app."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.elections'
    verbose_name = 'Wahlen'
