"""Ensure an optional initial root user exists."""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User
from config.settings.env_config import settings


class Command(BaseCommand):
    """Create an initial superuser from environment settings if needed."""

    help = "Create an initial root user from ROOT_USER_* environment variables if it does not exist."

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--promote-existing",
            action="store_true",
            help="Promote an existing user with ROOT_USER_EMAIL to superuser.",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        email = User.objects.normalize_email(settings.root_user_email.strip())
        password = settings.root_user_password

        if not email and not password:
            self.stdout.write("No ROOT_USER_* credentials configured; skipping root user setup.")
            return

        if not email or not password:
            raise CommandError("ROOT_USER_EMAIL and ROOT_USER_PASSWORD must both be set.")

        with transaction.atomic():
            existing_user = User.objects.filter(email=email).first()

            if existing_user is None:
                try:
                    validate_password(password)
                except ValidationError as error:
                    raise CommandError("ROOT_USER_PASSWORD does not meet password policy requirements.") from error

                User.objects.create_superuser(
                    email=email,
                    password=password,
                    first_name=settings.root_user_first_name,
                    last_name=settings.root_user_last_name,
                    gender=settings.root_user_gender,
                )
                self.stdout.write(self.style.SUCCESS(f"Root user '{email}' created."))
                return

            if existing_user.is_superuser:
                self.stdout.write(f"Root user '{email}' already exists; leaving password unchanged.")
                return

            if not options["promote_existing"]:
                raise CommandError(
                    f"User '{email}' already exists but is not a superuser. "
                    "Refusing to promote implicitly. Use --promote-existing explicitly if intended."
                )

            existing_user.is_staff = True
            existing_user.is_superuser = True
            existing_user.is_active = True
            existing_user.save(update_fields=["is_staff", "is_superuser", "is_active"])
            self.stdout.write(self.style.SUCCESS(f"Existing user '{email}' promoted to root user."))
