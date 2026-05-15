"""Admin configuration for resolutions app."""

from django.contrib import admin

from .models import Resolution, ResolutionAgendaItem


@admin.register(Resolution)
class ResolutionAdmin(admin.ModelAdmin):
    """Admin interface for Resolution model."""

    list_display = [
        "resolution_number",
        "title",
        "description_short",
        "committee",
        "status",
        "created_by",
        "created_at",
    ]
    list_filter = ["status", "committee", "propose_to_main_committee", "created_at"]
    search_fields = [
        "title",
        "description",
        "proposal",
        "justification",
        "resolution_number",
    ]
    readonly_fields = ["resolution_number", "created_at", "updated_at", "decided_at"]

    fieldsets = (
        (
            "Grunddaten",
            {
                "fields": (
                    "committee",
                    "title",
                    "description",
                    "propose_to_main_committee",
                )
            },
        ),
        (
            "Legacy-Daten",
            {"fields": ("proposal", "justification"), "classes": ("collapse",)},
        ),
        ("Status", {"fields": ("status", "resolution_number", "decided_at")}),
        (
            "Abstimmung",
            {
                "fields": ("is_quorate", "yes_votes", "no_votes", "abstentions"),
                "classes": ("collapse",),
            },
        ),
        (
            "Metadaten",
            {
                "fields": ("created_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def description_short(self, obj):
        """Return shortened description text."""
        return (
            obj.description[:75] + "..."
            if len(obj.description) > 75
            else obj.description
        )

    description_short.short_description = "Beschreibung"


@admin.register(ResolutionAgendaItem)
class ResolutionAgendaItemAdmin(admin.ModelAdmin):
    """Admin interface for agenda-linked resolution TOPs."""

    list_display = ["item_number", "title", "resolution", "agenda"]
    list_filter = ["agenda_item__agenda__meeting__committee"]
    search_fields = [
        "agenda_item__title",
        "resolution__title",
        "resolution__description",
        "resolution__proposal",
    ]
    readonly_fields = ["id", "title", "agenda", "item_number"]
    autocomplete_fields = ["agenda_item", "resolution"]

    fieldsets = (
        ("Verknüpfung", {"fields": ("agenda_item", "resolution")}),
        (
            "TOP-Daten",
            {
                "fields": ("id", "title", "agenda", "item_number"),
                "classes": ("collapse",),
            },
        ),
    )
