"""Tests for accounts management commands."""

from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.core.management import CommandError, call_command
from django.test import TestCase

import apps.accounts.management.commands.ensure_root_user as ensure_root_user_command


User = get_user_model()


class EnsureRootUserCommandTest(TestCase):
    """Tests for ensure_root_user management command."""

    def _settings(self, **overrides):
        """Build patched settings for the command."""
        defaults = {
            "root_user_email": "",
            "root_user_password": "",
            "root_user_first_name": "Admin",
            "root_user_last_name": "BR-Manager",
            "root_user_gender": "M",
        }
        defaults.update(overrides)
        return SimpleNamespace(**defaults)

    def test_no_root_credentials_is_noop(self):
        """Test command skips when no root credentials are configured."""
        with patch.object(ensure_root_user_command, "settings", self._settings()):
            stdout = StringIO()
            call_command("ensure_root_user", stdout=stdout)

        self.assertEqual(User.objects.count(), 0)
        self.assertIn("No ROOT_USER_* credentials configured", stdout.getvalue())

    def test_missing_email_raises_command_error(self):
        """Test missing email raises CommandError."""
        with patch.object(
            ensure_root_user_command,
            "settings",
            self._settings(root_user_password="CorrectHorseBatteryStaple42!"),
        ):
            with self.assertRaises(CommandError):
                call_command("ensure_root_user", stdout=StringIO())

    def test_missing_password_raises_command_error(self):
        """Test missing password raises CommandError."""
        with patch.object(
            ensure_root_user_command,
            "settings",
            self._settings(root_user_email="root@example.com"),
        ):
            with self.assertRaises(CommandError):
                call_command("ensure_root_user", stdout=StringIO())

    def test_configured_credentials_create_superuser(self):
        """Test configured credentials create a superuser with required fields."""
        with patch.object(
            ensure_root_user_command,
            "settings",
            self._settings(
                root_user_email="root@example.com",
                root_user_password="CorrectHorseBatteryStaple42!",
                root_user_first_name="Root",
                root_user_last_name="User",
                root_user_gender="F",
            ),
        ):
            stdout = StringIO()
            call_command("ensure_root_user", stdout=stdout)

        user = User.objects.get(email="root@example.com")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertEqual(user.first_name, "Root")
        self.assertEqual(user.last_name, "User")
        self.assertEqual(user.gender, "F")
        self.assertTrue(check_password("CorrectHorseBatteryStaple42!", user.password))
        self.assertIn("created", stdout.getvalue())

    def test_existing_superuser_keeps_password(self):
        """Test rerunning command for an existing superuser preserves password."""
        user = User.objects.create_superuser(
            email="root@example.com",
            password="old-secret",
            first_name="Root",
            last_name="User",
            gender="M",
        )
        original_password = user.password

        with patch.object(
            ensure_root_user_command,
            "settings",
            self._settings(
                root_user_email="root@example.com",
                root_user_password="CorrectHorseBatteryStaple42!",
            ),
        ):
            stdout = StringIO()
            call_command("ensure_root_user", stdout=stdout)

        user.refresh_from_db()
        self.assertEqual(user.password, original_password)
        self.assertTrue(user.check_password("old-secret"))
        self.assertFalse(user.check_password("CorrectHorseBatteryStaple42!"))
        self.assertIn("already exists", stdout.getvalue())

    def test_existing_superuser_does_not_validate_unused_password(self):
        """Test existing root no-op does not fail on an unused password value."""
        User.objects.create_superuser(
            email="root@example.com",
            password="old-secret",
            first_name="Root",
            last_name="User",
            gender="M",
        )

        with patch.object(
            ensure_root_user_command,
            "settings",
            self._settings(
                root_user_email="root@example.com",
                root_user_password="short",
            ),
        ):
            stdout = StringIO()
            call_command("ensure_root_user", stdout=stdout)

        self.assertIn("already exists", stdout.getvalue())

    def test_existing_regular_user_is_not_promoted_implicitly(self):
        """Test command refuses implicit privilege escalation for existing users."""
        user = User.objects.create_user(
            email="root@example.com",
            password="old-secret",
            first_name="Root",
            last_name="User",
            gender="M",
        )
        user.is_staff = False
        user.is_superuser = False
        user.is_active = False
        user.save(update_fields=["is_staff", "is_superuser", "is_active"])
        original_password = user.password

        with patch.object(
            ensure_root_user_command,
            "settings",
            self._settings(
                root_user_email="root@example.com",
                root_user_password="CorrectHorseBatteryStaple42!",
            ),
        ):
            with self.assertRaises(CommandError):
                call_command("ensure_root_user", stdout=StringIO())

        user.refresh_from_db()
        self.assertEqual(user.password, original_password)
        self.assertTrue(user.check_password("old-secret"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_active)

    def test_existing_user_can_be_promoted_explicitly(self):
        """Test explicit promotion fixes flags without changing password."""
        user = User.objects.create_user(
            email="root@example.com",
            password="old-secret",
            first_name="Root",
            last_name="User",
            gender="M",
        )
        user.is_active = False
        user.save(update_fields=["is_active"])
        original_password = user.password

        with patch.object(
            ensure_root_user_command,
            "settings",
            self._settings(
                root_user_email="root@example.com",
                root_user_password="CorrectHorseBatteryStaple42!",
            ),
        ):
            stdout = StringIO()
            call_command("ensure_root_user", promote_existing=True, stdout=stdout)

        user.refresh_from_db()
        self.assertEqual(user.password, original_password)
        self.assertTrue(user.check_password("old-secret"))
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertIn("promoted", stdout.getvalue())

