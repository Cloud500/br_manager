"""Models for meeting protocols and protocol revisions."""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Protocol(models.Model):
    """Mutable protocol draft for a meeting."""

    STATUS_DRAFT = "DRAFT"
    STATUS_LOCKED = "LOCKED"
    STATUS_FINALIZED = "FINALIZED"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Entwurf"),
        (STATUS_LOCKED, "Gesperrt"),
        (STATUS_FINALIZED, "Finalisiert"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meeting = models.OneToOneField(
        "meetings.Meeting",
        on_delete=models.CASCADE,
        related_name="protocol",
        verbose_name="Sitzung",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        verbose_name="Status",
    )
    body = models.TextField(blank=True, verbose_name="Protokolltext")
    metadata_snapshot = models.JSONField(default=dict, blank=True, verbose_name="Metadaten")
    attendance_snapshot = models.JSONField(default=dict, blank=True, verbose_name="Anwesenheit")
    agenda_snapshot = models.JSONField(default=list, blank=True, verbose_name="Tagesordnung")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Erstellt am")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_protocols",
        verbose_name="Aktualisiert von",
    )
    finalized_at = models.DateTimeField(null=True, blank=True, verbose_name="Finalisiert am")
    finalized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="finalized_protocols",
        verbose_name="Finalisiert von",
    )

    class Meta:
        verbose_name = "Protokoll"
        verbose_name_plural = "Protokolle"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Return protocol label."""
        return f"Protokoll {self.meeting.meeting_number}"

    @property
    def is_editable(self) -> bool:
        """Return whether regular protocol edits are allowed."""
        return self.status == self.STATUS_DRAFT


class ProtocolAgendaItemNote(models.Model):
    """Clerk note for one agenda item in the meeting protocol."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    protocol = models.ForeignKey(
        Protocol,
        on_delete=models.CASCADE,
        related_name="item_notes",
        verbose_name="Protokoll",
    )
    agenda_item = models.ForeignKey(
        "agendas.AgendaItem",
        on_delete=models.CASCADE,
        related_name="protocol_notes",
        verbose_name="Tagesordnungspunkt",
    )
    body = models.TextField(blank=True, verbose_name="Notiz")
    visible_to_loaded_participants = models.BooleanField(
        default=True,
        verbose_name="Für geladene Teilnehmer sichtbar",
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_protocol_notes",
        verbose_name="Aktualisiert von",
    )

    class Meta:
        verbose_name = "TOP-Protokollnotiz"
        verbose_name_plural = "TOP-Protokollnotizen"
        constraints = [
            models.UniqueConstraint(
                fields=["protocol", "agenda_item"],
                name="unique_protocol_note_per_item",
            ),
        ]
        indexes = [models.Index(fields=["protocol", "agenda_item"])]

    def __str__(self) -> str:
        """Return note label."""
        return f"Notiz zu {self.agenda_item}"


class ProtocolEntry(models.Model):
    """Structured protocol entry for agenda, resolution, election or attendance data."""

    ENTRY_AGENDA = "AGENDA"
    ENTRY_ATTENDANCE = "ATTENDANCE"
    ENTRY_RESOLUTION = "RESOLUTION"
    ENTRY_ELECTION = "ELECTION"

    ENTRY_TYPE_CHOICES = [
        (ENTRY_AGENDA, "Tagesordnung"),
        (ENTRY_ATTENDANCE, "Anwesenheit"),
        (ENTRY_RESOLUTION, "Beschluss"),
        (ENTRY_ELECTION, "Wahl"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    protocol = models.ForeignKey(
        Protocol,
        on_delete=models.CASCADE,
        related_name="entries",
        verbose_name="Protokoll",
    )
    agenda_item = models.ForeignKey(
        "agendas.AgendaItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="protocol_entries",
        verbose_name="Tagesordnungspunkt",
    )
    entry_type = models.CharField(max_length=30, choices=ENTRY_TYPE_CHOICES, verbose_name="Typ")
    title = models.CharField(max_length=500, verbose_name="Titel")
    content = models.TextField(blank=True, verbose_name="Inhalt")
    data = models.JSONField(default=dict, blank=True, verbose_name="Daten")
    object_ref = models.CharField(max_length=120, blank=True, verbose_name="Objektreferenz")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Erstellt am")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")

    class Meta:
        verbose_name = "Protokolleintrag"
        verbose_name_plural = "Protokolleinträge"
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["protocol", "entry_type"]),
            models.Index(fields=["object_ref"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["protocol", "object_ref"],
                name="unique_protocol_entry_object_ref",
            ),
        ]

    def __str__(self) -> str:
        """Return entry label."""
        return self.title


class ProtocolRevision(models.Model):
    """Protocol-specific revision history."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    protocol = models.ForeignKey(
        Protocol,
        on_delete=models.CASCADE,
        related_name="revisions",
        verbose_name="Protokoll",
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="protocol_revisions",
        verbose_name="Geändert von",
    )
    changed_at = models.DateTimeField(default=timezone.now, verbose_name="Geändert am")
    change_type = models.CharField(max_length=100, verbose_name="Änderungstyp")
    object_ref = models.CharField(max_length=120, blank=True, verbose_name="Objektreferenz")
    old_snapshot = models.JSONField(default=dict, blank=True, verbose_name="Alter Stand")
    new_snapshot = models.JSONField(default=dict, blank=True, verbose_name="Neuer Stand")

    class Meta:
        verbose_name = "Protokollrevision"
        verbose_name_plural = "Protokollrevisionen"
        ordering = ["-changed_at", "-id"]
        indexes = [models.Index(fields=["protocol", "change_type"])]

    def __str__(self) -> str:
        """Return revision label."""
        return f"{self.change_type} ({self.changed_at:%Y-%m-%d %H:%M})"

