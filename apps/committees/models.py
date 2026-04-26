"""Models for committees app."""

import uuid
from typing import Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    """
    QuerySet for soft-delete functionality.
    
    Provides methods to filter deleted/non-deleted objects and soft-delete operations.
    """
    
    def delete(self) -> tuple:
        """
        Soft-delete all objects in queryset.
        
        Sets deleted_at to current timestamp instead of removing from database.
        
        Returns:
            Tuple of (count, details_dict)
        """
        count = self.count()
        self.update(deleted_at=timezone.now())
        return (count, {f'{self.model._meta.label}': count})
    
    def hard_delete(self) -> tuple:
        """
        Permanently delete all objects in queryset.
        
        Returns:
            Tuple of (count, details_dict)
        """
        return super().delete()
    
    def alive(self) -> 'SoftDeleteQuerySet':
        """
        Filter for non-deleted objects.
        
        Returns:
            QuerySet containing only objects where deleted_at is NULL
        """
        return self.filter(deleted_at__isnull=True)
    
    def deleted(self) -> 'SoftDeleteQuerySet':
        """
        Filter for deleted objects.
        
        Returns:
            QuerySet containing only objects where deleted_at is not NULL
        """
        return self.filter(deleted_at__isnull=False)


class SoftDeleteManager(models.Manager):
    """
    Manager for soft-delete functionality.
    
    Default queryset returns only non-deleted objects.
    Use all_with_deleted() to get all objects including deleted ones.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize manager."""
        self.alive_only = kwargs.pop('alive_only', True)
        super().__init__(*args, **kwargs)
    
    def get_queryset(self) -> SoftDeleteQuerySet:
        """
        Return queryset with only non-deleted objects.
        
        Returns:
            SoftDeleteQuerySet filtered for alive objects
        """
        if self.alive_only:
            return SoftDeleteQuerySet(self.model, using=self._db).alive()
        return SoftDeleteQuerySet(self.model, using=self._db)
    
    def all_with_deleted(self) -> SoftDeleteQuerySet:
        """
        Return all objects including deleted ones.
        
        Returns:
            SoftDeleteQuerySet with all objects
        """
        return SoftDeleteQuerySet(self.model, using=self._db)
    
    def deleted_only(self) -> SoftDeleteQuerySet:
        """
        Return only deleted objects.
        
        Returns:
            SoftDeleteQuerySet filtered for deleted objects
        """
        return SoftDeleteQuerySet(self.model, using=self._db).deleted()
    
    def alive(self) -> SoftDeleteQuerySet:
        """
        Return only non-deleted objects.
        
        Returns:
            SoftDeleteQuerySet filtered for alive objects
        """
        return SoftDeleteQuerySet(self.model, using=self._db).alive()
    
    def deleted(self) -> SoftDeleteQuerySet:
        """
        Return only deleted objects.
        
        Returns:
            SoftDeleteQuerySet filtered for deleted objects
        """
        return SoftDeleteQuerySet(self.model, using=self._db).deleted()


