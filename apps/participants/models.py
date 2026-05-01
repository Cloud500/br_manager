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
        ]

    def __str__(self) -> str:
        """Return participant display string."""
        return f"{self.display_name_for_display} ({self.meeting.meeting_number})"

    def clean(self) -> None:
        """Validate participant state."""
        if not self.membership_id:
            raise ValidationError({"membership": "Eine Mitgliedschaft ist erforderlich."})

        if self.substitute_membership_id:
            if self.substitute_membership.committee_id != self.meeting.committee_id:
                raise ValidationError({
                    "substitute_membership": "Ersatzmitglied muss zum Gremium der Sitzung gehören."
                })
            if self.substitute_membership.member_type != "SUBSTITUTE":
                raise ValidationError({
                    "substitute_membership": "Ausgewählte Person ist kein Ersatzmitglied."
                })

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
            role_name = self.membership.role.name if self.membership.role else "Ohne Rolle"
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
