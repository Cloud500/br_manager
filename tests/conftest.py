"""Pytest configuration and fixtures for testing."""

import pytest

from apps.accounts.factories import DEV_TOTP_SECRET, UserFactory


@pytest.fixture
def user(db):
    """
    Create a single test user with 2FA enabled.
    
    Usage:
        def test_something(user):
            assert user.email.endswith('@example.org')
            assert user.two_factor_enabled is True
    """
    return UserFactory.create()


@pytest.fixture
def admin_user(db):
    """
    Create an admin user with staff and superuser privileges.
    
    Usage:
        def test_admin_access(admin_user):
            assert admin_user.is_staff is True
            assert admin_user.is_superuser is True
    """
    return UserFactory.create(
        email="admin@test.com",
        first_name="Admin",
        last_name="Test",
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def users(db):
    """
    Create a list of 5 test users.
    
    Usage:
        def test_multiple_users(users):
            assert len(users) == 5
            for user in users:
                assert user.two_factor_enabled is True
    """
    return [UserFactory.create() for _ in range(5)]


@pytest.fixture
def totp_secret():
    """
    Returns the DEV TOTP secret for testing.
    
    Usage:
        def test_totp_login(user, totp_secret):
            import pyotp
            totp = pyotp.TOTP(totp_secret)
            current_code = totp.now()
            # Use current_code for 2FA verification
    """
    return DEV_TOTP_SECRET


@pytest.fixture
def totp_code(totp_secret):
    """
    Returns the current TOTP code for testing.
    
    Usage:
        def test_login(client, user, totp_code):
            response = client.post('/login/', {
                'email': user.email,
                'password': 'testpass123',
                'totp_code': totp_code
            })
    """
    import pyotp

    totp = pyotp.TOTP(totp_secret)
    return totp.now()
