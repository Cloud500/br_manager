"""Models for agendas app."""

import uuid
from typing import Dict, List, Optional, TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .managers import AgendaManager

if TYPE_CHECKING:
    from apps.meetings.models import Meeting


class Agenda(models.Model):
    """
    Agenda model for meetings.
    
    Each meeting has exactly one agenda (OneToOne relationship).
    Finalization is automatic based on meeting status.
    
    Attributes:
        id: UUID primary key
        meeting: Associated meeting (OneToOne)
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    
    # Primary key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # Meeting relationship
    meeting = models.OneToOneField(
        'meetings.Meeting',
        on_delete=models.CASCADE,
        related_name='agenda',
        verbose_name='Sitzung'
    )
    
    # Audit fields
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Erstellt am'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Aktualisiert am'
    )
    
    # Custom manager
    objects = AgendaManager()
    
    class Meta:
        verbose_name = 'Tagesordnung'
        verbose_name_plural = 'Tagesordnungen'
        ordering = ['-created_at']
    
    def __str__(self) -> str:
        """String representation."""
        return f"Tagesordnung für {self.meeting.title}"
    
    @property
    def is_editable(self) -> bool:
        """
        Check if agenda is editable.
        
        Agenda is editable when meeting status is DRAFT or IN_PROGRESS.
        
        Returns:
            True if agenda can be edited
        """
        return self.meeting.status in ['DRAFT', 'IN_PROGRESS']
    
    @property
    def is_finalized(self) -> bool:
        """
        Check if agenda is finalized.
        
        Agenda is finalized when meeting status is SENT.
        
        Returns:
            True if agenda is finalized
        """
        return self.meeting.status == 'SENT'
    
    @property
    def item_count(self) -> int:
        """
        Count all agenda items.
        
        Returns:
            Number of items in this agenda
        """
        return self.agendaitemregular_items.count()
    
    def reorder_items(self, item_order: List[uuid.UUID]) -> None:
        """
        Reorder agenda items based on provided list of UUIDs.
        
        Updates sort_order field for each item based on its position
        in the list. After updating, recalculates all item numbers.
        
        Args:
            item_order: List of item UUIDs in desired order
        """
        items_to_update = []
        
        for index, item_id in enumerate(item_order):
            try:
                item = self.agendaitemregular_items.get(id=item_id)
                item.sort_order = float(index)
                items_to_update.append(item)
            except self.agendaitemregular_items.model.DoesNotExist:
                continue
        
        # Bulk update for efficiency
        if items_to_update:
            self.agendaitemregular_items.model.objects.bulk_update(
                items_to_update,
                fields=['sort_order'],
                batch_size=100
            )
        
        # Recalculate all item numbers
        self.recalculate_item_numbers()
    
    def recalculate_item_numbers(self) -> None:
        """
        Recalculate item numbers for all agenda items.
        
        Generates hierarchical numbering (1, 1.1, 1.2, 2, 2.1, 2.1.1, etc.)
        based on sort_order and parent relationships.
        
        Uses bulk_update for efficient database operations.
        Processes items in hierarchical order to ensure parent numbers are set first.
        """
        # Get all items ordered by sort_order
        all_items = list(
            self.agendaitemregular_items.select_related('parent').order_by('sort_order')
        )
        
        # Reset all item numbers first
        for item in all_items:
            item.item_number = ""
        
        # Build a map: item_id -> item for quick lookup
        item_map = {item.id: item for item in all_items}
        
        # Counter dictionary: {parent_id: next_number}
        counters: Dict[Optional[uuid.UUID], int] = {}
        
        def calculate_number(item):
            """Recursively calculate item number, ensuring parent is calculated first."""
            # Skip if already calculated
            if item.item_number:
                return item.item_number
            
            parent_id = item.parent_id
            
            # Initialize counter for this parent if not exists
            if parent_id not in counters:
                counters[parent_id] = 1
            else:
                counters[parent_id] += 1
            
            # Calculate item number
            if parent_id is None:
                # Top-level item: "1", "2", "3", ...
                item.item_number = str(counters[None])
            else:
                # Ensure parent number is calculated first
                parent = item_map.get(parent_id)
                if parent:
                    if not parent.item_number:
                        calculate_number(parent)
                    parent_number = parent.item_number
                else:
                    parent_number = ""
                
                item.item_number = f"{parent_number}.{counters[parent_id]}"
            
            return item.item_number
        
        # Calculate numbers for all items
        for item in all_items:
            calculate_number(item)
        
        # Bulk update all items
        if all_items:
            self.agendaitemregular_items.model.objects.bulk_update(
                all_items,
                fields=['item_number'],
                batch_size=100
            )


class AgendaItem(models.Model):
    """
    Abstract base model for all agenda item types.
    
    Defines common fields and methods for all agenda item types.
    Concrete models (AgendaItemRegular, AgendaItemResolution, etc.)
    inherit from this base model.
    
    Attributes:
        id: UUID primary key
        agenda: Associated agenda
        parent: Parent item (for hierarchical structure)
        item_number: Auto-calculated number (1, 1.1, 1.2, etc.)
        title: Item title
        description: Optional detailed description
        sort_order: Float value for drag-and-drop ordering
        item_type: Discriminator for polymorphism
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    
    # Primary key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # Agenda relationship - uses dynamic related_name for polymorphism
    agenda = models.ForeignKey(
        Agenda,
        on_delete=models.CASCADE,
        related_name='%(class)s_items',
        verbose_name='Tagesordnung'
    )
    
    # Hierarchical structure
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='Übergeordneter TOP'
    )
    
    # Item numbering and content
    item_number = models.CharField(
        max_length=20,
        editable=False,
        verbose_name='TOP-Nummer',
        help_text='Wird automatisch berechnet'
    )
    title = models.CharField(
        max_length=500,
        verbose_name='Titel'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Beschreibung'
    )
    
    # Ordering
    sort_order = models.FloatField(
        default=0.0,
        verbose_name='Sortierung'
    )
    
    # Polymorphism support
    item_type = models.CharField(
        max_length=50,
        editable=False,
        verbose_name='Typ'
    )
    
    # Audit fields
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Erstellt am'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Aktualisiert am'
    )
    
    class Meta:
        abstract = True
        ordering = ['sort_order']
    
    def __str__(self) -> str:
        """String representation."""
        return f"{self.item_number} {self.title}" if self.item_number else self.title
    
    def save(self, *args, **kwargs) -> None:
        """
        Save agenda item.
        
        Automatically sets item_type if not set, then triggers
        item number recalculation for the agenda.
        """
        # Set item_type if not already set
        if not self.item_type:
            self.item_type = self.__class__.__name__
        
        # Save the item
        super().save(*args, **kwargs)
        
        # Recalculate all item numbers for this agenda
        self.agenda.recalculate_item_numbers()
    
    def clean(self) -> None:
        """
        Validate agenda item.
        
        Checks if agenda is editable before allowing modifications.
        
        Raises:
            ValidationError: If agenda is not editable
        """
        super().clean()
        
        # Only validate if agenda is already set
        if hasattr(self, 'agenda') and self.agenda_id:
            if not self.agenda.is_editable:
                raise ValidationError(
                    f'Tagesordnung kann nicht bearbeitet werden. '
                    f'Sitzungsstatus: {self.agenda.meeting.get_status_display()}'
                )
    
    def get_type_display(self) -> str:
        """
        Get human-readable type name.
        
        Returns:
            Localized type name
        """
        type_names = {
            'AgendaItemRegular': 'Normaler TOP',
            'AgendaItemResolution': 'Beschluss',
            'AgendaItemElection': 'Wahl',
        }
        return type_names.get(self.item_type, self.item_type)


