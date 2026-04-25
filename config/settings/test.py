"""
Test-specific Django settings.

Uses in-memory SQLite for fast test execution, MD5 password
hashing, and a local-memory email backend.
"""

from .base import *  # noqa: F401,F403

DEBUG = False
SECRET_KEY = "django-insecure-test-key"

# Faster password hashing for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# In-memory SQLite for fast tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Email using in-memory backend
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Disable security settings for tests
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
