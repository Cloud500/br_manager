"""Tests for accounts views."""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class LoginViewTest(TestCase):
    """Tests for LoginView."""
    
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
        self.login_url = reverse('accounts:login')
    
    def test_login_view_get(self):
        """Test GET request shows login form."""
        response = self.client.get(self.login_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')
        self.assertContains(response, 'Login')
    
    def test_login_with_valid_credentials(self):
        """Test login with correct email and password."""
        response = self.client.post(self.login_url, {
            'username': 'test@example.com',  # Django uses 'username' field name
            'password': 'TestPass123!'
        })
        
        # Should redirect to dashboard
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:dashboard'))
        
        # User should be authenticated
        self.assertTrue(response.wsgi_request.user.is_authenticated)
    
    def test_login_with_invalid_credentials(self):
        """Test login with wrong password."""
        response = self.client.post(self.login_url, {
            'username': 'test@example.com',
            'password': 'WrongPassword!'
        })
        
        # Should stay on login page
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')
        
        # User should not be authenticated
        self.assertFalse(response.wsgi_request.user.is_authenticated)
    
    def test_login_redirect_authenticated_user(self):
        """Test that already logged in user is redirected."""
        # Log in first
        self.client.login(username='test@example.com', password='TestPass123!')
        
        # Try to access login page
        response = self.client.get(self.login_url)
        
        # Should redirect to dashboard
        self.assertEqual(response.status_code, 302)


class LogoutViewTest(TestCase):
    """Tests for LogoutView."""
    
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
        self.logout_url = reverse('accounts:logout')
    
    def test_logout(self):
        """Test logout functionality."""
        # Log in first
        self.client.login(username='test@example.com', password='TestPass123!')
        
        # Verify user is logged in
        response = self.client.get(reverse('core:dashboard'))
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        
        # Logout
        response = self.client.post(self.logout_url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:login'))
        
        # Verify user is logged out
        response = self.client.get(reverse('core:dashboard'))
        # Should redirect to login (because LoginRequiredMixin)
        self.assertEqual(response.status_code, 302)


class ProfileViewTest(TestCase):
    """Tests for ProfileView."""
    
    def setUp(self):
        """Set up test client and user."""
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User',
            gender='M',
            phone='0123456789'
        )
        self.profile_url = reverse('accounts:profile')
    
    def test_profile_view_requires_login(self):
        """Test that unauthenticated user is redirected to login."""
        response = self.client.get(self.profile_url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('accounts:login')))
    
    def test_profile_view_authenticated(self):
        """Test that authenticated user can access profile."""
        # Log in
        self.client.login(username='test@example.com', password='TestPass123!')
        
        # Access profile
        response = self.client.get(self.profile_url)
        
        # Should show profile
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/profile.html')
        
        # Should contain user data
        self.assertContains(response, 'Test User')
        self.assertContains(response, 'test@example.com')
        self.assertContains(response, 'Männlich')
        self.assertContains(response, '0123456789')
