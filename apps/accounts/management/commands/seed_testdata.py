"""Management command to seed test data for development."""

import random
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
from apps.committees.factories import (
    ExternalMembershipFactory,
    MainCommitteeFactory,
    RegularMembershipFactory,
    SubcommitteeFactory,
    SubstituteMembershipFactory,
)
from apps.committees.models import Committee, Membership
from apps.roles.models import Role


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
            default=10,
            help="Number of regular users to create (default: 10)",
        )
        parser.add_argument(
            "--no-committees",
            action="store_true",
            help="Skip committee and membership creation",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        user_count = options["users"]

        self.stdout.write(self.style.WARNING("\n" + "=" * 60))
        self.stdout.write(self.style.WARNING("  SEEDING TEST DATA"))
        self.stdout.write(self.style.WARNING("=" * 60 + "\n"))

        # Clear existing data if requested
        if options["clear"]:
            self.stdout.write("Clearing existing data...")
            Committee.all_objects.all().hard_delete()  # Use all_objects to get all including soft-deleted
            Membership.all_objects.all().hard_delete()
            User.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("[OK] Data cleared\n"))

        # Create test data
        with transaction.atomic():
            admin = self._create_admin()
            users = self._create_test_users(count=user_count)
            
            # Create committees and memberships
            committees_data = None
            if not options.get("no_committees"):
                committees_data = self._create_committees_structure(admin, users)

        # Show summary
        self._show_summary(admin, users, committees_data)

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

    def _create_committees_structure(self, admin, users):
        """Create realistic committee structure with memberships."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.HTTP_INFO("  CREATING COMMITTEES"))
        self.stdout.write("=" * 60 + "\n")
        
        # Get default roles
        try:
            chair_role = Role.objects.get(codename='CHAIR')
            member_role = Role.objects.get(codename='MEMBER')
            substitute_role = Role.objects.get(codename='SUBSTITUTE')
            external_role = Role.objects.get(codename='EXTERNAL_MEMBER')
        except Role.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(
                    "[SKIP] Roles not found. Run 'python manage.py seed_roles' first."
                )
            )
            return None
        
        # 1. Create main committee (Betriebsrat)
        main_committee = MainCommitteeFactory.create(
            name='Betriebsrat',
            total_seats=9,
            substitute_logic_enabled=True,
            minority_gender='F',
            minority_min_count=3
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"[OK] Created main committee: {main_committee.name} ({main_committee.total_seats} seats)"
            )
        )
        
        # 2. Create subcommittees
        subcommittees = []
        subcommittee_names = [
            ('Wirtschaftsausschuss', 5),
            ('Personalausschuss', 5),
            ('Arbeitsschutzausschuss', 7),
            ('Gleichstellungsausschuss', 5),
        ]
        
        for name, seats in subcommittee_names:
            sub = SubcommitteeFactory.create(
                name=name,
                parent=main_committee,
                total_seats=seats,
                committee_type='SUBCOMMITTEE'
            )
            subcommittees.append(sub)
            self.stdout.write(
                self.style.SUCCESS(f"[OK] Created subcommittee: {sub.name} ({sub.total_seats} seats)")
            )
        
        # 3. Assign memberships to main committee
        available_users = list(users)
        random.shuffle(available_users)
        
        # Assign chair (first user)
        chair_user = available_users[0]
        RegularMembershipFactory.create(
            user=chair_user,
            committee=main_committee,
            role=chair_role,
            election_list_name='Liste 1',
            election_list_position=1,
            election_votes=450
        )
        self.stdout.write(
            self.style.SUCCESS(f"[OK] Assigned chair: {chair_user.get_full_name()}")
        )
        
        # Assign regular members (next 8 users for 9-seat committee)
        election_lists = ['Liste 1', 'Liste 2', 'Liste 3']
        for i, user in enumerate(available_users[1:9], start=2):
            list_name = random.choice(election_lists)
            RegularMembershipFactory.create(
                user=user,
                committee=main_committee,
                role=member_role,
                election_list_name=list_name,
                election_list_position=i,
                election_votes=random.randint(100, 400)
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"[OK] Assigned {main_committee.total_seats} regular members to main committee"
            )
        )
        
        # 4. Create substitute members (remaining users)
        substitute_count = 0
        for i, user in enumerate(available_users[9:], start=1):
            if i > 10:  # Max 10 substitutes
                break
            list_name = random.choice(election_lists)
            SubstituteMembershipFactory.create(
                user=user,
                committee=main_committee,
                role=substitute_role,
                election_list_name=list_name,
                election_list_position=i,
                election_votes=random.randint(50, 250)
            )
            substitute_count += 1
        
        if substitute_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"[OK] Assigned {substitute_count} substitute members to main committee"
                )
            )
        
        # 5. Assign members to subcommittees
        for subcommittee in subcommittees:
            # Use members from main committee + external experts
            main_members = list(main_committee.get_active_members()[:subcommittee.total_seats - 1])
            
            for membership in main_members:
                # Check if user already has membership in this subcommittee
                if not Membership.objects.filter(
                    user=membership.user,
                    committee=subcommittee
                ).exists():
                    RegularMembershipFactory.create(
                        user=membership.user,
                        committee=subcommittee,
                        role=member_role,
                        election_list_name=membership.election_list_name,
                        election_list_position=1,
                        election_votes=membership.election_votes
                    )
            
            # Add one external expert to Wirtschaftsausschuss
            if subcommittee.name == 'Wirtschaftsausschuss' and len(available_users) > 15:
                external_user = available_users[15]
                if not Membership.objects.filter(
                    user=external_user,
                    committee=main_committee
                ).exists():
                    ExternalMembershipFactory.create(
                        user=external_user,
                        committee=subcommittee,
                        role=external_role
                    )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"[OK] Added external member to {subcommittee.name}"
                        )
                    )
        
        # Count totals
        total_memberships = Membership.objects.count()
        
        return {
            'main_committee': main_committee,
            'subcommittees': subcommittees,
            'total_memberships': total_memberships,
            'regular_members': main_committee.get_active_members().count(),
            'substitute_members': main_committee.get_active_substitutes().count(),
        }
    
    def _show_summary(self, admin, users, committees_data=None):
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
        
        # Show committee summary
        if committees_data:
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write(self.style.HTTP_INFO("  CREATED COMMITTEES"))
            self.stdout.write("=" * 60)
            
            main = committees_data['main_committee']
            self.stdout.write(f"\n  {self.style.SUCCESS('Main Committee:')}")
            self.stdout.write(f"    * {main.name} ({main.total_seats} seats)")
            self.stdout.write(f"    * Regular members: {committees_data['regular_members']}")
            self.stdout.write(f"    * Substitute members: {committees_data['substitute_members']}")
            if main.minority_gender:
                self.stdout.write(
                    f"    * Minority quota: {main.get_minority_gender_display()} "
                    f"(min: {main.minority_min_count})"
                )
            
            self.stdout.write(f"\n  {self.style.SUCCESS('Subcommittees (' + str(len(committees_data['subcommittees'])) + '):')}")
            for sub in committees_data['subcommittees']:
                member_count = sub.get_active_members().count()
                self.stdout.write(f"    * {sub.name} ({member_count} members)")
            
            self.stdout.write(f"\n  {self.style.SUCCESS('Total:')}")
            self.stdout.write(f"    * Total committees: {len(committees_data['subcommittees']) + 1}")
            self.stdout.write(f"    * Total memberships: {committees_data['total_memberships']}")
            
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
