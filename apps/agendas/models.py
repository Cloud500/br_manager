"""Models for agendas app."""

import uuid
from typing import List, Optional

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.utils import timezone

from .managers import AgendaManager


class Agenda(models.Model):
    """Agenda model for meetings."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meeting = models.OneToOneField(
        "meetings.Meeting",
        on_delete=models.CASCADE,
        related_name="agenda",
        verbose_name="Sitzung",
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Erstellt am")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")

    objects = AgendaManager()

    class Meta:
        verbose_name = "Tagesordnung"
        verbose_name_plural = "Tagesordnungen"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Return the agenda label."""
        return f"Tagesordnung für {self.meeting.title}"

    @property
    def is_editable(self) -> bool:
        """Return whether the agenda can be edited."""
        return self.meeting.status in ["DRAFT", "IN_PROGRESS"]

    @property
    def is_finalized(self) -> bool:
        """Return whether the agenda is finalized."""
        return self.meeting.status == "SENT"

    @property
    def item_count(self) -> int:
        """Return the number of agenda items."""
        return self.items.count()

    @property
    def all_items(self) -> List["AgendaItem"]:
        """Return all agenda items in display order."""
        return list(
            self.items.select_related("parent").order_by(
                "sort_order", "created_at", "id"
            )
        )

    @property
    def top_level_items(self) -> List["AgendaItem"]:
        """Return top-level agenda items in display order."""
        return [item for item in self.all_items if item.parent_id is None]

    def next_sort_order(self) -> float:
        """Return the next sort order for a new item."""
        last_item = self.items.order_by("-sort_order").first()
        if last_item is None:
            return 1.0
        return last_item.sort_order + 1.0

    def recalculate_item_numbers(self) -> None:
        """Recalculate hierarchical TOP numbers for all items in this agenda."""
        all_items = self.all_items
        item_map = {item.id: item for item in all_items}
        counters: dict[Optional[uuid.UUID], int] = {}
        visiting: set[uuid.UUID] = set()

        for item in all_items:
            item.item_number = ""

        def calculate_number(item: "AgendaItem") -> str:
            if item.item_number:
                return item.item_number
            if item.id in visiting:
                raise ValidationError(
                    "Ungültige TOP-Hierarchie: zirkuläre Unterordnung ist nicht erlaubt."
                )

            visiting.add(item.id)
            parent_id = item.parent_id
            counters[parent_id] = counters.get(parent_id, 0) + 1

            if parent_id is None:
                item.item_number = str(counters[parent_id])
            else:
                parent = item_map.get(parent_id)
                parent_number = calculate_number(parent) if parent else ""
                item.item_number = f"{parent_number}.{counters[parent_id]}"

            visiting.remove(item.id)
            return item.item_number

        for item in all_items:
            calculate_number(item)

        if all_items:
            AgendaItem.objects.bulk_update(
                all_items, fields=["item_number"], batch_size=100
            )


