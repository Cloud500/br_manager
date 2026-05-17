"""
Development-specific Django settings.

Enables debug mode, relaxes security settings, and adds
developer tools like django-debug-toolbar.
"""

from .base import *  # noqa: F401,F403

DEBUG = True
SECRET_KEY = "django-insecure-dev-key-change-in-production"

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# Disable security settings for development
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Debug Toolbar
INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405
INTERNAL_IPS = ["127.0.0.1"]

# Output email to console
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Database – SQLite for fast local development (optional)
# Can be kept for PostgreSQL or switched to SQLite:
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
    }
}
