"""Services for meeting workflow transitions."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.meetings.models import Meeting
from apps.protocols.services import ProtocolDraftService


class MeetingWorkflowService:
    """Coordinate meeting status transitions and related side effects."""

    @staticmethod
    @transaction.atomic
    def start_meeting(meeting: Meeting, actor=None) -> Meeting:
        """Start a sent meeting and create its protocol draft."""
        if meeting.status != "SENT":
            raise ValidationError("Sitzung kann nur aus dem Status SENT gestartet werden.")
        started_at = timezone.localtime()
        meeting.status = "IN_PROGRESS"
        meeting.actual_start_date = started_at.date()
        meeting.actual_start_time = started_at.time()
        meeting.save(update_fields=["status", "actual_start_date", "actual_start_time", "updated_at"])
        ProtocolDraftService.get_or_create_for_meeting(meeting, actor=actor)
        return meeting

    @staticmethod
    @transaction.atomic
    def complete_meeting(meeting: Meeting, actor=None) -> Meeting:
        """Complete an in-progress meeting and refresh protocol snapshots."""
        if not meeting.can_complete:
            raise ValidationError("Sitzung kann nur aus dem Status IN_PROGRESS abgeschlossen werden.")
        completed_at = timezone.localtime()
        meeting.status = "COMPLETED"
        meeting.actual_end_date = completed_at.date()
        meeting.actual_end_time = completed_at.time()
        meeting.save(update_fields=["status", "actual_end_date", "actual_end_time", "updated_at"])
        ProtocolDraftService.generate_from_meeting(meeting, actor=actor)
        return meeting
