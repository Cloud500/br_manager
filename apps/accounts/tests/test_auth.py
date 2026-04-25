"""Tests for Two-Factor Authentication."""

import pyotp
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import TwoFactorRecoveryCode
from apps.accounts.twofa_utils import (
    generate_recovery_codes,
    generate_totp_secret,
    verify_recovery_code,
    verify_totp_code,
)

User = get_user_model()


class TwoFactorUtilsTest(TestCase):
    """Tests for 2FA utility functions."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User',
            gender='M'
        )
    
    def test_generate_totp_secret(self):
        """Test TOTP secret generation."""
        secret = generate_totp_secret()
        
        # Should be Base32 string
        self.assertIsInstance(secret, str)
        self.assertEqual(len(secret), 32)
        
        # Should be valid Base32
        try:
            pyotp.TOTP(secret)
        except Exception as e:
            self.fail(f'Invalid TOTP secret: {e}')
    
    def test_verify_totp_code_valid(self):
        """Test TOTP verification with valid code."""
        secret = generate_totp_secret()
        self.user.totp_secret = secret
        self.user.save()
        
        # Generate valid code
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        
        # Should verify successfully
        self.assertTrue(verify_totp_code(self.user, valid_code))
    
    def test_verify_totp_code_invalid(self):
        """Test TOTP verification with invalid code."""
        secret = generate_totp_secret()
        self.user.totp_secret = secret
        self.user.save()
        
        # Should fail for invalid code
        self.assertFalse(verify_totp_code(self.user, '000000'))
        self.assertFalse(verify_totp_code(self.user, '999999'))
    
    def test_verify_totp_code_no_secret(self):
        """Test TOTP verification fails without secret."""
        # User without TOTP secret
        self.assertFalse(verify_totp_code(self.user, '123456'))
    
    def test_generate_recovery_codes(self):
        """Test recovery code generation."""
        codes = generate_recovery_codes(self.user, count=10)
        
        # Should return 10 codes
        self.assertEqual(len(codes), 10)
        
        # Codes should be in correct format (XXXX-XXXX-XXXX)
        for code in codes:
            self.assertRegex(code, r'^[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}$')
        
        # Should create 10 database entries
        self.assertEqual(
            TwoFactorRecoveryCode.objects.filter(user=self.user).count(),
            10
        )
    
    def test_recovery_codes_are_hashed(self):
        """Test that recovery codes are hashed in database."""
        codes = generate_recovery_codes(self.user, count=5)
        
        for plaintext_code in codes:
            # Find the recovery code in database
            found = False
            for db_code in TwoFactorRecoveryCode.objects.filter(user=self.user):
                if check_password(plaintext_code, db_code.code):
                    found = True
                    break
            
            self.assertTrue(found, f'Code {plaintext_code} not found in database')
    
    def test_verify_recovery_code_valid(self):
        """Test recovery code verification with valid code."""
        codes = generate_recovery_codes(self.user, count=5)
        
        # Use first code
        first_code = codes[0]
        self.assertTrue(verify_recovery_code(self.user, first_code))
        
        # Code should be marked as used
        recovery_code = TwoFactorRecoveryCode.objects.get(
            user=self.user,
            is_used=True
        )
        self.assertIsNotNone(recovery_code.used_at)
    
    def test_verify_recovery_code_cannot_reuse(self):
        """Test that recovery code cannot be used twice."""
        codes = generate_recovery_codes(self.user, count=5)
        
        first_code = codes[0]
        
        # First use should succeed
        self.assertTrue(verify_recovery_code(self.user, first_code))
        
        # Second use should fail
        self.assertFalse(verify_recovery_code(self.user, first_code))
    
    def test_verify_recovery_code_invalid(self):
        """Test recovery code verification with invalid code."""
        generate_recovery_codes(self.user, count=5)
        
        # Invalid code should fail
        self.assertFalse(verify_recovery_code(self.user, 'INVALID-CODE-HERE'))
    
    def test_regenerate_recovery_codes_deletes_old(self):
        """Test that regenerating codes deletes old codes."""
        # Generate first set
        generate_recovery_codes(self.user, count=5)
        self.assertEqual(TwoFactorRecoveryCode.objects.filter(user=self.user).count(), 5)
        
        # Generate second set
        generate_recovery_codes(self.user, count=10)
        self.assertEqual(TwoFactorRecoveryCode.objects.filter(user=self.user).count(), 10)


class TwoFactorViewsTest(TestCase):
    """Tests for 2FA views."""
    
    def setUp(self):
        """Set up test client and user."""
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User',
            gender='M'
        )
    
    def test_2fa_setup_view_requires_login(self):
        """Test that 2FA setup requires authentication."""
        response = self.client.get(reverse('accounts:2fa_setup'))
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('accounts:login')))
    
    def test_2fa_setup_view_authenticated(self):
        """Test 2FA setup view for logged in user."""
        self.client.login(username='test@example.com', password='TestPass123!')
        
        response = self.client.get(reverse('accounts:2fa_setup'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/2fa_setup.html')
        self.assertIn('totp_uri', response.context)
        self.assertIn('totp_secret', response.context)
    
    def test_2fa_setup_enables_2fa_with_valid_code(self):
        """Test that 2FA is enabled when correct code is provided."""
        self.client.login(username='test@example.com', password='TestPass123!')
        
        # Get setup page to generate secret
        self.client.get(reverse('accounts:2fa_setup'))
        
        # Reload user to get totp_secret
        self.user.refresh_from_db()
        
        # Generate valid code
        totp = pyotp.TOTP(self.user.totp_secret)
        valid_code = totp.now()
        
        # Submit code
        response = self.client.post(
            reverse('accounts:2fa_setup'),
            {'code': valid_code}
        )
        
        # Should redirect to recovery codes
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('accounts:2fa_recovery_codes'))
        
        # User should have 2FA enabled
        self.user.refresh_from_db()
        self.assertTrue(self.user.two_factor_enabled)
        self.assertEqual(self.user.two_factor_method, 'TOTP')
    
    def test_2fa_disable_view(self):
        """Test disabling 2FA."""
        self.client.login(username='test@example.com', password='TestPass123!')
        
        # Enable 2FA first
        self.user.two_factor_enabled = True
        self.user.two_factor_method = 'TOTP'
        self.user.totp_secret = generate_totp_secret()
        self.user.save()
        
        # Generate recovery codes
        generate_recovery_codes(self.user, count=10)
        
        # Disable 2FA
        response = self.client.post(reverse('accounts:2fa_disable'))
        
        # Should redirect to profile
        self.assertEqual(response.status_code, 302)
        
        # User should have 2FA disabled
        self.user.refresh_from_db()
        self.assertFalse(self.user.two_factor_enabled)
        self.assertEqual(self.user.two_factor_method, '')
        self.assertEqual(self.user.totp_secret, '')
        
        # Recovery codes should be deleted
        self.assertEqual(
            TwoFactorRecoveryCode.objects.filter(user=self.user).count(),
            0
        )
    
    def test_recovery_codes_view_shows_codes_once(self):
        """Test that recovery codes are shown only once."""
        self.client.login(username='test@example.com', password='TestPass123!')
        
        # Put codes in session
        codes = ['CODE1', 'CODE2', 'CODE3']
        session = self.client.session
        session['recovery_codes'] = codes
        session.save()
        
        # First request should show codes
        response = self.client.get(reverse('accounts:2fa_recovery_codes'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('recovery_codes', response.context)
        self.assertEqual(response.context['recovery_codes'], codes)
        
        # Second request should not show codes (removed from session)
        response = self.client.get(reverse('accounts:2fa_recovery_codes'))
        self.assertIsNone(response.context['recovery_codes'])