class Committee(models.Model):
    """
    Committee model for managing councils and sub-committees.
    
    Represents different types of employee representative bodies:
    - MAIN: Main works council (Betriebsrat)
    - COMMITTEE: Executive committee (Betriebsausschuss)
    - SUBCOMMITTEE: Specialized committees (Fachausschüsse)
    - ADHOC: Ad-hoc committees
    
    Supports hierarchical structure where committees can have parent committees.
    Implements soft-delete functionality.
    
    Attributes:
        id: UUID primary key
        name: Committee name
        committee_type: Type of committee
        parent: Parent committee (for hierarchical structure)
        description: Optional description
        created_at: Creation timestamp
        is_active: Whether committee is currently active
        deleted_at: Soft-delete timestamp
        deleted_by: User who deleted the committee
        total_seats: Total number of seats
        quorum_type: Quorum type for decisions
        personnel_enabled: Whether personnel measures are enabled
        substitute_logic_enabled: Whether substitute member logic is enabled
        minority_gender: Gender for minority quota (§ 15 Abs. 2 BetrVG)
        minority_min_count: Minimum count for minority gender
    """
    
    COMMITTEE_TYPE_CHOICES = [
        ('MAIN', 'Betriebsrat (Hauptgremium)'),
        ('COMMITTEE', 'Betriebsausschuss'),
        ('SUBCOMMITTEE', 'Fachausschuss'),
        ('ADHOC', 'Ad-hoc-Ausschuss'),
    ]
    
    QUORUM_TYPE_CHOICES = [
        ('SIMPLE_MAJORITY', 'Einfache Mehrheit'),
        ('QUALIFIED', 'Qualifizierte Mehrheit'),
    ]
    
    GENDER_CHOICES = [
        ('M', 'Männlich'),
        ('F', 'Weiblich'),
    ]
    
    # Primary fields
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(
        max_length=200,
        verbose_name='Name'
    )
    committee_type = models.CharField(
        max_length=20,
        choices=COMMITTEE_TYPE_CHOICES,
        verbose_name='Gremiumstyp'
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subcommittees',
        verbose_name='Übergeordnetes Gremium'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Beschreibung'
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Erstellt am'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Aktiv'
    )
    
    # Soft-delete fields
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Gelöscht am'
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deleted_committees',
        verbose_name='Gelöscht von'
    )
    
    # Configuration fields
    total_seats = models.PositiveIntegerField(
        verbose_name='Gesamtanzahl Sitze'
    )
    quorum_type = models.CharField(
        max_length=20,
        choices=QUORUM_TYPE_CHOICES,
        default='SIMPLE_MAJORITY',
        verbose_name='Quorum-Typ'
    )
    personnel_enabled = models.BooleanField(
        default=False,
        verbose_name='Personelle Einzelmaßnahmen aktiviert'
    )
    substitute_logic_enabled = models.BooleanField(
        default=False,
        verbose_name='Nachrücklogik aktiviert'
    )
    minority_gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        blank=True,
        null=True,
        verbose_name='Minderheitengeschlecht'
    )
    minority_min_count = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='Mindestanzahl Minderheitengeschlecht'
    )
    
    class Meta:
        verbose_name = 'Gremium'
        verbose_name_plural = 'Gremien'
        ordering = ['committee_type', 'name']
    
    # Managers
    objects = SoftDeleteManager()
    all_objects = SoftDeleteManager(alive_only=False)
    
    def __str__(self) -> str:
        """String representation of committee."""
        return self.name
    
    def clean(self) -> None:
        """
        Validate committee hierarchy rules.
        
        Rules:
        - MAIN committees cannot have a parent
        - Non-MAIN committees must have a parent
        - Prevent circular references
        - Validate minority gender configuration
        
        Raises:
            ValidationError: If validation rules are violated
        """
        # MAIN committees cannot have parent
        if self.committee_type == 'MAIN' and self.parent:
            raise ValidationError({
                'parent': 'Hauptgremium darf kein übergeordnetes Gremium haben'
            })
        
        # Non-MAIN committees must have parent
        if self.committee_type != 'MAIN' and not self.parent:
            raise ValidationError({
                'parent': 'Ausschuss benötigt ein übergeordnetes Gremium'
            })
        
        # Check for circular references
        if self.parent:
            current = self.parent
            visited = {self.id} if self.id else set()
            while current:
                if current.id in visited:
                    raise ValidationError({
                        'parent': 'Zirkelbezug in Gremien-Hierarchie erkannt'
                    })
                visited.add(current.id)
                current = current.parent
        
        # Validate minority gender configuration
        if self.minority_min_count and not self.minority_gender:
            raise ValidationError({
                'minority_gender': 'Minderheitengeschlecht muss angegeben werden wenn Mindestanzahl festgelegt ist'
            })
        
        if self.minority_min_count and self.minority_min_count > self.total_seats:
            raise ValidationError({
                'minority_min_count': 'Mindestanzahl darf nicht größer sein als Gesamtanzahl Sitze'
            })
    
    def delete(self, user: Optional['User'] = None) -> tuple:
        """
        Soft-delete committee and cascade to memberships.
        
        Args:
            user: User performing the delete operation
        
        Returns:
            Tuple of (count, details_dict) with deletion counts
        """
        self.deleted_at = timezone.now()
        if user:
            self.deleted_by = user
        self.save(update_fields=['deleted_at', 'deleted_by'])
        
        # Cascade to memberships
        memberships = self.memberships.filter(deleted_at__isnull=True)
        membership_count = 0
        for membership in memberships:
            membership.delete(user=user)
            membership_count += 1
        
        return (1 + membership_count, {
            'committees.Committee': 1,
            'committees.Membership': membership_count
        })
    
    def hard_delete(self) -> tuple:
        """
        Permanently delete committee from database.
        
        Returns:
            Tuple of (count, details_dict)
        """
        return super().delete()
    
    def get_active_members(self) -> models.QuerySet:
        """
        Get active regular members.
        
        Returns:
            QuerySet of active REGULAR memberships, ordered by role sort_order
        """
        return self.memberships.filter(
            is_active=True,
            member_type='REGULAR'
        ).select_related('user', 'role').order_by('role__sort_order', 'user__last_name')
    
    def get_active_substitutes(self) -> models.QuerySet:
        """
        Get active substitute members.
        
        Returns:
            QuerySet of active SUBSTITUTE memberships, ordered by role sort_order
        """
        return self.memberships.filter(
            is_active=True,
            member_type='SUBSTITUTE'
        ).select_related('user', 'role').order_by('role__sort_order', 'user__last_name')
    
    def get_external_members(self) -> models.QuerySet:
        """
        Get external members.
        
        Returns:
            QuerySet of EXTERNAL memberships, ordered by role sort_order
        """
        return self.memberships.filter(
            member_type='EXTERNAL'
        ).select_related('user', 'role').order_by('role__sort_order', 'user__last_name')