class AgendaItemRegular(AgendaItem):
    """
    Regular agenda item.
    
    Concrete implementation for normal agenda items.
    Inherits all fields from AgendaItem base model.
    """
    
    class Meta:
        verbose_name = 'Normaler TOP'
        verbose_name_plural = 'Normale TOPs'


class AgendaItemResolution(AgendaItem):
    """
    Resolution agenda item.
    
    Links a resolution to an agenda. Only resolutions with status PROPOSED
    can be added to an agenda.
    
    Attributes:
        resolution: Associated resolution (ForeignKey)
    """
    
    # Resolution relationship
    resolution = models.ForeignKey(
        'resolutions.Resolution',
        on_delete=models.CASCADE,
        related_name='agenda_items',
        verbose_name='Beschluss'
    )
    
    class Meta:
        verbose_name = 'Beschluss-TOP'
        verbose_name_plural = 'Beschluss-TOPs'
    
    def clean(self) -> None:
        """
        Validate resolution agenda item.
        
        Checks:
        - Base agenda item validation (is_editable)
        - Resolution must be in PROPOSED status
        - Resolution committee must match agenda's meeting committee
        
        Raises:
            ValidationError: If validation fails
        """
        super().clean()
        
        # Validate resolution exists
        if not hasattr(self, 'resolution') or not self.resolution:
            raise ValidationError({
                'resolution': 'Beschluss muss ausgewählt werden'
            })
        
        # Validate resolution is in PROPOSED status
        if self.resolution.status != 'PROPOSED':
            raise ValidationError({
                'resolution': f'Nur Beschlüsse im Status "Vorgeschlagen" können zur Tagesordnung hinzugefügt werden. '
                             f'Aktueller Status: {self.resolution.get_status_display()}'
            })
        
        # Validate committee match
        if hasattr(self, 'agenda') and self.agenda_id:
            meeting_committee = self.agenda.meeting.committee
            resolution_committee = self.resolution.committee
            
            # Resolution committee must match OR resolution must be proposed to this committee
            valid = False
            
            # Direct match
            if resolution_committee == meeting_committee:
                valid = True
            
            # Resolution from subcommittee proposed to this committee
            if self.resolution.propose_to_main_committee:
                if resolution_committee.parent == meeting_committee:
                    valid = True
            
            if not valid:
                raise ValidationError({
                    'resolution': f'Beschluss von "{resolution_committee.name}" kann nicht zur Tagesordnung '
                                 f'von "{meeting_committee.name}" hinzugefügt werden'
                })
        ordering = ['sort_order', 'item_number']
