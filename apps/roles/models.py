"""Models for roles and permissions."""

import uuid

from django.db import models
from django.utils import timezone


class Permission(models.Model):
    """
    Granular permission for role-based access control.
    
    Permissions are categorized by app/module (e.g. 'meeting', 'committee')
    and have unique codenames (e.g. 'meeting.create').
    
    Attributes:
        id: UUID primary key
        codename: Unique permission identifier (e.g. 'meeting.create')
        name: Human-readable permission name
        description: Detailed description of what this permission allows
        category: Module/app this permission belongs to
    
    Example:
        >>> perm = Permission.objects.create(
        ...     codename='meeting.create',
        ...     name='Sitzung erstellen',
        ...     category='meeting'
        ... )
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    codename = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Code-Name',
        help_text='z.B. "meeting.create"'
    )
    name = models.CharField(
        max_length=200,
        verbose_name='Name'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Beschreibung'
    )
    category = models.CharField(
        max_length=50,
        verbose_name='Kategorie',
        help_text='Modul/App (z.B. "meeting", "committee")'
    )
    
    class Meta:
        verbose_name = 'Berechtigung'
        verbose_name_plural = 'Berechtigungen'
        ordering = ['category', 'codename']
    
    def __str__(self) -> str:
        """String representation."""
        return f"{self.category}: {self.name} ({self.codename})"


class Role(models.Model):
    """
    Role with assigned permissions for RBAC.
    
    Roles can be system roles (predefined, not deletable) or
    custom roles created by administrators.
    
    Attributes:
        id: UUID primary key
        name: Role display name
        codename: Unique role identifier (e.g. 'CHAIR', 'SYSTEM_ADMIN')
        description: Description of role purpose
        role_type: SYSTEM or COMMITTEE role
        is_system_role: Whether this is a predefined system role
        created_at: Creation timestamp
        updated_at: Last update timestamp
        permissions: Many-to-many relationship to Permission
    
    Example:
        >>> role = Role.objects.create(
        ...     name='Vorsitz',
        ...     codename='CHAIR',
        ...     role_type='COMMITTEE',
        ...     is_system_role=True
        ... )
    """
    
    ROLE_TYPE_CHOICES = [
        ('SYSTEM', 'System-Rolle'),
        ('COMMITTEE', 'Gremiums-Rolle'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(
        max_length=100,
        verbose_name='Name'
    )
    codename = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Code-Name',
        help_text='z.B. "CHAIR", "SYSTEM_ADMIN"'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Beschreibung'
    )
    role_type = models.CharField(
        max_length=20,
        choices=ROLE_TYPE_CHOICES,
        verbose_name='Rollen-Typ'
    )
    is_system_role = models.BooleanField(
        default=False,
        verbose_name='System-Rolle',
        help_text='Standard-Rollen können nicht gelöscht werden'
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Erstellt am'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Aktualisiert am'
    )
    permissions = models.ManyToManyField(
        Permission,
        through='RolePermission',
        related_name='roles',
        verbose_name='Berechtigungen'
    )
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_roles',
        verbose_name='Erstellt von',
        help_text='NULL = System-generierte Rolle'
    )
    
    class Meta:
        verbose_name = 'Rolle'
        verbose_name_plural = 'Rollen'
        ordering = ['role_type', 'name']
    
    def __str__(self) -> str:
        """String representation."""
        return f"{self.name} ({self.codename})"


class RolePermission(models.Model):
    """
    Many-to-many relationship between Role and Permission with metadata.
    
    Tracks when and by whom permissions were assigned to roles.
    
    Attributes:
        id: UUID primary key
        role: Foreign key to Role
        permission: Foreign key to Permission
        assigned_at: Timestamp when permission was assigned
    
    Example:
        >>> RolePermission.objects.create(
        ...     role=chair_role,
        ...     permission=create_meeting_perm
        ... )
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        verbose_name='Rolle'
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        verbose_name='Berechtigung'
    )
    assigned_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Zugewiesen am'
    )
    assigned_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_permissions',
        verbose_name='Zugewiesen von'
    )
    
    class Meta:
        verbose_name = 'Rollen-Berechtigung'
        verbose_name_plural = 'Rollen-Berechtigungen'
        unique_together = [['role', 'permission']]
        ordering = ['role', 'permission']
    
    def __str__(self) -> str:
        """String representation."""
        return f"{self.role.codename} → {self.permission.codename}"