class Membership(models.Model):
    """
    Membership model for user-committee relationships.
    
    Represents a user's membership in a committee with role and type.
    Supports different member types (regular, substitute, external).
    Includes election information for substitute member logic.
    Implements soft-delete functionality.
    
    Attributes:
        id: UUID primary key
        user: User who is member
        committee: Committee the user belongs to
        role: Role in the committee
        is_active: Whether membership is currently active
        member_type: Type of membership (REGULAR, SUBSTITUTE, EXTERNAL)
        start_date: Start date of membership
        end_date: Optional end date of membership
        election_list_name: Name of election list (for substitutes)
        election_list_position: Position on election list
        election_votes: Number of votes received in election
        deleted_at: Soft-delete timestamp
        deleted_by: User who deleted the membership
    """
    
    MEMBER_TYPE_CHOICES = [
        ('REGULAR', 'Reguläres Mitglied'),
        ('SUBSTITUTE', 'Ersatzmitglied'),
        ('EXTERNAL', 'Externes Ausschussmitglied'),
    ]
    
    # Primary fields
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name='Benutzer'
    )
    committee = models.ForeignKey(
        Committee,
        on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name='Gremium'
    )
    role = models.ForeignKey(
        'roles.Role',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='committee_memberships',
        verbose_name='Rolle'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Aktiv'
    )
    member_type = models.CharField(
        max_length=20,
        choices=MEMBER_TYPE_CHOICES,
        default='REGULAR',
        verbose_name='Mitgliedstyp'
    )
    start_date = models.DateField(
        verbose_name='Beginn der Mitgliedschaft'
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Ende der Mitgliedschaft'
    )
    
    # Election information
    election_list_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Listenname bei Listenwahl'
    )
    election_list_position = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Listenplatz'
    )
    election_votes = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Stimmenzahl bei Wahl'
    )
    
    # Soft-delete fields
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Gelöscht am'
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deleted_memberships',
        verbose_name='Gelöscht von'
    )
    
    class Meta:
        verbose_name = 'Mitgliedschaft'
        verbose_name_plural = 'Mitgliedschaften'
        unique_together = [['user', 'committee']]
        ordering = ['committee', 'member_type', '-start_date']
    
    # Managers
    objects = SoftDeleteManager()
    all_objects = SoftDeleteManager(alive_only=False)
    
    def __str__(self) -> str:
        """String representation of membership."""
        return f"{self.user.get_full_name()} → {self.committee.name} ({self.get_member_type_display()})"
    
    def clean(self) -> None:
        """
        Validate membership rules.
        
        Rules:
        - External members cannot be in main committee simultaneously
        - External members cannot have election info
        
        Raises:
            ValidationError: If validation rules are violated
        """
        # External members cannot be in main committee simultaneously
        if self.member_type == 'EXTERNAL':
            # Get main committee
            main_committee = self.committee.parent if self.committee.committee_type != 'MAIN' else self.committee
            
            # Check if user is already in main committee
            if main_committee and Membership.objects.filter(
                user=self.user,
                committee__committee_type='MAIN',
                is_active=True
            ).exclude(id=self.id).exists():
                raise ValidationError({
                    'member_type': 'Externe Ausschussmitglieder dürfen nicht gleichzeitig im Hauptgremium sein'
                })
        
        # External members cannot have election info
        if self.member_type == 'EXTERNAL' and (self.election_list_name or self.election_list_position):
            raise ValidationError({
                'election_list_name': 'Externe Mitglieder haben keine Wahlinfo'
            })
    
    def delete(self, user: Optional['User'] = None) -> tuple:
        """
        Soft-delete membership.
        
        Args:
            user: User performing the delete operation
        
        Returns:
            Tuple of (count, details_dict)
        """
        self.deleted_at = timezone.now()
        if user:
            self.deleted_by = user
        self.save(update_fields=['deleted_at', 'deleted_by'])
        
        return (1, {'committees.Membership': 1})
    
    def hard_delete(self) -> tuple:
        """
        Permanently delete membership from database.
        
        Returns:
            Tuple of (count, details_dict)
        """
        return super().delete()
    
    @property
    def is_current(self) -> bool:
        """
        Check if membership is currently valid.
        
        Returns:
            True if membership is active, within date range, and not deleted
        """
        if self.deleted_at is not None:
            return False
        
        if not self.is_active:
            return False
        
        from datetime import date
        today = date.today()
        
        if self.start_date > today:
            return False
        
        if self.end_date and self.end_date < today:
            return False
        
        return True
