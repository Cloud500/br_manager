"""Tests for core management commands."""

from io import StringIO
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.db import OperationalError
from django.test import SimpleTestCase

import apps.core.management.commands.wait_for_database as wait_for_database_command


class WaitForDatabaseCommandTest(SimpleTestCase):
    """Tests for wait_for_database management command."""

    def test_available_database_returns_success(self):
        """Test command succeeds when ensure_connection succeeds."""
        stdout = StringIO()

        with patch.object(wait_for_database_command.connections["default"], "ensure_connection") as ensure_connection:
            call_command("wait_for_database", timeout=1, stdout=stdout)

        ensure_connection.assert_called_once()
        self.assertIn("Database connection available", stdout.getvalue())

    def test_unavailable_database_raises_after_timeout(self):
        """Test command raises CommandError when database remains unavailable."""
        with patch.object(
            wait_for_database_command.connections["default"],
            "ensure_connection",
            side_effect=OperationalError("not ready"),
        ):
            with patch.object(wait_for_database_command.time, "sleep"):
                with self.assertRaises(CommandError):
                    call_command("wait_for_database", timeout=0, stdout=StringIO())
