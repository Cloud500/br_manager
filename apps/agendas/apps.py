"""Agendas app configuration."""

from django.apps import AppConfig


class AgendasConfig(AppConfig):
    """Configuration for agendas app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.agendas'
    verbose_name = 'Tagesordnungen'
    
    def ready(self) -> None:
        """
        Register signal handlers when app is ready.
        
        This ensures signals are registered before any models are used.
        """
        import apps.agendas.signals  # noqa: F401
