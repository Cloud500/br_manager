"""Tests for committees models."""

from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.roles.models import Role
from apps.committees.models import Committee, Membership


class CommitteeModelTest(TestCase):
    """Tests for Committee model."""
    
    def setUp(self):
        """Set up test data."""
        self.admin = User.objects.create_superuser(
            email='admin@example.com',
            password='AdminPass123!',
            first_name='Admin',
            last_name='User',
            gender='M'
        )
    
    def test_committee_creation(self):
        """Test committee is created correctly."""
        committee = Committee.objects.create(
            name='Hauptbetriebsrat',
            committee_type='MAIN',
            total_seats=7
        )
        
        self.assertEqual(committee.name, 'Hauptbetriebsrat')
        self.assertEqual(committee.committee_type, 'MAIN')
        self.assertEqual(committee.total_seats, 7)
        self.assertTrue(committee.is_active)
        self.assertIsNone(committee.deleted_at)
    
    def test_main_committee_without_parent(self):
        """Test MAIN committee can be created without parent."""
        committee = Committee.objects.create(
            name='Betriebsrat',
            committee_type='MAIN',
            total_seats=9
        )
        committee.full_clean()
        
        self.assertIsNone(committee.parent)
        self.assertEqual(committee.committee_type, 'MAIN')
    
    def test_main_committee_with_parent_raises_error(self):
        """Test MAIN committee with parent raises ValidationError."""
        main_committee = Committee.objects.create(
            name='Hauptbetriebsrat',
            committee_type='MAIN',
            total_seats=7
        )
        
        invalid_committee = Committee(
            name='Invalid',
            committee_type='MAIN',
            parent=main_committee,
            total_seats=5
        )
        
        with self.assertRaises(ValidationError) as context:
            invalid_committee.full_clean()
        
        self.assertIn('parent', context.exception.message_dict)
    
    def test_subcommittee_without_parent_raises_error(self):
        """Test SUBCOMMITTEE without parent raises ValidationError."""
        invalid_committee = Committee(
            name='Wirtschaftsausschuss',
            committee_type='SUBCOMMITTEE',
            total_seats=5
        )
        
        with self.assertRaises(ValidationError) as context:
            invalid_committee.full_clean()
        
        self.assertIn('parent', context.exception.message_dict)
    
    def test_subcommittee_with_parent(self):
        """Test SUBCOMMITTEE with parent is created successfully."""
        main_committee = Committee.objects.create(
            name='Betriebsrat',
            committee_type='MAIN',
            total_seats=9
        )
        
        subcommittee = Committee.objects.create(
            name='Personalausschuss',
            committee_type='SUBCOMMITTEE',
            parent=main_committee,
            total_seats=3
        )
        subcommittee.full_clean()
        
        self.assertEqual(subcommittee.parent, main_committee)
        self.assertEqual(subcommittee.committee_type, 'SUBCOMMITTEE')
    
    def test_circular_reference_detection(self):
        """Test circular reference in hierarchy is detected."""
        committee_a = Committee.objects.create(
            name='Committee A',
            committee_type='COMMITTEE',
            parent=Committee.objects.create(
                name='Main',
                committee_type='MAIN',
                total_seats=5
            ),
            total_seats=3
        )
        
        committee_b = Committee.objects.create(
            name='Committee B',
            committee_type='SUBCOMMITTEE',
            parent=committee_a,
            total_seats=3
        )
        
        # Try to create circular reference
        committee_a.parent = committee_b
        
        with self.assertRaises(ValidationError) as context:
            committee_a.full_clean()
        
        self.assertIn('parent', context.exception.message_dict)
    
    def test_committee_str_representation(self):
        """Test __str__ returns committee name."""
        committee = Committee.objects.create(
            name='Betriebsrat',
            committee_type='MAIN',
            total_seats=7
        )
        
        self.assertEqual(str(committee), 'Betriebsrat')
    
    def test_get_active_members(self):
        """Test get_active_members returns only active REGULAR members."""
        committee = Committee.objects.create(
            name='Betriebsrat',
            committee_type='MAIN',
            total_seats=5
        )
        
        user1 = User.objects.create_user(
            email='user1@example.com',
            password='pass',
            first_name='User',
            last_name='One',
            gender='M'
        )
        user2 = User.objects.create_user(
            email='user2@example.com',
            password='pass',
            first_name='User',
            last_name='Two',
            gender='F'
        )
        user3 = User.objects.create_user(
            email='user3@example.com',
            password='pass',
            first_name='User',
            last_name='Three',
            gender='M'
        )
        
        # Active regular member
        Membership.objects.create(
            user=user1,
            committee=committee,
            member_type='REGULAR',
            is_active=True,
            start_date=date.today()
        )
        
        # Inactive regular member
        Membership.objects.create(
            user=user2,
            committee=committee,
            member_type='REGULAR',
            is_active=False,
            start_date=date.today()
        )
        
        # Active substitute member
        Membership.objects.create(
            user=user3,
            committee=committee,
            member_type='SUBSTITUTE',
            is_active=True,
            start_date=date.today()
        )
        
        active_members = committee.get_active_members()
        
        self.assertEqual(active_members.count(), 1)
        self.assertEqual(active_members.first().user, user1)
    
    def test_get_active_substitutes(self):
        """Test get_active_substitutes returns only active SUBSTITUTE members."""
        committee = Committee.objects.create(
            name='Betriebsrat',
            committee_type='MAIN',
            total_seats=5
        )
        
        user1 = User.objects.create_user(
            email='user1@example.com',
            password='pass',
            first_name='User',
            last_name='One',
            gender='M'
        )
        user2 = User.objects.create_user(
            email='user2@example.com',
            password='pass',
            first_name='User',
            last_name='Two',
            gender='F'
        )
        
        # Active substitute
        Membership.objects.create(
            user=user1,
            committee=committee,
            member_type='SUBSTITUTE',
            is_active=True,
            start_date=date.today()
        )
        
        # Regular member
        Membership.objects.create(
            user=user2,
            committee=committee,
            member_type='REGULAR',
            is_active=True,
            start_date=date.today()
        )
        
        substitutes = committee.get_active_substitutes()
        
        self.assertEqual(substitutes.count(), 1)
        self.assertEqual(substitutes.first().user, user1)
    
    def test_get_external_members(self):
        """Test get_external_members returns EXTERNAL members."""
        committee = Committee.objects.create(
            name='Wirtschaftsausschuss',
            committee_type='SUBCOMMITTEE',
            parent=Committee.objects.create(
                name='Main',
                committee_type='MAIN',
                total_seats=7
            ),
            total_seats=5
        )
        
        user1 = User.objects.create_user(
            email='external@example.com',
            password='pass',
            first_name='External',
            last_name='Member',
            gender='M'
        )
        
        Membership.objects.create(
            user=user1,
            committee=committee,
            member_type='EXTERNAL',
            is_active=True,
            start_date=date.today()
        )
        
        external = committee.get_external_members()
        
        self.assertEqual(external.count(), 1)
        self.assertEqual(external.first().member_type, 'EXTERNAL')
    
    def test_minority_gender_with_min_count(self):
        """Test committee with minority gender configuration."""
        committee = Committee.objects.create(
            name='Betriebsrat',
            committee_type='MAIN',
            total_seats=9,
            minority_gender='F',
            minority_min_count=3
        )
        committee.full_clean()
        
        self.assertEqual(committee.minority_gender, 'F')
        self.assertEqual(committee.minority_min_count, 3)
    
    def test_minority_min_count_without_gender_raises_error(self):
        """Test minority_min_count without gender raises ValidationError."""
        committee = Committee(
            name='Betriebsrat',
            committee_type='MAIN',
            total_seats=9,
            minority_min_count=3
        )
        
        with self.assertRaises(ValidationError) as context:
            committee.full_clean()
        
        self.assertIn('minority_gender', context.exception.message_dict)
    
    def test_minority_min_count_exceeds_total_seats_raises_error(self):
        """Test minority_min_count > total_seats raises ValidationError."""
        committee = Committee(
            name='Betriebsrat',
            committee_type='MAIN',
            total_seats=5,
            minority_gender='F',
            minority_min_count=6
        )
        
        with self.assertRaises(ValidationError) as context:
            committee.full_clean()
        
        self.assertIn('minority_min_count', context.exception.message_dict)
    
    def test_substitute_logic_enabled(self):
        """Test committee with substitute logic enabled."""
        committee = Committee.objects.create(
            name='Betriebsrat',
            committee_type='MAIN',
            total_seats=7,
            substitute_logic_enabled=True
        )
        
        self.assertTrue(committee.substitute_logic_enabled)


