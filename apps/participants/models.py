"""Models for meeting-scoped participants."""

import uuid
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from apps.committees.models import Membership
    from apps.meetings.models import Meeting


class MeetingParticipant(models.Model):
    """Meeting-scoped participant snapshot."""

    PARTICIPANT_TYPE_INTERNAL = "INTERNAL"
    PARTICIPANT_TYPE_EXTERNAL = "EXTERNAL"
    PARTICIPANT_TYPE_SUBSTITUTE = "SUBSTITUTE"

    PARTICIPANT_TYPE_CHOICES = [
        (PARTICIPANT_TYPE_INTERNAL, "Interner Teilnehmer"),
        (PARTICIPANT_TYPE_EXTERNAL, "Externer Teilnehmer"),
        (PARTICIPANT_TYPE_SUBSTITUTE, "Nachgerückter Ersatz"),
    ]

    STATUS_CREATED = "CREATED"
    STATUS_INVITED = "INVITED"
    STATUS_ABSENT = "ABSENT"
    STATUS_SUBSTITUTE_PROPOSED = "SUBSTITUTE_PROPOSED"
    STATUS_CANCELLED = "CANCELLED"

    STATUS_CHOICES = [
        (STATUS_CREATED, "Eingeplant"),
        (STATUS_INVITED, "Eingeladen"),
        (STATUS_ABSENT, "Abwesend"),
        (STATUS_SUBSTITUTE_PROPOSED, "Abwesend, Ersatz vorgeschlagen"),
    ]

    ACTIVE_STATUSES = [
        STATUS_CREATED,
        STATUS_INVITED,
    ]

    ATTENDANCE_NOT_CONFIRMED = "NOT_CONFIRMED"
    ATTENDANCE_PRESENT = "PRESENT"
    ATTENDANCE_LEFT = "LEFT"
    ATTENDANCE_ABSENT = "ABSENT"

    ATTENDANCE_STATUS_CHOICES = [
        (ATTENDANCE_NOT_CONFIRMED, "Nicht bestätigt"),
        (ATTENDANCE_PRESENT, "Anwesend"),
        (ATTENDANCE_LEFT, "Abwesend während der Sitzung"),
        (ATTENDANCE_ABSENT, "Abwesend"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    meeting = models.ForeignKey(
        "meetings.Meeting",
        on_delete=models.CASCADE,
        related_name="participants",
        verbose_name="Sitzung",
    )
    membership = models.ForeignKey(
        "committees.Membership",
        on_delete=models.PROTECT,
        related_name="meeting_participants",
        verbose_name="Mitgliedschaft",
    )
    participant_type = models.CharField(
        max_length=20,
        choices=PARTICIPANT_TYPE_CHOICES,
        default=PARTICIPANT_TYPE_INTERNAL,
        verbose_name="Teilnehmerart",
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_CREATED,
        verbose_name="Status",
    )
    absence_reason = models.TextField(
        blank=True,
        verbose_name="Abwesenheitsgrund",
    )
    nachladefaehig = models.BooleanField(
        default=True,
        verbose_name="Nachladefähig",
        help_text="Wenn aktiv, wird ein Ersatzvorschlag ermittelt.",
    )
    is_initially_invited = models.BooleanField(
        default=True,
        verbose_name="Initial eingeladen",
    )
    substitute_membership = models.ForeignKey(
        "committees.Membership",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="meeting_substitutions",
        verbose_name="Nachgeladenes Ersatzmitglied",
    )
    invite_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Einladung versendet am",
    )
    attendance_status = models.CharField(
        max_length=30,
        choices=ATTENDANCE_STATUS_CHOICES,
        default=ATTENDANCE_NOT_CONFIRMED,
        verbose_name="Anwesenheitsstatus",
    )
    last_attendance_event_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Letzte Anwesenheitsänderung",
    )
    last_self_confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Zuletzt selbst bestätigt",
    )
    last_written_confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Zuletzt schriftlich bestätigt",
    )
    last_notified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Zuletzt benachrichtigt am",
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Erstellt am",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Aktualisiert am",
    )

    class Meta:
        verbose_name = "Sitzungsteilnehmer"
        verbose_name_plural = "Sitzungsteilnehmer"
        ordering = [
            "meeting",
            "participant_type",
            "membership__user__last_name",
            "membership__user__first_name",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["meeting", "membership"],
                name="unique_meeting_participant_membership",
            ),
        ]
        indexes = [
            models.Index(fields=["meeting", "status"]),
            models.Index(fields=["meeting", "attendance_status"]),
        ]

    def __str__(self) -> str:
        """Return participant display string."""
        return f"{self.display_name_for_display} ({self.meeting.meeting_number})"

    def clean(self) -> None:
        """Validate participant state."""
        if not self.membership_id:
            raise ValidationError(
                {"membership": "Eine Mitgliedschaft ist erforderlich."}
            )

        if self.substitute_membership_id:
            if self.substitute_membership.committee_id != self.meeting.committee_id:
                raise ValidationError(
                    {
                        "substitute_membership": "Ersatzmitglied muss zum Gremium der Sitzung gehören."
                    }
                )
            if self.substitute_membership.member_type != "SUBSTITUTE":
                raise ValidationError(
                    {
                        "substitute_membership": "Ausgewählte Person ist kein Ersatzmitglied."
                    }
                )

    @property
    def is_active_for_invitation(self) -> bool:
        """Return whether the participant should receive agenda mail."""
        return self.status in self.ACTIVE_STATUSES or bool(
            self.status == self.STATUS_ABSENT
            and self.nachladefaehig
            and self.substitute_membership_id
        )

    @property
    def display_name_for_display(self) -> str:
        """Return the participant name without duplicating membership user data."""
        if self.membership_id and self.membership.user_id:
            return self.membership.user.get_full_name()
        return ""

    @property
    def email_for_delivery(self) -> str:
        """Return the delivery address from membership or external participant data."""
        if self.membership_id and self.membership.user_id:
            return self.membership.user.email
        return ""

    @property
    def role_for_display(self) -> str:
        """Return role/function derived from membership or participant type."""
        if self.membership_id:
            role_name = (
                self.membership.role.name if self.membership.role else "Ohne Rolle"
            )
            if self.membership.committee_id != self.meeting.committee_id:
                return f"{role_name} ({self.membership.committee.name})"
            return role_name
        return "Ohne Rolle"

    @property
    def substitute_name_for_display(self) -> str:
        """Return selected substitute name for this participant row."""
        if self.substitute_membership_id and self.substitute_membership.user_id:
            return self.substitute_membership.user.get_full_name()
        return ""

    @property
    def substitute_role_for_display(self) -> str:
        """Return selected substitute role for this participant row."""
        if not self.substitute_membership_id:
            return ""
        role_name = (
            self.substitute_membership.role.name
            if self.substitute_membership.role
            else "Ohne Rolle"
        )
        return f"{role_name} ({self.substitute_membership.committee.name})"

    @classmethod
    def from_membership(
        cls,
        meeting: "Meeting",
        membership: "Membership",
        participant_type: str | None = None,
    ) -> "MeetingParticipant":
        """Create an unsaved participant snapshot from a membership."""
        resolved_type = participant_type or cls._participant_type_for_membership(
            membership
        )
        return cls(
            meeting=meeting,
            membership=membership,
            participant_type=resolved_type,
        )

    @classmethod
    def _participant_type_for_membership(cls, membership: "Membership") -> str:
        """Map committee membership type to participant type."""
        if membership.member_type == "EXTERNAL":
            return cls.PARTICIPANT_TYPE_EXTERNAL
        if membership.member_type == "SUBSTITUTE":
            return cls.PARTICIPANT_TYPE_SUBSTITUTE
        return cls.PARTICIPANT_TYPE_INTERNAL


