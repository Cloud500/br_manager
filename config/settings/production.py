"""
Production-specific Django settings.

Enforces strict security headers, HTTPS, HSTS and uses
WhiteNoise for compressed static file serving.
"""

from .base import *  # noqa: F401,F403
from .env_config import settings
from .logging_config import setup_logging

DEBUG = False

SECRET_KEY = settings.django_secret_key

ALLOWED_HOSTS = settings.django_allowed_hosts

# ---------------------------------------------------------------------------
# Security-Header
# ---------------------------------------------------------------------------
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ---------------------------------------------------------------------------
# Static Files – WhiteNoise
# ---------------------------------------------------------------------------
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# ---------------------------------------------------------------------------
# Logging – using loguru
# ---------------------------------------------------------------------------
# Initialize loguru logging
setup_logging()

# Django logging configuration to intercept Django's logging and redirect to loguru
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": settings.log_level,
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": settings.log_level,
            "propagate": False,
        },
    },
}
