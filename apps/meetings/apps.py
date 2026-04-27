from django.apps import AppConfig


class MeetingsConfig(AppConfig):
    """Configuration for meetings app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.meetings'
    verbose_name = 'Sitzungsverwaltung'