class MembershipModelTest(TestCase):
    """Tests for Membership model."""
    
    def setUp(self):
        """Set up test data."""
        self.admin = User.objects.create_superuser(
            email='admin@example.com',
            password='AdminPass123!',
            first_name='Admin',
            last_name='User',
            gender='M'
        )
        
        self.committee = Committee.objects.create(
            name='Betriebsrat',
            committee_type='MAIN',
            total_seats=7
        )
        
        self.user = User.objects.create_user(
            email='member@example.com',
            password='pass',
            first_name='Max',
            last_name='Mustermann',
            gender='M'
        )
        
        # Create a default role
        self.role = Role.objects.create(
            name='Member',
            codename='MEMBER',
            role_type='COMMITTEE'
        )
    
    def test_membership_creation(self):
        """Test membership is created correctly."""
        membership = Membership.objects.create(
            user=self.user,
            committee=self.committee,
            role=self.role,
            member_type='REGULAR',
            start_date=date.today()
        )
        
        self.assertEqual(membership.user, self.user)
        self.assertEqual(membership.committee, self.committee)
        self.assertEqual(membership.role, self.role)
        self.assertEqual(membership.member_type, 'REGULAR')
        self.assertTrue(membership.is_active)
    
    def test_membership_unique_user_committee(self):
        """Test user can only have one membership per committee."""
        Membership.objects.create(
            user=self.user,
            committee=self.committee,
            member_type='REGULAR',
            start_date=date.today()
        )
        
        with self.assertRaises(IntegrityError):
            Membership.objects.create(
                user=self.user,
                committee=self.committee,
                member_type='SUBSTITUTE',
                start_date=date.today()
            )
    
    def test_membership_str_representation(self):
        """Test __str__ returns formatted string."""
        membership = Membership.objects.create(
            user=self.user,
            committee=self.committee,
            member_type='REGULAR',
            start_date=date.today()
        )
        
        expected = f"Max Mustermann → Betriebsrat (Reguläres Mitglied)"
        self.assertEqual(str(membership), expected)
    
    def test_membership_is_current_active(self):
        """Test is_current returns True for active current membership."""
        membership = Membership.objects.create(
            user=self.user,
            committee=self.committee,
            member_type='REGULAR',
            start_date=date.today() - timedelta(days=30),
            is_active=True
        )
        
        self.assertTrue(membership.is_current)
    
    def test_membership_is_current_future(self):
        """Test is_current returns False for future membership."""
        membership = Membership.objects.create(
            user=self.user,
            committee=self.committee,
            member_type='REGULAR',
            start_date=date.today() + timedelta(days=30),
            is_active=True
        )
        
        self.assertFalse(membership.is_current)
    
    def test_membership_is_current_expired(self):
        """Test is_current returns False for expired membership."""
        membership = Membership.objects.create(
            user=self.user,
            committee=self.committee,
            member_type='REGULAR',
            start_date=date.today() - timedelta(days=60),
            end_date=date.today() - timedelta(days=30),
            is_active=True
        )
        
        self.assertFalse(membership.is_current)
    
    def test_membership_is_current_inactive(self):
        """Test is_current returns False for inactive membership."""
        membership = Membership.objects.create(
            user=self.user,
            committee=self.committee,
            member_type='REGULAR',
            start_date=date.today() - timedelta(days=30),
            is_active=False
        )
        
        self.assertFalse(membership.is_current)
    
    def test_external_member_not_in_main_committee(self):
        """Test external member cannot be in main committee simultaneously."""
        # Create main committee membership
        Membership.objects.create(
            user=self.user,
            committee=self.committee,
            member_type='REGULAR',
            start_date=date.today(),
            is_active=True
        )
        
        # Create subcommittee
        subcommittee = Committee.objects.create(
            name='Wirtschaftsausschuss',
            committee_type='SUBCOMMITTEE',
            parent=self.committee,
            total_seats=5
        )
        
        # Try to create external membership
        external_user = User.objects.create_user(
            email='external@example.com',
            password='pass',
            first_name='External',
            last_name='User',
            gender='F'
        )
        
        # First create main membership
        Membership.objects.create(
            user=external_user,
            committee=self.committee,
            member_type='REGULAR',
            start_date=date.today(),
            is_active=True
        )
        
        # Try to create external membership in subcommittee
        invalid_membership = Membership(
            user=external_user,
            committee=subcommittee,
            member_type='EXTERNAL',
            start_date=date.today()
        )
        
        with self.assertRaises(ValidationError) as context:
            invalid_membership.full_clean()
        
        self.assertIn('member_type', context.exception.message_dict)
    
    def test_external_member_no_election_info(self):
        """Test external member cannot have election info."""
        subcommittee = Committee.objects.create(
            name='Wirtschaftsausschuss',
            committee_type='SUBCOMMITTEE',
            parent=self.committee,
            total_seats=5
        )
        
        external_user = User.objects.create_user(
            email='external@example.com',
            password='pass',
            first_name='External',
            last_name='User',
            gender='F'
        )
        
        invalid_membership = Membership(
            user=external_user,
            committee=subcommittee,
            member_type='EXTERNAL',
            start_date=date.today(),
            election_list_name='Liste A'
        )
        
        with self.assertRaises(ValidationError) as context:
            invalid_membership.full_clean()
        
        self.assertIn('election_list_name', context.exception.message_dict)
    
    def test_substitute_with_election_info(self):
        """Test substitute member can have election info."""
        membership = Membership.objects.create(
            user=self.user,
            committee=self.committee,
            member_type='SUBSTITUTE',
            start_date=date.today(),
            election_list_name='Liste A',
            election_list_position=1,
            election_votes=150
        )
        membership.full_clean()
        
        self.assertEqual(membership.election_list_name, 'Liste A')
        self.assertEqual(membership.election_list_position, 1)
        self.assertEqual(membership.election_votes, 150)


