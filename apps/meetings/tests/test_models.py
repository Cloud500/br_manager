"""Tests for meetings models."""

from datetime import date, time, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.committees.models import Committee, Membership
from apps.meetings.models import Meeting
from apps.roles.models import Permission, Role, RolePermission


class MeetingModelTest(TestCase):
    """Test suite for Meeting model."""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data for all test methods."""
        # Create users
        cls.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123',
            first_name='Max',
            last_name='Mustermann'
        )
        cls.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123',
            first_name='Erika',
            last_name='Musterfrau'
        )
        cls.user3 = User.objects.create_user(
            username='user3',
            email='user3@example.com',
            password='testpass123',
            first_name='Hans',
            last_name='Schmidt'
        )
        
        # Create committees
        cls.committee_main = Committee.objects.create(
            name='Betriebsrat MAIN',
            short_name='BR MAIN',
            committee_type='MAIN',
            is_active=True
        )
        cls.committee_ba = Committee.objects.create(
            name='Betriebsausschuss',
            short_name='BA',
            committee_type='BETRIEBSAUSSCHUSS',
            is_active=True
        )
        cls.committee_other = Committee.objects.create(
            name='Anderes Gremium',
            short_name='AG',
            committee_type='OTHER',
            is_active=True
        )
        
        # Create memberships
        cls.membership1 = Membership.objects.create(
            committee=cls.committee_main,
            user=cls.user1,
            is_active=True
        )
        cls.membership2 = Membership.objects.create(
            committee=cls.committee_main,
            user=cls.user2,
            is_active=True
        )
        cls.membership3 = Membership.objects.create(
            committee=cls.committee_ba,
            user=cls.user1,
            is_active=True
        )
        cls.membership2 = CommitteeMembership.objects.create(
            committee=cls.committee_main,
            user=cls.user2,
            is_active=True
        )
        cls.membership3 = CommitteeMembership.objects.create(
            committee=cls.committee_ba,
            user=cls.user1,
            is_active=True
        )
        
        # Create permissions
        cls.perm_view = Permission.objects.create(
            category='meeting',
            codename='view',
            name='Sitzungen ansehen'
        )
        cls.perm_create = Permission.objects.create(
            category='meeting',
            codename='create',
            name='Sitzungen erstellen'
        )
        cls.perm_create_other = Permission.objects.create(
            category='meeting',
            codename='create_other',
            name='Sitzungen in allen Gremien erstellen'
        )
        cls.perm_send_invitation = Permission.objects.create(
            category='meeting',
            codename='send_invitation',
            name='Einladungen versenden'
        )
        cls.perm_start_meeting = Permission.objects.create(
            category='meeting',
            codename='start_meeting',
            name='Sitzung starten'
        )
        cls.perm_complete_meeting = Permission.objects.create(
            category='meeting',
            codename='complete_meeting',
            name='Sitzung abschließen'
        )
        cls.perm_lead_meeting = Permission.objects.create(
            category='meeting',
            codename='lead_meeting',
            name='Sitzung leiten'
        )
        cls.perm_write_minutes = Permission.objects.create(
            category='meeting',
            codename='write_minutes',
            name='Protokoll schreiben'
        )
        
        # Create roles
        cls.role_admin = Role.objects.create(
            committee=None,  # Global role
            name='System Admin',
            description='System administrator with full access'
        )
        cls.role_admin.permissions.add(
            cls.perm_view,
            cls.perm_create_other,
            cls.perm_send_invitation,
            cls.perm_start_meeting,
            cls.perm_complete_meeting
        )
        
        cls.role_chair = Role.objects.create(
            committee=cls.committee_main,
            name='Vorsitzender',
            description='Committee chair'
        )
        cls.role_chair.permissions.add(
            cls.perm_view,
            cls.perm_create,
            cls.perm_send_invitation,
            cls.perm_start_meeting,
            cls.perm_complete_meeting,
            cls.perm_lead_meeting
        )
        
        cls.role_clerk = Role.objects.create(
            committee=cls.committee_main,
            name='Schriftführer',
            description='Committee clerk'
        )
        cls.role_clerk.permissions.add(
            cls.perm_view,
            cls.perm_write_minutes
        )
    
    # Basic Creation Tests
    
    def test_create_meeting_minimal_online(self):
        """Test creating a minimal ONLINE meeting."""
        meeting = Meeting.objects.create(
            committee=self.committee_main,
            title='Test Online Meeting',
            date=date.today() + timedelta(days=7),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://zoom.us/meeting123',
            created_by=self.user1
        )
        self.assertEqual(meeting.title, 'Test Online Meeting')
        self.assertEqual(meeting.status, 'DRAFT')
        self.assertIsNotNone(meeting.meeting_number)
    
    def test_create_meeting_minimal_in_person(self):
        """Test creating a minimal IN_PERSON meeting."""
        meeting = Meeting.objects.create(
            committee=self.committee_main,
            title='Test Präsenz Meeting',
            date=date.today() + timedelta(days=7),
            start_time=time(10, 0),
            meeting_type='IN_PERSON',
            location_name='Betriebsratsbüro',
            location_street='Hauptstraße 1',
            location_zip='12345',
            location_city='Musterstadt',
            created_by=self.user1
        )
        self.assertEqual(meeting.meeting_type, 'IN_PERSON')
        self.assertIsNone(meeting.location_url)
    
    def test_create_meeting_minimal_hybrid(self):
        """Test creating a minimal HYBRID meeting."""
        meeting = Meeting.objects.create(
            committee=self.committee_main,
            title='Test Hybrid Meeting',
            date=date.today() + timedelta(days=7),
            start_time=time(10, 0),
            meeting_type='HYBRID',
            location_url='https://zoom.us/meeting123',
            location_name='Betriebsratsbüro',
            location_street='Hauptstraße 1',
            location_zip='12345',
            location_city='Musterstadt',
            created_by=self.user1
        )
        self.assertEqual(meeting.meeting_type, 'HYBRID')
        self.assertIsNotNone(meeting.location_url)
        self.assertIsNotNone(meeting.location_name)
    
    def test_meeting_number_auto_generation(self):
        """Test automatic generation of meeting_number on save."""
        meeting = Meeting(
            committee=self.committee_main,
            title='Test Meeting',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://zoom.us/test',
            created_by=self.user1
        )
        # Meeting number should be None before save
        self.assertIsNone(meeting.meeting_number)
        
        meeting.save()
        
        # Meeting number should be generated after save
        self.assertIsNotNone(meeting.meeting_number)
        # Format: YYYY-NN (e.g., 2026-01)
        self.assertTrue(meeting.meeting_number.startswith(str(date.today().year)))
    
    def test_meeting_number_increments_per_year(self):
        """Test that meeting numbers increment for same committee and year."""
        meeting1 = Meeting.objects.create(
            committee=self.committee_main,
            title='Meeting 1',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://zoom.us/test1',
            created_by=self.user1
        )
        meeting2 = Meeting.objects.create(
            committee=self.committee_main,
            title='Meeting 2',
            date=date.today(),
            start_time=time(11, 0),
            meeting_type='ONLINE',
            location_url='https://zoom.us/test2',
            created_by=self.user1
        )
        
        # Extract numbers from meeting_number (format: YYYY-NN)
        num1 = int(meeting1.meeting_number.split('-')[1])
        num2 = int(meeting2.meeting_number.split('-')[1])
        
        self.assertEqual(num2, num1 + 1)
    
    def test_meeting_number_is_unique_per_committee(self):
        """Test that meeting numbers are unique per committee."""
        meeting1 = Meeting.objects.create(
            committee=self.committee_main,
            title='Meeting 1',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://zoom.us/test1',
            created_by=self.user1
        )
        meeting2 = Meeting.objects.create(
            committee=self.committee_other,
            title='Meeting 2',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://zoom.us/test2',
            created_by=self.user1
        )
        
        # Both meetings should have number 01 for this year (different committees)
        self.assertTrue(meeting1.meeting_number.endswith('-01'))
        self.assertTrue(meeting2.meeting_number.endswith('-01'))
    
    def test_str_representation(self):
        """Test string representation of Meeting."""
        meeting = Meeting.objects.create(
            committee=self.committee_main,
            title='Test Meeting',
            date=date(2026, 5, 15),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://zoom.us/test',
            created_by=self.user1
        )
        expected = f'{meeting.meeting_number} - Test Meeting (2026-05-15)'
        self.assertEqual(str(meeting), expected)
    
    # Meeting Type Validation Tests
    
    def test_online_meeting_requires_location_url(self):
        """Test that ONLINE meetings require location_url."""
        meeting = Meeting(
            committee=self.committee_main,
            title='Test Online Meeting',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            # location_url is missing
            created_by=self.user1
        )
        with self.assertRaises(ValidationError) as context:
            meeting.full_clean()
        
        self.assertIn('location_url', context.exception.message_dict)
    
    def test_online_meeting_cannot_have_address_fields(self):
        """Test that ONLINE meetings cannot have address fields."""
        meeting = Meeting(
            committee=self.committee_main,
            title='Test Online Meeting',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://zoom.us/test',
            location_name='Betriebsratsbüro',  # Not allowed for ONLINE
            created_by=self.user1
        )
        with self.assertRaises(ValidationError) as context:
            meeting.full_clean()
        
        self.assertIn('meeting_type', context.exception.message_dict)
    
    def test_in_person_meeting_requires_full_address(self):
        """Test that IN_PERSON meetings require full address."""
        meeting = Meeting(
            committee=self.committee_main,
            title='Test Meeting',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='IN_PERSON',
            location_name='Betriebsratsbüro',
            # Missing other address fields
            created_by=self.user1
        )
        with self.assertRaises(ValidationError) as context:
            meeting.full_clean()
        
        self.assertIn('location_name', context.exception.message_dict)
    
    def test_in_person_meeting_cannot_have_location_url(self):
        """Test that IN_PERSON meetings cannot have location_url."""
        meeting = Meeting(
            committee=self.committee_main,
            title='Test Meeting',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='IN_PERSON',
            location_url='https://zoom.us/test',  # Not allowed for IN_PERSON
            location_name='Betriebsratsbüro',
            location_street='Hauptstraße 1',
            location_zip='12345',
            location_city='Musterstadt',
            created_by=self.user1
        )
        with self.assertRaises(ValidationError) as context:
            meeting.full_clean()
        
        self.assertIn('location_url', context.exception.message_dict)
    
    def test_hybrid_meeting_requires_both_url_and_address(self):
        """Test that HYBRID meetings require both URL and address."""
        # Missing location_url
        meeting1 = Meeting(
            committee=self.committee_main,
            title='Test Hybrid Meeting',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='HYBRID',
            location_name='Betriebsratsbüro',
            location_street='Hauptstraße 1',
            location_zip='12345',
            location_city='Musterstadt',
            created_by=self.user1
        )
        with self.assertRaises(ValidationError) as context:
            meeting1.full_clean()
        self.assertIn('location_url', context.exception.message_dict)
        
        # Missing address fields
        meeting2 = Meeting(
            committee=self.committee_main,
            title='Test Hybrid Meeting',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='HYBRID',
            location_url='https://zoom.us/test',
            created_by=self.user1
        )
        with self.assertRaises(ValidationError) as context:
            meeting2.full_clean()
        self.assertIn('location_name', context.exception.message_dict)
    
    # Time Validation Tests
    
    def test_end_time_must_be_after_start_time(self):
        """Test that end_time must be after start_time."""
        meeting = Meeting(
            committee=self.committee_main,
            title='Test Meeting',
            date=date.today(),
            start_time=time(12, 0),
            end_time=time(10, 0),  # Before start_time
            meeting_type='ONLINE',
            location_url='https://zoom.us/test',
            created_by=self.user1
        )
        with self.assertRaises(ValidationError) as context:
            meeting.full_clean()
        
        self.assertIn('end_time', context.exception.message_dict)
    
    def test_actual_end_time_after_actual_start_time(self):
        """Test that actual_end_time must be after actual_start_time."""
        meeting = Meeting.objects.create(
            committee=self.committee_main,
            title='Test Meeting',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://zoom.us/test',
            created_by=self.user1,
            status='IN_PROGRESS'
        )
        
        meeting.actual_start_time = time(10, 0)
        meeting.actual_end_time = time(9, 0)  # Before actual_start_time
        
        with self.assertRaises(ValidationError) as context:
            meeting.full_clean()
        
        self.assertIn('actual_end_time', context.exception.message_dict)
    
    def test_get_duration_calculation(self):
        """Test get_duration() calculates correct timedelta."""
        meeting = Meeting.objects.create(
            committee=self.committee_main,
            title='Test Meeting',
            date=date.today(),
            start_time=time(10, 0),
            end_time=time(12, 0),
            meeting_type='ONLINE',
            location_url='https://zoom.us/test',
            created_by=self.user1
        )
        
        duration = meeting.get_duration()
        self.assertEqual(duration, timedelta(hours=2))
    
    def test_get_actual_duration_calculation(self):
        """Test get_actual_duration() calculates correct timedelta."""
        meeting = Meeting.objects.create(
            committee=self.committee_main,
            title='Test Meeting',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://zoom.us/test',
            created_by=self.user1,
            status='COMPLETED',
            actual_start_time=time(10, 15),
            actual_end_time=time(12, 30)
        )
        
        duration = meeting.get_actual_duration()
        expected = timedelta(hours=2, minutes=15)
        self.assertEqual(duration, expected)
    
    def test_get_duration_returns_none_without_end_time(self):
        """Test get_duration() returns None when end_time is not set."""
        meeting = Meeting.objects.create(
            committee=self.committee_main,
            title='Test Meeting',
            date=date.today(),
            start_time=time(10, 0),
            # No end_time
            meeting_type='ONLINE',
            location_url='https://zoom.us/test',
            created_by=self.user1
        )
        
        self.assertIsNone(meeting.get_duration())
    
    # Chair/Clerk Validation Tests
    
    def test_chair_must_be_committee_member(self):
        """Test that chair must be an active committee member."""
        meeting = Meeting(
            committee=self.committee_main,
            title='Test Meeting',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://zoom.us/test',
            chair=self.user3,  # Not a member of committee_main
            created_by=self.user1
        )
        with self.assertRaises(ValidationError) as context:
            meeting.full_clean()
        
        self.assertIn('chair', context.exception.message_dict)
    
    def test_clerk_must_be_committee_member(self):
        """Test that clerk must be an active committee member."""
        meeting = Meeting(
            committee=self.committee_main,
            title='Test Meeting',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://zoom.us/test',
            clerk=self.user3,  # Not a member of committee_main
            created_by=self.user1
        )
        with self.assertRaises(ValidationError) as context:
            meeting.full_clean()
        
        self.assertIn('clerk', context.exception.message_dict)
    
    def test_chair_and_clerk_can_be_same_person(self):
        """Test that chair and clerk can be the same person."""
        meeting = Meeting.objects.create(
            committee=self.committee_main,
            title='Test Meeting',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://zoom.us/test',
            chair=self.user1,
            clerk=self.user1,  # Same as chair
            created_by=self.user1
        )
        # Should not raise an exception
        meeting.full_clean()
        self.assertEqual(meeting.chair, meeting.clerk)
    
    def test_get_default_chair_returns_user_with_lead_permission(self):
        """Test get_default_chair() returns user with meeting.lead_meeting permission."""
        # Assign chair role to user1
        RoleAssignment.objects.create(
            user=self.user1,
            role=self.role_chair,
            committee=self.committee_main
        )
        
        default_chair = Meeting.get_default_chair(self.committee_main)
        self.assertEqual(default_chair, self.user1)
    
    def test_get_default_chair_returns_none_if_no_permission(self):
        """Test get_default_chair() returns None if no user has lead permission."""
        default_chair = Meeting.get_default_chair(self.committee_other)
        self.assertIsNone(default_chair)
    
    def test_get_default_clerk_returns_user_with_minutes_permission(self):
        """Test get_default_clerk() returns user with meeting.write_minutes permission."""
        # Assign clerk role to user2
        RoleAssignment.objects.create(
            user=self.user2,
            role=self.role_clerk,
            committee=self.committee_main
        )
        
        default_clerk = Meeting.get_default_clerk(self.committee_main)
        self.assertEqual(default_clerk, self.user2)
    
    # Property Tests
    
    def test_is_upcoming_for_future_meeting(self):
        """Test is_upcoming property for future meeting."""
        meeting = Meeting.objects.create(
            committee=self.committee_main,
            title='Future Meeting',
            date=date.today() + timedelta(days=7),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://zoom.us/test',
            created_by=self.user1
        )
        self.assertTrue(meeting.is_upcoming)
    
    def test_is_past_for_past_meeting(self):
        """Test is_past property for past meeting."""
        meeting = Meeting.objects.create(
            committee=self.committee_main,
            title='Past Meeting',
            date=date.today() - timedelta(days=7),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://zoom.us/test',
            created_by=self.user1
        )
        self.assertTrue(meeting.is_past)
    
    def test_is_editable_only_in_draft(self):
        """Test is_editable property is True only for DRAFT status."""
        meeting = Meeting.objects.create(
            committee=self.committee_main,
            title='Test Meeting',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://zoom.us/test',
            created_by=self.user1,
            status='DRAFT'
        )
        self.assertTrue(meeting.is_editable)
        
        meeting.status = 'COMPLETED'
        meeting.save()
        self.assertFalse(meeting.is_editable)
    
    def test_is_deletable_only_in_draft(self):
        """Test is_deletable property is True only for DRAFT status."""
        meeting = Meeting.objects.create(
            committee=self.committee_main,
            title='Test Meeting',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://zoom.us/test',
            created_by=self.user1,
            status='DRAFT'
        )
        self.assertTrue(meeting.is_deletable)
        
        meeting.status = 'SENT'
        meeting.save()
        self.assertFalse(meeting.is_deletable)
    
    def test_can_send_invitation_only_in_draft(self):
        """Test can_send_invitation property is True only for DRAFT status."""
        meeting = Meeting.objects.create(
            committee=self.committee_main,
            title='Test Meeting',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://zoom.us/test',
            created_by=self.user1,
            status='DRAFT'
        )
        self.assertTrue(meeting.can_send_invitation)
        
        meeting.status = 'SENT'
        meeting.save()
        self.assertFalse(meeting.can_send_invitation)
        
        meeting.status = 'IN_PROGRESS'
        meeting.save()
        self.assertFalse(meeting.can_send_invitation)
    
    def test_can_complete_only_in_progress(self):
        """Test can_complete property is True only for IN_PROGRESS status."""
        meeting = Meeting.objects.create(
            committee=self.committee_main,
            title='Test Meeting',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://zoom.us/test',
            created_by=self.user1,
            status='IN_PROGRESS'
        )
        self.assertTrue(meeting.can_complete)
        
        meeting.status = 'DRAFT'
        meeting.save()
        self.assertFalse(meeting.can_complete)
        
        meeting.status = 'SENT'
        meeting.save()
        self.assertFalse(meeting.can_complete)
    
    def test_get_full_location_online(self):
        """Test get_full_location for ONLINE meeting."""
        meeting = Meeting.objects.create(
            committee=self.committee_main,
            title='Test Meeting',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://zoom.us/test',
            created_by=self.user1
        )
        self.assertIn('Online:', meeting.get_full_location)
        self.assertIn('https://zoom.us/test', meeting.get_full_location)
    
    def test_get_full_location_in_person(self):
        """Test get_full_location for IN_PERSON meeting."""
        meeting = Meeting.objects.create(
            committee=self.committee_main,
            title='Test Meeting',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='IN_PERSON',
            location_name='Betriebsratsbüro',
            location_street='Hauptstraße 1',
            location_zip='12345',
            location_city='Musterstadt',
            created_by=self.user1
        )
        location = meeting.get_full_location
        self.assertIn('Betriebsratsbüro', location)
        self.assertIn('Hauptstraße 1', location)
        self.assertIn('12345', location)
        self.assertIn('Musterstadt', location)
    
    def test_get_full_location_hybrid(self):
        """Test get_full_location for HYBRID meeting."""
        meeting = Meeting.objects.create(
            committee=self.committee_main,
            title='Test Meeting',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='HYBRID',
            location_url='https://zoom.us/test',
            location_name='Betriebsratsbüro',
            location_street='Hauptstraße 1',
            location_zip='12345',
            location_city='Musterstadt',
            created_by=self.user1
        )
        location = meeting.get_full_location
        self.assertIn('Betriebsratsbüro', location)
        self.assertIn('https://zoom.us/test', location)
    
    def test_get_absolute_url(self):
        """Test get_absolute_url() returns correct URL."""
        meeting = Meeting.objects.create(
            committee=self.committee_main,
            title='Test Meeting',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://zoom.us/test',
            created_by=self.user1
        )
        expected_url = f'/meetings/{meeting.pk}/'
        self.assertEqual(meeting.get_absolute_url(), expected_url)
    
    # Permission Method Tests
    
    def test_user_can_create_with_permission_in_own_committee(self):
        """Test user_can_create() with permission in own committee."""
        # Assign chair role (has meeting.create permission) to user1 in committee_main
        RoleAssignment.objects.create(
            user=self.user1,
            role=self.role_chair,
            committee=self.committee_main
        )
        
        can_create = Meeting.user_can_create(self.user1, self.committee_main)
        self.assertTrue(can_create)
    
    def test_user_can_create_with_permission_in_betriebsausschuss_for_main(self):
        """Test user_can_create() for MAIN committee when user has permission in Betriebsausschuss."""
        # Create role with create permission in Betriebsausschuss
        role_ba = Role.objects.create(
            committee=self.committee_ba,
            name='BA Member',
            description='Betriebsausschuss member'
        )
        role_ba.permissions.add(self.perm_create)
        
        # Assign role to user1
        RoleAssignment.objects.create(
            user=self.user1,
            role=role_ba,
            committee=self.committee_ba
        )
        
        can_create = Meeting.user_can_create(self.user1, self.committee_main)
        self.assertTrue(can_create)
    
    def test_user_cannot_create_in_other_committee(self):
        """Test user_can_create() returns False for other committee."""
        # Assign chair role to user1 in committee_main only
        RoleAssignment.objects.create(
            user=self.user1,
            role=self.role_chair,
            committee=self.committee_main
        )
        
        can_create = Meeting.user_can_create(self.user1, self.committee_other)
        self.assertFalse(can_create)
    
    def test_user_can_create_with_create_other_permission(self):
        """Test user_can_create() with meeting.create_other (admin) permission."""
        # Assign admin role to user1
        RoleAssignment.objects.create(
            user=self.user1,
            role=self.role_admin,
            committee=None
        )
        
        # Admin can create in any committee
        can_create_main = Meeting.user_can_create(self.user1, self.committee_main)
        can_create_other = Meeting.user_can_create(self.user1, self.committee_other)
        
        self.assertTrue(can_create_main)
        self.assertTrue(can_create_other)
    
    def test_user_can_send_invitation_with_permission(self):
        """Test user_can_send_invitation() with permission."""
        meeting = Meeting.objects.create(
            committee=self.committee_main,
            title='Test Meeting',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://zoom.us/test',
            created_by=self.user1,
            status='DRAFT'
        )
        
        # Assign chair role (has send_invitation permission) to user1
        RoleAssignment.objects.create(
            user=self.user1,
            role=self.role_chair,
            committee=self.committee_main
        )
        
        can_send = Meeting.user_can_send_invitation(self.user1, meeting)
        self.assertTrue(can_send)
    
    def test_user_cannot_send_invitation_without_permission(self):
        """Test user_can_send_invitation() without permission."""
        meeting = Meeting.objects.create(
            committee=self.committee_main,
            title='Test Meeting',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://zoom.us/test',
            created_by=self.user1,
            status='DRAFT'
        )
        
        # user3 has no role assignments
        can_send = Meeting.user_can_send_invitation(self.user3, meeting)
        self.assertFalse(can_send)
    
    def test_user_can_start_meeting_with_permission(self):
        """Test user_can_start_meeting() with permission."""
        meeting = Meeting.objects.create(
            committee=self.committee_main,
            title='Test Meeting',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://zoom.us/test',
            created_by=self.user1,
            status='SENT'
        )
        
        # Assign chair role (has start_meeting permission) to user1
        RoleAssignment.objects.create(
            user=self.user1,
            role=self.role_chair,
            committee=self.committee_main
        )
        
        can_start = Meeting.user_can_start_meeting(self.user1, meeting)
        self.assertTrue(can_start)
    
    def test_user_can_complete_meeting_with_permission(self):
        """Test user_can_complete_meeting() with permission."""
        meeting = Meeting.objects.create(
            committee=self.committee_main,
            title='Test Meeting',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://zoom.us/test',
            created_by=self.user1,
            status='IN_PROGRESS'
        )
        
        # Assign chair role (has complete_meeting permission) to user1
        RoleAssignment.objects.create(
            user=self.user1,
            role=self.role_chair,
            committee=self.committee_main
        )
        
        can_complete = Meeting.user_can_complete_meeting(self.user1, meeting)
        self.assertTrue(can_complete)
    
    def test_user_can_view_meeting_with_permission(self):
        """Test user_can_view_meeting() with permission."""
        meeting = Meeting.objects.create(
            committee=self.committee_main,
            title='Test Meeting',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://zoom.us/test',
            created_by=self.user1
        )
        
        # Assign chair role (has view permission) to user1
        RoleAssignment.objects.create(
            user=self.user1,
            role=self.role_chair,
            committee=self.committee_main
        )
        
        can_view = Meeting.user_can_view_meeting(self.user1, meeting)
        self.assertTrue(can_view)
    
    def test_guest_cannot_view_meeting_without_permission(self):
        """Test user_can_view_meeting() without permission."""
        meeting = Meeting.objects.create(
            committee=self.committee_main,
            title='Test Meeting',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://zoom.us/test',
            created_by=self.user1
        )
        
        # user3 has no permissions
        can_view = Meeting.user_can_view_meeting(self.user3, meeting)
        self.assertFalse(can_view)
    
    def test_flexible_role_permissions(self):
        """Test flexible role permissions (custom role with start_meeting permission)."""
        # Create custom role "2. Stellvertreter" with start_meeting permission
        custom_role = Role.objects.create(
            committee=self.committee_main,
            name='2. Stellvertreter',
            description='Second deputy'
        )
        custom_role.permissions.add(
            self.perm_view,
            self.perm_start_meeting
        )
        
        # Assign custom role to user2
        RoleAssignment.objects.create(
            user=self.user2,
            role=custom_role,
            committee=self.committee_main
        )
        
        meeting = Meeting.objects.create(
            committee=self.committee_main,
            title='Test Meeting',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://zoom.us/test',
            created_by=self.user1,
            status='SENT'
        )
        
        can_start = Meeting.user_can_start_meeting(self.user2, meeting)
        self.assertTrue(can_start)
