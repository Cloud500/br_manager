"""Tests for User model."""

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.db import IntegrityError
from django.test import TestCase

from apps.accounts.models import TwoFactorRecoveryCode, UserProfile

User = get_user_model()


class UserModelTest(TestCase):
    """Tests for User model."""
    
    def setUp(self):
        """Set up test data."""
        self.user_data = {
            'email': 'test@example.com',
            'password': 'SecurePass123!',
            'first_name': 'Max',
            'last_name': 'Mustermann',
            'gender': 'M'
        }
    
    def test_user_creation_with_email(self):
        """Test user is created correctly with all required fields."""
        user = User.objects.create_user(**self.user_data)
        
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.first_name, 'Max')
        self.assertEqual(user.last_name, 'Mustermann')
        self.assertEqual(user.gender, 'M')
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
    
    def test_user_email_unique(self):
        """Test that creating two users with same email raises IntegrityError."""
        User.objects.create_user(**self.user_data)
        
        with self.assertRaises(IntegrityError):
            User.objects.create_user(**self.user_data)
    
    def test_user_get_full_name(self):
        """Test get_full_name method returns correct format."""
        user = User.objects.create_user(**self.user_data)
        
        self.assertEqual(user.get_full_name(), 'Max Mustermann')
    
    def test_user_get_short_name(self):
        """Test get_short_name method returns first name."""
        user = User.objects.create_user(**self.user_data)
        
        self.assertEqual(user.get_short_name(), 'Max')
    
    def test_user_str_representation(self):
        """Test __str__ method returns correct format."""
        user = User.objects.create_user(**self.user_data)
        expected = 'Max Mustermann (test@example.com)'
        
        self.assertEqual(str(user), expected)
    
    def test_create_user_without_email(self):
        """Test creating user without email raises ValueError."""
        user_data = self.user_data.copy()
        user_data['email'] = ''
        
        with self.assertRaises(ValueError) as context:
            User.objects.create_user(**user_data)
        
        self.assertIn('E-Mail-Adresse', str(context.exception))
    
    def test_create_superuser(self):
        """Test create_superuser sets is_staff and is_superuser to True."""
        superuser = User.objects.create_superuser(**self.user_data)
        
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.is_active)
    
    def test_password_is_hashed(self):
        """Test that password is hashed and check_password works."""
        plain_password = self.user_data['password']
        user = User.objects.create_user(**self.user_data)
        
        # Password should not be stored in plain text
        self.assertNotEqual(user.password, plain_password)
        
        # check_password should work
        self.assertTrue(user.check_password(plain_password))
        self.assertFalse(user.check_password('wrong_password'))
    
    def test_email_normalization(self):
        """Test that email is normalized (lowercase domain)."""
        user_data = self.user_data.copy()
        user_data['email'] = 'Test@EXAMPLE.COM'
        user = User.objects.create_user(**user_data)
        
        self.assertEqual(user.email, 'Test@example.com')


