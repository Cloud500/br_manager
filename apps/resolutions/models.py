"""Models for resolutions app."""

import uuid
from datetime import date
from typing import Optional, TYPE_CHECKING

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone

if TYPE_CHECKING:
    from apps.accounts.models import User
    from apps.committees.models import Committee


class Resolution(models.Model):
    """
    Resolution model for committee decisions.
    
    Represents a resolution (Beschluss) with proposal, justification,
    and voting results. Supports status workflow and can be proposed
    to parent committees.
    
    Attributes:
        id: UUID primary key
        committee: Committee this resolution belongs to
        resolution_number: Auto-generated number (format: YYYYMMDD-XXX)
        proposal: Resolution proposal text
        justification: Justification for the resolution
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
        ('DRAFT', 'Entwurf'),
        ('PROPOSED', 'Vorgeschlagen'),
        ('APPROVED', 'Beschlossen'),
        ('REJECTED', 'Abgelehnt'),
    ]
    
    # Primary key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # Committee relationship
    committee = models.ForeignKey(
        'committees.Committee',
        on_delete=models.CASCADE,
        related_name='resolutions',
        verbose_name='Gremium'
    )
    
    # Resolution number (auto-generated)
    resolution_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Beschlussnummer',
        help_text='Wird automatisch generiert bei Beschlussfassung (Format: YYYYMMDD-XXX)'
    )
    
    # Content fields
    proposal = models.TextField(
        verbose_name='Beschlussvorschlag',
        help_text='Der zur Abstimmung gestellte Beschlusstext'
    )
    justification = models.TextField(
        blank=True,
        verbose_name='Begründung',
        help_text='Begründung für den Beschlussvorschlag'
    )
    
    # Voting results (filled during meeting)
    is_quorate = models.BooleanField(
        null=True,
        blank=True,
        verbose_name='Beschlussfähig',
        help_text='Wird während der Sitzung gesetzt (§ 33 BetrVG)'
    )
    yes_votes = models.PositiveIntegerField(
        default=0,
        verbose_name='Ja-Stimmen'
    )
    no_votes = models.PositiveIntegerField(
        default=0,
        verbose_name='Nein-Stimmen'
    )
    abstentions = models.PositiveIntegerField(
        default=0,
        verbose_name='Enthaltungen'
    )
    
    # Status and workflow
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        verbose_name='Status'
    )
    propose_to_main_committee = models.BooleanField(
        default=False,
        verbose_name='Für Hauptgremium vorschlagen',
        help_text='Beschluss kann in TOP des Hauptgremiums aufgenommen werden (§ 28 BetrVG)'
    )
    
    # Audit fields
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_resolutions',
        verbose_name='Erstellt von'
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Erstellt am'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Aktualisiert am'
    )
    decided_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Beschlossen/Abgelehnt am',
        help_text='Zeitpunkt der Beschlussfassung'
    )
    
    class Meta:
        verbose_name = 'Beschluss'
        verbose_name_plural = 'Beschlüsse'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['committee', 'resolution_number'],
                condition=~models.Q(resolution_number=''),
                name='unique_resolution_number_per_committee',
            ),
        ]
        indexes = [
            models.Index(fields=['committee', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['resolution_number']),
        ]
    
    def __str__(self) -> str:
        """String representation of resolution."""
        if self.resolution_number:
            return f"{self.resolution_number} - {self.proposal[:50]}"
        return f"Entwurf - {self.proposal[:50]}"
    
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
        
        # Betriebsausschuss must always propose to main committee
        if self.committee and self.committee.committee_type == 'COMMITTEE':
            if not self.propose_to_main_committee:
                raise ValidationError({
                    'propose_to_main_committee': 
                    'Betriebsausschuss kann nur Beschlussvorschläge für das Hauptgremium erstellen (§ 27 BetrVG)'
                })
        
        # propose_to_main_committee only for committees with parent
        if self.propose_to_main_committee and self.committee:
            if not self.committee.parent:
                raise ValidationError({
                    'propose_to_main_committee': 
                    'Nur Beschlüsse von Ausschüssen können dem Hauptgremium vorgeschlagen werden'
                })
    
    def save(self, *args, **kwargs) -> None:
        """
        Save resolution instance.
        
        Auto-generates resolution_number when status changes to APPROVED or REJECTED.
        Format: {YYYYMMDD}-{COUNT:03d} (e.g., "20260428-001")
        """
        # Auto-generate resolution number when approved/rejected
        if self.status in ['APPROVED', 'REJECTED'] and not self.resolution_number:
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
        date_prefix = today.strftime('%Y%m%d')
        
        # Count existing resolutions for this committee on this date
        existing_count = Resolution.objects.filter(
            committee=self.committee,
            resolution_number__startswith=date_prefix
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
        if self.status not in ['DRAFT', 'PROPOSED']:
            return False
        
        # Check if linked to agenda item in a non-DRAFT meeting
        if hasattr(self, 'agenda_items') and self.agenda_items.exists():
            for agenda_item in self.agenda_items.all():
                if agenda_item.agenda.meeting.status not in ['DRAFT', 'IN_PROGRESS']:
                    return False
        
        return True
    
    @property
    def is_deletable(self) -> bool:
        """
        Check if resolution can be deleted.
        
        Returns:
            True if status is DRAFT and not linked to any agenda item
        """
        if self.status != 'DRAFT':
            return False
        
        # Cannot delete if linked to agenda item
        if hasattr(self, 'agenda_items') and self.agenda_items.exists():
            return False
        
        return True
    
    @property
    def can_be_proposed(self) -> bool:
        """
        Check if resolution can be changed to PROPOSED status.
        
        Returns:
            True if status is DRAFT
        """
        return self.status == 'DRAFT'
    
    @property
    def can_be_withdrawn(self) -> bool:
        """
        Check if resolution can be withdrawn (PROPOSED → DRAFT).
        
        Returns:
            True if status is PROPOSED and not linked to any agenda item
        """
        if self.status != 'PROPOSED':
            return False
        
        # Cannot withdraw if linked to agenda item
        if hasattr(self, 'agenda_items') and self.agenda_items.exists():
            return False
        
        return True
    
    @property
    def show_voting_fields(self) -> bool:
        """
        Check if voting fields should be displayed.
        
        Returns:
            True if status is APPROVED or REJECTED
        """
        return self.status in ['APPROVED', 'REJECTED']
    
    @property
    def is_linked_to_agenda(self) -> bool:
        """
        Check if resolution is linked to any agenda item.
        
        Returns:
            True if resolution is part of at least one agenda
        """
        return hasattr(self, 'agenda_items') and self.agenda_items.exists()
    
    def get_absolute_url(self) -> str:
        """Return absolute URL for resolution detail view."""
        return reverse('resolutions:resolution_detail', kwargs={'pk': self.pk})
    
    @staticmethod
    def user_can_create(user: 'User', committee: 'Committee') -> bool:
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
            user=user,
            committee=committee,
            is_active=True
        ).select_related('role')
        
        for membership in memberships:
            if membership.role and membership.role.permissions.filter(
                codename='resolution.create'
            ).exists():
                return committee.can_create_resolutions
        
        # Sub-committee membership (can propose to parent)
        for sub_committee in committee.subcommittees.filter(is_active=True):
            if Membership.objects.filter(
                user=user,
                committee=sub_committee,
                is_active=True,
                role__permissions__codename='resolution.create'
            ).exists():
                return True
        
        return False
