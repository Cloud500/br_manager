"""Tests for permissions management commands."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.roles.models import Permission, Role, RolePermission


class SeedRolesCommandTest(TestCase):
    """Tests for seed_roles management command."""
    
    def test_seed_roles_command(self):
        """Test that all expected roles are created."""
        call_command('seed_roles', stdout=StringIO())
        
        # Check system roles
        self.assertTrue(Role.objects.filter(codename='SYSTEM_ADMIN').exists())
        self.assertTrue(Role.objects.filter(codename='USER').exists())
        
        # Check committee roles
        expected_committee_roles = [
            'CHAIR', 'VICE_CHAIR', 'MEMBER', 'CLERK',
            'SUBSTITUTE', 'EXTERNAL_MEMBER', 'GUEST'
        ]
        
        for codename in expected_committee_roles:
            self.assertTrue(
                Role.objects.filter(codename=codename).exists(),
                f'Role {codename} should exist'
            )
        
        # Check total count (2 system + 7 committee = 9)
        self.assertEqual(Role.objects.count(), 9)
    
    def test_seed_roles_idempotent(self):
        """Test that running command twice doesn't create duplicates."""
        # Run command first time
        call_command('seed_roles', stdout=StringIO())
        first_count = Role.objects.count()
        
        # Run command second time
        call_command('seed_roles', stdout=StringIO())
        second_count = Role.objects.count()
        
        # Should have same count
        self.assertEqual(first_count, second_count)
    
    def test_system_admin_has_all_permissions(self):
        """Test that SYSTEM_ADMIN role has all permissions."""
        call_command('seed_roles', stdout=StringIO())
        
        system_admin = Role.objects.get(codename='SYSTEM_ADMIN')
        permissions = Permission.objects.all()
        
        # Check that SYSTEM_ADMIN has all permissions
        for perm in permissions:
            self.assertTrue(
                RolePermission.objects.filter(
                    role=system_admin,
                    permission=perm
                ).exists(),
                f'SYSTEM_ADMIN should have permission {perm.codename}'
            )
        
        self.assertEqual(
            system_admin.permissions.count(),
            permissions.count()
        )
    
    def test_system_roles_marked_correctly(self):
        """Test that system roles have is_system_role=True."""
        call_command('seed_roles', stdout=StringIO())
        
        system_admin = Role.objects.get(codename='SYSTEM_ADMIN')
        user = Role.objects.get(codename='USER')
        
        self.assertTrue(system_admin.is_system_role)
        self.assertTrue(user.is_system_role)
        self.assertEqual(system_admin.role_type, 'SYSTEM')
        self.assertEqual(user.role_type, 'SYSTEM')
    
    def test_committee_roles_created(self):
        """Test that all committee roles exist with correct type."""
        call_command('seed_roles', stdout=StringIO())
        
        expected_roles = [
            'CHAIR', 'VICE_CHAIR', 'MEMBER', 'CLERK',
            'SUBSTITUTE', 'EXTERNAL_MEMBER', 'GUEST'
        ]
        
        for codename in expected_roles:
            role = Role.objects.get(codename=codename)
            self.assertEqual(role.role_type, 'COMMITTEE')
            self.assertTrue(role.is_system_role)

    def test_seed_roles_assigns_email_template_edit_permission(self):
        """Test default roles for editing e-mail templates."""
        call_command('seed_roles', stdout=StringIO())

        permission = Permission.objects.get(codename='email_template.edit')
        allowed_roles = ['SYSTEM_ADMIN', 'CHAIR', 'VICE_CHAIR']
        denied_roles = [
            'USER', 'CLERK', 'MEMBER', 'SUBSTITUTE',
            'EXTERNAL_MEMBER', 'GUEST'
        ]

        for codename in allowed_roles:
            role = Role.objects.get(codename=codename)
            self.assertTrue(
                RolePermission.objects.filter(
                    role=role,
                    permission=permission
                ).exists(),
                f'{codename} should have email_template.edit'
            )

        for codename in denied_roles:
            role = Role.objects.get(codename=codename)
            self.assertFalse(
                RolePermission.objects.filter(
                    role=role,
                    permission=permission
                ).exists(),
                f'{codename} should not have email_template.edit'
            )