class MeetingAttendanceEvent(models.Model):
    """Append-only attendance event for a meeting participant."""

    EVENT_CONFIRMED_PRESENT = "CONFIRMED_PRESENT"
    EVENT_RECONFIRMED = "RECONFIRMED"
    EVENT_LEFT = "LEFT"
    EVENT_RETURNED = "RETURNED"
    EVENT_MARKED_ABSENT = "MARKED_ABSENT"

    EVENT_TYPE_CHOICES = [
        (EVENT_CONFIRMED_PRESENT, "Anwesenheit bestätigt"),
        (EVENT_RECONFIRMED, "Sitzung erneut bestätigt"),
        (EVENT_LEFT, "Abwesend gemeldet"),
        (EVENT_RETURNED, "Zurückgemeldet"),
        (EVENT_MARKED_ABSENT, "Abwesend markiert"),
    ]

    METHOD_SELF = "SELF"
    METHOD_TOTP = "TOTP"
    METHOD_RECOVERY = "RECOVERY"
    METHOD_SYSTEM = "SYSTEM"

    METHOD_CHOICES = [
        (METHOD_SELF, "Selbst"),
        (METHOD_TOTP, "TOTP"),
        (METHOD_RECOVERY, "Recovery-Code"),
        (METHOD_SYSTEM, "System"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meeting = models.ForeignKey(
        "meetings.Meeting",
        on_delete=models.CASCADE,
        related_name="attendance_events",
        verbose_name="Sitzung",
    )
    participant = models.ForeignKey(
        MeetingParticipant,
        on_delete=models.CASCADE,
        related_name="attendance_events",
        verbose_name="Teilnehmer",
    )
    actor = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="meeting_attendance_events",
        verbose_name="Akteur",
    )
    event_type = models.CharField(
        max_length=40, choices=EVENT_TYPE_CHOICES, verbose_name="Ereignis"
    )
    occurred_at = models.DateTimeField(default=timezone.now, verbose_name="Zeitpunkt")
    method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        default=METHOD_SELF,
        verbose_name="Methode",
    )
    written_confirmation = models.TextField(
        blank=True,
        verbose_name="Schriftliche Anwesenheitsbestätigung",
        help_text="Vom Teilnehmer eingegebene Erklärung zur persönlichen Anwesenheit.",
    )
    metadata = models.JSONField(default=dict, blank=True, verbose_name="Metadaten")

    class Meta:
        verbose_name = "Anwesenheitsereignis"
        verbose_name_plural = "Anwesenheitsereignisse"
        ordering = ["occurred_at", "id"]
        indexes = [
            models.Index(fields=["meeting", "occurred_at"]),
            models.Index(fields=["participant", "event_type"]),
        ]

    def __str__(self) -> str:
        """Return attendance event label."""
        return f"{self.participant.display_name_for_display}: {self.get_event_type_display()}"
