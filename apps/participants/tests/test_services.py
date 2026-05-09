"""Focused tests for participants workflows."""

from datetime import date, time, timedelta

from django.core import mail
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.agendas.models import AgendaItem
from apps.committees.models import Committee, Membership
from apps.email_templates.models import EmailTemplate
from apps.meetings.models import Meeting
from apps.participants.models import MeetingParticipant
from apps.participants.models import MeetingAttendanceEvent
from apps.participants.forms import AddParticipantForm
from apps.participants.mixins import user_has_participant_permission
from apps.participants.services import (
    add_participant,
    available_substitutes_for_participant,
    confirm_presence,
    confirm_substitute,
    current_voting_participants,
    mark_self_left,
    mark_self_returned,
    mark_absent,
    reconfirm_presence,
    remove_absence,
    remove_substitute,
    send_meeting_invitations,
    suggest_substitute,
)
from apps.roles.models import Permission, Role, RolePermission


class ParticipantsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.permission_view, _ = Permission.objects.get_or_create(
            codename="participant.view", defaults={"name": "Teilnehmer ansehen", "category": "participant"}
        )
        cls.permission_edit, _ = Permission.objects.get_or_create(
            codename="participant.edit", defaults={"name": "Teilnehmer bearbeiten", "category": "participant"}
        )
        cls.permission_mark_absent, _ = Permission.objects.get_or_create(
            codename="participant.mark_absent", defaults={"name": "Abwesenheit setzen", "category": "participant"}
        )
        cls.permission_manage_substitutes, _ = Permission.objects.get_or_create(
            codename="participant.manage_substitutes", defaults={"name": "Ersatz verwalten", "category": "participant"}
        )
        cls.permission_send_notifications, _ = Permission.objects.get_or_create(
            codename="participant.send_notifications", defaults={"name": "Teilnehmer benachrichtigen", "category": "participant"}
        )

        cls.role_viewer, _ = Role.objects.get_or_create(codename="VIEWER", defaults={"name": "Viewer", "role_type": "COMMITTEE"})
        cls.role_member, _ = Role.objects.get_or_create(codename="MEMBER", defaults={"name": "Member", "role_type": "COMMITTEE"})
        cls.role_helper, _ = Role.objects.get_or_create(codename="HELPER", defaults={"name": "Helper", "role_type": "COMMITTEE"})
        RolePermission.objects.create(role=cls.role_viewer, permission=cls.permission_view)
        RolePermission.objects.create(role=cls.role_helper, permission=cls.permission_view)
        RolePermission.objects.create(role=cls.role_helper, permission=cls.permission_edit)
        RolePermission.objects.create(role=cls.role_helper, permission=cls.permission_mark_absent)
        RolePermission.objects.create(role=cls.role_helper, permission=cls.permission_manage_substitutes)
        RolePermission.objects.create(role=cls.role_helper, permission=cls.permission_send_notifications)

        cls.committee = Committee.objects.create(
            name="BR",
            committee_type="MAIN",
            total_seats=7,
        )
        cls.created_by = User.objects.create_user(
            email="creator@example.com",
            password="testpass123",
            first_name="C",
            last_name="Creator",
            gender="M",
        )
        cls.viewer = User.objects.create_user(
            email="viewer@example.com",
            password="testpass123",
            first_name="V",
            last_name="Viewer",
            gender="F",
        )
        cls.member = User.objects.create_user(
            email="member@example.com",
            password="testpass123",
            first_name="M",
            last_name="Member",
            gender="M",
        )
        cls.helper = User.objects.create_user(
            email="helper@example.com",
            password="testpass123",
            first_name="H",
            last_name="Helper",
            gender="F",
        )
        cls.regular = User.objects.create_user(
            email="regular@example.com",
            password="testpass123",
            first_name="Reg",
            last_name="Ular",
            gender="M",
        )
        cls.external = User.objects.create_user(
            email="external@example.com",
            password="testpass123",
            first_name="Ext",
            last_name="Ernal",
            gender="F",
        )
        cls.substitute = User.objects.create_user(
            email="sub@example.com",
            password="testpass123",
            first_name="Sub",
            last_name="Stitute",
            gender="M",
        )

        cls.regular_membership = Membership.objects.create(
            user=cls.regular,
            committee=cls.committee,
            role=cls.role_viewer,
            member_type="REGULAR",
            start_date=date.today(),
            is_active=True,
        )
        cls.external_membership = Membership.objects.create(
            user=cls.external,
            committee=cls.committee,
            role=cls.role_viewer,
            member_type="EXTERNAL",
            start_date=date.today(),
            is_active=True,
        )
        cls.substitute_membership = Membership.objects.create(
            user=cls.substitute,
            committee=cls.committee,
            role=cls.role_viewer,
            member_type="SUBSTITUTE",
            start_date=date.today(),
            is_active=True,
            election_list_position=1,
            election_votes=99,
        )
        cls.other_substitute_membership = Membership.objects.create(
            user=User.objects.create_user(
                email="sub2@example.com",
                password="testpass123",
                first_name="Sub2",
                last_name="Stitute",
                gender="F",
            ),
            committee=cls.committee,
            role=cls.role_viewer,
            member_type="SUBSTITUTE",
            start_date=date.today(),
            is_active=True,
            election_list_position=2,
            election_votes=10,
        )
        cls.viewer_membership = Membership.objects.create(
            user=cls.viewer,
            committee=cls.committee,
            role=cls.role_viewer,
            member_type="REGULAR",
            start_date=date.today(),
            is_active=True,
        )
        cls.member_membership = Membership.objects.create(
            user=cls.member,
            committee=cls.committee,
            role=cls.role_member,
            member_type="REGULAR",
            start_date=date.today(),
            is_active=True,
        )
        cls.helper_membership = Membership.objects.create(
            user=cls.helper,
            committee=cls.committee,
            role=cls.role_helper,
            member_type="REGULAR",
            start_date=date.today(),
            is_active=True,
        )

    def setUp(self):
        mail.outbox = []
        self.meeting = Meeting.objects.create(
            committee=self.committee,
            title="Sitzung",
            meeting_number="2026-01",
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0),
            meeting_type="ONLINE",
            location_url="https://example.com/meet",
            created_by=self.created_by,
        )

    def test_mark_absent_page_shows_absent_participant_election_data(self):
        """The absent participant card includes list, position and vote data."""
        self.regular_membership.election_list_name = "Liste A"
        self.regular_membership.election_list_position = 4
        self.regular_membership.election_votes = 123
        self.regular_membership.save(update_fields=[
            "election_list_name",
            "election_list_position",
            "election_votes",
        ])
        participant = MeetingParticipant.objects.get(
            meeting=self.meeting,
            membership=self.regular_membership,
        )
        self.client.force_login(self.helper)

        response = self.client.get(reverse("participants:participant_mark_absent", args=[participant.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Abwesender Teilnehmer")
        self.assertContains(response, "Liste A")
        self.assertContains(response, "4")
        self.assertContains(response, "123")

    def test_meeting_initializes_regular_and_external_only(self):
        committee = Committee.objects.create(name="BR-Init", committee_type="MAIN", total_seats=5)
        regular = User.objects.create_user(email="init-regular@example.com", password="testpass123", first_name="Init", last_name="Regular", gender="M")
        external = User.objects.create_user(email="init-external@example.com", password="testpass123", first_name="Init", last_name="External", gender="F")
        substitute = User.objects.create_user(email="init-sub@example.com", password="testpass123", first_name="Init", last_name="Sub", gender="M")
        regular_membership = Membership.objects.create(user=regular, committee=committee, role=self.role_viewer, member_type="REGULAR", start_date=date.today(), is_active=True)
        external_membership = Membership.objects.create(user=external, committee=committee, role=self.role_viewer, member_type="EXTERNAL", start_date=date.today(), is_active=True)
        Membership.objects.create(user=substitute, committee=committee, role=self.role_viewer, member_type="SUBSTITUTE", start_date=date.today(), is_active=True)
        meeting = Meeting.objects.create(
            committee=committee,
            title="Init",
            meeting_number="2026-02",
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0),
            meeting_type="ONLINE",
            location_url="https://example.com/init",
            created_by=self.created_by,
        )
        participants = meeting.participants.order_by("membership__user__last_name")
        self.assertEqual(participants.count(), 2)
        self.assertSetEqual(
            set(participants.values_list("membership_id", flat=True)),
            {regular_membership.id, external_membership.id},
        )
        self.assertEqual(len(mail.outbox), 0)
        for participant in participants:
            self.assertEqual(participant.role_for_display, self.role_viewer.name)

    def test_confirm_presence_records_attendance_event(self):
        """Loaded users can explicitly confirm presence during a running meeting."""
        self.meeting.status = "IN_PROGRESS"
        self.meeting.save(update_fields=["status", "updated_at"])

        participant = confirm_presence(self.meeting, self.regular)

        participant.refresh_from_db()
        self.assertEqual(participant.attendance_status, MeetingParticipant.ATTENDANCE_PRESENT)
        self.assertIsNotNone(participant.last_self_confirmed_at)
        event = MeetingAttendanceEvent.objects.get(participant=participant)
        self.assertEqual(event.event_type, MeetingAttendanceEvent.EVENT_CONFIRMED_PRESENT)
        self.assertEqual(event.actor, self.regular)

    def test_self_absence_and_return_update_current_voting_participants(self):
        """Self-service absence removes and return restores current voting presence."""
        self.meeting.status = "IN_PROGRESS"
        self.meeting.save(update_fields=["status", "updated_at"])
        participant = confirm_presence(self.meeting, self.regular)

        mark_self_left(self.meeting, self.regular)
        participant.refresh_from_db()
        self.assertEqual(participant.attendance_status, MeetingParticipant.ATTENDANCE_LEFT)
        self.assertNotIn(participant, current_voting_participants(self.meeting))

        mark_self_returned(self.meeting, self.regular)
        participant.refresh_from_db()
        self.assertEqual(participant.attendance_status, MeetingParticipant.ATTENDANCE_PRESENT)
        self.assertIn(participant, current_voting_participants(self.meeting))

    def test_substitute_assignment_resets_stale_attendance_confirmation(self):
        """Substitutes must confirm themselves before their replacement row counts as voting."""
        participant = MeetingParticipant.objects.get(meeting=self.meeting, membership=self.regular_membership)
        participant.status = MeetingParticipant.STATUS_SUBSTITUTE_PROPOSED
        participant.attendance_status = MeetingParticipant.ATTENDANCE_PRESENT
        participant.last_self_confirmed_at = timezone.now()
        participant.save(update_fields=["status", "attendance_status", "last_self_confirmed_at", "updated_at"])

        confirm_substitute(participant, self.substitute_membership, changed_by=self.helper)

        participant.refresh_from_db()
        self.assertEqual(participant.status, MeetingParticipant.STATUS_ABSENT)
        self.assertEqual(participant.substitute_membership, self.substitute_membership)
        self.assertEqual(participant.attendance_status, MeetingParticipant.ATTENDANCE_NOT_CONFIRMED)
        self.assertIsNone(participant.last_self_confirmed_at)
        self.assertNotIn(participant, current_voting_participants(self.meeting))

    def test_substitute_removal_resets_stale_attendance_confirmation(self):
        """Removing a substitute must not transfer the substitute's presence to the original member."""
        participant = MeetingParticipant.objects.get(meeting=self.meeting, membership=self.regular_membership)
        participant.status = MeetingParticipant.STATUS_SUBSTITUTE_PROPOSED
        participant.save(update_fields=["status", "updated_at"])
        confirm_substitute(participant, self.substitute_membership, changed_by=self.helper)
        participant.attendance_status = MeetingParticipant.ATTENDANCE_PRESENT
        participant.last_self_confirmed_at = timezone.now()
        participant.save(update_fields=["attendance_status", "last_self_confirmed_at", "updated_at"])

        remove_substitute(participant, changed_by=self.helper)

        participant.refresh_from_db()
        self.assertIsNone(participant.substitute_membership)
        self.assertIn(participant.status, MeetingParticipant.ACTIVE_STATUSES)
        self.assertEqual(participant.attendance_status, MeetingParticipant.ATTENDANCE_NOT_CONFIRMED)
        self.assertIsNone(participant.last_self_confirmed_at)
        self.assertNotIn(participant, current_voting_participants(self.meeting))

    def test_reconfirm_presence_requires_running_meeting_and_valid_password(self):
        """Meeting-scoped re-confirmation validates credentials and running status."""
        with self.assertRaises(ValidationError):
            reconfirm_presence(self.meeting, self.regular, password="testpass123")

        self.meeting.status = "IN_PROGRESS"
        self.meeting.save(update_fields=["status", "updated_at"])

        with self.assertRaises(ValidationError):
            reconfirm_presence(self.meeting, self.regular, password="wrong")

        participant = reconfirm_presence(self.meeting, self.regular, password="testpass123")

        participant.refresh_from_db()
        self.assertEqual(participant.attendance_status, MeetingParticipant.ATTENDANCE_PRESENT)
        self.assertIsNotNone(participant.last_self_confirmed_at)
        self.assertTrue(
            participant.attendance_events.filter(
                event_type=MeetingAttendanceEvent.EVENT_RECONFIRMED,
            ).exists()
        )

    def test_add_external_membership_participant_sends_mail_after_meeting_sent(self):
        self.meeting.status = "SENT"
        self.meeting.sent_at = timezone.now()
        self.meeting.save(update_fields=["status", "sent_at", "updated_at"])
        other_committee = Committee.objects.create(
            name="Externe Stelle",
            committee_type="SUBCOMMITTEE",
            parent=self.committee,
            total_seats=1,
        )
        external_user = User.objects.create_user(
            email="expertin@example.com",
            password="testpass123",
            first_name="Eva",
            last_name="Expertin",
            gender="F",
        )
        external_membership = Membership.objects.create(
            user=external_user,
            committee=other_committee,
            role=self.role_viewer,
            member_type="EXTERNAL",
            start_date=date.today(),
            is_active=True,
        )

        participant = add_participant(
            self.meeting,
            membership=external_membership,
            changed_by=self.helper,
        )

        participant.refresh_from_db()
        self.assertEqual(participant.membership, external_membership)
        self.assertEqual(participant.participant_type, MeetingParticipant.PARTICIPANT_TYPE_EXTERNAL)
        self.assertEqual(participant.display_name_for_display, external_user.get_full_name())
        self.assertEqual(participant.email_for_delivery, external_user.email)
        self.assertFalse(participant.is_initially_invited)
        self.assertIsNotNone(participant.invite_sent_at)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Einladung", mail.outbox[0].subject)

    def test_add_participant_from_other_committee_keeps_membership_unchanged(self):
        other_committee = Committee.objects.create(
            name="Wirtschaftsausschuss",
            committee_type="SUBCOMMITTEE",
            parent=self.committee,
            total_seats=3,
        )
        other_user = User.objects.create_user(
            email="wa@example.com",
            password="testpass123",
            first_name="Willi",
            last_name="Ausschuss",
            gender="M",
        )
        other_membership = Membership.objects.create(
            user=other_user,
            committee=other_committee,
            role=self.role_viewer,
            member_type="REGULAR",
            start_date=date.today(),
            is_active=True,
        )

        participant = add_participant(
            self.meeting,
            membership=other_membership,
            changed_by=self.helper,
        )

        participant.refresh_from_db()
        other_membership.refresh_from_db()
        self.assertEqual(participant.membership, other_membership)
        self.assertEqual(participant.display_name_for_display, other_user.get_full_name())
        self.assertIn("Wirtschaftsausschuss", participant.role_for_display)
        self.assertEqual(other_membership.committee, other_committee)
        self.assertEqual(other_membership.member_type, "REGULAR")

    def test_add_participant_rejects_unrelated_committee_membership_in_service(self):
        unrelated_committee = Committee.objects.create(
            name="Fremder BR",
            committee_type="MAIN",
            total_seats=3,
        )
        unrelated_user = User.objects.create_user(
            email="fremd@example.com",
            password="testpass123",
            first_name="Fremd",
            last_name="Person",
            gender="F",
        )
        unrelated_membership = Membership.objects.create(
            user=unrelated_user,
            committee=unrelated_committee,
            role=self.role_viewer,
            member_type="REGULAR",
            start_date=date.today(),
            is_active=True,
        )

        with self.assertRaises(ValidationError):
            add_participant(
                self.meeting,
                membership=unrelated_membership,
                changed_by=self.helper,
            )

    def test_mark_absent_sets_status_and_suggests_substitute(self):
        participant = self.meeting.participants.get(membership=self.regular_membership)
        substitute = mark_absent(participant, "krank", False, changed_by=self.helper)
        participant.refresh_from_db()
        self.assertIsNone(substitute)
        self.assertEqual(participant.status, MeetingParticipant.STATUS_ABSENT)

        participant = self.meeting.participants.get(membership=self.external_membership)
        substitute = mark_absent(participant, "dienstlich", True, changed_by=self.helper)
        participant.refresh_from_db()
        self.assertEqual(participant.status, MeetingParticipant.STATUS_SUBSTITUTE_PROPOSED)
        self.assertEqual(substitute, self.substitute_membership)

    def test_confirm_substitute_stays_on_original_participant_row_and_sends_mail_after_meeting_sent(self):
        participant = self.meeting.participants.get(membership=self.regular_membership)
        mark_absent(participant, "krank", True, changed_by=self.helper)
        participant.refresh_from_db()
        self.meeting.status = "SENT"
        self.meeting.sent_at = timezone.now()
        self.meeting.save(update_fields=["status", "sent_at", "updated_at"])

        replacement1 = confirm_substitute(participant, self.substitute_membership, changed_by=self.helper)
        replacement2 = confirm_substitute(participant, self.substitute_membership, changed_by=self.helper)

        participant.refresh_from_db()
        self.assertEqual(replacement1.pk, replacement2.pk)
        self.assertEqual(participant.status, MeetingParticipant.STATUS_ABSENT)
        self.assertEqual(participant.substitute_membership, self.substitute_membership)
        self.assertEqual(Membership.objects.get(pk=self.substitute_membership.pk).member_type, "SUBSTITUTE")
        self.assertEqual(MeetingParticipant.objects.filter(meeting=self.meeting, membership=self.substitute_membership).count(), 0)
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(mail.outbox[0].subject.startswith("Einladung:"))

    def test_mark_absent_can_confirm_and_change_substitute_in_one_step(self):
        participant = self.meeting.participants.get(membership=self.regular_membership)

        selected = mark_absent(
            participant,
            "krank",
            True,
            substitute_membership=self.substitute_membership,
            changed_by=self.helper,
        )
        participant.refresh_from_db()

        self.assertEqual(selected, self.substitute_membership)
        self.assertEqual(participant.status, MeetingParticipant.STATUS_ABSENT)
        self.assertEqual(participant.substitute_membership, self.substitute_membership)
        self.assertEqual(MeetingParticipant.objects.filter(meeting=self.meeting).count(), 5)

        selected = mark_absent(
            participant,
            "weiter krank",
            True,
            substitute_membership=self.other_substitute_membership,
            changed_by=self.helper,
        )
        participant.refresh_from_db()

        self.assertEqual(selected, self.other_substitute_membership)
        self.assertEqual(participant.substitute_membership, self.other_substitute_membership)
        self.assertEqual(MeetingParticipant.objects.filter(meeting=self.meeting).count(), 5)
        self.assertEqual(participant.absence_reason, "weiter krank")

    def test_mark_absent_can_remove_replacement_when_not_nachladefaehig(self):
        participant = self.meeting.participants.get(membership=self.regular_membership)
        mark_absent(
            participant,
            "krank",
            True,
            substitute_membership=self.substitute_membership,
            changed_by=self.helper,
        )
        participant.refresh_from_db()

        mark_absent(participant, "nicht nachladefähig", False, changed_by=self.helper)

        participant.refresh_from_db()
        self.assertEqual(participant.status, MeetingParticipant.STATUS_ABSENT)
        self.assertIsNone(participant.substitute_membership)
        self.assertEqual(MeetingParticipant.objects.filter(meeting=self.meeting).count(), 5)

    def test_mark_absent_keeps_existing_replacement_without_extra_rows(self):
        participant = self.meeting.participants.get(membership=self.regular_membership)
        mark_absent(
            participant,
            "krank",
            True,
            substitute_membership=self.substitute_membership,
            changed_by=self.helper,
        )
        participant.refresh_from_db()
        self.assertEqual(participant.substitute_membership, self.substitute_membership)

        mark_absent(participant, "weiter krank", True, changed_by=self.helper)

        participant.refresh_from_db()
        self.assertEqual(participant.status, MeetingParticipant.STATUS_ABSENT)
        self.assertEqual(participant.substitute_membership, self.substitute_membership)
        self.assertEqual(participant.absence_reason, "weiter krank")
        self.assertEqual(MeetingParticipant.objects.filter(meeting=self.meeting).count(), 5)

    def test_remove_substitute_restores_original_with_invitation_only(self):
        participant = self.meeting.participants.get(membership=self.regular_membership)
        self.meeting.status = "SENT"
        self.meeting.sent_at = timezone.now()
        self.meeting.save(update_fields=["status", "sent_at", "updated_at"])
        mark_absent(
            participant,
            "krank",
            True,
            substitute_membership=self.substitute_membership,
            changed_by=self.helper,
        )
        participant.refresh_from_db()
        self.assertEqual(participant.substitute_membership, self.substitute_membership)
        self.assertEqual(len(mail.outbox), 1)

        remove_substitute(participant, changed_by=self.helper)

        participant.refresh_from_db()
        self.assertIsNone(participant.substitute_membership)
        self.assertEqual(participant.status, MeetingParticipant.STATUS_INVITED)
        self.assertEqual(participant.absence_reason, "")
        self.assertEqual(MeetingParticipant.objects.filter(meeting=self.meeting).count(), 5)
        self.assertEqual(len(mail.outbox), 2)
        self.assertTrue(mail.outbox[1].subject.startswith("Einladung:"))
        self.assertEqual(mail.outbox[1].to, [self.regular.email])
        self.assertTrue(all(message.subject.startswith("Einladung:") for message in mail.outbox))

    def test_remove_absence_restores_original_with_invitation_when_sent(self):
        participant = self.meeting.participants.get(membership=self.regular_membership)
        self.meeting.status = "SENT"
        self.meeting.sent_at = timezone.now()
        self.meeting.save(update_fields=["status", "sent_at", "updated_at"])
        mark_absent(participant, "krank", False, changed_by=self.helper)
        participant.refresh_from_db()
        self.assertEqual(participant.status, MeetingParticipant.STATUS_ABSENT)
        self.assertIsNone(participant.substitute_membership)

        remove_absence(participant, changed_by=self.helper)

        participant.refresh_from_db()
        self.assertEqual(participant.status, MeetingParticipant.STATUS_INVITED)
        self.assertEqual(participant.absence_reason, "")
        self.assertTrue(participant.nachladefaehig)
        self.assertIsNone(participant.substitute_membership)
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(mail.outbox[0].subject.startswith("Einladung:"))
        self.assertEqual(mail.outbox[0].to, [self.regular.email])

    def test_remove_absence_view_allowed_and_denied(self):
        participant = self.meeting.participants.get(membership=self.regular_membership)
        mark_absent(participant, "krank", False, changed_by=self.helper)
        participant.refresh_from_db()
        allowed = Client()
        allowed.force_login(self.helper)

        response = allowed.post(
            reverse("participants:participant_remove_absence", kwargs={"pk": participant.pk}),
        )

        self.assertEqual(response.status_code, 302)
        participant.refresh_from_db()
        self.assertEqual(participant.status, MeetingParticipant.STATUS_CREATED)
        self.assertEqual(participant.absence_reason, "")

        mark_absent(participant, "erneut krank", False, changed_by=self.helper)
        denied = Client()
        denied.force_login(self.member)
        response = denied.post(
            reverse("participants:participant_remove_absence", kwargs={"pk": participant.pk}),
        )

        self.assertEqual(response.status_code, 302)
        participant.refresh_from_db()
        self.assertEqual(participant.status, MeetingParticipant.STATUS_ABSENT)

    def test_mark_absent_edit_keeps_existing_replacement_without_duplicate_mails(self):
        participant = self.meeting.participants.get(membership=self.regular_membership)
        self.meeting.status = "SENT"
        self.meeting.sent_at = timezone.now()
        self.meeting.save(update_fields=["status", "sent_at", "updated_at"])

        mark_absent(
            participant,
            "krank",
            True,
            substitute_membership=self.substitute_membership,
            changed_by=self.helper,
        )
        participant.refresh_from_db()
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(mail.outbox[0].subject.startswith("Einladung:"))

        mark_absent(
            participant,
            "weiter krank",
            True,
            substitute_membership=self.substitute_membership,
            changed_by=self.helper,
        )
        participant.refresh_from_db()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(participant.status, MeetingParticipant.STATUS_ABSENT)
        self.assertEqual(participant.substitute_membership, self.substitute_membership)

        mark_absent(
            participant,
            "anderer Ersatz nötig",
            True,
            substitute_membership=self.other_substitute_membership,
            changed_by=self.helper,
        )

        self.assertEqual(len(mail.outbox), 2)
        self.assertTrue(mail.outbox[1].subject.startswith("Einladung:"))
        self.assertTrue(all(message.subject.startswith("Einladung:") for message in mail.outbox))
        participant.refresh_from_db()
        self.assertEqual(participant.substitute_membership, self.other_substitute_membership)
        self.assertEqual(MeetingParticipant.objects.filter(meeting=self.meeting).count(), 5)

    def test_mark_absent_edit_with_same_substitute_saves_absence_reason(self):
        participant = self.meeting.participants.get(membership=self.regular_membership)
        mark_absent(
            participant,
            "krank",
            True,
            substitute_membership=self.substitute_membership,
            changed_by=self.helper,
        )
        participant.refresh_from_db()

        mark_absent(
            participant,
            "weiterhin krank",
            True,
            substitute_membership=self.substitute_membership,
            changed_by=self.helper,
        )

        participant.refresh_from_db()
        self.assertEqual(participant.absence_reason, "weiterhin krank")
        self.assertEqual(participant.substitute_membership, self.substitute_membership)

    def test_invalid_substitute_confirmation_is_rejected(self):
        participant = self.meeting.participants.get(membership=self.regular_membership)

        with self.assertRaises(ValidationError):
            confirm_substitute(participant, self.substitute_membership, changed_by=self.helper)

        participant.refresh_from_db()
        self.assertEqual(participant.status, MeetingParticipant.STATUS_CREATED)
        self.assertEqual(MeetingParticipant.objects.filter(meeting=self.meeting, membership=self.substitute_membership).count(), 0)

    def test_send_meeting_invitations_uses_membership_addresses_and_updates_timestamps(self):
        committee = Committee.objects.create(name="BR-Mail", committee_type="MAIN", total_seats=5)
        regular = User.objects.create_user(email="mail-regular@example.com", password="testpass123", first_name="Mail", last_name="Regular", gender="M")
        external = User.objects.create_user(email="mail-external@example.com", password="testpass123", first_name="Mail", last_name="External", gender="F")
        Membership.objects.create(user=regular, committee=committee, role=self.role_viewer, member_type="REGULAR", start_date=date.today(), is_active=True)
        Membership.objects.create(user=external, committee=committee, role=self.role_viewer, member_type="EXTERNAL", start_date=date.today(), is_active=True)
        meeting = Meeting.objects.create(
            committee=committee,
            title="Mail",
            meeting_number="2026-03",
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0),
            meeting_type="ONLINE",
            location_url="https://example.com/mail",
            created_by=self.created_by,
        )
        participant = meeting.participants.get(membership__user=external)
        sent_count = send_meeting_invitations(meeting, message="Bitte pünktlich sein")
        participant.refresh_from_db()
        self.assertEqual(sent_count, 2)
        self.assertEqual(len(mail.outbox), 2)
        recipients = [recipient for message in mail.outbox for recipient in message.to]
        self.assertIn(external.email, recipients)
        self.assertIsNotNone(participant.invite_sent_at)
        self.assertIsNotNone(participant.last_notified_at)
        self.assertEqual(participant.status, MeetingParticipant.STATUS_INVITED)

    def test_send_meeting_invitations_embeds_agenda_text_without_attachment(self):
        AgendaItem.objects.create(
            agenda=self.meeting.agenda,
            title="Begrüßung und Feststellung der Beschlussfähigkeit",
            description="Kurze Einführung in die Sitzung.",
            sort_order=1,
        )
        AgendaItem.objects.create(
            agenda=self.meeting.agenda,
            title="Beratung aktueller Themen",
            sort_order=2,
        )

        send_meeting_invitations(self.meeting, message="Bitte pünktlich sein")

        self.assertGreater(len(mail.outbox), 0)
        message = mail.outbox[0]
        self.assertEqual(message.attachments, [])
        self.assertIn("Tagesordnung:", message.body)
        self.assertIn("1. Begrüßung und Feststellung der Beschlussfähigkeit", message.body)
        self.assertIn("   Kurze Einführung in die Sitzung.", message.body)
        self.assertIn("2. Beratung aktueller Themen", message.body)
        self.assertNotIn("TOP 1:", message.body)
        self.assertIn("Bitte pünktlich sein", message.body)

    def test_send_meeting_invitations_uses_configured_email_template(self):
        """Meeting invitations use the editable system template."""
        template = EmailTemplate.get_default(EmailTemplate.MEETING_INVITATION)
        template.subject = "BR-Termin: {{ meeting_title }}"
        template.body_text = (
            "Empfänger: {{ recipient_name }}\n"
            "Gremium: {{ committee_name }}\n"
            "Nachricht: {{ message }}"
        )
        template.save()

        send_meeting_invitations(self.meeting, message="Bitte Unterlagen mitbringen")

        self.assertGreater(len(mail.outbox), 0)
        message = mail.outbox[0]
        self.assertEqual(message.subject, "BR-Termin: Sitzung")
        self.assertIn("Gremium: BR", message.body)
        self.assertIn("Nachricht: Bitte Unterlagen mitbringen", message.body)

    def test_meeting_invitation_context_values_do_not_add_outer_blank_lines(self):
        """Editable templates control blank lines around agenda placeholders."""
        AgendaItem.objects.create(
            agenda=self.meeting.agenda,
            title="Beschlussfassung",
            sort_order=1,
        )
        template = EmailTemplate.get_default(EmailTemplate.MEETING_INVITATION)
        template.subject = "BR-Termin: {{ meeting_title }}"
        template.body_text = (
            "Ort: {{ meeting_location }}\n\n"
            "{{ agenda_text }}\n\n"
            "XYZ\n\n"
            "{{ additional_message_block }}"
        )
        template.save()

        send_meeting_invitations(self.meeting, message="Bitte Unterlagen mitbringen")

        message = mail.outbox[0]
        self.assertIn(f"Ort: {self.meeting.get_full_location}\n\nTagesordnung:", message.body)
        self.assertIn("1. Beschlussfassung\n\nXYZ\n\nZusätzliche Nachricht:", message.body)
        self.assertNotIn(f"Ort: {self.meeting.get_full_location}\n\n\nTagesordnung:", message.body)
        self.assertNotIn("XYZ\n\n\nZusätzliche Nachricht:", message.body)

    def test_draft_meeting_with_preserved_sent_timestamp_does_not_auto_send_invitation(self):
        self.meeting.status = "DRAFT"
        self.meeting.sent_at = timezone.now()
        self.meeting.save(update_fields=["status", "sent_at", "updated_at"])
        added_user = User.objects.create_user(
            email="added-draft@example.com",
            password="testpass123",
            first_name="Added",
            last_name="Draft",
            gender="F",
        )
        added_membership = Membership.objects.create(
            user=added_user,
            committee=self.committee,
            role=self.role_viewer,
            member_type="REGULAR",
            start_date=date.today(),
            is_active=True,
        )

        add_participant(self.meeting, added_membership, changed_by=self.helper)

        self.assertEqual(len(mail.outbox), 0)

    def test_absent_and_substitute_proposed_participants_do_not_receive_invitation(self):
        regular = self.meeting.participants.get(membership=self.regular_membership)
        external = self.meeting.participants.get(membership=self.external_membership)
        mark_absent(regular, "krank", False, changed_by=self.helper)
        mark_absent(external, "dienstlich", True, changed_by=self.helper)

        sent_count = send_meeting_invitations(self.meeting, message="Bitte pünktlich sein")
        regular.refresh_from_db()
        external.refresh_from_db()

        self.assertEqual(sent_count, self.meeting.participants.filter(status=MeetingParticipant.STATUS_INVITED).count())
        self.assertEqual(regular.status, MeetingParticipant.STATUS_ABSENT)
        self.assertEqual(external.status, MeetingParticipant.STATUS_SUBSTITUTE_PROPOSED)
        self.assertIsNone(regular.invite_sent_at)
        self.assertIsNone(external.invite_sent_at)

    def test_substitute_suggestion_uses_membership_assignments(self):
        self.assertEqual(suggest_substitute(self.meeting), self.substitute_membership)

    def test_substitute_suggestion_prefers_same_election_list_like_member_replacement(self):
        committee = Committee.objects.create(name="BR-Liste", committee_type="MAIN", total_seats=5)
        absent_user = User.objects.create_user(email="liste-abwesend@example.com", password="testpass123", first_name="Liste", last_name="Abwesend", gender="M")
        other_regular_user = User.objects.create_user(email="liste-regular@example.com", password="testpass123", first_name="Liste", last_name="Regular", gender="M")
        same_list_sub_user = User.objects.create_user(email="liste-same-sub@example.com", password="testpass123", first_name="Same", last_name="List", gender="M")
        other_list_sub_user = User.objects.create_user(email="liste-other-sub@example.com", password="testpass123", first_name="Other", last_name="List", gender="F")
        absent_membership = Membership.objects.create(user=absent_user, committee=committee, role=self.role_viewer, member_type="REGULAR", start_date=date.today(), is_active=True, election_list_name="Liste A", election_list_position=2)
        Membership.objects.create(user=other_regular_user, committee=committee, role=self.role_viewer, member_type="REGULAR", start_date=date.today(), is_active=True, election_list_name="Liste A", election_list_position=3)
        same_list_substitute = Membership.objects.create(user=same_list_sub_user, committee=committee, role=self.role_viewer, member_type="SUBSTITUTE", start_date=date.today(), is_active=True, election_list_name="Liste A", election_list_position=4, election_votes=10)
        other_list_substitute = Membership.objects.create(user=other_list_sub_user, committee=committee, role=self.role_viewer, member_type="SUBSTITUTE", start_date=date.today(), is_active=True, election_list_name="Liste B", election_list_position=1, election_votes=999)
        meeting = Meeting.objects.create(
            committee=committee,
            title="Liste",
            meeting_number="2026-04",
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0),
            meeting_type="ONLINE",
            location_url="https://example.com/liste",
            created_by=self.created_by,
        )
        participant = meeting.participants.get(membership=absent_membership)

        self.assertEqual(suggest_substitute(meeting, participant), same_list_substitute)
        self.assertNotEqual(suggest_substitute(meeting, participant), other_list_substitute)

    def test_substitute_suggestion_prioritizes_minority_gender_when_quota_not_met(self):
        committee = Committee.objects.create(
            name="BR-Minderheit",
            committee_type="MAIN",
            total_seats=5,
            minority_gender="F",
            minority_min_count=2,
        )
        absent_user = User.objects.create_user(email="minority-absent@example.com", password="testpass123", first_name="Minority", last_name="Absent", gender="F")
        regular_user = User.objects.create_user(email="minority-regular@example.com", password="testpass123", first_name="Minority", last_name="Regular", gender="M")
        male_sub_user = User.objects.create_user(email="minority-male-sub@example.com", password="testpass123", first_name="Male", last_name="Sub", gender="M")
        female_sub_user = User.objects.create_user(email="minority-female-sub@example.com", password="testpass123", first_name="Female", last_name="Sub", gender="F")
        absent_membership = Membership.objects.create(user=absent_user, committee=committee, role=self.role_viewer, member_type="REGULAR", start_date=date.today(), is_active=True, election_list_name="Liste A", election_list_position=1)
        Membership.objects.create(user=regular_user, committee=committee, role=self.role_viewer, member_type="REGULAR", start_date=date.today(), is_active=True, election_list_name="Liste A", election_list_position=2)
        male_substitute = Membership.objects.create(user=male_sub_user, committee=committee, role=self.role_viewer, member_type="SUBSTITUTE", start_date=date.today(), is_active=True, election_list_name="Liste A", election_list_position=3, election_votes=100)
        female_substitute = Membership.objects.create(user=female_sub_user, committee=committee, role=self.role_viewer, member_type="SUBSTITUTE", start_date=date.today(), is_active=True, election_list_name="Liste A", election_list_position=4, election_votes=1)
        meeting = Meeting.objects.create(
            committee=committee,
            title="Minderheit",
            meeting_number="2026-05",
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0),
            meeting_type="ONLINE",
            location_url="https://example.com/minority",
            created_by=self.created_by,
        )
        participant = meeting.participants.get(membership=absent_membership)

        self.assertEqual(suggest_substitute(meeting, participant), female_substitute)
        self.assertNotEqual(suggest_substitute(meeting, participant), male_substitute)

    def test_available_substitutes_uses_fair_rotation_order_after_current_list_positions(self):
        committee = Committee.objects.create(name="BR-Rotation", committee_type="MAIN", total_seats=5)
        absent_user = User.objects.create_user(email="rotation-absent@example.com", password="testpass123", first_name="Rotation", last_name="Absent", gender="M")
        regular_a_user = User.objects.create_user(email="rotation-a@example.com", password="testpass123", first_name="Rotation", last_name="A", gender="M")
        sub_a_user = User.objects.create_user(email="rotation-sub-a@example.com", password="testpass123", first_name="Sub", last_name="A", gender="M")
        sub_b_user = User.objects.create_user(email="rotation-sub-b@example.com", password="testpass123", first_name="Sub", last_name="B", gender="F")
        absent_membership = Membership.objects.create(user=absent_user, committee=committee, role=self.role_viewer, member_type="REGULAR", start_date=date.today(), is_active=True, election_list_name="Liste A", election_list_position=1)
        Membership.objects.create(user=regular_a_user, committee=committee, role=self.role_viewer, member_type="REGULAR", start_date=date.today(), is_active=True, election_list_name="Liste A", election_list_position=2)
        sub_a = Membership.objects.create(user=sub_a_user, committee=committee, role=self.role_viewer, member_type="SUBSTITUTE", start_date=date.today(), is_active=True, election_list_name="Liste A", election_list_position=3)
        sub_b = Membership.objects.create(user=sub_b_user, committee=committee, role=self.role_viewer, member_type="SUBSTITUTE", start_date=date.today(), is_active=True, election_list_name="Liste B", election_list_position=1)
        meeting = Meeting.objects.create(
            committee=committee,
            title="Rotation",
            meeting_number="2026-06",
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0),
            meeting_type="ONLINE",
            location_url="https://example.com/rotation",
            created_by=self.created_by,
        )
        participant = meeting.participants.get(membership=absent_membership)

        self.assertEqual(
            list(available_substitutes_for_participant(participant)),
            [sub_a, sub_b],
        )

    def test_user_has_participant_permission(self):
        self.assertTrue(user_has_participant_permission(self.viewer, self.meeting, "participant.view"))
        self.assertFalse(user_has_participant_permission(self.member, self.meeting, "participant.edit"))

    def test_meeting_detail_sorts_participants_by_role_order_then_name(self):
        meeting_view_permission, _ = Permission.objects.get_or_create(
            codename="meeting.view",
            defaults={"name": "Sitzung ansehen", "category": "meeting"},
        )
        RolePermission.objects.get_or_create(
            role=self.role_helper,
            permission=meeting_view_permission,
        )
        self.role_member.sort_order = 1
        self.role_member.save(update_fields=["sort_order"])
        self.role_viewer.sort_order = 2
        self.role_viewer.save(update_fields=["sort_order"])
        self.role_helper.sort_order = 3
        self.role_helper.save(update_fields=["sort_order"])
        client = Client()
        client.force_login(self.helper)

        response = client.get(reverse("meetings:meeting_detail", kwargs={"pk": self.meeting.pk}))

        self.assertEqual(response.status_code, 200)
        participants = list(response.context["participants"])
        self.assertEqual(
            [participant.membership for participant in participants],
            [
                self.member_membership,
                self.external_membership,
                self.regular_membership,
                self.viewer_membership,
                self.helper_membership,
            ],
        )

    def test_mark_absent_view_allowed_and_denied(self):
        participant = self.meeting.participants.get(membership=self.regular_membership)
        allowed = Client()
        allowed.force_login(self.helper)
        response = allowed.post(reverse("participants:participant_mark_absent", kwargs={"pk": participant.pk}), data={"absence_reason": "krank", "nachladefaehig": ""})
        self.assertEqual(response.status_code, 302)
        participant.refresh_from_db()
        participant.refresh_from_db()
        self.assertEqual(participant.status, MeetingParticipant.STATUS_ABSENT)

        denied = Client()
        denied.force_login(self.member)
        response = denied.post(reverse("participants:participant_mark_absent", kwargs={"pk": participant.pk}), data={"absence_reason": "krank", "nachladefaehig": ""})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("meetings:meeting_detail", kwargs={"pk": self.meeting.pk}), response.url)

    def test_mark_absent_view_combines_absence_and_substitute(self):
        participant = self.meeting.participants.get(membership=self.regular_membership)
        allowed = Client()
        allowed.force_login(self.helper)

        response = allowed.post(
            reverse("participants:participant_mark_absent", kwargs={"pk": participant.pk}),
            data={
                "absence_reason": "krank",
                "nachladefaehig": "on",
                "substitute_membership": self.substitute_membership.pk,
            },
        )

        self.assertEqual(response.status_code, 302)
        participant.refresh_from_db()
        self.assertEqual(participant.status, MeetingParticipant.STATUS_ABSENT)
        self.assertEqual(participant.substitute_membership, self.substitute_membership)
        self.assertEqual(MeetingParticipant.objects.filter(meeting=self.meeting).count(), 5)

    def test_mark_absent_view_does_not_allow_substitute_without_manage_permission(self):
        RolePermission.objects.get_or_create(
            role=self.role_member,
            permission=self.permission_mark_absent,
        )
        participant = self.meeting.participants.get(membership=self.regular_membership)
        client = Client()
        client.force_login(self.member)

        response = client.post(
            reverse("participants:participant_mark_absent", kwargs={"pk": participant.pk}),
            data={
                "absence_reason": "krank",
                "nachladefaehig": "on",
                "substitute_membership": self.substitute_membership.pk,
            },
        )

        self.assertEqual(response.status_code, 302)
        participant.refresh_from_db()
        self.assertNotEqual(participant.status, MeetingParticipant.STATUS_ABSENT)
        self.assertIsNone(participant.substitute_membership)

    def test_mark_absent_view_does_not_allow_clearing_substitute_without_manage_permission(self):
        RolePermission.objects.get_or_create(
            role=self.role_member,
            permission=self.permission_mark_absent,
        )
        participant = self.meeting.participants.get(membership=self.regular_membership)
        mark_absent(
            participant,
            "krank",
            True,
            substitute_membership=self.substitute_membership,
            changed_by=self.helper,
        )
        participant.refresh_from_db()
        client = Client()
        client.force_login(self.member)

        response = client.post(
            reverse("participants:participant_mark_absent", kwargs={"pk": participant.pk}),
            data={
                "absence_reason": "weiter krank",
                "nachladefaehig": "on",
                "substitute_membership": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        participant.refresh_from_db()
        self.assertEqual(participant.substitute_membership, self.substitute_membership)

    def test_add_participant_form_limits_choices_to_related_committees_and_unused_members(self):
        related_committee = Committee.objects.create(
            name="Wirtschaftsausschuss",
            committee_type="SUBCOMMITTEE",
            parent=self.committee,
            total_seats=3,
        )
        unrelated_committee = Committee.objects.create(
            name="Anderer BR",
            committee_type="MAIN",
            total_seats=3,
        )
        related_user = User.objects.create_user(
            email="related@example.com",
            password="testpass123",
            first_name="Rel",
            last_name="Ated",
            gender="F",
        )
        unrelated_user = User.objects.create_user(
            email="unrelated@example.com",
            password="testpass123",
            first_name="Un",
            last_name="Related",
            gender="M",
        )
        related_membership = Membership.objects.create(
            user=related_user,
            committee=related_committee,
            role=self.role_viewer,
            member_type="REGULAR",
            start_date=date.today(),
            is_active=True,
        )
        duplicate_user_membership = Membership.objects.create(
            user=self.regular,
            committee=related_committee,
            role=self.role_viewer,
            member_type="REGULAR",
            start_date=date.today(),
            is_active=True,
        )
        unrelated_membership = Membership.objects.create(
            user=unrelated_user,
            committee=unrelated_committee,
            role=self.role_viewer,
            member_type="REGULAR",
            start_date=date.today(),
            is_active=True,
        )

        form = AddParticipantForm(meeting=self.meeting)
        candidate_ids = set(form.fields["membership"].queryset.values_list("id", flat=True))

        self.assertIn(related_membership.id, candidate_ids)
        self.assertIn(self.substitute_membership.id, candidate_ids)
        self.assertNotIn(unrelated_membership.id, candidate_ids)
        self.assertNotIn(self.regular_membership.id, candidate_ids)
        self.assertNotIn(duplicate_user_membership.id, candidate_ids)

    def test_add_participant_rejects_duplicate_user_from_other_committee(self):
        related_committee = Committee.objects.create(
            name="Personalausschuss",
            committee_type="SUBCOMMITTEE",
            parent=self.committee,
            total_seats=3,
        )
        duplicate_user_membership = Membership.objects.create(
            user=self.regular,
            committee=related_committee,
            role=self.role_viewer,
            member_type="REGULAR",
            start_date=date.today(),
            is_active=True,
        )

        with self.assertRaises(ValidationError):
            add_participant(
                self.meeting,
                duplicate_user_membership,
                changed_by=self.helper,
            )

    def test_add_participant_form_excludes_user_already_selected_as_substitute(self):
        related_committee = Committee.objects.create(
            name="Sozialausschuss",
            committee_type="SUBCOMMITTEE",
            parent=self.committee,
            total_seats=3,
        )
        duplicate_substitute_user_membership = Membership.objects.create(
            user=self.substitute,
            committee=related_committee,
            role=self.role_viewer,
            member_type="REGULAR",
            start_date=date.today(),
            is_active=True,
        )
        participant = self.meeting.participants.get(membership=self.regular_membership)
        mark_absent(
            participant,
            "krank",
            True,
            substitute_membership=self.substitute_membership,
            changed_by=self.helper,
        )

        form = AddParticipantForm(meeting=self.meeting)
        candidate_ids = set(form.fields["membership"].queryset.values_list("id", flat=True))

        self.assertNotIn(duplicate_substitute_user_membership.id, candidate_ids)

    def test_add_participant_view_allowed_and_denied(self):
        other_committee = Committee.objects.create(
            name="JAV",
            committee_type="SUBCOMMITTEE",
            parent=self.committee,
            total_seats=3,
        )
        guest = User.objects.create_user(
            email="beraterin@example.com",
            password="testpass123",
            first_name="Externe",
            last_name="Beraterin",
            gender="F",
        )
        guest_membership = Membership.objects.create(
            user=guest,
            committee=other_committee,
            role=self.role_viewer,
            member_type="EXTERNAL",
            start_date=date.today(),
            is_active=True,
        )
        allowed = Client()
        allowed.force_login(self.helper)
        response = allowed.post(
            reverse("participants:participant_add", kwargs={"meeting_pk": self.meeting.pk}),
            data={"membership": guest_membership.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            MeetingParticipant.objects.filter(
                meeting=self.meeting,
                membership=guest_membership,
            ).exists()
        )

        denied_membership = self.other_substitute_membership
        denied = Client()
        denied.force_login(self.member)
        response = denied.post(
            reverse("participants:participant_add", kwargs={"meeting_pk": self.meeting.pk}),
            data={"membership": denied_membership.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            MeetingParticipant.objects.filter(
                meeting=self.meeting,
                membership=denied_membership,
            ).exists()
        )

    def _grant_role_permission(self, role: Role, permission: Permission) -> None:
        RolePermission.objects.get_or_create(role=role, permission=permission)
