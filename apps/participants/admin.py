"""Admin configuration for meeting participants."""

from django.contrib import admin

from apps.participants.models import MeetingParticipant


@admin.register(MeetingParticipant)
class MeetingParticipantAdmin(admin.ModelAdmin):
    """Admin for meeting participant snapshots."""

    list_display = (
        "display_name_for_display",
        "meeting",
        "participant_type",
        "status",
        "substitute_name_for_display",
        "email_for_delivery",
        "invite_sent_at",
    )
    list_filter = ("participant_type", "status", "nachladefaehig")
    search_fields = (
        "membership__user__first_name",
        "membership__user__last_name",
        "membership__user__email",
        "meeting__title",
    )
    readonly_fields = ("created_at", "updated_at")
