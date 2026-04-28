# 05 - Implementierungsplan: Beschlüsse (Resolutions)

**Version:** 1.0  
**Stand:** April 2026  
**Status:** ✅ Ready for Implementation

---

## Inhaltsverzeichnis

1. [Übersicht](#1-übersicht)
2. [Datenmodell](#2-datenmodell)
3. [Berechtigungen](#3-berechtigungen)
4. [Committee-Erweiterung](#4-committee-erweiterung)
5. [CRUD-Funktionalität](#5-crud-funktionalität)
6. [Agenda-Integration](#6-agenda-integration)
7. [Template-Struktur](#7-template-struktur)
8. [Implementierungs-Phasen](#8-implementierungs-phasen)
9. [BetrVG-Compliance](#9-betrvg-compliance)
10. [Testing-Strategie](#10-testing-strategie)

---

## 1. Übersicht

### 1.1 Ziele

Implementierung eines **Beschluss-Management-Systems** für Betriebsratsgremien mit folgenden Kernfunktionen:

1. **Beschlussvorschläge erstellen und verwalten**
2. **Status-Workflow**: `DRAFT` → `PROPOSED` → `APPROVED`/`REJECTED`
3. **Integration in Tagesordnung**: Beschlüsse als spezielle TOP-Typen
4. **BetrVG-konforme Abstimmungslogik** (Vorbereitung für Phase 5)
5. **Gremien-übergreifende Vorschläge**: Sub-Gremien können dem Hauptgremium Beschlüsse vorlegen

### 1.2 Abgrenzung - Was NICHT in dieser Phase implementiert wird

❌ **Abstimmungs-Logik während Sitzung** (kommt später in "Sitzungsablauf")
- Keine automatische Beschlussfähigkeits-Prüfung
- Keine Live-Abstimmung
- Keine automatische Stimmen-Validierung

❌ **Protokoll-Integration**
- Beschlüsse werden erst in späteren Phasen ins Protokoll übernommen

✅ **Was WIRD implementiert:**
- Datenmodell mit allen Feldern (inkl. Stimmen-Felder für späteren Gebrauch)
- Status-Workflow (DRAFT, PROPOSED, APPROVED, REJECTED)
- CRUD-Funktionalität
- Agenda-Integration (AgendaItemResolution)
- Berechtigungssystem

### 1.3 BetrVG-Grundlagen

**Relevante Paragraphen:**

| Paragraph | Thema | Relevanz |
|-----------|-------|----------|
| **§ 27 BetrVG** | Betriebsausschuss | Betriebsausschuss erstellt nur Beschlussvorschläge für BR |
| **§ 28 BetrVG** | Beschlussfassung | Ausschüsse machen Beschlussvorschläge, BR beschließt |
| **§ 33 BetrVG** | Beschlussfähigkeit | Mehrheit der Mitglieder muss anwesend sein |

**Wichtige Regel: Betriebsausschuss (BA)**
- Betriebsausschuss kann **keine eigenen Beschlüsse** fassen
- Erstellt ausschließlich Beschlussvorschläge für das Hauptgremium (BR)
- Technisch: `committee` zeigt auf BA, aber `propose_to_main_committee` ist immer `True`

---

## 2. Datenmodell

### 2.1 Resolution Model

**Datei:** `apps/resolutions/models.py`

```python
"""Models for resolutions app."""

import uuid
from datetime import date
from typing import Optional, TYPE_CHECKING

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
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
        unique_together = [['committee', 'resolution_number']]
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
        from django.urls import reverse
        return reverse('resolutions:resolution_detail', kwargs={'pk': self.pk})
    
    @staticmethod
    def user_can_create(user: 'User', committee: 'Committee') -> bool:
        """
        Check if user can create resolutions for the given committee.
        
        Rules:
        - User is superuser/staff, OR
        - User has 'resolution.create' permission in THIS committee, OR
        - User has 'resolution.create' in parent committee (for BA members)
        
        Args:
            user: User instance
            committee: Committee instance
        
        Returns:
            True if user can create resolution in this committee
        """
        from apps.committees.models import Membership
        
        # Guard: Superuser can always create
        if user.is_superuser or user.is_staff:
            return True
        
        # Check if user has permission in this committee
        memberships = Membership.objects.filter(
            user=user,
            committee=committee,
            is_active=True
        ).select_related('role')
        
        for membership in memberships:
            if membership.role:
                has_create_permission = membership.role.permissions.filter(
                    codename='resolution.create'
                ).exists()
                
                if has_create_permission:
                    return True
        
        # Special case: Betriebsausschuss members can create for parent BR
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
                            codename='resolution.create'
                        ).exists()
                        
                        if has_create_permission:
                            return True
        
        return False
```

### 2.2 Database Migrations

**Datei:** `apps/resolutions/migrations/0001_initial.py`

```python
# Generated by Django

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('committees', '0003_add_betriebsausschuss_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Resolution',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('resolution_number', models.CharField(blank=True, help_text='Wird automatisch generiert bei Beschlussfassung (Format: YYYYMMDD-XXX)', max_length=20, verbose_name='Beschlussnummer')),
                ('proposal', models.TextField(help_text='Der zur Abstimmung gestellte Beschlusstext', verbose_name='Beschlussvorschlag')),
                ('justification', models.TextField(blank=True, help_text='Begründung für den Beschlussvorschlag', verbose_name='Begründung')),
                ('is_quorate', models.BooleanField(blank=True, help_text='Wird während der Sitzung gesetzt (§ 33 BetrVG)', null=True, verbose_name='Beschlussfähig')),
                ('yes_votes', models.PositiveIntegerField(default=0, verbose_name='Ja-Stimmen')),
                ('no_votes', models.PositiveIntegerField(default=0, verbose_name='Nein-Stimmen')),
                ('abstentions', models.PositiveIntegerField(default=0, verbose_name='Enthaltungen')),
                ('status', models.CharField(choices=[('DRAFT', 'Entwurf'), ('PROPOSED', 'Vorgeschlagen'), ('APPROVED', 'Beschlossen'), ('REJECTED', 'Abgelehnt')], default='DRAFT', max_length=20, verbose_name='Status')),
                ('propose_to_main_committee', models.BooleanField(default=False, help_text='Beschluss kann in TOP des Hauptgremiums aufgenommen werden (§ 28 BetrVG)', verbose_name='Für Hauptgremium vorschlagen')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Erstellt am')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Aktualisiert am')),
                ('decided_at', models.DateTimeField(blank=True, help_text='Zeitpunkt der Beschlussfassung', null=True, verbose_name='Beschlossen/Abgelehnt am')),
                ('committee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='resolutions', to='committees.committee', verbose_name='Gremium')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_resolutions', to=settings.AUTH_USER_MODEL, verbose_name='Erstellt von')),
            ],
            options={
                'verbose_name': 'Beschluss',
                'verbose_name_plural': 'Beschlüsse',
                'ordering': ['-created_at'],
                'unique_together': {('committee', 'resolution_number')},
                'indexes': [
                    models.Index(fields=['committee', 'status'], name='resolutions_committ_status_idx'),
                    models.Index(fields=['status'], name='resolutions_status_idx'),
                    models.Index(fields=['resolution_number'], name='resolutions_number_idx'),
                ],
            },
        ),
    ]
```

---

## 3. Berechtigungen

### 3.1 Permission Definitions

**Datei:** `apps/resolutions/migrations/9999_seed_resolution_permissions.py`

```python
# Generated by Django

from django.db import migrations


def seed_resolution_permissions(apps, schema_editor):
    """Create resolution permissions and assign them to roles."""
    Permission = apps.get_model('roles', 'Permission')
    Role = apps.get_model('roles', 'Role')
    RolePermission = apps.get_model('roles', 'RolePermission')
    
    # ========== STEP 1: Create Permissions ==========
    
    RESOLUTION_PERMISSIONS = [
        ('resolution.create', 'Beschluss erstellen',
         'Neue Beschlussvorschläge erstellen', 'resolution'),
        ('resolution.edit', 'Beschluss bearbeiten',
         'Beschlussvorschläge bearbeiten (vor Aufnahme in TOP)', 'resolution'),
        ('resolution.edit_during_meeting', 'Beschluss während Sitzung bearbeiten',
         'Beschlussvorschläge während laufender Sitzung bearbeiten (nur Vorsitz/Stellv.)', 'resolution'),
        ('resolution.delete', 'Beschluss löschen',
         'Beschlussvorschläge löschen (nur im Status DRAFT)', 'resolution'),
        ('resolution.view', 'Beschluss anzeigen',
         'Beschlussvorschläge und Details ansehen', 'resolution'),
        ('resolution.propose', 'Beschluss vorschlagen',
         'Status auf "Vorgeschlagen" setzen', 'resolution'),
        ('resolution.decide', 'Beschluss beschließen/ablehnen',
         'Status auf "Beschlossen" oder "Abgelehnt" setzen (während Sitzung)', 'resolution'),
    ]
    
    for codename, name, description, category in RESOLUTION_PERMISSIONS:
        Permission.objects.get_or_create(
            codename=codename,
            defaults={
                'name': name,
                'description': description,
                'category': category
            }
        )
    
    # ========== STEP 2: Assign Permissions to Roles ==========
    
    resolution_perms = Permission.objects.filter(category='resolution')
    
    # SYSTEM_ADMIN gets all resolution permissions
    try:
        system_admin = Role.objects.get(codename='SYSTEM_ADMIN')
        for perm in resolution_perms:
            RolePermission.objects.get_or_create(
                role=system_admin,
                permission=perm
            )
    except Role.DoesNotExist:
        pass
    
    # CHAIR gets: create, edit, edit_during_meeting, delete, view, propose, decide
    try:
        chair = Role.objects.get(codename='CHAIR')
        chair_perms = resolution_perms.filter(
            codename__in=[
                'resolution.create', 'resolution.edit', 'resolution.edit_during_meeting',
                'resolution.delete', 'resolution.view', 'resolution.propose', 'resolution.decide'
            ]
        )
        for perm in chair_perms:
            RolePermission.objects.get_or_create(
                role=chair,
                permission=perm
            )
    except Role.DoesNotExist:
        pass
    
    # VICE_CHAIR gets: create, edit, edit_during_meeting, delete, view, propose, decide
    try:
        vice_chair = Role.objects.get(codename='VICE_CHAIR')
        vice_chair_perms = resolution_perms.filter(
            codename__in=[
                'resolution.create', 'resolution.edit', 'resolution.edit_during_meeting',
                'resolution.delete', 'resolution.view', 'resolution.propose', 'resolution.decide'
            ]
        )
        for perm in vice_chair_perms:
            RolePermission.objects.get_or_create(
                role=vice_chair,
                permission=perm
            )
    except Role.DoesNotExist:
        pass
    
    # CLERK gets: create, edit, edit_during_meeting, view, delete, propose
    try:
        clerk = Role.objects.get(codename='CLERK')
        clerk_perms = resolution_perms.filter(
            codename__in=[
                'resolution.create', 'resolution.edit', 'resolution.edit_during_meeting',
                'resolution.view', 'resolution.delete', 'resolution.propose'
            ]
        )
        for perm in clerk_perms:
            RolePermission.objects.get_or_create(
                role=clerk,
                permission=perm
            )
    except Role.DoesNotExist:
        pass
    
    # MEMBER gets: create, edit, view, delete, propose
    try:
        member = Role.objects.get(codename='MEMBER')
        member_perms = resolution_perms.filter(
            codename__in=[
                'resolution.create', 'resolution.edit', 'resolution.view',
                'resolution.delete', 'resolution.propose'
            ]
        )
        for perm in member_perms:
            RolePermission.objects.get_or_create(
                role=member,
                permission=perm
            )
    except Role.DoesNotExist:
        pass
    
    # SUBSTITUTE, EXTERNAL_MEMBER, GUEST: keine Permissions


def reverse_resolution_permissions(apps, schema_editor):
    """Remove resolution permissions."""
    Permission = apps.get_model('roles', 'Permission')
    RolePermission = apps.get_model('roles', 'RolePermission')
    
    # Delete RolePermissions for resolution permissions
    resolution_perms = Permission.objects.filter(category='resolution')
    RolePermission.objects.filter(permission__in=resolution_perms).delete()
    
    # Delete all resolution permissions
    resolution_perms.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('resolutions', '0001_initial'),
        ('roles', '9999_seed_roles_and_permissions'),
    ]

    operations = [
        migrations.RunPython(seed_resolution_permissions, reverse_resolution_permissions),
    ]
```

### 3.2 Permission Matrix

| Permission | SYSTEM_ADMIN | CHAIR | VICE_CHAIR | CLERK | MEMBER | SUBSTITUTE | EXTERNAL | GUEST |
|------------|--------------|-------|------------|-------|--------|------------|----------|-------|
| `resolution.create` | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| `resolution.edit` | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| `resolution.edit_during_meeting` | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| `resolution.delete` | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| `resolution.view` | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| `resolution.propose` | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| `resolution.decide` | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |

---

## 4. Committee-Erweiterung

### 4.1 Committee Model Update

**Datei:** `apps/committees/models.py` (Erweiterung)

Folgendes Feld zum `Committee`-Model hinzufügen:

```python
# Resolution configuration
can_create_resolutions = models.BooleanField(
    default=False,
    verbose_name='Beschlüsse erstellen erlauben',
    help_text='Erlaubt diesem Gremium Beschlüsse zu erstellen (Betriebsausschuss automatisch)'
)
```

**Logik in `Committee.clean()`:**

```python
# Betriebsausschuss must always be able to create resolutions
if self.committee_type == 'COMMITTEE':
    self.can_create_resolutions = True
```

**Logik in `Committee.save()`:**

```python
# Auto-set can_create_resolutions for Betriebsausschuss
if self.committee_type == 'COMMITTEE':
    self.can_create_resolutions = True
```

### 4.2 Migration

**Datei:** `apps/committees/migrations/0004_add_can_create_resolutions.py`

```python
# Generated by Django

from django.db import migrations, models


def set_betriebsausschuss_can_create_resolutions(apps, schema_editor):
    """Set can_create_resolutions=True for all COMMITTEE types."""
    Committee = apps.get_model('committees', 'Committee')
    Committee.objects.filter(committee_type='COMMITTEE').update(can_create_resolutions=True)


class Migration(migrations.Migration):

    dependencies = [
        ('committees', '0003_add_betriebsausschuss_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='committee',
            name='can_create_resolutions',
            field=models.BooleanField(
                default=False,
                help_text='Erlaubt diesem Gremium Beschlüsse zu erstellen (Betriebsausschuss automatisch)',
                verbose_name='Beschlüsse erstellen erlauben'
            ),
        ),
        migrations.RunPython(
            set_betriebsausschuss_can_create_resolutions,
            reverse_code=migrations.RunPython.noop
        ),
    ]
```

### 4.3 Committee Form Update

**Datei:** `apps/committees/forms.py`

```python
class CommitteeForm(forms.ModelForm):
    """Form for creating/editing committees."""
    
    class Meta:
        model = Committee
        fields = [
            'name', 'committee_type', 'parent', 'description',
            'total_seats', 'quorum_type', 'can_create_resolutions',
            # ... other fields
        ]
        widgets = {
            # ... existing widgets
            'can_create_resolutions': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Disable can_create_resolutions for COMMITTEE type
        if self.instance and self.instance.committee_type == 'COMMITTEE':
            self.fields['can_create_resolutions'].disabled = True
            self.fields['can_create_resolutions'].help_text = (
                'Betriebsausschuss kann immer Beschlussvorschläge erstellen (§ 27 BetrVG)'
            )
```

---

## 5. CRUD-Funktionalität

### 5.1 Forms

**Datei:** `apps/resolutions/forms.py`

```python
"""Forms for resolutions app."""

from django import forms
from django.core.exceptions import ValidationError

from .models import Resolution
from apps.committees.models import Committee, Membership


class ResolutionForm(forms.ModelForm):
    """Form for creating/editing resolutions."""
    
    class Meta:
        model = Resolution
        fields = [
            'committee', 'proposal', 'justification',
            'propose_to_main_committee'
        ]
        widgets = {
            'committee': forms.Select(attrs={'class': 'form-select'}),
            'proposal': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Beschlusstext eingeben...'
            }),
            'justification': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Begründung (optional)...'
            }),
            'propose_to_main_committee': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, user, *args, **kwargs):
        """Initialize form with user context."""
        self.user = user
        super().__init__(*args, **kwargs)
        
        # Filter committees: only those user is member of + parent committees
        self._filter_committee_choices()
        
        # Disable propose_to_main_committee for committees without parent
        if self.instance and self.instance.committee:
            if not self.instance.committee.parent:
                self.fields['propose_to_main_committee'].disabled = True
                self.fields['propose_to_main_committee'].widget.attrs['disabled'] = 'disabled'
        
        # Auto-set and disable for Betriebsausschuss
        if self.instance and self.instance.committee:
            if self.instance.committee.committee_type == 'COMMITTEE':
                self.fields['propose_to_main_committee'].initial = True
                self.fields['propose_to_main_committee'].disabled = True
                self.fields['propose_to_main_committee'].help_text = (
                    'Betriebsausschuss erstellt nur Beschlussvorschläge für das Hauptgremium (§ 27 BetrVG)'
                )
    
    def _filter_committee_choices(self):
        """Filter committee choices based on user membership."""
        if self.user.is_superuser or self.user.is_staff:
            # Superuser sees all committees with can_create_resolutions=True
            allowed_committees = Committee.objects.filter(
                can_create_resolutions=True
            )
        else:
            # Get committees where user is member
            user_committees = Committee.objects.filter(
                memberships__user=self.user,
                memberships__is_active=True,
                can_create_resolutions=True
            ).distinct()
            
            # Get parent committees of user's committees
            parent_committees = Committee.objects.filter(
                subcommittees__in=user_committees,
                can_create_resolutions=True
            ).distinct()
            
            # Combine both querysets
            allowed_committees = (user_committees | parent_committees).distinct()
        
        self.fields['committee'].queryset = allowed_committees
    
    def clean(self):
        """Validate form data."""
        cleaned_data = super().clean()
        committee = cleaned_data.get('committee')
        propose_to_main = cleaned_data.get('propose_to_main_committee')
        
        # Validate user can create for this committee
        if committee:
            if not Resolution.user_can_create(self.user, committee):
                raise ValidationError({
                    'committee': 'Sie haben keine Berechtigung für dieses Gremium.'
                })
            
            # Check if committee allows resolutions
            if not committee.can_create_resolutions:
                raise ValidationError({
                    'committee': 'Dieses Gremium darf keine Beschlüsse erstellen.'
                })
            
            # Validate propose_to_main_committee
            if propose_to_main and not committee.parent:
                raise ValidationError({
                    'propose_to_main_committee': 
                    'Nur Beschlüsse von Ausschüssen können dem Hauptgremium vorgeschlagen werden.'
                })
            
            # Force propose_to_main for Betriebsausschuss
            if committee.committee_type == 'COMMITTEE':
                cleaned_data['propose_to_main_committee'] = True
        
        return cleaned_data


class ResolutionStatusForm(forms.Form):
    """Form for changing resolution status."""
    
    new_status = forms.ChoiceField(
        choices=[
            ('PROPOSED', 'Vorschlagen'),
            ('DRAFT', 'Zurückziehen'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Neuer Status'
    )
    
    def __init__(self, resolution, *args, **kwargs):
        """Initialize form with resolution context."""
        self.resolution = resolution
        super().__init__(*args, **kwargs)
        
        # Filter available status transitions
        available_choices = []
        
        if resolution.can_be_proposed:
            available_choices.append(('PROPOSED', 'Vorschlagen'))
        
        if resolution.can_be_withdrawn:
            available_choices.append(('DRAFT', 'Zurückziehen'))
        
        self.fields['new_status'].choices = available_choices
```

### 5.2 Views

**Datei:** `apps/resolutions/views.py`

```python
"""Views for resolutions app."""

from typing import Any, Dict

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, DetailView, ListView, FormView

from .forms import ResolutionForm, ResolutionStatusForm
from .models import Resolution
from .mixins import ResolutionPermissionMixin
from apps.committees.models import Committee


class ResolutionListView(LoginRequiredMixin, ListView):
    """
    List all resolutions for committees user is member of.
    
    Filters by committee if provided in URL query parameter.
    """
    
    model = Resolution
    template_name = 'resolutions/resolution_list.html'
    context_object_name = 'resolutions'
    paginate_by = 20
    
    def get_queryset(self) -> QuerySet:
        """
        Get resolutions for committees user is member of.
        
        Returns:
            QuerySet of resolutions
        """
        user = self.request.user
        
        if user.is_superuser or user.is_staff:
            queryset = Resolution.objects.all()
        else:
            # Get committees where user is member
            user_committees = Committee.objects.filter(
                memberships__user=user,
                memberships__is_active=True
            ).distinct()
            
            queryset = Resolution.objects.filter(
                committee__in=user_committees
            )
        
        # Filter by committee if provided
        committee_id = self.request.GET.get('committee')
        if committee_id:
            queryset = queryset.filter(committee_id=committee_id)
        
        # Filter by status if provided
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.select_related('committee', 'created_by').order_by('-created_at')
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Add filter context."""
        context = super().get_context_data(**kwargs)
        
        # Get user's committees for filter
        user = self.request.user
        if user.is_superuser or user.is_staff:
            user_committees = Committee.objects.filter(can_create_resolutions=True)
        else:
            user_committees = Committee.objects.filter(
                memberships__user=user,
                memberships__is_active=True,
                can_create_resolutions=True
            ).distinct()
        
        context['user_committees'] = user_committees
        context['selected_committee'] = self.request.GET.get('committee')
        context['selected_status'] = self.request.GET.get('status')
        context['status_choices'] = Resolution.STATUS_CHOICES
        
        return context


class ResolutionDetailView(LoginRequiredMixin, ResolutionPermissionMixin, DetailView):
    """
    Display resolution details.
    
    Requires 'resolution.view' permission.
    """
    
    model = Resolution
    template_name = 'resolutions/resolution_detail.html'
    context_object_name = 'resolution'
    required_permission = 'resolution.view'
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Add permission context."""
        context = super().get_context_data(**kwargs)
        
        resolution = self.object
        user = self.request.user
        
        # Check user permissions
        context['user_can_edit'] = self.user_has_permission(user, resolution.committee, 'resolution.edit')
        context['user_can_delete'] = self.user_has_permission(user, resolution.committee, 'resolution.delete')
        context['user_can_propose'] = self.user_has_permission(user, resolution.committee, 'resolution.propose')
        
        return context


class ResolutionCreateView(LoginRequiredMixin, CreateView):
    """
    Create new resolution.
    
    Requires 'resolution.create' permission for selected committee.
    """
    
    model = Resolution
    form_class = ResolutionForm
    template_name = 'resolutions/resolution_form.html'
    
    def get_form_kwargs(self) -> Dict[str, Any]:
        """Add user to form kwargs."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        """Handle valid form submission."""
        # Set created_by
        form.instance.created_by = self.request.user
        
        # Check permission
        committee = form.instance.committee
        if not Resolution.user_can_create(self.request.user, committee):
            messages.error(
                self.request,
                'Sie haben keine Berechtigung, Beschlüsse für dieses Gremium zu erstellen.'
            )
            return self.form_invalid(form)
        
        response = super().form_valid(form)
        
        messages.success(
            self.request,
            f'Beschlussvorschlag wurde erstellt.'
        )
        
        return response
    
    def get_success_url(self) -> str:
        """Redirect to detail page."""
        return reverse('resolutions:resolution_detail', kwargs={'pk': self.object.pk})


class ResolutionUpdateView(LoginRequiredMixin, ResolutionPermissionMixin, UpdateView):
    """
    Update existing resolution.
    
    Requires 'resolution.edit' permission.
    Only allowed if resolution.is_editable is True.
    """
    
    model = Resolution
    form_class = ResolutionForm
    template_name = 'resolutions/resolution_form.html'
    required_permission = 'resolution.edit'
    
    def get_form_kwargs(self) -> Dict[str, Any]:
        """Add user to form kwargs."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def dispatch(self, request, *args, **kwargs):
        """Check if resolution is editable."""
        resolution = self.get_object()
        
        # Check if editable
        if not resolution.is_editable:
            messages.error(
                request,
                'Dieser Beschluss kann nicht mehr bearbeitet werden.'
            )
            return redirect('resolutions:resolution_detail', pk=resolution.pk)
        
        # Check if user needs edit_during_meeting permission
        if resolution.is_linked_to_agenda:
            for agenda_item in resolution.agenda_items.all():
                if agenda_item.agenda.meeting.status == 'IN_PROGRESS':
                    if not self.user_has_permission(request.user, resolution.committee, 'resolution.edit_during_meeting'):
                        raise PermissionDenied('Sie benötigen die Berechtigung "Beschluss während Sitzung bearbeiten".')
        
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        """Handle valid form submission."""
        response = super().form_valid(form)
        
        messages.success(
            self.request,
            f'Beschlussvorschlag wurde aktualisiert.'
        )
        
        return response
    
    def get_success_url(self) -> str:
        """Redirect to detail page."""
        return reverse('resolutions:resolution_detail', kwargs={'pk': self.object.pk})


class ResolutionDeleteView(LoginRequiredMixin, ResolutionPermissionMixin, DeleteView):
    """
    Delete resolution.
    
    Requires 'resolution.delete' permission.
    Only allowed if resolution.is_deletable is True.
    """
    
    model = Resolution
    template_name = 'resolutions/resolution_confirm_delete.html'
    success_url = reverse_lazy('resolutions:resolution_list')
    required_permission = 'resolution.delete'
    
    def dispatch(self, request, *args, **kwargs):
        """Check if resolution is deletable."""
        resolution = self.get_object()
        
        if not resolution.is_deletable:
            messages.error(
                request,
                'Dieser Beschluss kann nicht gelöscht werden. Nur Entwürfe ohne Verknüpfung zu Tagesordnungen können gelöscht werden.'
            )
            return redirect('resolutions:resolution_detail', pk=resolution.pk)
        
        return super().dispatch(request, *args, **kwargs)
    
    def delete(self, request, *args, **kwargs):
        """Handle delete with success message."""
        messages.success(request, 'Beschlussvorschlag wurde gelöscht.')
        return super().delete(request, *args, **kwargs)


class ResolutionChangeStatusView(LoginRequiredMixin, ResolutionPermissionMixin, FormView):
    """
    Change resolution status (DRAFT ↔ PROPOSED).
    
    Requires 'resolution.propose' permission.
    """
    
    form_class = ResolutionStatusForm
    template_name = 'resolutions/resolution_change_status.html'
    required_permission = 'resolution.propose'
    
    def get_resolution(self) -> Resolution:
        """Get resolution from URL."""
        return get_object_or_404(Resolution, pk=self.kwargs['pk'])
    
    def get_form_kwargs(self) -> Dict[str, Any]:
        """Add resolution to form kwargs."""
        kwargs = super().get_form_kwargs()
        kwargs['resolution'] = self.get_resolution()
        return kwargs
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Add resolution to context."""
        context = super().get_context_data(**kwargs)
        context['resolution'] = self.get_resolution()
        return context
    
    def form_valid(self, form):
        """Handle status change."""
        resolution = self.get_resolution()
        new_status = form.cleaned_data['new_status']
        
        # Validate transition
        if new_status == 'PROPOSED' and not resolution.can_be_proposed:
            messages.error(self.request, 'Status kann nicht geändert werden.')
            return redirect('resolutions:resolution_detail', pk=resolution.pk)
        
        if new_status == 'DRAFT' and not resolution.can_be_withdrawn:
            messages.error(self.request, 'Beschluss kann nicht zurückgezogen werden.')
            return redirect('resolutions:resolution_detail', pk=resolution.pk)
        
        # Change status
        old_status = resolution.get_status_display()
        resolution.status = new_status
        resolution.save()
        
        messages.success(
            self.request,
            f'Status geändert von "{old_status}" zu "{resolution.get_status_display()}".'
        )
        
        return redirect('resolutions:resolution_detail', pk=resolution.pk)
    
    def get_success_url(self) -> str:
        """Redirect to detail page."""
        return reverse('resolutions:resolution_detail', kwargs={'pk': self.get_resolution().pk})
```

### 5.3 Permission Mixin

**Datei:** `apps/resolutions/mixins.py`

```python
"""Mixins for resolutions app."""

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from .models import Resolution
from apps.committees.models import Committee, Membership


class ResolutionPermissionMixin:
    """
    Mixin to check resolution permissions.
    
    Checks if user has required permission for the resolution's committee.
    Set 'required_permission' attribute on view.
    """
    
    required_permission = None
    
    def dispatch(self, request, *args, **kwargs):
        """Check permission before dispatching."""
        if not self.required_permission:
            raise ValueError('required_permission must be set')
        
        # Get resolution
        resolution = self.get_object()
        
        # Check permission
        if not self.user_has_permission(request.user, resolution.committee, self.required_permission):
            raise PermissionDenied(
                f'Sie haben keine Berechtigung: {self.required_permission}'
            )
        
        return super().dispatch(request, *args, **kwargs)
    
    @staticmethod
    def user_has_permission(user, committee, permission_codename):
        """
        Check if user has permission in committee.
        
        Args:
            user: User instance
            committee: Committee instance
            permission_codename: Permission codename (e.g. 'resolution.view')
        
        Returns:
            True if user has permission
        """
        # Superuser always has permission
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
```

### 5.4 URLs

**Datei:** `apps/resolutions/urls.py`

```python
"""URL configuration for resolutions app."""

from django.urls import path

from . import views

app_name = 'resolutions'

urlpatterns = [
    # List and detail
    path('', views.ResolutionListView.as_view(), name='resolution_list'),
    path('<uuid:pk>/', views.ResolutionDetailView.as_view(), name='resolution_detail'),
    
    # CRUD operations
    path('create/', views.ResolutionCreateView.as_view(), name='resolution_create'),
    path('<uuid:pk>/edit/', views.ResolutionUpdateView.as_view(), name='resolution_edit'),
    path('<uuid:pk>/delete/', views.ResolutionDeleteView.as_view(), name='resolution_delete'),
    
    # Status change
    path('<uuid:pk>/change-status/', views.ResolutionChangeStatusView.as_view(), name='resolution_change_status'),
]
```

**In Haupt-URLs registrieren:** `config/urls.py`

```python
urlpatterns = [
    # ... existing patterns
    path('resolutions/', include('apps.resolutions.urls')),
]
```

---

## 6. Agenda-Integration

### 6.1 AgendaItemResolution Model

**Datei:** `apps/agendas/models.py` (Erweiterung)

```python
class AgendaItemResolution(AgendaItem):
    """
    Agenda item for resolutions.
    
    Links a resolution to an agenda. Title and description are separate
    from the resolution's proposal/justification to allow customization
    for the specific meeting context.
    
    Attributes:
        resolution: ForeignKey to Resolution
    """
    
    resolution = models.ForeignKey(
        'resolutions.Resolution',
        on_delete=models.CASCADE,
        related_name='agenda_items',
        verbose_name='Beschluss'
    )
    
    class Meta:
        verbose_name = 'Beschluss-TOP'
        verbose_name_plural = 'Beschluss-TOPs'
        ordering = ['sort_order', 'item_number']
    
    def clean(self) -> None:
        """
        Validate agenda item resolution.
        
        Validates:
        - Resolution must be in PROPOSED status
        - Resolution's committee must match agenda's meeting's committee OR
          resolution must be proposed to main committee
        
        Raises:
            ValidationError: If validation fails
        """
        super().clean()
        
        if self.resolution:
            # Check status
            if self.resolution.status != 'PROPOSED':
                raise ValidationError({
                    'resolution': 'Nur Beschlüsse im Status "Vorgeschlagen" können zur Tagesordnung hinzugefügt werden.'
                })
            
            # Check committee match
            if self.agenda and self.agenda.meeting:
                meeting_committee = self.agenda.meeting.committee
                
                # Direct match
                if self.resolution.committee == meeting_committee:
                    return
                
                # Resolution proposed to main committee
                if self.resolution.propose_to_main_committee:
                    if self.resolution.committee.parent == meeting_committee:
                        return
                
                raise ValidationError({
                    'resolution': 'Beschluss gehört nicht zu diesem Gremium.'
                })
```

### 6.2 Migration

**Datei:** `apps/agendas/migrations/0002_add_agenda_item_resolution.py`

```python
# Generated by Django

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('agendas', '0001_initial'),
        ('resolutions', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AgendaItemResolution',
            fields=[
                ('agendaitem_ptr', models.OneToOneField(
                    auto_created=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    parent_link=True,
                    primary_key=True,
                    serialize=False,
                    to='agendas.agendaitem'
                )),
                ('resolution', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='agenda_items',
                    to='resolutions.resolution',
                    verbose_name='Beschluss'
                )),
            ],
            options={
                'verbose_name': 'Beschluss-TOP',
                'verbose_name_plural': 'Beschluss-TOPs',
                'ordering': ['sort_order', 'item_number'],
            },
            bases=('agendas.agendaitem',),
        ),
    ]
```

### 6.3 Forms

**Datei:** `apps/agendas/forms.py` (Erweiterung)

```python
class AgendaItemResolutionForm(forms.ModelForm):
    """Form for adding resolution to agenda."""
    
    class Meta:
        model = AgendaItemResolution
        fields = ['resolution', 'title', 'description']
        widgets = {
            'resolution': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'TOP-Titel für diesen Beschluss'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Beschreibung (optional)...'
            }),
        }
    
    def __init__(self, agenda, *args, **kwargs):
        """Initialize form with agenda context."""
        self.agenda = agenda
        super().__init__(*args, **kwargs)
        
        # Filter resolutions: only PROPOSED for this committee
        self._filter_resolution_choices()
    
    def _filter_resolution_choices(self):
        """Filter resolution choices based on agenda's meeting committee."""
        from apps.resolutions.models import Resolution
        
        meeting_committee = self.agenda.meeting.committee
        
        # Get resolutions directly for this committee
        direct_resolutions = Resolution.objects.filter(
            committee=meeting_committee,
            status='PROPOSED'
        )
        
        # Get resolutions proposed to this committee from sub-committees
        proposed_resolutions = Resolution.objects.filter(
            committee__parent=meeting_committee,
            status='PROPOSED',
            propose_to_main_committee=True
        )
        
        # Combine querysets
        available_resolutions = (direct_resolutions | proposed_resolutions).distinct()
        
        # Exclude resolutions already in this agenda
        existing_resolution_ids = AgendaItemResolution.objects.filter(
            agenda=self.agenda
        ).values_list('resolution_id', flat=True)
        
        available_resolutions = available_resolutions.exclude(
            id__in=existing_resolution_ids
        )
        
        self.fields['resolution'].queryset = available_resolutions
    
    def save(self, commit=True):
        """Save agenda item with agenda set."""
        instance = super().save(commit=False)
        instance.agenda = self.agenda
        
        if commit:
            instance.save()
        
        return instance
```

### 6.4 Views

**Datei:** `apps/agendas/views.py` (Erweiterung)

```python
class AgendaItemResolutionCreateView(LoginRequiredMixin, AgendaPermissionMixin, CreateView):
    """
    Add resolution to agenda.
    
    Requires 'agenda.add_item_resolution' permission.
    """
    
    model = AgendaItemResolution
    form_class = AgendaItemResolutionForm
    template_name = 'agendas/item_resolution_form.html'
    required_permission = 'agenda.add_item_resolution'
    
    def get_agenda(self) -> Agenda:
        """Get agenda from URL parameter."""
        agenda_id = self.request.GET.get('agenda') or self.kwargs.get('agenda_id')
        return get_object_or_404(Agenda, pk=agenda_id)
    
    def get_form_kwargs(self) -> Dict[str, Any]:
        """Add agenda to form kwargs."""
        kwargs = super().get_form_kwargs()
        kwargs['agenda'] = self.get_agenda()
        return kwargs
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Add agenda to context."""
        context = super().get_context_data(**kwargs)
        context['agenda'] = self.get_agenda()
        context['is_create'] = True
        return context
    
    def form_valid(self, form):
        """Handle valid form submission."""
        agenda = self.get_agenda()
        
        # Check if agenda is editable
        if not agenda.is_editable:
            messages.error(
                self.request,
                f'Tagesordnung kann nicht bearbeitet werden. '
                f'Sitzungsstatus: {agenda.meeting.get_status_display()}'
            )
            return redirect('meetings:meeting_detail', pk=agenda.meeting.pk)
        
        # Calculate sort_order
        last_item = AgendaItemResolution.objects.filter(
            agenda=agenda
        ).order_by('-sort_order').first()
        
        if last_item:
            form.instance.sort_order = last_item.sort_order + 1.0
        else:
            # Check all agenda items
            last_any_item = agenda.agendaitemregular_items.order_by('-sort_order').first()
            if last_any_item:
                form.instance.sort_order = last_any_item.sort_order + 1.0
            else:
                form.instance.sort_order = 1.0
        
        response = super().form_valid(form)
        
        messages.success(
            self.request,
            f'Beschluss "{form.instance.title}" wurde zur Tagesordnung hinzugefügt.'
        )
        
        return response
    
    def get_success_url(self) -> str:
        """Redirect to meeting detail page."""
        return reverse('meetings:meeting_detail', kwargs={'pk': self.object.agenda.meeting.pk})
```

### 6.5 URL Update

**Datei:** `apps/agendas/urls.py` (Erweiterung)

```python
urlpatterns = [
    # ... existing patterns
    
    # Resolution items
    path('item/resolution/create/', views.AgendaItemResolutionCreateView.as_view(), name='item_resolution_create'),
]
```

### 6.6 Permission Update

**Datei:** `apps/agendas/migrations/9999_seed_agenda_permissions.py` (Erweiterung)

Neue Permission hinzufügen:

```python
('agenda.add_item_resolution', 'Beschluss-TOP hinzufügen',
 'Beschluss zur Tagesordnung hinzufügen', 'agenda'),
```

---

## 7. Template-Struktur

### 7.1 Template-Hierarchie

```
apps/resolutions/templates/resolutions/
├── resolution_list.html           # List view
├── resolution_detail.html         # Full page detail
├── resolution_detail_modal.html   # Modal wrapper for agenda
├── resolution_form.html           # Create/Edit form
├── resolution_confirm_delete.html # Delete confirmation
├── resolution_change_status.html  # Status change form
└── includes/
    ├── resolution_detail_content.html  # Shared detail content
    ├── resolution_card.html            # Card for list view
    └── resolution_status_badge.html    # Status badge component
```

### 7.2 Detail Content Template (Shared)

**Datei:** `apps/resolutions/templates/resolutions/includes/resolution_detail_content.html`

```html
<!-- Shared resolution detail content -->
<div class="resolution-detail">
    <!-- Status Badge -->
    <div class="mb-3">
        {% include 'resolutions/includes/resolution_status_badge.html' with status=resolution.status %}
    </div>
    
    <!-- Resolution Number -->
    {% if resolution.resolution_number %}
    <div class="mb-3">
        <strong>Beschlussnummer:</strong> {{ resolution.resolution_number }}
    </div>
    {% endif %}
    
    <!-- Committee -->
    <div class="mb-3">
        <strong>Gremium:</strong> 
        <a href="{% url 'committees:committee_detail' resolution.committee.pk %}">
            {{ resolution.committee.name }}
        </a>
    </div>
    
    <!-- Propose to Main Committee Badge -->
    {% if resolution.propose_to_main_committee %}
    <div class="mb-3">
        <span class="badge bg-info">
            <i class="bi bi-arrow-up-circle"></i> Für Hauptgremium vorgeschlagen
        </span>
    </div>
    {% endif %}
    
    <!-- Proposal -->
    <div class="mb-4">
        <h5>Beschlussvorschlag</h5>
        <div class="border rounded p-3 bg-light">
            {{ resolution.proposal|linebreaks }}
        </div>
    </div>
    
    <!-- Justification -->
    {% if resolution.justification %}
    <div class="mb-4">
        <h5>Begründung</h5>
        <div class="border rounded p-3 bg-light">
            {{ resolution.justification|linebreaks }}
        </div>
    </div>
    {% endif %}
    
    <!-- Voting Results (only if decided) -->
    {% if resolution.show_voting_fields %}
    <div class="mb-4">
        <h5>Abstimmungsergebnis</h5>
        <table class="table table-bordered">
            <tbody>
                <tr>
                    <th>Beschlussfähig:</th>
                    <td>
                        {% if resolution.is_quorate %}
                            <span class="text-success"><i class="bi bi-check-circle"></i> Ja</span>
                        {% elif resolution.is_quorate is False %}
                            <span class="text-danger"><i class="bi bi-x-circle"></i> Nein</span>
                        {% else %}
                            <span class="text-muted">Nicht gesetzt</span>
                        {% endif %}
                    </td>
                </tr>
                <tr>
                    <th>Ja-Stimmen:</th>
                    <td>{{ resolution.yes_votes }}</td>
                </tr>
                <tr>
                    <th>Nein-Stimmen:</th>
                    <td>{{ resolution.no_votes }}</td>
                </tr>
                <tr>
                    <th>Enthaltungen:</th>
                    <td>{{ resolution.abstentions }}</td>
                </tr>
            </tbody>
        </table>
    </div>
    {% endif %}
    
    <!-- Metadata -->
    <div class="mb-3">
        <small class="text-muted">
            Erstellt von {{ resolution.created_by.get_full_name }} am {{ resolution.created_at|date:"d.m.Y H:i" }} Uhr
            {% if resolution.decided_at %}
            <br>Beschlossen am {{ resolution.decided_at|date:"d.m.Y H:i" }} Uhr
            {% endif %}
        </small>
    </div>
</div>
```

### 7.3 Full Page Detail Template

**Datei:** `apps/resolutions/templates/resolutions/resolution_detail.html`

```html
{% extends 'base.html' %}
{% load static %}

{% block title %}{{ resolution.proposal|truncatewords:10 }} - Beschlüsse - BR-Manager{% endblock %}

{% block content %}
<div class="container mt-4">
    <div class="row">
        <div class="col-12">
            <!-- Header -->
            <div class="d-flex justify-content-between align-items-start mb-4">
                <div>
                    <h1>
                        <i class="bi bi-file-text"></i> Beschlussvorschlag
                    </h1>
                </div>
                <div class="btn-group" role="group">
                    <a href="{% url 'resolutions:resolution_list' %}" class="btn btn-outline-secondary">
                        <i class="bi bi-arrow-left"></i> Zurück
                    </a>
                </div>
            </div>
            
            <!-- Action Buttons -->
            {% if resolution.is_editable and user_can_edit %}
            <div class="mb-4">
                <div class="btn-toolbar gap-2" role="toolbar">
                    <a href="{% url 'resolutions:resolution_edit' resolution.pk %}" class="btn btn-primary">
                        <i class="bi bi-pencil"></i> Bearbeiten
                    </a>
                    
                    {% if resolution.can_be_proposed and user_can_propose %}
                    <a href="{% url 'resolutions:resolution_change_status' resolution.pk %}" class="btn btn-success">
                        <i class="bi bi-arrow-up-circle"></i> Vorschlagen
                    </a>
                    {% endif %}
                    
                    {% if resolution.can_be_withdrawn and user_can_propose %}
                    <a href="{% url 'resolutions:resolution_change_status' resolution.pk %}" class="btn btn-warning">
                        <i class="bi bi-arrow-down-circle"></i> Zurückziehen
                    </a>
                    {% endif %}
                    
                    {% if resolution.is_deletable and user_can_delete %}
                    <a href="{% url 'resolutions:resolution_delete' resolution.pk %}" class="btn btn-danger">
                        <i class="bi bi-trash"></i> Löschen
                    </a>
                    {% endif %}
                </div>
            </div>
            {% endif %}
            
            <!-- Resolution Detail Content -->
            <div class="card">
                <div class="card-body">
                    {% include 'resolutions/includes/resolution_detail_content.html' %}
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### 7.4 Modal Detail Template

**Datei:** `apps/resolutions/templates/resolutions/resolution_detail_modal.html`

```html
<!-- Modal for displaying resolution details in agenda context -->
<div class="modal fade" id="resolutionDetailModal" tabindex="-1" aria-labelledby="resolutionDetailModalLabel" aria-hidden="true">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="resolutionDetailModalLabel">
                    <i class="bi bi-file-text"></i> Beschlussvorschlag
                </h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body">
                {% include 'resolutions/includes/resolution_detail_content.html' %}
            </div>
            <div class="modal-footer">
                <a href="{% url 'resolutions:resolution_detail' resolution.pk %}" class="btn btn-primary" target="_blank">
                    <i class="bi bi-box-arrow-up-right"></i> In neuem Tab öffnen
                </a>
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Schließen</button>
            </div>
        </div>
    </div>
</div>
```

### 7.5 Agenda Item Template (Resolution)

**Datei:** `apps/agendas/templates/agendas/includes/agenda_item_resolution.html`

```html
{% load agenda_tags %}
<!-- Agenda Item Resolution -->
<li class="list-group-item agenda-item agenda-item-resolution" data-item-id="{{ item.pk }}">
    <div class="d-flex align-items-start">
        <!-- Drag Handle -->
        {% if can_reorder %}
        <div class="drag-handle me-2" style="cursor: move;">
            <i class="bi bi-grip-vertical text-muted"></i>
        </div>
        {% endif %}
        
        <!-- Item Number -->
        <div class="item-number me-3">
            <strong>{{ item.item_number }}</strong>
        </div>
        
        <!-- Item Type Badge -->
        <div class="me-2">
            <span class="badge bg-primary">
                <i class="bi bi-file-text"></i> Beschluss
            </span>
        </div>
        
        <!-- Item Content -->
        <div class="flex-grow-1">
            <div class="item-title">
                <strong>{{ item.title }}</strong>
            </div>
            {% if item.description %}
            <div class="item-description text-muted small mt-1">
                {{ item.description|linebreaks }}
            </div>
            {% endif %}
            
            <!-- Resolution Preview -->
            <div class="mt-2">
                <small class="text-muted">
                    Beschluss: {{ item.resolution.proposal|truncatewords:15 }}
                </small>
            </div>
        </div>
        
        <!-- Resolution Detail Button -->
        <div class="ms-2">
            <button type="button" 
                    class="btn btn-sm btn-outline-info" 
                    data-bs-toggle="modal" 
                    data-bs-target="#resolutionModal{{ item.resolution.pk }}"
                    title="Beschlussdetails anzeigen">
                <i class="bi bi-eye"></i>
            </button>
        </div>
        
        <!-- Actions -->
        <div class="ms-2">
            <div class="btn-group btn-group-sm" role="group">
                {% if can_edit %}
                <a href="{% url 'agendas:item_update' item.pk %}" 
                   class="btn btn-outline-primary" 
                   title="Bearbeiten">
                    <i class="bi bi-pencil"></i>
                </a>
                {% endif %}
                {% if can_delete %}
                <a href="{% url 'agendas:item_delete' item.pk %}" 
                   class="btn btn-outline-danger" 
                   title="Löschen">
                    <i class="bi bi-trash"></i>
                </a>
                {% endif %}
            </div>
        </div>
    </div>
    
    <!-- Resolution Detail Modal (embedded) -->
    <div class="modal fade" id="resolutionModal{{ item.resolution.pk }}" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">
                        <i class="bi bi-file-text"></i> Beschlussvorschlag
                    </h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    {% include 'resolutions/includes/resolution_detail_content.html' with resolution=item.resolution %}
                </div>
                <div class="modal-footer">
                    <a href="{% url 'resolutions:resolution_detail' item.resolution.pk %}" 
                       class="btn btn-primary" 
                       target="_blank">
                        <i class="bi bi-box-arrow-up-right"></i> In neuem Tab öffnen
                    </a>
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Schließen</button>
                </div>
            </div>
        </div>
    </div>
</li>
```

### 7.6 Meeting Detail Template Update

**Datei:** `apps/meetings/templates/meetings/meeting_detail.html` (Erweiterung)

Im Agenda-Bereich zwei Buttons hinzufügen:

```html
<!-- Add Agenda Items Buttons -->
{% if meeting.has_agenda and meeting.agenda.is_editable %}
<div class="d-flex gap-2 mb-3">
    <a href="{% url 'agendas:item_create' %}?agenda={{ meeting.agenda.pk }}" 
       class="btn btn-success">
        <i class="bi bi-plus-circle"></i> Neuer Punkt
    </a>
    
    {% if meeting.committee.can_create_resolutions %}
    <a href="{% url 'agendas:item_resolution_create' %}?agenda={{ meeting.agenda.pk }}" 
       class="btn btn-primary">
        <i class="bi bi-file-text"></i> Beschluss hinzufügen
    </a>
    {% endif %}
</div>
{% endif %}
```

In der Agenda-Item-Liste Polymorphie unterstützen:

```html
<!-- Agenda Items List -->
<ul class="list-group agenda-items-sortable">
    {% for item in agenda_items %}
        {% if item.item_type == 'AgendaItemRegular' %}
            {% include 'agendas/includes/agenda_item.html' with item=item %}
        {% elif item.item_type == 'AgendaItemResolution' %}
            {% include 'agendas/includes/agenda_item_resolution.html' with item=item %}
        {% endif %}
    {% empty %}
        <li class="list-group-item text-muted">
            Noch keine Tagesordnungspunkte vorhanden.
        </li>
    {% endfor %}
</ul>
```

---

## 8. Implementierungs-Phasen

### Phase 1: Basis-Infrastruktur ✅

**Ziel:** Datenmodell, Migrations, Permissions

**Tasks:**
1. ✅ Django-App erstellen: `python manage.py startapp resolutions apps/resolutions`
2. ✅ Resolution Model implementieren
3. ✅ Migration erstellen: `0001_initial.py`
4. ✅ Permission Migration erstellen: `9999_seed_resolution_permissions.py`
5. ✅ Apps in `INSTALLED_APPS` registrieren
6. ✅ Migrations ausführen: `python manage.py migrate`
7. ✅ Model im Admin registrieren

**Acceptance Criteria:**
- Resolution Model existiert mit allen Feldern
- Permissions sind in DB gespeichert
- Admin-Interface zeigt Beschlüsse an

### Phase 2: Committee-Erweiterung ✅

**Ziel:** Gremium-Konfiguration für Beschlüsse

**Tasks:**
1. ✅ `can_create_resolutions` Feld zu Committee hinzufügen
2. ✅ Migration erstellen: `0004_add_can_create_resolutions.py`
3. ✅ Validation in `Committee.clean()` hinzufügen
4. ✅ CommitteeForm aktualisieren
5. ✅ Template aktualisieren (checkbox)
6. ✅ Migration ausführen

**Acceptance Criteria:**
- Betriebsausschuss hat automatisch `can_create_resolutions=True`
- Feld kann für andere Gremien manuell gesetzt werden
- UI zeigt Checkbox an (disabled für BA)

### Phase 3: CRUD-Funktionalität ✅

**Ziel:** Beschlüsse erstellen, bearbeiten, löschen, anzeigen

**Tasks:**
1. ✅ Forms implementieren (`ResolutionForm`, `ResolutionStatusForm`)
2. ✅ Views implementieren (List, Detail, Create, Update, Delete, ChangeStatus)
3. ✅ Permission Mixin implementieren
4. ✅ URLs konfigurieren
5. ✅ Templates erstellen (alle 6 Templates)
6. ✅ Tests schreiben

**Acceptance Criteria:**
- Beschlüsse können erstellt werden
- Nur für Gremien mit `can_create_resolutions=True`
- Berechtigungen werden geprüft
- Status kann geändert werden (DRAFT ↔ PROPOSED)
- BA-Beschlüsse haben automatisch `propose_to_main_committee=True`

### Phase 4: Agenda-Integration ✅

**Ziel:** Beschlüsse als TOP-Typ

**Tasks:**
1. ✅ `AgendaItemResolution` Model implementieren
2. ✅ Migration erstellen: `0002_add_agenda_item_resolution.py`
3. ✅ `AgendaItemResolutionForm` implementieren
4. ✅ `AgendaItemResolutionCreateView` implementieren
5. ✅ Permission `agenda.add_item_resolution` hinzufügen
6. ✅ Templates erstellen (Form + Agenda Item)
7. ✅ Meeting Detail Template aktualisieren (2 Buttons)
8. ✅ Modal-Integration implementieren
9. ✅ Tests schreiben

**Acceptance Criteria:**
- Button "Beschluss hinzufügen" erscheint in Meeting Detail (wenn `can_create_resolutions=True`)
- Nur Beschlüsse im Status `PROPOSED` können ausgewählt werden
- Beschlüsse des eigenen Gremiums + Sub-Gremien (mit `propose_to_main_committee=True`) sind verfügbar
- Bereits hinzugefügte Beschlüsse werden nicht nochmal angezeigt
- Modal zeigt Beschlussdetails an
- Beschlüsse können nicht mehr bearbeitet/zurückgezogen werden, wenn in TOP

### Phase 5: Status-Workflow (Basis) ✅

**Ziel:** Status-Übergänge implementieren

**Tasks:**
1. ✅ `can_be_proposed` Property implementieren
2. ✅ `can_be_withdrawn` Property implementieren
3. ✅ `is_editable` Property implementieren (prüft Agenda-Verknüpfung)
4. ✅ `is_deletable` Property implementieren
5. ✅ Validation in Views hinzufügen
6. ✅ Tests schreiben

**Acceptance Criteria:**
- DRAFT → PROPOSED: Jederzeit möglich (mit `resolution.propose`)
- PROPOSED → DRAFT: Nur wenn nicht in Agenda
- Bearbeiten: Nur wenn nicht in finalisierter Agenda
- Löschen: Nur DRAFT + nicht in Agenda

**NICHT in dieser Phase:**
- ❌ PROPOSED → APPROVED/REJECTED (kommt später mit Sitzungsablauf)
- ❌ Abstimmungs-Logik
- ❌ Automatische Beschlussfähigkeits-Prüfung

---

## 9. BetrVG-Compliance

### 9.1 Implementierte Paragraphen

| Paragraph | Regelung | Implementierung |
|-----------|----------|-----------------|
| **§ 27 BetrVG** | Betriebsausschuss erstellt nur Beschlussvorschläge für BR | `committee_type='COMMITTEE'` → `propose_to_main_committee` immer `True` |
| **§ 28 BetrVG** | Ausschüsse machen Beschlussvorschläge, BR beschließt | Feld `propose_to_main_committee` ermöglicht Vorlage an Hauptgremium |
| **§ 33 BetrVG** | Beschlussfähigkeit (Quorum) | Feld `is_quorate` vorbereitet (Nutzung in Phase 5) |

### 9.2 Betriebsausschuss-Sonderregeln

**Automatismen:**
1. `can_create_resolutions` ist immer `True` (nicht änderbar)
2. `propose_to_main_committee` ist immer `True` (nicht änderbar)
3. `committee` zeigt auf BA, aber Beschluss ist für BR-Tagesordnung verfügbar

**Validierung:**
```python
# In Resolution.clean()
if self.committee.committee_type == 'COMMITTEE':
    if not self.propose_to_main_committee:
        raise ValidationError(...)
```

**Filter für Agenda:**
```python
# Beschlüsse für BR-Tagesordnung
- Direkte BR-Beschlüsse (committee = BR)
- BA-Beschlüsse (committee = BA, propose_to_main_committee = True)
```

---

## 10. Testing-Strategie

### 10.1 Model Tests

**Datei:** `apps/resolutions/tests/test_models.py`

```python
"""Tests for Resolution model."""

from datetime import date
from django.test import TestCase
from django.core.exceptions import ValidationError

from apps.resolutions.models import Resolution
from apps.committees.models import Committee
from apps.accounts.models import User


class ResolutionModelTest(TestCase):
    """Tests for Resolution model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='SecurePass123!'
        )
        
        self.main_committee = Committee.objects.create(
            name='Betriebsrat',
            committee_type='MAIN',
            total_seats=9,
            can_create_resolutions=True
        )
        
        self.betriebsausschuss = Committee.objects.create(
            name='Betriebsausschuss',
            committee_type='COMMITTEE',
            parent=self.main_committee,
            total_seats=3,
            can_create_resolutions=True
        )
    
    def test_resolution_creation(self):
        """Test creating a resolution."""
        resolution = Resolution.objects.create(
            committee=self.main_committee,
            proposal='Test proposal',
            justification='Test justification',
            created_by=self.user
        )
        
        self.assertEqual(resolution.status, 'DRAFT')
        self.assertEqual(resolution.proposal, 'Test proposal')
        self.assertFalse(resolution.propose_to_main_committee)
        self.assertEqual(resolution.resolution_number, '')
    
    def test_betriebsausschuss_must_propose_to_main(self):
        """Test BA must always propose to main committee."""
        resolution = Resolution(
            committee=self.betriebsausschuss,
            proposal='BA proposal',
            propose_to_main_committee=False,
            created_by=self.user
        )
        
        with self.assertRaises(ValidationError):
            resolution.full_clean()
    
    def test_resolution_number_generation(self):
        """Test auto-generation of resolution number."""
        resolution = Resolution.objects.create(
            committee=self.main_committee,
            proposal='Test proposal',
            status='DRAFT',
            created_by=self.user
        )
        
        # No number in DRAFT
        self.assertEqual(resolution.resolution_number, '')
        
        # Generate number when approved
        resolution.status = 'APPROVED'
        resolution.save()
        
        today = date.today().strftime('%Y%m%d')
        self.assertTrue(resolution.resolution_number.startswith(today))
        self.assertTrue(resolution.resolution_number.endswith('-001'))
    
    def test_is_editable_property(self):
        """Test is_editable property."""
        resolution = Resolution.objects.create(
            committee=self.main_committee,
            proposal='Test proposal',
            status='DRAFT',
            created_by=self.user
        )
        
        # DRAFT is editable
        self.assertTrue(resolution.is_editable)
        
        # APPROVED is not editable
        resolution.status = 'APPROVED'
        resolution.save()
        self.assertFalse(resolution.is_editable)
```

### 10.2 View Tests

**Datei:** `apps/resolutions/tests/test_views.py`

```python
"""Tests for Resolution views."""

from django.test import TestCase, Client
from django.urls import reverse

from apps.resolutions.models import Resolution
from apps.committees.models import Committee, Membership
from apps.roles.models import Role, Permission
from apps.accounts.models import User


class ResolutionViewTest(TestCase):
    """Tests for Resolution views."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create user
        self.user = User.objects.create_user(
            email='member@example.com',
            password='SecurePass123!'
        )
        
        # Create committee
        self.committee = Committee.objects.create(
            name='Betriebsrat',
            committee_type='MAIN',
            total_seats=9,
            can_create_resolutions=True
        )
        
        # Create role with permissions
        self.role = Role.objects.create(
            name='Member',
            codename='MEMBER',
            role_type='COMMITTEE'
        )
        
        # Add permissions
        perm_create = Permission.objects.create(
            codename='resolution.create',
            name='Create Resolution',
            category='resolution'
        )
        self.role.permissions.add(perm_create)
        
        # Add membership
        Membership.objects.create(
            user=self.user,
            committee=self.committee,
            role=self.role,
            member_type='REGULAR',
            start_date='2026-01-01'
        )
    
    def test_create_resolution_requires_login(self):
        """Test create view requires authentication."""
        response = self.client.get(reverse('resolutions:resolution_create'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_create_resolution_with_permission(self):
        """Test creating resolution with permission."""
        self.client.login(email='member@example.com', password='SecurePass123!')
        
        response = self.client.post(reverse('resolutions:resolution_create'), {
            'committee': self.committee.pk,
            'proposal': 'Test proposal',
            'justification': 'Test justification',
            'propose_to_main_committee': False
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertEqual(Resolution.objects.count(), 1)
        
        resolution = Resolution.objects.first()
        self.assertEqual(resolution.proposal, 'Test proposal')
        self.assertEqual(resolution.created_by, self.user)
```

### 10.3 Integration Tests

**Datei:** `apps/resolutions/tests/test_integration.py`

```python
"""Integration tests for resolutions and agendas."""

from django.test import TestCase

from apps.resolutions.models import Resolution
from apps.agendas.models import Agenda, AgendaItemResolution
from apps.meetings.models import Meeting
from apps.committees.models import Committee
from apps.accounts.models import User


class ResolutionAgendaIntegrationTest(TestCase):
    """Tests for resolution-agenda integration."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='SecurePass123!'
        )
        
        self.committee = Committee.objects.create(
            name='Betriebsrat',
            committee_type='MAIN',
            total_seats=9,
            can_create_resolutions=True
        )
        
        self.meeting = Meeting.objects.create(
            committee=self.committee,
            title='Test Meeting',
            date='2026-05-01',
            start_time='10:00',
            meeting_type='IN_PERSON',
            location_name='Office',
            location_street='Street 1',
            location_zip='12345',
            location_city='City',
            created_by=self.user
        )
        
        self.agenda = Agenda.objects.create(meeting=self.meeting)
    
    def test_add_resolution_to_agenda(self):
        """Test adding resolution to agenda."""
        # Create resolution
        resolution = Resolution.objects.create(
            committee=self.committee,
            proposal='Test proposal',
            status='PROPOSED',
            created_by=self.user
        )
        
        # Add to agenda
        agenda_item = AgendaItemResolution.objects.create(
            agenda=self.agenda,
            resolution=resolution,
            title='Beschluss über XYZ',
            sort_order=1.0
        )
        
        self.assertEqual(agenda_item.resolution, resolution)
        self.assertTrue(resolution.is_linked_to_agenda)
        self.assertFalse(resolution.can_be_withdrawn)
```

---

## Anhang A: Checkliste für AI-Agent

### Pre-Implementation
- [ ] Alle dependencies installiert (`uv add` falls nötig)
- [ ] Bestehende Migrations ausgeführt (`python manage.py migrate`)
- [ ] CODE_STYLE_GUIDE.md gelesen

### Phase 1: Basis-Infrastruktur
- [ ] App erstellt: `python manage.py startapp resolutions apps/resolutions`
- [ ] `apps/resolutions/models.py` mit Resolution Model
- [ ] `apps/resolutions/migrations/0001_initial.py`
- [ ] `apps/resolutions/migrations/9999_seed_resolution_permissions.py`
- [ ] `config/settings/base.py`: App registriert in `INSTALLED_APPS`
- [ ] `apps/resolutions/admin.py`: Model registriert
- [ ] Migrations ausgeführt: `python manage.py makemigrations resolutions`
- [ ] Migrations ausgeführt: `python manage.py migrate`
- [ ] Test: Admin-Interface aufrufen

### Phase 2: Committee-Erweiterung
- [ ] `apps/committees/models.py`: `can_create_resolutions` Feld hinzugefügt
- [ ] `apps/committees/models.py`: Validation in `clean()` und `save()`
- [ ] `apps/committees/migrations/0004_add_can_create_resolutions.py`
- [ ] `apps/committees/forms.py`: Feld hinzugefügt, disabled für BA
- [ ] Template: Checkbox hinzugefügt
- [ ] Migration ausgeführt
- [ ] Test: BA hat automatisch `can_create_resolutions=True`

### Phase 3: CRUD-Funktionalität
- [ ] `apps/resolutions/forms.py`: ResolutionForm, ResolutionStatusForm
- [ ] `apps/resolutions/mixins.py`: ResolutionPermissionMixin
- [ ] `apps/resolutions/views.py`: Alle 6 Views
- [ ] `apps/resolutions/urls.py`: URL-Konfiguration
- [ ] `config/urls.py`: Include resolutions.urls
- [ ] Templates: Alle 6 Templates erstellt
- [ ] Tests: `test_models.py`, `test_views.py`
- [ ] Test: Beschluss erstellen via UI

### Phase 4: Agenda-Integration
- [ ] `apps/agendas/models.py`: AgendaItemResolution Model
- [ ] `apps/agendas/migrations/0002_add_agenda_item_resolution.py`
- [ ] `apps/agendas/forms.py`: AgendaItemResolutionForm
- [ ] `apps/agendas/views.py`: AgendaItemResolutionCreateView
- [ ] `apps/agendas/urls.py`: URL hinzugefügt
- [ ] `apps/agendas/migrations/9999_seed_agenda_permissions.py`: Permission hinzugefügt
- [ ] Templates: item_resolution_form.html, agenda_item_resolution.html
- [ ] `apps/meetings/templates/meetings/meeting_detail.html`: 2 Buttons + Polymorphie
- [ ] Migration ausgeführt
- [ ] Tests: `test_integration.py`
- [ ] Test: Beschluss zu Agenda hinzufügen via UI

### Phase 5: Status-Workflow
- [ ] `apps/resolutions/models.py`: Properties implementiert
- [ ] Views: Validierung in dispatch() Methoden
- [ ] Tests: Status-Übergänge testen
- [ ] Test: Status-Workflow via UI

### Final Checks
- [ ] Alle Migrations ausgeführt: `python manage.py migrate`
- [ ] Keine Migration Warnings: `python manage.py makemigrations --check`
- [ ] Alle Tests laufen: `pytest apps/resolutions/`
- [ ] Code Style OK: `ruff check apps/resolutions/`
- [ ] Semantic Commit Messages verwendet
- [ ] ROLES_PERMISSIONS_MATRIX.md aktualisiert (Resolution-Sektion hinzugefügt)

---

**Ende des Implementierungsplans**

Dieser Plan ist bereit für die Umsetzung durch einen AI-Agenten. Alle Anforderungen sind geklärt, BetrVG-Aspekte berücksichtigt, und die Implementierung folgt strikt der CODE_STYLE_GUIDE.md.
