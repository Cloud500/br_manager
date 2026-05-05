"""Tests for roles models."""

from django.db import IntegrityError
from django.test import TestCase

from apps.roles.models import Permission, Role, RolePermission


class PermissionModelTest(TestCase):
    """Tests for Permission model."""
    
    def setUp(self):
        """Set up test data."""
        self.permission_data = {
            'codename': 'test.meeting_create',
            'name': 'Test-Sitzung erstellen',
            'category': 'test',
            'description': 'Erlaubt das Erstellen neuer Sitzungen'
        }
    
    def test_permission_creation(self):
        """Test permission is created correctly with all fields."""
        perm = Permission.objects.create(**self.permission_data)
        
        self.assertEqual(perm.codename, 'test.meeting_create')
        self.assertEqual(perm.name, 'Test-Sitzung erstellen')
        self.assertEqual(perm.category, 'test')
        self.assertEqual(perm.description, 'Erlaubt das Erstellen neuer Sitzungen')
    
    def test_permission_codename_unique(self):
        """Test that creating two permissions with same codename raises IntegrityError."""
        Permission.objects.create(**self.permission_data)
        
        with self.assertRaises(IntegrityError):
            Permission.objects.create(**self.permission_data)
    
    def test_permission_str_representation(self):
        """Test __str__ method returns correct format."""
        perm = Permission.objects.create(**self.permission_data)
        expected = 'test: Test-Sitzung erstellen (test.meeting_create)'
        
        self.assertEqual(str(perm), expected)


class RoleModelTest(TestCase):
    """Tests for Role model."""
    
    def setUp(self):
        """Set up test data."""
        self.role_data = {
            'name': 'Test-Vorsitz',
            'codename': 'TEST_CHAIR',
            'role_type': 'COMMITTEE',
            'description': 'Vorsitzender des Gremiums',
            'is_system_role': True
        }
    
    def test_role_creation(self):
        """Test role is created correctly with all fields."""
        role = Role.objects.create(**self.role_data)
        
        self.assertEqual(role.name, 'Test-Vorsitz')
        self.assertEqual(role.codename, 'TEST_CHAIR')
        self.assertEqual(role.role_type, 'COMMITTEE')
        self.assertTrue(role.is_system_role)
    
    def test_role_codename_unique(self):
        """Test that creating two roles with same codename raises IntegrityError."""
        Role.objects.create(**self.role_data)
        
        with self.assertRaises(IntegrityError):
            Role.objects.create(**self.role_data)
    
    def test_role_permissions_relationship(self):
        """Test role can be linked to permissions via RolePermission."""
        role = Role.objects.create(**self.role_data)
        
        perm1 = Permission.objects.create(
            codename='test.meeting_create_primary',
            name='Test-Sitzung erstellen',
            category='test'
        )
        perm2 = Permission.objects.create(
            codename='test.meeting_edit_primary',
            name='Test-Sitzung bearbeiten',
            category='test'
        )
        
        RolePermission.objects.create(role=role, permission=perm1)
        RolePermission.objects.create(role=role, permission=perm2)
        
        self.assertEqual(role.permissions.count(), 2)
        self.assertIn(perm1, role.permissions.all())
        self.assertIn(perm2, role.permissions.all())
    
    def test_role_str_representation(self):
        """Test __str__ method returns correct format."""
        role = Role.objects.create(**self.role_data)
        expected = 'Test-Vorsitz (TEST_CHAIR)'
        
        self.assertEqual(str(role), expected)
    
    def test_system_role_flag(self):
        """Test is_system_role flag works correctly."""
        system_role = Role.objects.create(**self.role_data)
        self.assertTrue(system_role.is_system_role)
        
        custom_role_data = self.role_data.copy()
        custom_role_data['codename'] = 'CUSTOM'
        custom_role_data['is_system_role'] = False
        custom_role = Role.objects.create(**custom_role_data)
        
        self.assertFalse(custom_role.is_system_role)


class RolePermissionModelTest(TestCase):
    """Tests for RolePermission model."""
    
    def setUp(self):
        """Set up test data."""
        self.role = Role.objects.create(
            name='Test-Vorsitz',
            codename='TEST_CHAIR',
            role_type='COMMITTEE'
        )
        self.permission = Permission.objects.create(
            codename='test.meeting_create',
            name='Test-Sitzung erstellen',
            category='test'
        )
    
    def test_role_permission_creation(self):
        """Test RolePermission is created correctly."""
        rp = RolePermission.objects.create(
            role=self.role,
            permission=self.permission
        )
        
        self.assertEqual(rp.role, self.role)
        self.assertEqual(rp.permission, self.permission)
        self.assertIsNotNone(rp.assigned_at)
    
    def test_role_permission_unique_together(self):
        """Test that same role+permission combination can only exist once."""
        RolePermission.objects.create(
            role=self.role,
            permission=self.permission
        )
        
        with self.assertRaises(IntegrityError):
            RolePermission.objects.create(
                role=self.role,
                permission=self.permission
            )
    
    def test_role_permission_str_representation(self):
        """Test __str__ method returns correct format."""
        rp = RolePermission.objects.create(
            role=self.role,
            permission=self.permission
        )
        expected = 'TEST_CHAIR → test.meeting_create'
        
        self.assertEqual(str(rp), expected)
    
    def test_cascade_delete_role(self):
        """Test that deleting role deletes RolePermission."""
        RolePermission.objects.create(
            role=self.role,
            permission=self.permission
        )
        
        self.assertTrue(
            RolePermission.objects.filter(
                role=self.role,
                permission=self.permission
            ).exists()
        )
        self.role.delete()
        self.assertFalse(
            RolePermission.objects.filter(permission=self.permission).exists()
        )
    
    def test_cascade_delete_permission(self):
        """Test that deleting permission deletes RolePermission."""
        RolePermission.objects.create(
            role=self.role,
            permission=self.permission
        )
        
        self.assertTrue(
            RolePermission.objects.filter(
                role=self.role,
                permission=self.permission
            ).exists()
        )
        self.permission.delete()
        self.assertFalse(
            RolePermission.objects.filter(role=self.role).exists()
        )
