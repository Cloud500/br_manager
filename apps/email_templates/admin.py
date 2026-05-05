"""Admin configuration for e-mail templates."""

from django.contrib import admin

from apps.email_templates.models import EmailTemplate


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    """Admin for system e-mail templates."""

    list_display = ["name", "key", "is_system_template", "updated_at"]
    list_filter = ["is_system_template"]
    search_fields = ["name", "key", "subject"]
    readonly_fields = ["key", "available_placeholders", "created_at", "updated_at"]

# Register your models here.
