"""Wait until Django can connect to the configured database."""

import time

from django.core.management.base import BaseCommand, CommandError
from django.db import OperationalError, connections


class Command(BaseCommand):
    """Block until the default database is reachable or a timeout is exceeded."""

    help = "Wait until the default database connection is available."

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--timeout",
            type=int,
            default=60,
            help="Maximum number of seconds to wait for the database.",
        )
        parser.add_argument(
            "--interval",
            type=float,
            default=1.0,
            help="Number of seconds between connection attempts.",
        )

    def handle(self, *args, **options):
        """Wait for the database connection."""
        timeout = options["timeout"]
        interval = options["interval"]
        deadline = time.monotonic() + timeout
        last_error = None

        while time.monotonic() <= deadline:
            try:
                connections["default"].ensure_connection()
                self.stdout.write(self.style.SUCCESS("Database connection available."))
                return
            except OperationalError as error:
                last_error = error
                self.stdout.write("Waiting for database connection...")
                time.sleep(interval)

        raise CommandError(f"Database connection not available after {timeout} seconds: {last_error}")
