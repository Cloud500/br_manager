"""Management command to seed test data for development."""

import time
from datetime import datetime
from pathlib import Path

import pyotp
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.factories import (
    DEV_TOTP_SECRET,
    TwoFactorRecoveryCodeFactory,
    UserFactory,
    UserProfileFactory,
)
from apps.accounts.models import User


class Command(BaseCommand):
    """
    Seed test data for development environment.
    
    Creates test users with 2FA enabled using a shared TOTP secret.
    All users have the password 'testpass123'.
    
    Usage:
        python manage.py seed_testdata
        python manage.py seed_testdata --users 10
        python manage.py seed_testdata --clear --users 5
    """

    help = "Seed test data for development (users with 2FA enabled)"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear all existing user data before seeding",
        )
        parser.add_argument(
            "--users",
            type=int,
            default=7,
            help="Number of regular users to create (default: 7)",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        user_count = options["users"]

        self.stdout.write(self.style.WARNING("\n" + "=" * 60))
        self.stdout.write(self.style.WARNING("  SEEDING TEST DATA"))
        self.stdout.write(self.style.WARNING("=" * 60 + "\n"))

        # Clear existing data if requested
        if options["clear"]:
            self.stdout.write("Clearing existing user data...")
            User.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("[OK] Data cleared\n"))

        # Create test data
        with transaction.atomic():
            admin = self._create_admin()
            users = self._create_test_users(count=user_count)

        # Show summary
        self._show_summary(admin, users)

        # Show TOTP info
        self._show_totp_info()

        # Write users to file for easy reference
        self._write_users_file(admin, users)

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("  [OK] SEEDING COMPLETE"))
        self.stdout.write(self.style.SUCCESS("=" * 60 + "\n"))

    def _create_admin(self):
        """Create superuser admin."""
        admin = UserFactory.create(
            email="admin@example.org",
            first_name="Admin",
            last_name="User",
            gender="M",
            is_staff=True,
            is_superuser=True,
        )
        UserProfileFactory.create(user=admin, department="IT", employee_id="ADMIN-001")
        self._create_recovery_codes(admin)

        self.stdout.write(self.style.SUCCESS(f"[OK] Admin created: {admin.email}"))

        return admin

    def _create_test_users(self, count=7):
        """Create regular test users."""
        users = []
        for i in range(count):
            user = UserFactory.create()
            UserProfileFactory.create(user=user)
            self._create_recovery_codes(user)

            self.stdout.write(
                self.style.SUCCESS(f"[OK] User {i+1}/{count} created: {user.email}")
            )
            users.append(user)

        return users

    def _create_recovery_codes(self, user, count=10):
        """Create recovery codes for user."""
        for _ in range(count):
            TwoFactorRecoveryCodeFactory.create(user=user)

    def _show_summary(self, admin, users):
        """Show summary of created users."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.HTTP_INFO("  CREATED USERS"))
        self.stdout.write("=" * 60)

        self.stdout.write(f"\n  {self.style.SUCCESS('Admin User:')}")
        self.stdout.write(f"    * {admin.email} (Superuser)")

        self.stdout.write(f"\n  {self.style.SUCCESS(f'Regular Users ({len(users)}):')}")
        for user in users:
            self.stdout.write(f"    * {user.email}")

        self.stdout.write("")

    def _show_totp_info(self):
        """Show TOTP information for login."""
        totp = pyotp.TOTP(DEV_TOTP_SECRET)
        current_code = totp.now()
        remaining = 30 - (int(time.time()) % 30)

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.HTTP_INFO("  2FA LOGIN INFORMATION"))
        self.stdout.write("=" * 60)

        info_text = f"""
All test users have 2FA ENABLED with the SAME secret.
You can use this code for ALL users:

  {self.style.WARNING('PASSWORD:')}       testpass123
  
  {self.style.WARNING('TOTP SECRET:')}    {DEV_TOTP_SECRET}
  {self.style.WARNING('CURRENT CODE:')}   {self.style.SUCCESS(current_code)}  (valid for {remaining}s)

{self.style.HTTP_INFO('To add to Authenticator App:')}
  1. Open your Authenticator (Google/Authy/etc.)
  2. Select "Enter a setup key" (manual entry)
  3. Enter name: "BR-Manager DEV"
  4. Enter key:  {DEV_TOTP_SECRET}
  5. Save - you can now use this for ALL test users!

{self.style.HTTP_INFO('Recovery codes:')} Each user has 10 recovery codes (check DB if needed)
        """

        self.stdout.write(info_text)

    def _write_users_file(self, admin, users):
        """Write all created users to a text file in project root."""
        file_path = Path(settings.BASE_DIR) / "testdata_users.txt"
        
        totp = pyotp.TOTP(DEV_TOTP_SECRET)
        current_code = totp.now()
        remaining = 30 - (int(time.time()) % 30)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        content = f"""================================================================================
  BR-MANAGER TEST DATA - CREATED USERS
================================================================================
Generated: {timestamp}
Total Users: {len(users) + 1} (1 Admin + {len(users)} Regular Users)

================================================================================
  LOGIN CREDENTIALS (SAME FOR ALL USERS)
================================================================================
Password:     testpass123
2FA Method:   TOTP (Authenticator App)
TOTP Secret:  {DEV_TOTP_SECRET}
Current Code: {current_code} (valid for {remaining}s)

To add to Authenticator App:
  1. Open your Authenticator (Google Authenticator, Authy, etc.)
  2. Select "Enter a setup key" or "Manual entry"
  3. Enter name: "BR-Manager DEV"
  4. Enter key:  {DEV_TOTP_SECRET}
  5. Save - you can now use this for ALL test users!

================================================================================
  ADMIN USER
================================================================================
Email:      {admin.email}
Name:       {admin.get_full_name()}
Type:       Superuser (Staff)
Department: IT
Employee:   ADMIN-001

================================================================================
  REGULAR USERS ({len(users)})
================================================================================
"""
        
        for i, user in enumerate(users, 1):
            profile = user.profile
            content += f"""
{i}. {user.get_full_name()}
   Email:      {user.email}
   Gender:     {user.get_gender_display()}
   Department: {profile.department}
   Employee:   {profile.employee_id}
"""
        
        content += f"""
================================================================================
  NOTES
================================================================================
- All users have 2FA enabled with the SAME TOTP secret
- Use the same authenticator code for ALL users
- Each user has 10 recovery codes (stored hashed in database)
- To reset: python manage.py seed_testdata --clear

This file is auto-generated and will be overwritten on next seed.
================================================================================
"""
        
        # Write file
        file_path.write_text(content, encoding='utf-8')
        
        self.stdout.write(
            self.style.SUCCESS(f"\n[OK] User list written to: {file_path}")
        )
