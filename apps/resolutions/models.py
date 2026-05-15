"""Models for resolutions app."""

import uuid
from datetime import date
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone

from apps.agendas.models import AgendaItem

if TYPE_CHECKING:
    from apps.accounts.models import User
    from apps.committees.models import Committee


class Resolution(models.Model):
    """
    Resolution model for committee decisions.

    Represents a resolution (Beschluss) with title, description, and voting results.
    Supports status workflow and can be proposed
    to parent committees.

    Attributes:
        id: UUID primary key
        committee: Committee this resolution belongs to
        resolution_number: Auto-generated number (format: YYYYMMDD-XXX)
        title: Short display title for the resolution
        description: Description used for agenda preparation
        is_quorate: Whether quorum was met (set during meeting)
        yes_votes: Number of yes votes
        no_votes: Number of no votes
        abstentions: Number of abstentions
        status: Current status (DRAFT, PROPOSED, APPROVED, REJECTED)
        propose_to_main_committee: Whether to propose to parent committee
        created_by: User who created the resolution
        created_at: Creation timestamp
        updated_at: Last update timestamp
        decided_at: When resolution was approved/rejected
    """

    # Status choices
    STATUS_CHOICES = [
        ("DRAFT", "Entwurf"),
        ("PROPOSED", "Vorgeschlagen"),
        ("APPROVED", "Beschlossen"),
        ("REJECTED", "Abgelehnt"),
    ]

    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Committee relationship
    committee = models.ForeignKey(
        "committees.Committee",
        on_delete=models.CASCADE,
        related_name="resolutions",
        verbose_name="Gremium",
    )

    # Resolution number (auto-generated)
    resolution_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Beschlussnummer",
        help_text="Wird automatisch generiert bei Beschlussfassung (Format: YYYYMMDD-XXX)",
    )

    # Content fields
    title = models.CharField(
        max_length=255,
        verbose_name="Titel",
        help_text="Kurzer Name zur übersichtlichen Anzeige des Beschlusses",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Beschreibung",
        help_text="Beschreibung zur Vorbereitung des Beschlussthemas",
    )
    proposal = models.TextField(
        blank=True,
        default="",
        verbose_name="Beschlussvorschlag",
        help_text="Der zur Abstimmung gestellte Beschlusstext",
    )
    justification = models.TextField(
        blank=True,
        default="",
        verbose_name="Begründung",
        help_text="Begründung für den Beschlussvorschlag",
    )

    # Voting results (filled during meeting)
    is_quorate = models.BooleanField(
        null=True,
        blank=True,
        verbose_name="Beschlussfähig",
        help_text="Wird während der Sitzung gesetzt (§ 33 BetrVG)",
    )
    quorum_manually_overridden = models.BooleanField(
        default=False,
        verbose_name="Beschlussfähigkeit manuell überschrieben",
    )
    quorum_override_reason = models.TextField(
        blank=True,
        verbose_name="Begründung Quorum-Override",
    )
    yes_votes = models.PositiveIntegerField(default=0, verbose_name="Ja-Stimmen")
    no_votes = models.PositiveIntegerField(default=0, verbose_name="Nein-Stimmen")
    abstentions = models.PositiveIntegerField(default=0, verbose_name="Enthaltungen")
    decision_text = models.TextField(
        blank=True,
        verbose_name="Beschlussfassung",
        help_text="Formatierter Text der tatsächlichen Beschlussfassung in der Sitzung",
    )

    # Status and workflow
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="DRAFT", verbose_name="Status"
    )
    propose_to_main_committee = models.BooleanField(
        default=False,
        verbose_name="Für Hauptgremium vorschlagen",
        help_text="Beschluss kann in TOP des Hauptgremiums aufgenommen werden (§ 28 BetrVG)",
    )

    # Audit fields
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_resolutions",
        verbose_name="Erstellt von",
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Erstellt am")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")
    decided_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Beschlossen/Abgelehnt am",
        help_text="Zeitpunkt der Beschlussfassung",
    )

    class Meta:
        verbose_name = "Beschluss"
        verbose_name_plural = "Beschlüsse"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["committee", "resolution_number"],
                condition=~models.Q(resolution_number=""),
                name="unique_resolution_number_per_committee",
            ),
        ]
        indexes = [
            models.Index(fields=["committee", "status"]),
            models.Index(fields=["status"]),
            models.Index(fields=["resolution_number"]),
        ]

    def __str__(self) -> str:
        """String representation of resolution."""
        if self.resolution_number:
            return f"{self.resolution_number} - {self.title}"
        return f"Entwurf - {self.title}"

    def clean(self) -> None:
        """
        Validate resolution data.

        Validates:
        - Betriebsausschuss must always propose to main committee
        - propose_to_main_committee only for committees with parent
        - Voting fields only visible for APPROVED/REJECTED status

        Raises:
            ValidationError: If validation fails
        """
        super().clean()

        committee = None
        if self.committee_id:
            try:
                committee = self.committee
            except ObjectDoesNotExist:
                # Field-level validation reports missing/invalid committee values.
                return
        else:
            # ModelForm validation may exclude committee after a field error; do
            # not turn that normal form error into RelatedObjectDoesNotExist.
            return

        # Betriebsausschuss must always propose to main committee
        if committee.committee_type == "COMMITTEE":
            if not self.propose_to_main_committee:
                raise ValidationError(
                    {
                        "propose_to_main_committee": "Betriebsausschuss kann nur Beschlussvorschläge für das Hauptgremium erstellen (§ 27 BetrVG)"
                    }
                )

        # propose_to_main_committee only for committees with parent
        if self.propose_to_main_committee:
            if not committee.parent_id:
                raise ValidationError(
                    {
                        "propose_to_main_committee": "Nur Beschlüsse von Ausschüssen können dem Hauptgremium vorgeschlagen werden"
                    }
                )

    def save(self, *args, **kwargs) -> None:
        """
        Save resolution instance.

        Auto-generates resolution_number when status changes to APPROVED or REJECTED.
        Format: {YYYYMMDD}-{COUNT:03d} (e.g., "20260428-001")
        """
        # Auto-generate resolution number when approved/rejected
        if self.status in ["APPROVED", "REJECTED"] and not self.resolution_number:
            self._generate_resolution_number()

            # Set decided_at timestamp
            if not self.decided_at:
                self.decided_at = timezone.now()

        # Call full_clean for validation
        self.full_clean()
        super().save(*args, **kwargs)

    def _generate_resolution_number(self) -> None:
        """
        Generate unique resolution number.

        Format: YYYYMMDD-XXX
        - YYYYMMDD: Date when resolution was decided
        - XXX: Sequential number for that day (001, 002, ...)
        """
        today = date.today()
        date_prefix = today.strftime("%Y%m%d")

        # Count existing resolutions for this committee on this date
        existing_count = Resolution.objects.filter(
            committee=self.committee, resolution_number__startswith=date_prefix
        ).count()

        # Generate number
        self.resolution_number = f"{date_prefix}-{existing_count + 1:03d}"

    @property
    def is_editable(self) -> bool:
        """
        Check if resolution is editable.

        Returns:
            True if status is DRAFT or PROPOSED and not linked to agenda item
        """
        if self.status not in ["DRAFT", "PROPOSED"]:
            return False

        # Check if linked to agenda item in a non-DRAFT meeting
        if hasattr(self, "agenda_items") and self.agenda_items.exists():
            for agenda_item in self.agenda_items.select_related(
                "agenda_item__agenda__meeting"
            ):
                if agenda_item.agenda_item.agenda.meeting.status not in [
                    "DRAFT",
                    "IN_PROGRESS",
                ]:
                    return False

        return True

    @property
    def is_deletable(self) -> bool:
        """
        Check if resolution can be deleted.

        Returns:
            True if status is DRAFT and not linked to any agenda item
        """
        if self.status != "DRAFT":
            return False

        # Cannot delete if linked to agenda item
        if hasattr(self, "agenda_items") and self.agenda_items.exists():
            return False

        return True

    @property
    def can_be_proposed(self) -> bool:
        """
        Check if resolution can be changed to PROPOSED status.

        Returns:
            True if status is DRAFT
        """
        return self.status == "DRAFT"

    @property
    def can_be_withdrawn(self) -> bool:
        """
        Check if resolution can be withdrawn (PROPOSED → DRAFT).

        Returns:
            True if status is PROPOSED and not linked to any agenda item
        """
        if self.status != "PROPOSED":
            return False

        # Cannot withdraw if linked to agenda item
        if hasattr(self, "agenda_items") and self.agenda_items.exists():
            return False

        return True

    @property
    def show_voting_fields(self) -> bool:
        """
        Check if voting fields should be displayed.

        Returns:
            True if status is APPROVED or REJECTED
        """
        return self.status in ["APPROVED", "REJECTED"]

    @property
    def is_linked_to_agenda(self) -> bool:
        """
        Check if resolution is linked to any agenda item.

        Returns:
            True if resolution is part of at least one agenda
        """
        return hasattr(self, "agenda_items") and self.agenda_items.exists()

    def get_absolute_url(self) -> str:
        """Return absolute URL for resolution detail view."""
        return reverse("resolutions:resolution_detail", kwargs={"pk": self.pk})

    @staticmethod
    def user_can_create(user: "User", committee: "Committee") -> bool:
        """
        Check if user can create resolutions for the given committee.

        Rules:
        - User is superuser/staff, OR
        - User has 'resolution.create' in THIS committee (and committee.can_create_resolutions), OR
        - User has 'resolution.create' in any sub-committee (can propose to parent)

        Args:
            user: User instance
            committee: Committee instance (target)

        Returns:
            True if user can create resolution for this committee
        """
        from apps.committees.models import Membership

        if user.is_superuser or user.is_staff:
            return True

        # Direct membership in target committee
        memberships = Membership.objects.filter(
            user=user, committee=committee, is_active=True
        ).select_related("role")

        for membership in memberships:
            if (
                membership.role
                and membership.role.permissions.filter(
                    codename="resolution.create"
                ).exists()
            ):
                return committee.can_create_resolutions

        # Sub-committee membership (can propose to parent)
        for sub_committee in committee.subcommittees.filter(is_active=True):
            if Membership.objects.filter(
                user=user,
                committee=sub_committee,
                is_active=True,
                role__permissions__codename="resolution.create",
            ).exists():
                return True

        return False

    @staticmethod
    def user_can_propose(user: "User", committee: "Committee") -> bool:
        """Check if user can propose resolutions for the given committee."""
        from apps.committees.models import Membership

        if user.is_superuser or user.is_staff:
            return True

        if Membership.objects.filter(
            user=user,
            committee=committee,
            is_active=True,
            role__permissions__codename="resolution.propose",
        ).exists():
            return True

        if committee.committee_type == "MAIN":
            return Membership.objects.filter(
                user=user,
                committee__parent=committee,
                committee__committee_type="COMMITTEE",
                committee__is_active=True,
                is_active=True,
                role__permissions__codename="resolution.propose",
            ).exists()

        return False