class AgendaItem(models.Model):
    """Concrete agenda item shared by all TOP types."""

    TYPE_REGULAR = "REGULAR"
    TYPE_RESOLUTION = "RESOLUTION"
    TYPE_ELECTION = "ELECTION"
    ITEM_TYPE_CHOICES = [
        (TYPE_REGULAR, "Normaler TOP"),
        (TYPE_RESOLUTION, "Beschluss"),
        (TYPE_ELECTION, "Wahl"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agenda = models.ForeignKey(
        Agenda,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Tagesordnung",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="Übergeordneter TOP",
    )
    item_number = models.CharField(
        max_length=20,
        blank=True,
        default="",
        editable=False,
        verbose_name="TOP-Nummer",
        help_text="Wird automatisch berechnet",
    )
    title = models.CharField(max_length=500, verbose_name="Titel")
    description = models.TextField(blank=True, verbose_name="Beschreibung")
    sort_order = models.FloatField(default=0.0, verbose_name="Sortierung")
    item_type = models.CharField(
        max_length=20,
        choices=ITEM_TYPE_CHOICES,
        default=TYPE_REGULAR,
        verbose_name="Typ",
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Erstellt am")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")

    class Meta:
        verbose_name = "Tagesordnungspunkt"
        verbose_name_plural = "Tagesordnungspunkte"
        ordering = ["agenda", "sort_order", "created_at"]
        indexes = [
            models.Index(fields=["agenda", "item_type"]),
            models.Index(fields=["agenda", "parent"]),
        ]

    def __str__(self) -> str:
        """Return the display label."""
        return f"{self.item_number} {self.title}" if self.item_number else self.title

    def clean(self) -> None:
        """Validate agenda item invariants."""
        super().clean()

        if self.agenda_id and not self.agenda.is_editable:
            raise ValidationError(
                f"Tagesordnung kann nicht bearbeitet werden. "
                f"Sitzungsstatus: {self.agenda.meeting.get_status_display()}"
            )

        if self.parent_id:
            if self.parent_id == self.pk:
                raise ValidationError(
                    "Ein TOP kann sich nicht selbst untergeordnet werden."
                )
            if self.parent.agenda_id != self.agenda_id:
                raise ValidationError(
                    "Der übergeordnete TOP muss zur gleichen Tagesordnung gehören."
                )
            if self._would_create_cycle():
                raise ValidationError(
                    "Ungültige TOP-Hierarchie: zirkuläre Unterordnung ist nicht erlaubt."
                )

        if not self._state.adding and self.pk and self._is_published_election_changed():
            raise ValidationError(
                "Veröffentlichte Wahlen können nicht mehr bearbeitet werden."
            )

        if (
            not self._state.adding
            and self.pk
            and self._is_resolution_snapshot_invariant_changed()
        ):
            raise ValidationError(
                "Beschluss-TOPs übernehmen Titel und Beschreibung aus dem verknüpften Beschluss; "
                "Typ, Tagesordnung, Titel und Beschreibung können hier nicht geändert werden."
            )

    def save(self, *args, **kwargs) -> None:
        """Save the item and recalculate agenda numbering."""
        self.full_clean()
        super().save(*args, **kwargs)
        self.agenda.recalculate_item_numbers()

    def delete(self, *args, **kwargs):
        """Delete the item unless domain rules block deletion."""
        if self.is_published_election:
            raise ValidationError(
                "Veröffentlichte Wahlen können nicht gelöscht werden."
            )
        if self.has_published_election_descendant():
            raise ValidationError(
                "TOPs mit veröffentlichten Wahlen können nicht gelöscht werden."
            )
        agenda = self.agenda
        result = super().delete(*args, **kwargs)
        agenda.recalculate_item_numbers()
        return result

    def get_type_display(self) -> str:
        """Return the localized type name."""
        return dict(self.ITEM_TYPE_CHOICES).get(self.item_type, "Unbekannt")

    def get_ordered_children(self) -> List["AgendaItem"]:
        """Return direct children in display order."""
        return list(self.children.order_by("sort_order", "created_at", "id"))

    @property
    def is_regular(self) -> bool:
        """Return whether this item is a regular TOP."""
        return self.item_type == self.TYPE_REGULAR

    @property
    def is_resolution(self) -> bool:
        """Return whether this item is a resolution TOP."""
        return self.item_type == self.TYPE_RESOLUTION

    @property
    def is_election(self) -> bool:
        """Return whether this item is an election TOP."""
        return self.item_type == self.TYPE_ELECTION

    @property
    def election(self):
        """Return the linked election or None."""
        try:
            return self.election_link
        except ObjectDoesNotExist:
            return None

    @property
    def resolution_agenda_item(self):
        """Return the linked resolution agenda item or None."""
        try:
            return self.resolution_link
        except ObjectDoesNotExist:
            return None

    @property
    def is_published_election(self) -> bool:
        """Return whether this item belongs to a published election."""
        election = self.election
        return bool(election and election.status == election.STATUS_PUBLISHED)

    def has_published_election_descendant(self) -> bool:
        """Return whether any descendant contains a published election."""
        children = list(self.children.all())
        return any(
            child.is_published_election or child.has_published_election_descendant()
            for child in children
        )

    def _would_create_cycle(self) -> bool:
        """Return whether the current parent assignment creates a cycle."""
        current = self.parent
        seen = {self.pk}
        while current:
            if current.pk in seen:
                return True
            seen.add(current.pk)
            current = current.parent
        return False

    def _is_published_election_changed(self) -> bool:
        """Return whether a published election agenda item was changed."""
        if not self.pk:
            return False
        original = AgendaItem.objects.get(pk=self.pk)
        if not original.is_published_election:
            return False
        fields = [
            "agenda_id",
            "parent_id",
            "title",
            "description",
            "sort_order",
            "item_type",
        ]
        return any(getattr(self, field) != getattr(original, field) for field in fields)

    def _is_resolution_snapshot_invariant_changed(self) -> bool:
        """Return whether an existing resolution TOP invariant was changed."""
        if not self.pk:
            return False
        original = AgendaItem.objects.get(pk=self.pk)
        if not original.is_resolution or not original.resolution_agenda_item:
            return False
        fields = ["agenda_id", "item_type", "title", "description"]
        return any(getattr(self, field) != getattr(original, field) for field in fields)