class UserProfileModelTest(TestCase):
    """Tests for UserProfile model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User',
            gender='M'
        )
    
    def test_user_profile_creation(self):
        """Test UserProfile can be created and linked to User."""
        profile = UserProfile.objects.create(
            user=self.user,
            department='IT',
            employee_id='EMP-12345'
        )
        
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.department, 'IT')
        self.assertEqual(profile.employee_id, 'EMP-12345')
        self.assertEqual(profile.notification_preferences, {})
    
    def test_user_profile_one_to_one_relationship(self):
        """Test OneToOne relationship between User and UserProfile."""
        profile = UserProfile.objects.create(
            user=self.user,
            department='HR'
        )
        
        # Access profile from user
        self.assertEqual(self.user.profile, profile)
        
        # Profile should be deleted when user is deleted
        user_id = self.user.id
        self.user.delete()
        
        self.assertFalse(UserProfile.objects.filter(user_id=user_id).exists())
    
    def test_user_profile_str_representation(self):
        """Test __str__ method returns correct format."""
        profile = UserProfile.objects.create(user=self.user)
        expected = 'Profil von Test User'
        
        self.assertEqual(str(profile), expected)
    
    def test_user_profile_notification_preferences(self):
        """Test notification_preferences JSON field."""
        profile = UserProfile.objects.create(
            user=self.user,
            notification_preferences={
                'email_notifications': True,
                'sms_notifications': False
            }
        )
        
        self.assertTrue(profile.notification_preferences['email_notifications'])
        self.assertFalse(profile.notification_preferences['sms_notifications'])


class TwoFactorRecoveryCodeModelTest(TestCase):
    """Tests for TwoFactorRecoveryCode model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User',
            gender='M'
        )
    
    def test_recovery_code_creation(self):
        """Test TwoFactorRecoveryCode can be created."""
        plain_code = 'RECOVERY-CODE-123'
        recovery_code = TwoFactorRecoveryCode.objects.create(
            user=self.user,
            code=make_password(plain_code)
        )
        
        self.assertEqual(recovery_code.user, self.user)
        self.assertFalse(recovery_code.is_used)
        self.assertIsNone(recovery_code.used_at)
        self.assertIsNotNone(recovery_code.created_at)
    
    def test_recovery_code_is_hashed(self):
        """Test that recovery code is hashed and not stored in plaintext."""
        plain_code = 'RECOVERY-CODE-ABC123'
        recovery_code = TwoFactorRecoveryCode.objects.create(
            user=self.user,
            code=make_password(plain_code)
        )
        
        # Code should not be stored in plaintext
        self.assertNotEqual(recovery_code.code, plain_code)
        
        # But should be verifiable
        self.assertTrue(check_password(plain_code, recovery_code.code))
        self.assertFalse(check_password('wrong-code', recovery_code.code))
    
    def test_recovery_code_mark_as_used(self):
        """Test mark_as_used method sets is_used and used_at."""
        recovery_code = TwoFactorRecoveryCode.objects.create(
            user=self.user,
            code=make_password('CODE-123')
        )
        
        self.assertFalse(recovery_code.is_used)
        self.assertIsNone(recovery_code.used_at)
        
        # Mark as used
        recovery_code.mark_as_used()
        
        self.assertTrue(recovery_code.is_used)
        self.assertIsNotNone(recovery_code.used_at)
    
    def test_recovery_code_str_representation(self):
        """Test __str__ method shows correct status."""
        # Unused code
        unused_code = TwoFactorRecoveryCode.objects.create(
            user=self.user,
            code=make_password('CODE-1')
        )
        self.assertIn('verfügbar', str(unused_code))
        
        # Used code
        used_code = TwoFactorRecoveryCode.objects.create(
            user=self.user,
            code=make_password('CODE-2')
        )
        used_code.mark_as_used()
        self.assertIn('verwendet', str(used_code))
    
    def test_multiple_recovery_codes_per_user(self):
        """Test user can have multiple recovery codes."""
        codes = []
        for i in range(5):
            code = TwoFactorRecoveryCode.objects.create(
                user=self.user,
                code=make_password(f'CODE-{i}')
            )
            codes.append(code)
        
        self.assertEqual(self.user.recovery_codes.count(), 5)
    
    def test_recovery_codes_deleted_with_user(self):
        """Test that recovery codes are deleted when user is deleted."""
        TwoFactorRecoveryCode.objects.create(
            user=self.user,
            code=make_password('CODE-1')
        )
        TwoFactorRecoveryCode.objects.create(
            user=self.user,
            code=make_password('CODE-2')
        )
        
        self.assertEqual(TwoFactorRecoveryCode.objects.filter(user=self.user).count(), 2)
        
        # Delete user
        self.user.delete()
        
        # Recovery codes should be deleted
        self.assertEqual(TwoFactorRecoveryCode.objects.count(), 0)
