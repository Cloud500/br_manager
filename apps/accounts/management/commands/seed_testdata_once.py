"""Run development test-data seeding once for an empty database."""

from django.conf import settings as django_settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User
from config.settings.env_config import settings as env_settings


class Command(BaseCommand):
    """Seed development test data only when no users exist yet."""

    help = "Run seed_testdata once for a freshly created development database."

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--config",
            default=env_settings.django_seed_testdata_config,
            help="Path to the seed_testdata JSON config file.",
        )
        parser.add_argument(
            "--no-committees",
            action="store_true",
            help="Pass --no-committees through to seed_testdata.",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        if not django_settings.DEBUG:
            raise CommandError("seed_testdata_once is only allowed with DEBUG=True.")

        if User.objects.exists():
            self.stdout.write("Users already exist; skipping development test-data seed.")
            return

        command_args = ["seed_testdata"]
        if options["config"]:
            command_args.extend(["--config", options["config"]])
        if options["no_committees"]:
            command_args.append("--no-committees")

        self.stdout.write("No users found; seeding development test data.")
        call_command(*command_args, stdout=self.stdout, stderr=self.stderr)
