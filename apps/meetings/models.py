"""Models for meetings app."""

import uuid
from datetime import timedelta
from typing import TYPE_CHECKING, Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone

if TYPE_CHECKING:
    from apps.accounts.models import User
    from apps.committees.models import Committee


class Meeting(models.Model):
    """
    Meeting model for committee sessions.
    
    Supports three meeting types: ONLINE, HYBRID, IN_PERSON with dynamic
    location field validation. Implements a status workflow:
    DRAFT → SENT → IN_PROGRESS → COMPLETED
    
    Attributes:
        id: UUID primary key
        committee: Associated committee
        title: Meeting title
        meeting_number: Auto-generated number (format: YYYY-NN)
        date: Meeting date
        start_time: Scheduled start time
        end_time: Scheduled end time
        actual_start_time: Actual start time (optional)
        actual_end_time: Actual end time (optional)
        meeting_type: Type of meeting (ONLINE, HYBRID, IN_PERSON)
        location_url: Online meeting URL (required for ONLINE/HYBRID)
        location_name: Location name (required for IN_PERSON/HYBRID)
        location_street: Street address (required for IN_PERSON/HYBRID)
        location_zip: ZIP code (required for IN_PERSON/HYBRID)
        location_city: City (required for IN_PERSON/HYBRID)
        location_room: Room number (optional)
        status: Meeting status (DRAFT, SENT, IN_PROGRESS, COMPLETED)
        is_quorate: Whether meeting has quorum (optional)
        chair: Meeting chair (selected from committee members)
        clerk: Meeting clerk (selected from committee members)
        created_by: User who created the meeting
        created_at: Creation timestamp
        updated_at: Last update timestamp
        sent_at: When invitation was sent
    """
    
    # Meeting type choices
    MEETING_TYPE_CHOICES = [
        ('ONLINE', 'Online-Sitzung'),
        ('HYBRID', 'Hybrid-Sitzung'),
        ('IN_PERSON', 'Präsenzsitzung'),
    ]
    
    # Status workflow: DRAFT → SENT → IN_PROGRESS → COMPLETED
    STATUS_CHOICES = [
        ('DRAFT', 'Entwurf'),
        ('SENT', 'Einladung versendet'),
        ('IN_PROGRESS', 'In Bearbeitung'),
        ('COMPLETED', 'Abgeschlossen'),
    ]
    
    # Primary key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # Basic information
    committee = models.ForeignKey(
        'committees.Committee',
        on_delete=models.CASCADE,
        related_name='meetings',
        verbose_name='Gremium'
    )
    title = models.CharField(
        max_length=300,
        verbose_name='Titel'
    )
    meeting_number = models.CharField(
        max_length=20,
        verbose_name='Sitzungsnummer',
        help_text='Wird automatisch generiert (Format: YYYY-NN)'
    )
    
    # Date and time
    date = models.DateField(
        verbose_name='Datum'
    )
    start_time = models.TimeField(
        verbose_name='Beginn'
    )
    end_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Geplantes Ende'
    )
    actual_start_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Tatsächlicher Beginn'
    )
    actual_end_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Tatsächliches Ende'
    )
    
    # Meeting type and location
    meeting_type = models.CharField(
        max_length=10,
        choices=MEETING_TYPE_CHOICES,
        default='IN_PERSON',
        verbose_name='Sitzungstyp'
    )
    location_url = models.URLField(
        max_length=500,
        blank=True,
        verbose_name='Online-Link'
    )
    location_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Ortsbezeichnung'
    )
    location_street = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Straße'
    )
    location_zip = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='PLZ'
    )
    location_city = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Stadt'
    )
    location_room = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Raum'
    )
    
    # Status and metadata
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        verbose_name='Status'
    )
    is_quorate = models.BooleanField(
        null=True,
        blank=True,
        verbose_name='Beschlussfähig',
        help_text='Wird nach Anwesenheitsprüfung automatisch gesetzt'
    )
    
    # Responsible persons (dynamically selected from committee members)
    chair = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chaired_meetings',
        verbose_name='Vorsitz',
        help_text='Dynamische Auswahl aus allen aktiven Gremiumsmitgliedern'
    )
    clerk = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clerked_meetings',
        verbose_name='Protokollführung',
        help_text='Dynamische Auswahl aus allen aktiven Gremiumsmitgliedern'
    )
    
    # Audit fields
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_meetings',
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
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Einladung versendet am'
    )
    
    class Meta:
        verbose_name = 'Sitzung'
        verbose_name_plural = 'Sitzungen'
        ordering = ['-date', '-start_time']
        unique_together = [['committee', 'meeting_number']]
        indexes = [
            models.Index(fields=['committee', 'date']),
            models.Index(fields=['status']),
            models.Index(fields=['date', 'start_time']),
        ]
    
    def __str__(self) -> str:
        """String representation of meeting."""
        return f"{self.meeting_number} - {self.title} ({self.date})"
    
    def clean(self) -> None:
        """
        Validate meeting data.
        
        Validates:
        - Meeting type-specific location requirements
        - Time constraints (end_time after start_time)
        - Chair/Clerk membership validation
        
        Raises:
            ValidationError: If validation fails
        """
        from django.core.exceptions import ValidationError
        
        # Meeting type validation
        if self.meeting_type == 'ONLINE':
            # Online: location_url required, address fields not allowed
            if not self.location_url:
                raise ValidationError({
                    'location_url': 'Online-Link ist erforderlich für Online-Sitzungen'
                })
            
            has_address_fields = any([
                self.location_name,
                self.location_street,
                self.location_zip,
                self.location_city,
                self.location_room
            ])
            if has_address_fields:
                raise ValidationError({
                    'meeting_type': 'Adressfelder nicht erlaubt für Online-Sitzungen'
                })
        
        elif self.meeting_type == 'IN_PERSON':
            # In-person: address required, location_url not allowed
            has_full_address = all([
                self.location_name,
                self.location_street,
                self.location_zip,
                self.location_city
            ])
            if not has_full_address:
                raise ValidationError({
                    'location_name': 'Vollständige Adresse erforderlich für Präsenzsitzungen'
                })
            
            if self.location_url:
                raise ValidationError({
                    'location_url': 'Online-Link nicht erlaubt für Präsenzsitzungen'
                })
        
        elif self.meeting_type == 'HYBRID':
            # Hybrid: both URL and address required
            if not self.location_url:
                raise ValidationError({
                    'location_url': 'Online-Link erforderlich für Hybrid-Sitzungen'
                })
            
            has_full_address = all([
                self.location_name,
                self.location_street,
                self.location_zip,
                self.location_city
            ])
            if not has_full_address:
                raise ValidationError({
                    'location_name': 'Vollständige Adresse erforderlich für Hybrid-Sitzungen'
                })
        
        # Time validation
        if self.end_time and self.start_time and self.end_time <= self.start_time:
            raise ValidationError({
                'end_time': 'Endzeit muss nach Startzeit liegen'
            })
        
        if self.actual_end_time and self.actual_start_time:
            if self.actual_end_time <= self.actual_start_time:
                raise ValidationError({
                    'actual_end_time': 'Tatsächliches Ende muss nach tatsächlichem Beginn liegen'
                })
        
        # Chair/Clerk must be members of committee (if set)
        if self.chair and self.committee:
            is_member = self.committee.memberships.filter(
                user=self.chair,
                is_active=True
            ).exists()
            if not is_member:
                raise ValidationError({
                    'chair': f'{self.chair.get_full_name()} ist kein aktives Mitglied des Gremiums'
                })
        
        if self.clerk and self.committee:
            is_member = self.committee.memberships.filter(
                user=self.clerk,
                is_active=True
            ).exists()
            if not is_member:
                raise ValidationError({
                    'clerk': f'{self.clerk.get_full_name()} ist kein aktives Mitglied des Gremiums'
                })
    
    def save(self, *args, **kwargs) -> None:
        """
        Save meeting instance.
        
        Auto-generates meeting_number if new meeting.
        Format: {YEAR}-{COUNT:02d} (e.g., "2026-05")
        """
        if not self.meeting_number and self.committee and self.date:
            year = self.date.year
            
            # Count existing meetings for this committee in this year
            count = Meeting.objects.filter(
                committee=self.committee,
                date__year=year
            ).count() + 1
            
            self.meeting_number = f"{year}-{count:02d}"
        
        # Call full_clean for validation before saving
        self.full_clean()
        super().save(*args, **kwargs)
    
    def get_absolute_url(self) -> str:
        """Return absolute URL for meeting detail view."""
        return reverse('meetings:meeting_detail', kwargs={'pk': self.pk})
    
    @property
    def get_full_location(self) -> str:
        """
        Return formatted location string based on meeting_type.
        
        Returns:
            Formatted location string (URL for ONLINE, address for IN_PERSON,
            both for HYBRID)
        """
        if self.meeting_type == 'ONLINE':
            return f"Online: {self.location_url}"
        
        elif self.meeting_type == 'IN_PERSON':
            parts = [self.location_name]
            if self.location_room:
                parts.append(f"Raum {self.location_room}")
            parts.append(f"{self.location_street}, {self.location_zip} {self.location_city}")
            return ", ".join(parts)
        
        elif self.meeting_type == 'HYBRID':
            parts = [self.location_name]
            if self.location_room:
                parts.append(f"Raum {self.location_room}")
            parts.append(f"{self.location_street}, {self.location_zip} {self.location_city}")
            parts.append(f"(Online: {self.location_url})")
            return ", ".join(parts)
        
        return ""
    
    @property
    def is_upcoming(self) -> bool:
        """Check if meeting date is in the future."""
        from datetime import date
        return self.date >= date.today()
    
    @property
    def is_past(self) -> bool:
        """Check if meeting date is in the past."""
        from datetime import date
        return self.date < date.today()
    
    @property
    def is_editable(self) -> bool:
        """Meeting is editable only in DRAFT status."""
        return self.status == 'DRAFT'
    
    @property
    def is_deletable(self) -> bool:
        """Meeting is deletable only in DRAFT status."""
        return self.status == 'DRAFT'
    
    @property
    def can_send_invitation(self) -> bool:
        """Invitation can be sent only in DRAFT status."""
        return self.status == 'DRAFT'
    
    @property
    def can_complete(self) -> bool:
        """Meeting can be completed only when IN_PROGRESS."""
        return self.status == 'IN_PROGRESS'
    
    @property
    def has_agenda(self) -> bool:
        """
        Check if meeting has an associated agenda.
        
        Returns:
            True if an Agenda object exists for this meeting
        """
        return hasattr(self, 'agenda')
    
    @property
    def agenda_finalized(self) -> bool:
        """
        Check if the meeting's agenda is finalized (status = SENT).
        
        Returns:
            True if agenda exists and is finalized, False otherwise
        """
        if not self.has_agenda:
            return False
        return self.agenda.is_finalized
    
    def get_duration(self) -> Optional[timedelta]:
        """
        Calculate planned duration.
        
        Returns:
            timedelta if both start_time and end_time are set, None otherwise
        """
        if self.start_time and self.end_time:
            from datetime import datetime, date
            start_dt = datetime.combine(date.today(), self.start_time)
            end_dt = datetime.combine(date.today(), self.end_time)
            return end_dt - start_dt
        return None
    
    def get_actual_duration(self) -> Optional[timedelta]:
        """
        Calculate actual duration.
        
        Returns:
            timedelta if both actual times are set, None otherwise
        """
        if self.actual_start_time and self.actual_end_time:
            from datetime import datetime, date
            start_dt = datetime.combine(date.today(), self.actual_start_time)
            end_dt = datetime.combine(date.today(), self.actual_end_time)
            return end_dt - start_dt
        return None
    
    # Permission check methods
    @staticmethod
    def user_can_create(user: 'User', committee: 'Committee') -> bool:
        """
        Check if user is allowed to create a meeting for the given committee.
        
        Rules:
        - User has permission 'meeting.create' via role in THIS committee, OR
        - User has permission 'meeting.create_other' (admins), OR
        - Special rule: MAIN committee - Betriebsausschuss members with
          'meeting.create' permission
        
        Args:
            user: User instance
            committee: Committee instance
        
        Returns:
            True if user can create meeting in this committee
        """
        from apps.committees.models import Membership
        
        # Guard: Superuser can always create
        if user.is_superuser:
            return True
        
        # Check if user has 'meeting.create_other' permission (admin permission)
        if user.is_staff:
            return True
        
        # Get user's memberships in this committee
        memberships = Membership.objects.filter(
            user=user,
            committee=committee,
            is_active=True
        ).select_related('role')
        
        for membership in memberships:
            if membership.role:
                has_create_permission = membership.role.permissions.filter(
                    codename='meeting.create'
                ).exists()
                
                if has_create_permission:
                    return True
        
        # Special rule for MAIN committee
        if committee.committee_type == 'MAIN':
            betriebsausschuss = committee.subcommittees.filter(
                committee_type='COMMITTEE',
                is_active=True
            ).first()
            
            if betriebsausschuss:
                ba_memberships = Membership.objects.filter(
                    user=user,
                    committee=betriebsausschuss,
                    is_active=True
                ).select_related('role')
                
                for ba_membership in ba_memberships:
                    if ba_membership.role:
                        has_create_permission = ba_membership.role.permissions.filter(
                            codename='meeting.create'
                        ).exists()
                        
                        if has_create_permission:
                            return True
        
        return False
    
    @staticmethod
    def _user_has_permission(
        user: 'User',
        committee: 'Committee',
        permission_codename: str
    ) -> bool:
        """
        Helper method to check if user has specific permission in committee.
        
        Args:
            user: User instance
            committee: Committee instance
            permission_codename: Permission codename to check
        
        Returns:
            True if user has permission
        """
        from apps.committees.models import Membership
        
        # Guard: Superuser always has permission
        if user.is_superuser or user.is_staff:
            return True
        
        # Check if user has permission via role in committee
        memberships = Membership.objects.filter(
            user=user,
            committee=committee,
            is_active=True
        ).select_related('role')
        
        for membership in memberships:
            if membership.role:
                has_permission = membership.role.permissions.filter(
                    codename=permission_codename
                ).exists()
                
                if has_permission:
                    return True
        
        return False
    
    @staticmethod
    def user_can_send_invitation(user: 'User', meeting: 'Meeting') -> bool:
        """
        Check if user is allowed to send invitation (DRAFT → SENT).
        
        Args:
            user: User instance
            meeting: Meeting instance
        
        Returns:
            True if user can send invitation
        """
        return Meeting._user_has_permission(
            user,
            meeting.committee,
            'meeting.send_invitation'
        )
    
    @staticmethod
    def user_can_start_meeting(user: 'User', meeting: 'Meeting') -> bool:
        """
        Check if user is allowed to start meeting (SENT → IN_PROGRESS).
        
        Args:
            user: User instance
            meeting: Meeting instance
        
        Returns:
            True if user can start meeting
        """
        return Meeting._user_has_permission(
            user,
            meeting.committee,
            'meeting.start_meeting'
        )
    
    @staticmethod
    def user_can_complete_meeting(user: 'User', meeting: 'Meeting') -> bool:
        """
        Check if user is allowed to complete meeting (IN_PROGRESS → COMPLETED).
        
        Args:
            user: User instance
            meeting: Meeting instance
        
        Returns:
            True if user can complete meeting
        """
        return Meeting._user_has_permission(
            user,
            meeting.committee,
            'meeting.complete_meeting'
        )
    
    @staticmethod
    def user_can_view_meeting(user: 'User', meeting: 'Meeting') -> bool:
        """
        Check if user is allowed to view meeting details.
        
        Important for controlling access for guests/external users.
        
        Args:
            user: User instance
            meeting: Meeting instance
        
        Returns:
            True if user can view meeting
        """
        return Meeting._user_has_permission(
            user,
            meeting.committee,
            'meeting.view'
        )
