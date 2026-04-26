"""Management command to seed test data for development."""

import json
import random
import time
from datetime import datetime
from pathlib import Path

import pyotp
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
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
        python manage.py seed_testdata --config testdata_config.json
        python manage.py seed_testdata --clear --config testdata_config.json
        python manage.py seed_testdata --users 10  (legacy mode without config)
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
            "--config",
            type=str,
            default=None,
            help="Path to JSON config file (relative to project root)",
        )
        parser.add_argument(
            "--users",
            type=int,
            default=None,
            help="Number of regular users to create (legacy mode, ignored if --config is provided)",
        )
        parser.add_argument(
            "--no-committees",
            action="store_true",
            help="Skip committee and membership creation",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        self.stdout.write(self.style.WARNING("\n" + "=" * 60))
        self.stdout.write(self.style.WARNING("  SEEDING TEST DATA"))
        self.stdout.write(self.style.WARNING("=" * 60 + "\n"))

        # Load configuration
        config = None
        if options.get("config"):
            config = self._load_config(options["config"])
        
        # Determine user count
        if config:
            user_count = (
                config["users"]["male_count"] 
                + config["users"]["female_count"] 
                + config["users"]["guest_count"]
            )
        else:
            user_count = options["users"] if options["users"] is not None else 10

        # Clear existing data if requested
        if options["clear"]:
            self.stdout.write("Clearing existing TEST data (Users, Committees, Memberships)...")
            Committee.all_objects.all().hard_delete()
            Membership.all_objects.all().hard_delete()
            User.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("[OK] Test data cleared"))
            self.stdout.write(self.style.WARNING("[INFO] System data (Roles, Permissions) is NOT touched - managed by migrations only\n"))

        # Create test data
        with transaction.atomic():
            admin = self._create_admin()
            
            if config:
                users = self._create_configured_users(config)
            else:
                users = self._create_test_users(count=user_count)
            
            # Create committees and memberships
            committees_data = None
            if not options.get("no_committees"):
                if config:
                    committees_data = self._create_configured_committees(admin, users, config)
                else:
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

        # Show summary
        self._show_summary(admin, users, committees_data)

        # Show TOTP info
        self._show_totp_info()

        # Write users to file for easy reference
        self._write_users_file(admin, users)

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("  [OK] SEEDING COMPLETE"))
        self.stdout.write(self.style.SUCCESS("=" * 60 + "\n"))

    def _load_config(self, config_path):
        """Load and validate configuration from JSON file."""
        full_path = Path(settings.BASE_DIR) / config_path
        
        if not full_path.exists():
            raise CommandError(f"Config file not found: {full_path}")
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON in config file: {e}")
        
        # Validate configuration
        self._validate_config(config)
        
        self.stdout.write(self.style.SUCCESS(f"[OK] Loaded config from: {config_path}\n"))
        return config
    
    def _validate_config(self, config):
        """Validate configuration structure and constraints."""
        # Validate users section
        if "users" not in config:
            raise CommandError("Config missing 'users' section")
        
        users_cfg = config["users"]
        required_user_fields = ["male_count", "female_count", "guest_count"]
        for field in required_user_fields:
            if field not in users_cfg:
                raise CommandError(f"Config users section missing '{field}'")
            if not isinstance(users_cfg[field], int) or users_cfg[field] < 0:
                raise CommandError(f"Config users.{field} must be a non-negative integer")
        
        # Validate main_committee section
        if "main_committee" not in config:
            raise CommandError("Config missing 'main_committee' section")
        
        committee_cfg = config["main_committee"]
        required_committee_fields = ["name", "total_seats", "minority_gender", "minority_min_count", "election_lists"]
        for field in required_committee_fields:
            if field not in committee_cfg:
                raise CommandError(f"Config main_committee section missing '{field}'")
        
        # Validate minority_gender
        if committee_cfg["minority_gender"] not in ["M", "F", None]:
            raise CommandError("Config main_committee.minority_gender must be 'M', 'F', or null")
        
        # Validate total_seats
        if not isinstance(committee_cfg["total_seats"], int) or committee_cfg["total_seats"] < 1:
            raise CommandError("Config main_committee.total_seats must be a positive integer")
        
        # Validate election lists
        if not isinstance(committee_cfg["election_lists"], list):
            raise CommandError("Config main_committee.election_lists must be a list")
        
        total_list_users = 0
        total_seats_assigned = 0
        for i, election_list in enumerate(committee_cfg["election_lists"]):
            if "name" not in election_list:
                raise CommandError(f"Election list {i} missing 'name'")
            if "user_count" not in election_list:
                raise CommandError(f"Election list {i} missing 'user_count'")
            if "seats_in_committee" not in election_list:
                raise CommandError(f"Election list {i} missing 'seats_in_committee'")
            
            total_list_users += election_list["user_count"]
            total_seats_assigned += election_list["seats_in_committee"]
        
        # Check if seats match
        if total_seats_assigned != committee_cfg["total_seats"]:
            raise CommandError(
                f"Sum of seats_in_committee ({total_seats_assigned}) must equal "
                f"total_seats ({committee_cfg['total_seats']})"
            )
        
        # Check if we have enough users
        total_available_users = users_cfg["male_count"] + users_cfg["female_count"]
        if total_list_users > total_available_users:
            raise CommandError(
                f"Sum of election list user_count ({total_list_users}) exceeds "
                f"available non-guest users ({total_available_users})"
            )
        
        # Validate subcommittees section (optional)
        if "subcommittees" in config:
            if not isinstance(config["subcommittees"], list):
                raise CommandError("Config subcommittees must be a list")
            
            total_external_count = 0
            for i, subcommittee in enumerate(config["subcommittees"]):
                required_sub_fields = ["name", "member_count", "external_count"]
                for field in required_sub_fields:
                    if field not in subcommittee:
                        raise CommandError(f"Subcommittee {i} missing '{field}'")
                
                # Check if subcommittee doesn't exceed main committee size
                if subcommittee["member_count"] > committee_cfg["total_seats"]:
                    raise CommandError(
                        f"Subcommittee '{subcommittee['name']}' member_count ({subcommittee['member_count']}) "
                        f"exceeds main committee total_seats ({committee_cfg['total_seats']})"
                    )
                
                total_external_count += subcommittee["external_count"]
            
            # Check if we have enough guests for all subcommittees combined
            if total_external_count > users_cfg["guest_count"]:
                raise CommandError(
                    f"Sum of all subcommittee external_count ({total_external_count}) "
                    f"exceeds available guest_count ({users_cfg['guest_count']})"
                )
        
        self.stdout.write(self.style.SUCCESS("[OK] Configuration validated\n"))

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
    
    def _create_configured_users(self, config):
        """Create users based on configuration."""
        users_cfg = config["users"]
        categorized_users = {
            'male': [],
            'female': [],
            'guest': []
        }
        
        # Create male users
        for i in range(users_cfg["male_count"]):
            user = UserFactory.create(gender='M')
            UserProfileFactory.create(user=user)
            self._create_recovery_codes(user)
            categorized_users['male'].append(user)
            self.stdout.write(
                self.style.SUCCESS(f"[OK] Male user {i+1}/{users_cfg['male_count']} created: {user.email}")
            )
        
        # Create female users
        for i in range(users_cfg["female_count"]):
            user = UserFactory.create(gender='F')
            UserProfileFactory.create(user=user)
            self._create_recovery_codes(user)
            categorized_users['female'].append(user)
            self.stdout.write(
                self.style.SUCCESS(f"[OK] Female user {i+1}/{users_cfg['female_count']} created: {user.email}")
            )
        
        # Create guest users (gender random)
        for i in range(users_cfg["guest_count"]):
            user = UserFactory.create()
            UserProfileFactory.create(user=user)
            self._create_recovery_codes(user)
            categorized_users['guest'].append(user)
            self.stdout.write(
                self.style.SUCCESS(f"[OK] Guest user {i+1}/{users_cfg['guest_count']} created: {user.email}")
            )
        
        # Create custom list class that can store categorized data
        class UserList(list):
            pass
        
        # Flatten for compatibility with existing code
        all_users = UserList(categorized_users['male'] + categorized_users['female'] + categorized_users['guest'])
        
        # Store categorized users for later use
        all_users._categorized = categorized_users
        
        return all_users

    def _create_recovery_codes(self, user, count=10):
        """Create recovery codes for user."""
        for _ in range(count):
            TwoFactorRecoveryCodeFactory.create(user=user)
    
    def _create_configured_committees(self, admin, users, config):
        """Create committees based on configuration."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.HTTP_INFO("  CREATING CONFIGURED COMMITTEES"))
        self.stdout.write("=" * 60 + "\n")
        
        # Get required roles
        try:
            chair_role = Role.objects.get(codename='CHAIR')
            vice_chair_role = Role.objects.get(codename='VICE_CHAIR')
            clerk_role = Role.objects.get(codename='CLERK')
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
        
        committee_cfg = config["main_committee"]
        
        # 1. Create main committee
        main_committee = MainCommitteeFactory.create(
            name=committee_cfg["name"],
            total_seats=committee_cfg["total_seats"],
            substitute_logic_enabled=True,
            minority_gender=committee_cfg["minority_gender"],
            minority_min_count=committee_cfg["minority_min_count"]
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"[OK] Created main committee: {main_committee.name} ({main_committee.total_seats} seats)"
            )
        )
        
        # 2. Prepare user pools
        categorized = getattr(users, '_categorized', None)
        if categorized:
            male_users = list(categorized['male'])
            female_users = list(categorized['female'])
            guest_users = list(categorized['guest'])
        else:
            # Fallback if not using configured users
            male_users = [u for u in users if u.gender == 'M']
            female_users = [u for u in users if u.gender == 'F']
            guest_users = []
        
        random.shuffle(male_users)
        random.shuffle(female_users)
        random.shuffle(guest_users)
        
        # Pool of non-guest users for committee assignment
        available_users = male_users + female_users
        random.shuffle(available_users)
        
        # 3. Assign users to election lists and create memberships
        assigned_users = []
        list_assignments = {}  # Track which users are on which list
        seat_counter = 0  # Track how many seats have been filled
        
        for list_cfg in committee_cfg["election_lists"]:
            list_name = list_cfg["name"]
            user_count = list_cfg["user_count"]
            seats_in_committee = list_cfg["seats_in_committee"]
            
            # Take users for this list
            list_users = []
            while len(list_users) < user_count and available_users:
                list_users.append(available_users.pop(0))
            
            list_assignments[list_name] = list_users
            
            # Assign votes (descending order)
            base_votes = 500
            for i, user in enumerate(list_users):
                votes = base_votes - (i * 20)
                
                # First N users from this list become regular members
                if i < seats_in_committee:
                    # Assign special roles for first three members overall
                    if seat_counter == 0:
                        role = chair_role
                        role_name = "chair"
                    elif seat_counter == 1:
                        role = vice_chair_role
                        role_name = "vice chair"
                    elif seat_counter == 2:
                        role = clerk_role
                        role_name = "clerk"
                    else:
                        role = member_role
                        role_name = None
                    
                    RegularMembershipFactory.create(
                        user=user,
                        committee=main_committee,
                        role=role,
                        election_list_name=list_name,
                        election_list_position=i + 1,
                        election_votes=votes
                    )
                    assigned_users.append(user)
                    seat_counter += 1
                    
                    if role_name:
                        self.stdout.write(
                            self.style.SUCCESS(f"[OK] Assigned {role_name}: {user.get_full_name()} ({list_name})")
                        )
                else:
                    # Others become substitutes
                    SubstituteMembershipFactory.create(
                        user=user,
                        committee=main_committee,
                        role=substitute_role,
                        election_list_name=list_name,
                        election_list_position=i + 1,
                        election_votes=votes
                    )
        
        # Verify minority gender quota
        self._verify_minority_quota(main_committee, assigned_users)
        
        self.stdout.write(
            self.style.SUCCESS(
                f"[OK] Assigned {len(assigned_users)} regular members to main committee"
            )
        )
        
        substitute_count = main_committee.get_active_substitutes().count()
        if substitute_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"[OK] Assigned {substitute_count} substitute members to main committee"
                )
            )
        
        # 4. Create subcommittees
        subcommittees = []
        if "subcommittees" in config:
            used_guests = []
            
            # Get all main committee members for distribution
            all_main_members = list(main_committee.get_active_members())
            member_index = 0  # Track position for round-robin distribution
            
            for sub_cfg in config["subcommittees"]:
                # Create subcommittee (no substitute logic)
                subcommittee = SubcommitteeFactory.create(
                    name=sub_cfg["name"],
                    parent=main_committee,
                    total_seats=sub_cfg["member_count"] + sub_cfg["external_count"],
                    committee_type='SUBCOMMITTEE',
                    substitute_logic_enabled=False
                )
                subcommittees.append(subcommittee)
                
                self.stdout.write(
                    self.style.SUCCESS(f"[OK] Created subcommittee: {subcommittee.name}")
                )
                
                # Assign members from main committee using round-robin
                # This ensures better distribution across subcommittees
                members_for_this_subcommittee = []
                for _ in range(sub_cfg["member_count"]):
                    if all_main_members:
                        # Use modulo to wrap around if we need more assignments than available members
                        members_for_this_subcommittee.append(all_main_members[member_index % len(all_main_members)])
                        member_index += 1
                
                # Assign roles: first = chair, second = vice chair, third = clerk, rest = member
                for idx, membership in enumerate(members_for_this_subcommittee):
                    if idx == 0:
                        role = chair_role
                    elif idx == 1:
                        role = vice_chair_role
                    elif idx == 2:
                        role = clerk_role
                    else:
                        role = member_role
                    
                    RegularMembershipFactory.create(
                        user=membership.user,
                        committee=subcommittee,
                        role=role,
                        election_list_name='',
                        election_list_position=None,
                        election_votes=None
                    )
                
                # Assign external guests
                for _ in range(sub_cfg["external_count"]):
                    if guest_users:
                        guest = guest_users.pop(0)
                        used_guests.append(guest)
                        
                        ExternalMembershipFactory.create(
                            user=guest,
                            committee=subcommittee,
                            role=external_role
                        )
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"[OK] Added external member to {subcommittee.name}: {guest.get_full_name()}"
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
    
    def _verify_minority_quota(self, committee, members):
        """Verify that minority gender quota is met."""
        if not committee.minority_gender or not committee.minority_min_count:
            return
        
        minority_count = sum(1 for m in members if m.gender == committee.minority_gender)
        
        if minority_count < committee.minority_min_count:
            self.stdout.write(
                self.style.WARNING(
                    f"[WARNING] Minority quota not met! "
                    f"Required: {committee.minority_min_count} {committee.get_minority_gender_display()}, "
                    f"Got: {minority_count}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"[OK] Minority quota met: {minority_count}/{committee.minority_min_count} "
                    f"{committee.get_minority_gender_display()}"
                )
            )

    def _create_committees_structure(self, admin, users):
        """Create realistic committee structure with memberships."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.HTTP_INFO("  CREATING COMMITTEES"))
        self.stdout.write("=" * 60 + "\n")
        
        # Get default roles
        try:
            chair_role = Role.objects.get(codename='CHAIR')
            vice_chair_role = Role.objects.get(codename='VICE_CHAIR')
            clerk_role = Role.objects.get(codename='CLERK')
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
        
        # Assign vice chair (second user)
        vice_chair_user = available_users[1]
        RegularMembershipFactory.create(
            user=vice_chair_user,
            committee=main_committee,
            role=vice_chair_role,
            election_list_name='Liste 2',
            election_list_position=1,
            election_votes=420
        )
        self.stdout.write(
            self.style.SUCCESS(f"[OK] Assigned vice chair: {vice_chair_user.get_full_name()}")
        )
        
        # Assign clerk (third user)
        clerk_user = available_users[2]
        RegularMembershipFactory.create(
            user=clerk_user,
            committee=main_committee,
            role=clerk_role,
            election_list_name='Liste 1',
            election_list_position=2,
            election_votes=400
        )
        self.stdout.write(
            self.style.SUCCESS(f"[OK] Assigned clerk: {clerk_user.get_full_name()}")
        )
        
        # Assign regular members (next users to fill remaining seats)
        election_lists = ['Liste 1', 'Liste 2', 'Liste 3']
        for i, user in enumerate(available_users[3:main_committee.total_seats], start=3):
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
            # Use members from main committee
            main_members = list(main_committee.get_active_members()[:subcommittee.total_seats])
            
            for idx, membership in enumerate(main_members):
                # Check if user already has membership in this subcommittee
                if not Membership.objects.filter(
                    user=membership.user,
                    committee=subcommittee
                ).exists():
                    # Assign roles: first = chair, second = vice chair, third = clerk, rest = member
                    if idx == 0:
                        role = chair_role
                    elif idx == 1:
                        role = vice_chair_role
                    elif idx == 2:
                        role = clerk_role
                    else:
                        role = member_role
                    
                    RegularMembershipFactory.create(
                        user=membership.user,
                        committee=subcommittee,
                        role=role,
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
