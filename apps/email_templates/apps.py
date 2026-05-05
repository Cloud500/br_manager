from django.apps import AppConfig


class EmailTemplatesConfig(AppConfig):
    """Configuration for e-mail templates app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.email_templates"
    verbose_name = "E-Mail-Vorlagen"
