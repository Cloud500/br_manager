"""Management command to seed committee test data."""

import random

from django.core.management.base import BaseCommand
from django.db import transaction

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
    Seed committee test data.
    
    Creates a realistic committee structure:
    - Main committee (Betriebsrat)
    - Several subcommittees
    - Memberships for existing users
    
    Usage:
        python manage.py seed_committees
        python manage.py seed_committees --clear
    """
    
    help = 'Seed committee test data (requires existing users)'
    
    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing committee data before seeding',
        )
    
    def handle(self, *args, **options):
        """Execute the command."""
        self.stdout.write(self.style.WARNING('\n' + '=' * 60))
        self.stdout.write(self.style.WARNING('  SEEDING COMMITTEE TEST DATA'))
        self.stdout.write(self.style.WARNING('=' * 60 + '\n'))
        
        # Check if users exist
        user_count = User.objects.count()
        if user_count < 10:
            self.stdout.write(
                self.style.ERROR(
                    f'[ERROR] Only {user_count} users found. '
                    'Please create users first with: python manage.py seed_testdata'
                )
            )
            return
        
        # Clear existing data if requested
        if options['clear']:
            self.stdout.write('Clearing existing committee data...')
            Committee.all_objects.all().hard_delete()
            Membership.all_objects.all().hard_delete()
            self.stdout.write(self.style.SUCCESS('[OK] Committee data cleared\n'))
        
        # Create committees
        with transaction.atomic():
            committees_data = self._create_committees_structure()
        
        # Show summary
        self._show_summary(committees_data)
        
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('  [OK] COMMITTEE SEEDING COMPLETE'))
        self.stdout.write(self.style.SUCCESS('=' * 60 + '\n'))
    
    def _create_committees_structure(self):
        """Create realistic committee structure with memberships."""
        # Get users
        users = list(User.objects.all()[:20])  # Use up to 20 users
        
        if not users:
            self.stdout.write(
                self.style.ERROR('[ERROR] No users found. Create users first.')
            )
            return None
        
        # Get roles
        try:
            chair_role = Role.objects.get(codename='CHAIR')
            vice_chair_role = Role.objects.get(codename='VICE_CHAIR')
            clerk_role = Role.objects.get(codename='CLERK')
            member_role = Role.objects.get(codename='MEMBER')
            substitute_role = Role.objects.get(codename='SUBSTITUTE')
            external_role = Role.objects.get(codename='EXTERNAL_MEMBER')
        except Role.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    '[ERROR] Roles not found. Run: python manage.py seed_roles'
                )
            )
            return None
        
        # 1. Create main committee
        main_committee = MainCommitteeFactory.create(
            name='Betriebsrat',
            total_seats=9,
            substitute_logic_enabled=True,
            minority_gender='F',
            minority_min_count=3
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'[OK] Created main committee: {main_committee.name} ({main_committee.total_seats} seats)'
            )
        )
        
        # 2. Create subcommittees
        subcommittees = []
        betriebsausschuss = None
        subcommittee_configs = [
            ('Betriebsausschuss', 7, 'COMMITTEE'),  # § 27 BetrVG - Will be auto-populated
            ('Personalausschuss', 5, 'SUBCOMMITTEE'),
            ('Arbeitsschutzausschuss', 7, 'SUBCOMMITTEE'),
            ('Gleichstellungsausschuss', 5, 'SUBCOMMITTEE'),
            ('Gesundheitsausschuss', 5, 'SUBCOMMITTEE'),
        ]
        
        for name, seats, comm_type in subcommittee_configs:
            sub = SubcommitteeFactory.create(
                name=name,
                parent=main_committee,
                total_seats=seats,
                committee_type=comm_type,
                auto_composition_enabled=(comm_type == 'COMMITTEE')  # Enable for BA
            )
            subcommittees.append(sub)
            if comm_type == 'COMMITTEE':
                betriebsausschuss = sub
            self.stdout.write(
                self.style.SUCCESS(f'[OK] Created: {sub.name} ({sub.total_seats} seats)')
            )
        
        # 3. Shuffle users for random assignment
        random.shuffle(users)
        
        # 4. Assign chair to main committee
        chair_user = users[0]
        RegularMembershipFactory.create(
            user=chair_user,
            committee=main_committee,
            role=chair_role,
            election_list_name='Liste 1',
            election_list_position=1,
            election_votes=480
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'[OK] Assigned chair: {chair_user.get_full_name()}'
            )
        )
        
        # 4b. Assign vice chair
        vice_chair_user = users[1]
        RegularMembershipFactory.create(
            user=vice_chair_user,
            committee=main_committee,
            role=vice_chair_role,
            election_list_name='Liste 2',
            election_list_position=1,
            election_votes=450
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'[OK] Assigned vice chair: {vice_chair_user.get_full_name()}'
            )
        )
        
        # 4c. Assign clerk
        clerk_user = users[2]
        RegularMembershipFactory.create(
            user=clerk_user,
            committee=main_committee,
            role=clerk_role,
            election_list_name='Liste 1',
            election_list_position=2,
            election_votes=420
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'[OK] Assigned clerk: {clerk_user.get_full_name()}'
            )
        )
        
        # 5. Assign regular members to main committee
        election_lists = ['Liste 1', 'Liste 2', 'Liste 3', 'Gewerkschaftsliste']
        regular_count = min(main_committee.total_seats, len(users))
        
        for i, user in enumerate(users[3:regular_count], start=3):
            list_name = random.choice(election_lists)
            RegularMembershipFactory.create(
                user=user,
                committee=main_committee,
                role=member_role,
                election_list_name=list_name,
                election_list_position=i,
                election_votes=random.randint(150, 450)
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'[OK] Assigned {regular_count} regular members'
            )
        )
        
        # 6. Create substitute members
        substitute_count = 0
        for i, user in enumerate(users[regular_count:], start=1):
            if substitute_count >= 8:  # Max 8 substitutes
                break
            
            list_name = random.choice(election_lists)
            SubstituteMembershipFactory.create(
                user=user,
                committee=main_committee,
                role=substitute_role,
                election_list_name=list_name,
                election_list_position=i,
                election_votes=random.randint(80, 300)
            )
            substitute_count += 1
        
        if substitute_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'[OK] Assigned {substitute_count} substitute members'
                )
            )
        
        # 6.5. Get all main committee members
        main_members = list(main_committee.get_active_members())
        
        # 6.6. Populate Betriebsausschuss automatically
        if betriebsausschuss:
            # Sync auto-members (Chair + Vice-Chair already created in main committee)
            added, skipped = betriebsausschuss.sync_auto_ba_members()
            self.stdout.write(
                self.style.SUCCESS(
                    f'[OK] Betriebsausschuss: {added} auto-members added, {skipped} already present'
                )
            )
            
            # Get required size info
            ba_info = betriebsausschuss.get_ba_size_info()
            manual_needed = ba_info['manual_members_required']
            
            if manual_needed > 0:
                # Select additional members from main committee (excluding chair and vice-chair)
                available_members = [
                    m for m in main_members 
                    if m.role.codename not in ['CHAIR', 'VICE_CHAIR']
                    and not Membership.objects.filter(
                        user=m.user,
                        committee=betriebsausschuss
                    ).exists()
                ]
                
                # Select random members to fill BA
                selected_for_ba = random.sample(
                    available_members,
                    min(manual_needed, len(available_members))
                )
                
                for membership in selected_for_ba:
                    RegularMembershipFactory.create(
                        user=membership.user,
                        committee=betriebsausschuss,
                        role=member_role,  # Regular member role
                        election_list_name=membership.election_list_name,
                        election_list_position=membership.election_list_position,
                        election_votes=membership.election_votes
                    )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'[OK] Betriebsausschuss: {len(selected_for_ba)} additional members added'
                    )
                )
                
                # Validate BA composition
                is_valid, message = betriebsausschuss.get_ba_composition_status()
                if is_valid:
                    self.stdout.write(
                        self.style.SUCCESS(f'[OK] Betriebsausschuss composition: {message}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'[WARN] Betriebsausschuss composition: {message}')
                    )
        
        # 7. Assign members to subcommittees (excluding BA)
        for subcommittee in subcommittees:
            # Skip Betriebsausschuss - already populated
            if subcommittee.committee_type == 'COMMITTEE':
                continue
            
            # Select random members from main committee
            selected_members = random.sample(
                main_members,
                min(subcommittee.total_seats, len(main_members))
            )
            
            # First member becomes chair
            if selected_members:
                chair_membership = selected_members[0]
                RegularMembershipFactory.create(
                    user=chair_membership.user,
                    committee=subcommittee,
                    role=chair_role,
                    election_list_name=chair_membership.election_list_name,
                    election_list_position=1,
                    election_votes=chair_membership.election_votes
                )
            
            # Second member becomes vice chair (if available)
            if len(selected_members) > 1:
                vice_chair_membership = selected_members[1]
                RegularMembershipFactory.create(
                    user=vice_chair_membership.user,
                    committee=subcommittee,
                    role=vice_chair_role,
                    election_list_name=vice_chair_membership.election_list_name,
                    election_list_position=2,
                    election_votes=vice_chair_membership.election_votes
                )
            
            # Third member becomes clerk (if available)
            if len(selected_members) > 2:
                clerk_membership = selected_members[2]
                RegularMembershipFactory.create(
                    user=clerk_membership.user,
                    committee=subcommittee,
                    role=clerk_role,
                    election_list_name=clerk_membership.election_list_name,
                    election_list_position=3,
                    election_votes=clerk_membership.election_votes
                )
            
            # Rest are regular members
            for membership in selected_members[3:]:
                RegularMembershipFactory.create(
                    user=membership.user,
                    committee=subcommittee,
                    role=member_role,
                    election_list_name=membership.election_list_name,
                    election_list_position=4,
                    election_votes=membership.election_votes
                )
            
            # Add external expert to some committees (not to Betriebsausschuss)
            if subcommittee.name in ['Gesundheitsausschuss']:
                # Find users not in main committee
                non_main_users = [
                    u for u in users
                    if not Membership.objects.filter(
                        user=u,
                        committee=main_committee
                    ).exists()
                ]
                
                if non_main_users:
                    external_user = random.choice(non_main_users)
                    ExternalMembershipFactory.create(
                        user=external_user,
                        committee=subcommittee,
                        role=external_role
                    )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'[OK] Added external expert to {subcommittee.name}'
                        )
                    )
        
        # Calculate statistics
        total_memberships = Membership.objects.count()
        regular_members = main_committee.get_active_members().count()
        substitute_members = main_committee.get_active_substitutes().count()
        
        return {
            'main_committee': main_committee,
            'subcommittees': subcommittees,
            'total_memberships': total_memberships,
            'regular_members': regular_members,
            'substitute_members': substitute_members,
        }
    
    def _show_summary(self, committees_data):
        """Show summary of created committees."""
        if not committees_data:
            return
        
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.HTTP_INFO('  CREATED COMMITTEES'))
        self.stdout.write('=' * 60)
        
        main = committees_data['main_committee']
        self.stdout.write(f"\n  {self.style.SUCCESS('Main Committee:')}")
        self.stdout.write(f'    * Name: {main.name}')
        self.stdout.write(f'    * Seats: {main.total_seats}')
        self.stdout.write(f'    * Regular members: {committees_data["regular_members"]}')
        self.stdout.write(f'    * Substitute members: {committees_data["substitute_members"]}')
        
        if main.minority_gender:
            self.stdout.write(
                f'    * Minority quota: {main.get_minority_gender_display()} '
                f'(minimum: {main.minority_min_count})'
            )
        
        self.stdout.write(f"\n  {self.style.SUCCESS('Subcommittees (' + str(len(committees_data['subcommittees'])) + '):')}")
        for sub in committees_data['subcommittees']:
            member_count = sub.get_active_members().count()
            external_count = sub.get_external_members().count()
            
            info = f'    * {sub.name}: {member_count} members'
            if external_count > 0:
                info += f' ({external_count} external)'
            self.stdout.write(info)
        
        self.stdout.write(f"\n  {self.style.SUCCESS('Totals:')}")
        self.stdout.write(f'    * Committees: {len(committees_data["subcommittees"]) + 1}')
        self.stdout.write(f'    * Memberships: {committees_data["total_memberships"]}')
        
        self.stdout.write('')