class ResolutionAgendaItem(models.Model):
    """Links a resolution to a concrete agenda item."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agenda_item = models.OneToOneField(
        AgendaItem,
        on_delete=models.CASCADE,
        related_name="resolution_link",
        verbose_name="Tagesordnungspunkt",
    )
    resolution = models.ForeignKey(
        Resolution,
        on_delete=models.CASCADE,
        related_name="agenda_items",
        verbose_name="Beschluss",
    )

    class Meta:
        verbose_name = "Beschluss-TOP"
        verbose_name_plural = "Beschluss-TOPs"
        ordering = ["agenda_item__agenda", "agenda_item__sort_order"]

    def __str__(self) -> str:
        """Return display label."""
        return f"{self.agenda_item} - {self.resolution}"

    @property
    def agenda(self):
        """Return linked agenda."""
        return self.agenda_item.agenda

    @property
    def title(self) -> str:
        """Return linked TOP title."""
        return self.agenda_item.title

    @property
    def description(self) -> str:
        """Return linked TOP description."""
        return self.agenda_item.description

    @property
    def item_number(self) -> str:
        """Return linked TOP number."""
        return self.agenda_item.item_number

    def clean(self) -> None:
        """Validate resolution agenda item."""
        super().clean()
        if (
            self.agenda_item_id
            and self.agenda_item.item_type != AgendaItem.TYPE_RESOLUTION
        ):
            raise ValidationError(
                "Ein Beschluss-TOP muss mit einem Beschluss-TOP verknüpft sein."
            )
        if self.resolution_id and self.agenda_item_id:
            if self.resolution.status != "PROPOSED":
                raise ValidationError(
                    "Nur vorgeschlagene Beschlüsse können zur Tagesordnung hinzugefügt werden."
                )

            meeting_committee = self.agenda_item.agenda.meeting.committee
            resolution_committee = self.resolution.committee
            if resolution_committee != meeting_committee:
                allowed_subcommittee = (
                    resolution_committee.parent_id == meeting_committee.id
                    and self.resolution.propose_to_main_committee
                )
                if not allowed_subcommittee:
                    raise ValidationError(
                        "Der Beschluss passt nicht zum Gremium dieser Sitzung."
                    )

    def save(self, *args, **kwargs) -> None:
        """Save with validation and snapshot the linked resolution text on creation."""
        from django.db import transaction

        should_snapshot = (
            self._state.adding and self.agenda_item_id and self.resolution_id
        )
        self.full_clean()
        if should_snapshot:
            with transaction.atomic():
                self.agenda_item.title = self.resolution.title
                self.agenda_item.description = self.resolution.description
                self.agenda_item.save(
                    update_fields=["title", "description", "updated_at"]
                )
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Delete the linked agenda item as the owning TOP."""
        if self.agenda_item_id:
            return self.agenda_item.delete(*args, **kwargs)
        return super().delete(*args, **kwargs)


@receiver(pre_delete, sender=Resolution)
def delete_resolution_agenda_items(sender, instance: Resolution, **kwargs) -> None:
    """Delete owning agenda items when a linked resolution is deleted directly."""
    agenda_items = [
        link.agenda_item for link in instance.agenda_items.select_related("agenda_item")
    ]
    for agenda_item in agenda_items:
        agenda_item.delete()