class SoftDeleteCommitteeTest(TestCase):
    """Tests for Committee soft-delete functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.admin = User.objects.create_superuser(
            email='admin@example.com',
            password='AdminPass123!',
            first_name='Admin',
            last_name='User',
            gender='M'
        )
        
        self.committee = Committee.objects.create(
            name='Betriebsrat',
            committee_type='MAIN',
            total_seats=7
        )
    
    def test_committee_soft_delete(self):
        """Test committee soft-delete sets deleted_at."""
        self.committee.delete(user=self.admin)
        
        self.assertIsNotNone(self.committee.deleted_at)
        self.assertEqual(self.committee.deleted_by, self.admin)
        
        # Committee should not be in default queryset
        self.assertNotIn(self.committee, Committee.objects.all())
        
        # Committee should be in deleted queryset
        self.assertIn(self.committee, Committee.all_objects.deleted_only())
    
    def test_committee_soft_delete_with_user(self):
        """Test soft-delete tracks deleting user."""
        self.committee.delete(user=self.admin)
        
        self.assertEqual(self.committee.deleted_by, self.admin)
    
    def test_committee_soft_delete_cascades_to_memberships(self):
        """Test committee soft-delete cascades to memberships."""
        # Create memberships
        for i in range(3):
            user = User.objects.create_user(
                email=f'user{i}@example.com',
                password='pass',
                first_name=f'User',
                last_name=f'{i}',
                gender='M'
            )
            Membership.objects.create(
                user=user,
                committee=self.committee,
                member_type='REGULAR',
                start_date=date.today()
            )
        
        # Delete committee
        deleted_count, details = self.committee.delete(user=self.admin)
        
        # Check all memberships are deleted
        self.assertEqual(Membership.objects.filter(committee=self.committee).count(), 0)
        self.assertEqual(Membership.all_objects.filter(committee=self.committee).count(), 3)
        
        # Check return value
        self.assertEqual(deleted_count, 4)  # 1 committee + 3 memberships
        self.assertEqual(details['committees.Committee'], 1)
        self.assertEqual(details['committees.Membership'], 3)
    
    def test_committee_hard_delete(self):
        """Test committee hard_delete removes from database."""
        committee_id = self.committee.id
        self.committee.hard_delete()
        
        # Committee should not exist at all
        self.assertFalse(Committee.all_objects.filter(id=committee_id).exists())
    
    def test_committee_queryset_excludes_deleted(self):
        """Test default queryset excludes deleted committees."""
        committee2 = Committee.objects.create(
            name='Committee 2',
            committee_type='MAIN',
            total_seats=5
        )
        
        # Delete one committee
        self.committee.delete(user=self.admin)
        
        # Default queryset should only show active
        self.assertEqual(Committee.objects.count(), 1)
        self.assertIn(committee2, Committee.objects.all())
        
        # all_objects should show both
        self.assertEqual(Committee.all_objects.all().count(), 2)
    
    def test_deleted_committee_not_in_get_active_members(self):
        """Test deleted committee's get_active_members returns empty."""
        user = User.objects.create_user(
            email='user@example.com',
            password='pass',
            first_name='User',
            last_name='One',
            gender='M'
        )
        
        Membership.objects.create(
            user=user,
            committee=self.committee,
            member_type='REGULAR',
            start_date=date.today(),
            is_active=True
        )
        
        # Delete committee
        self.committee.delete(user=self.admin)
        
        # get_active_members should return empty
        self.assertEqual(self.committee.get_active_members().count(), 0)


