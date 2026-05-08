"""
Environment configuration using pydantic-settings.

Manages all environment variables with type validation and default values.
"""

from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Django Core Settings
    django_secret_key: str = Field(
        default="CHANGE-ME-IN-PRODUCTION",
        description="Django secret key for cryptographic signing",
    )
    django_debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )
    django_allowed_hosts: str = Field(
        default="localhost,127.0.0.1",
        description="Comma-separated list of allowed hosts",
    )
    django_csrf_trusted_origins: str = Field(
        default="",
        description="Comma-separated list of trusted CSRF origins",
    )

    # Database Settings
    db_name: str = Field(
        default="br_manager",
        description="Database name",
    )
    db_user: str = Field(
        default="br_manager",
        description="Database user",
    )
    db_password: str = Field(
        default="br_manager",
        description="Database password",
    )
    db_host: str = Field(
        default="localhost",
        description="Database host",
    )
    db_port: int = Field(
        default=5432,
        description="Database port",
    )

    # Email Settings
    django_email_backend: str = Field(
        default="django.core.mail.backends.console.EmailBackend",
        description="Django email backend",
    )
    email_host: str = Field(
        default="localhost",
        description="Email server host",
    )
    email_port: int = Field(
        default=587,
        description="Email server port",
    )
    email_use_tls: bool = Field(
        default=True,
        description="Use TLS for email",
    )
    email_host_user: str = Field(
        default="",
        description="Email server username",
    )
    email_host_password: str = Field(
        default="",
        description="Email server password",
    )
    default_from_email: str = Field(
        default="noreply@br-manager.local",
        description="Default sender email address",
    )

    # Logging Settings
    django_log_file: str = Field(
        default="/var/log/br_manager/django.log",
        description="Path to Django log file",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    # Development Test Data Settings
    django_seed_testdata_config: str = Field(
        default="testdata_config_small.json",
        description="Default config file for development test-data seeding",
    )

    # Initial Root User Settings
    root_user_email: str = Field(
        default="",
        description="Email address for the optional initial root user",
    )
    root_user_password: str = Field(
        default="",
        description="Password for the optional initial root user",
    )
    root_user_first_name: str = Field(
        default="Admin",
        description="First name for the optional initial root user",
    )
    root_user_last_name: str = Field(
        default="BR-Manager",
        description="Last name for the optional initial root user",
    )
    root_user_gender: str = Field(
        default="M",
        description="Gender code for the optional initial root user",
    )

    @field_validator("django_allowed_hosts")
    @classmethod
    def split_allowed_hosts(cls, v: str) -> List[str]:
        """Split comma-separated allowed hosts into a list."""
        return [host.strip() for host in v.split(",") if host.strip()]

    @field_validator("django_csrf_trusted_origins")
    @classmethod
    def split_csrf_trusted_origins(cls, v: str) -> List[str]:
        """Split comma-separated CSRF trusted origins into a list."""
        return [origin.strip() for origin in v.split(",") if origin.strip()]

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v_upper

    @field_validator("root_user_gender")
    @classmethod
    def validate_root_user_gender(cls, v: str) -> str:
        """Validate initial root user gender code."""
        gender = v.upper()
        if gender not in {"M", "F"}:
            raise ValueError("Root user gender must be either 'M' or 'F'")
        return gender


# Create a singleton instance
settings = Settings()
