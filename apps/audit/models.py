"""Append-only audit models."""

import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone


class AuditEntry(models.Model):
    """Append-only audit event for legally relevant changes."""

    ACTION_CREATED = "CREATED"
    ACTION_UPDATED = "UPDATED"
    ACTION_DELETED = "DELETED"
    ACTION_FINALIZED = "FINALIZED"
    ACTION_RECONFIRMED = "RECONFIRMED"

    ACTION_CHOICES = [
        (ACTION_CREATED, "Erstellt"),
        (ACTION_UPDATED, "Geändert"),
        (ACTION_DELETED, "Gelöscht"),
        (ACTION_FINALIZED, "Finalisiert"),
        (ACTION_RECONFIRMED, "Erneut bestätigt"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        related_name="audit_entries",
        verbose_name="Objekttyp",
    )
    object_id = models.CharField(max_length=64, verbose_name="Objekt-ID")
    content_object = GenericForeignKey("content_type", "object_id")
    action = models.CharField(
        max_length=30,
        choices=ACTION_CHOICES,
        verbose_name="Aktion",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_entries",
        verbose_name="Akteur",
    )
    changed_at = models.DateTimeField(default=timezone.now, verbose_name="Geändert am")
    change_type = models.CharField(max_length=100, verbose_name="Änderungstyp")
    old_snapshot = models.JSONField(default=dict, blank=True, verbose_name="Alter Stand")
    new_snapshot = models.JSONField(default=dict, blank=True, verbose_name="Neuer Stand")
    metadata = models.JSONField(default=dict, blank=True, verbose_name="Metadaten")

    class Meta:
        verbose_name = "Audit-Eintrag"
        verbose_name_plural = "Audit-Einträge"
        ordering = ["-changed_at", "-id"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["action", "changed_at"]),
        ]

    def __str__(self) -> str:
        """Return a short audit event label."""
        return f"{self.change_type} ({self.changed_at:%Y-%m-%d %H:%M})"

# Create your models here.