class SoftDeleteMembershipTest(TestCase):
    """Tests for Membership soft-delete functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.admin = User.objects.create_superuser(
            email='admin@example.com',
            password='AdminPass123!',
            first_name='Admin',
            last_name='User',
            gender='M'
        )
        
        self.committee = Committee.objects.create(
            name='Betriebsrat',
            committee_type='MAIN',
            total_seats=7
        )
        
        self.user = User.objects.create_user(
            email='member@example.com',
            password='pass',
            first_name='Max',
            last_name='Mustermann',
            gender='M'
        )
        
        self.membership = Membership.objects.create(
            user=self.user,
            committee=self.committee,
            member_type='REGULAR',
            start_date=date.today()
        )
    
    def test_membership_soft_delete(self):
        """Test membership soft-delete sets deleted_at."""
        self.membership.delete(user=self.admin)
        
        self.assertIsNotNone(self.membership.deleted_at)
        self.assertEqual(self.membership.deleted_by, self.admin)
        
        # Membership should not be in default queryset
        self.assertNotIn(self.membership, Membership.objects.all())
    
    def test_membership_soft_delete_with_user(self):
        """Test soft-delete tracks deleting user."""
        self.membership.delete(user=self.admin)
        
        self.assertEqual(self.membership.deleted_by, self.admin)
    
    def test_membership_hard_delete(self):
        """Test membership hard_delete removes from database."""
        membership_id = self.membership.id
        self.membership.hard_delete()
        
        # Membership should not exist at all
        self.assertFalse(Membership.all_objects.filter(id=membership_id).exists())
    
    def test_membership_is_current_deleted(self):
        """Test is_current returns False for deleted membership."""
        self.membership.delete(user=self.admin)
        
        self.assertFalse(self.membership.is_current)
    
    def test_membership_queryset_excludes_deleted(self):
        """Test default queryset excludes deleted memberships."""
        user2 = User.objects.create_user(
            email='user2@example.com',
            password='pass',
            first_name='User',
            last_name='Two',
            gender='F'
        )
        
        user3 = User.objects.create_user(
            email='user3@example.com',
            password='pass',
            first_name='User',
            last_name='Three',
            gender='M'
        )
        
        membership2 = Membership.objects.create(
            user=user2,
            committee=self.committee,
            member_type='REGULAR',
            start_date=date.today()
        )
        
        membership3 = Membership.objects.create(
            user=user3,
            committee=self.committee,
            member_type='SUBSTITUTE',
            start_date=date.today()
        )
        
        # Delete one membership
        self.membership.delete(user=self.admin)
        
        # Default queryset should only show active
        self.assertEqual(Membership.objects.count(), 2)
        
        # all_objects should show all three
        self.assertEqual(Membership.all_objects.all().count(), 3)
    
    def test_soft_delete_manager_alive_method(self):
        """Test SoftDeleteManager alive() method."""
        user2 = User.objects.create_user(
            email='user2@example.com',
            password='pass',
            first_name='User',
            last_name='Two',
            gender='F'
        )
        
        membership2 = Membership.objects.create(
            user=user2,
            committee=self.committee,
            member_type='REGULAR',
            start_date=date.today()
        )
        
        # Delete one
        self.membership.delete(user=self.admin)
        
        # alive() should return same as default queryset
        self.assertEqual(
            Membership.objects.alive().count(),
            Membership.objects.all().count()
        )
        
        # all_objects.alive() should filter correctly
        self.assertEqual(Membership.all_objects.alive().count(), 1)
        self.assertIn(membership2, Membership.all_objects.alive())
    
    def test_soft_delete_manager_deleted_method(self):
        """Test SoftDeleteManager deleted() method."""
        user2 = User.objects.create_user(
            email='user2@example.com',
            password='pass',
            first_name='User',
            last_name='Two',
            gender='F'
        )
        
        membership2 = Membership.objects.create(
            user=user2,
            committee=self.committee,
            member_type='REGULAR',
            start_date=date.today()
        )
        
        # Delete one
        self.membership.delete(user=self.admin)
        
        # deleted() should only return deleted
        deleted = Membership.all_objects.deleted()
        self.assertEqual(deleted.count(), 1)
        self.assertIn(self.membership, deleted)
        self.assertNotIn(membership2, deleted)
