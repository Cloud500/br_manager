"""App configuration for meeting participants."""

from django.apps import AppConfig


class ParticipantsConfig(AppConfig):
    """Configuration for participants app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.participants"
    verbose_name = "Teilnehmer"

    def ready(self) -> None:
        """Register signal handlers."""
        import apps.participants.signals  # noqa: F401
