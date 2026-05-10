"""Tests for meeting workflow views."""

from datetime import date, datetime, time, timedelta
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.agendas.models import AgendaItem
from apps.committees.models import Committee
from apps.committees.models import Membership
from apps.elections.models import Election, ElectionCandidate
from apps.meetings.models import Meeting
from apps.meetings.services import MeetingWorkflowService
from apps.participants.models import MeetingParticipant
from apps.protocols.models import Protocol
from apps.resolutions.models import Resolution, ResolutionAgendaItem
from apps.roles.models import Permission, Role


class MeetingCreateViewPermissionTest(TestCase):
    """Tests for meeting creation permission checks."""

    @classmethod
    def setUpTestData(cls):
        cls.chair = User.objects.create_user(
            email="chair-create@example.com",
            password="testpass123",
            first_name="Create",
            last_name="Chair",
            gender="F",
        )
        cls.regular_user = User.objects.create_user(
            email="regular-create@example.com",
            password="testpass123",
            first_name="Create",
            last_name="Regular",
            gender="M",
        )
        cls.inactive_committee_user = User.objects.create_user(
            email="inactive-create@example.com",
            password="testpass123",
            first_name="Create",
            last_name="Inactive",
            gender="F",
        )
        cls.committee = Committee.objects.create(
            name="BR Create",
            committee_type="MAIN",
            total_seats=5,
        )
        cls.other_committee = Committee.objects.create(
            name="BR Other Create",
            committee_type="MAIN",
            total_seats=5,
        )
        cls.inactive_committee = Committee.objects.create(
            name="BR Inactive Create",
            committee_type="MAIN",
            total_seats=5,
            is_active=False,
        )
        cls.create_permission, _created = Permission.objects.get_or_create(
            codename="meeting.create",
            defaults={
                "name": "Sitzung erstellen",
                "category": "meeting",
            },
        )
        cls.chair_role = Role.objects.create(
            codename="CREATE_VIEW_CHAIR",
            name="Create View Chair",
            role_type="COMMITTEE",
        )
        cls.chair_role.permissions.add(cls.create_permission)
        Membership.objects.create(
            user=cls.chair,
            committee=cls.committee,
            role=cls.chair_role,
            member_type="REGULAR",
            start_date=date.today(),
            is_active=True,
        )
        Membership.objects.create(
            user=cls.regular_user,
            committee=cls.committee,
            member_type="REGULAR",
            start_date=date.today(),
            is_active=True,
        )
        Membership.objects.create(
            user=cls.inactive_committee_user,
            committee=cls.inactive_committee,
            role=cls.chair_role,
            member_type="REGULAR",
            start_date=date.today(),
            is_active=True,
        )

    def test_chair_can_open_create_form_without_committee_query_parameter(self):
        """Users with create permission can open the create form before choosing a committee."""
        self.client.force_login(self.chair)

        response = self.client.get(reverse("meetings:meeting_create"))

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(
            response.context["form"].fields["committee"].queryset,
            [self.committee],
            transform=lambda committee: committee,
        )

    def test_user_without_create_permission_cannot_open_create_form_without_committee(self):
        """Users without create permission are still denied when no committee is selected."""
        self.client.force_login(self.regular_user)

        response = self.client.get(reverse("meetings:meeting_create"))

        self.assertRedirects(response, reverse("meetings:meeting_list"))

    def test_user_with_create_permission_only_in_inactive_committee_is_denied(self):
        """Create permission in inactive committees must not open the create form."""
        self.client.force_login(self.inactive_committee_user)

        response = self.client.get(reverse("meetings:meeting_create"))

        self.assertRedirects(response, reverse("meetings:meeting_list"))

    def test_invalid_committee_query_parameter_is_denied_without_server_error(self):
        """Malformed committee IDs fail closed instead of falling back to broad create access."""
        self.client.force_login(self.chair)

        response = self.client.get(f'{reverse("meetings:meeting_create")}?committee=not-a-uuid')

        self.assertRedirects(response, reverse("meetings:meeting_list"))

    def test_create_post_to_committee_without_permission_is_denied(self):
        """Opening the generic form must not allow posting to another committee."""
        self.client.force_login(self.chair)

        response = self.client.post(
            reverse("meetings:meeting_create"),
            {
                "committee": str(self.other_committee.pk),
                "title": "Unberechtigte Sitzung",
                "date": date.today().isoformat(),
                "start_time": "10:00",
                "meeting_type": "ONLINE",
                "location_url": "https://example.com/meeting",
            },
        )

        self.assertRedirects(response, reverse("meetings:meeting_list"))
        self.assertFalse(Meeting.objects.filter(title="Unberechtigte Sitzung").exists())


class MeetingResetToDraftViewTest(TestCase):
    """Tests for resetting sent meetings back to draft."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            email="admin@example.com",
            password="testpass123",
            first_name="Admin",
            last_name="User",
            gender="M",
            two_factor_enabled=True,
        )
        cls.regular_user = User.objects.create_user(
            email="regular@example.com",
            password="testpass123",
            first_name="Regular",
            last_name="User",
            gender="F",
        )
        cls.committee = Committee.objects.create(
            name="BR Workflow",
            committee_type="MAIN",
            total_seats=5,
        )

    def setUp(self):
        self.meeting = Meeting.objects.create(
            committee=self.committee,
            title="Gesendete Sitzung",
            meeting_number="2026-10",
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0),
            meeting_type="ONLINE",
            location_url="https://example.com/meeting",
            created_by=self.admin,
            status="SENT",
            sent_at=timezone.now(),
        )

    def test_admin_can_reset_sent_meeting_to_draft(self):
        self.client.force_login(self.admin)

        response = self.client.post(reverse("meetings:meeting_reset_to_draft", args=[self.meeting.pk]))

        self.assertRedirects(response, reverse("meetings:meeting_detail", args=[self.meeting.pk]))
        self.meeting.refresh_from_db()
        self.assertEqual(self.meeting.status, "DRAFT")
        self.assertIsNotNone(self.meeting.sent_at)
        self.assertTrue(self.meeting.is_editable)

    def test_reset_does_not_allow_users_without_edit_permission_to_edit_or_delete(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("meetings:meeting_reset_to_draft", args=[self.meeting.pk]))

        self.client.force_login(self.regular_user)
        edit_response = self.client.get(reverse("meetings:meeting_edit", args=[self.meeting.pk]))
        delete_response = self.client.get(reverse("meetings:meeting_delete", args=[self.meeting.pk]))

        self.assertRedirects(edit_response, reverse("meetings:meeting_list"))
        self.assertRedirects(delete_response, reverse("meetings:meeting_list"))

    def test_non_admin_cannot_reset_sent_meeting_to_draft(self):
        self.client.force_login(self.regular_user)

        response = self.client.post(reverse("meetings:meeting_reset_to_draft", args=[self.meeting.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("meetings:meeting_detail", args=[self.meeting.pk]))
        self.meeting.refresh_from_db()
        self.assertEqual(self.meeting.status, "SENT")
        self.assertIsNotNone(self.meeting.sent_at)

    def test_admin_cannot_reset_non_sent_meeting_to_draft(self):
        self.meeting.status = "IN_PROGRESS"
        self.meeting.save(update_fields=["status", "updated_at"])
        self.client.force_login(self.admin)

        response = self.client.post(reverse("meetings:meeting_reset_to_draft", args=[self.meeting.pk]))

        self.assertRedirects(response, reverse("meetings:meeting_detail", args=[self.meeting.pk]))
        self.meeting.refresh_from_db()
        self.assertEqual(self.meeting.status, "IN_PROGRESS")


class MeetingLiveWorkflowTest(TestCase):
    """Tests for meeting start side effects and live access gating."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="member-live@example.com",
            password="testpass123",
            first_name="Live",
            last_name="Member",
            gender="F",
        )
        self.chair = User.objects.create_user(
            email="chair-live@example.com",
            password="testpass123",
            first_name="Live",
            last_name="Chair",
            gender="M",
        )
        self.committee = Committee.objects.create(
            name="BR Live",
            committee_type="MAIN",
            total_seats=5,
        )
        self.role = Role.objects.create(
            codename="LIVE_MEMBER",
            name="Live Member",
            role_type="COMMITTEE",
        )
        self.view_permission, _created = Permission.objects.get_or_create(
            codename="meeting.view",
            defaults={
                "name": "Sitzung anzeigen",
                "category": "meeting",
            },
        )
        self.role.permissions.add(self.view_permission)
        for codename in [
            "agenda.edit_item_regular",
            "agenda.delete_item_regular",
            "agenda.reorder_items",
            "agenda.add_item_regular",
            "election.view",
            "resolution.view",
        ]:
            permission, _created = Permission.objects.get_or_create(
                codename=codename,
                defaults={"name": codename, "category": "agenda"},
            )
            self.role.permissions.add(permission)
        self.membership = Membership.objects.create(
            user=self.user,
            committee=self.committee,
            role=self.role,
            member_type="REGULAR",
            start_date=date.today(),
            is_active=True,
        )
        self.chair_membership = Membership.objects.create(
            user=self.chair,
            committee=self.committee,
            role=self.role,
            member_type="REGULAR",
            start_date=date.today(),
            is_active=True,
        )
        self.meeting = Meeting.objects.create(
            committee=self.committee,
            title="Live Sitzung",
            meeting_number="2026-20",
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0),
            meeting_type="ONLINE",
            location_url="https://example.com/live",
            created_by=self.chair,
            chair=self.chair,
            clerk=self.user,
            status="DRAFT",
        )
        self.agenda_item = AgendaItem.objects.create(
            agenda=self.meeting.agenda,
            title="Bericht",
            sort_order=1,
        )
        self.meeting.status = "SENT"
        self.meeting.sent_at = timezone.now()
        self.meeting.save(update_fields=["status", "sent_at", "updated_at"])

    def test_start_meeting_creates_protocol_draft(self):
        """Starting a meeting moves it into progress and creates a protocol."""
        MeetingWorkflowService.start_meeting(self.meeting, actor=self.chair)

        self.meeting.refresh_from_db()
        self.assertEqual(self.meeting.status, "IN_PROGRESS")
        self.assertIsNotNone(self.meeting.actual_start_time)
        self.assertTrue(Protocol.objects.filter(meeting=self.meeting).exists())

    @patch("apps.meetings.services.ProtocolDraftService.generate_from_meeting")
    @patch("apps.meetings.services.timezone.localtime")
    def test_complete_meeting_allows_end_after_midnight(
        self,
        mock_localtime,
        mock_generate_from_meeting,
    ):
        """Completing a meeting after midnight must not compare times only."""
        meeting_date = date(2026, 5, 10)
        completion_date = date(2026, 5, 11)
        mock_localtime.return_value = timezone.make_aware(datetime(2026, 5, 11, 0, 30))
        self.meeting.date = meeting_date
        self.meeting.status = "IN_PROGRESS"
        self.meeting.actual_start_date = meeting_date
        self.meeting.actual_start_time = time(23, 30)
        self.meeting.save(update_fields=["date", "status", "actual_start_date", "actual_start_time", "updated_at"])

        MeetingWorkflowService.complete_meeting(self.meeting, actor=self.chair)

        self.meeting.refresh_from_db()
        self.assertEqual(self.meeting.status, "COMPLETED")
        self.assertEqual(self.meeting.actual_end_date, completion_date)
        self.assertEqual(self.meeting.actual_end_time, time(0, 30))
        mock_generate_from_meeting.assert_called_once_with(self.meeting, actor=self.chair)

    def test_live_view_requires_loaded_participant_reconfirmation(self):
        """Loaded participants must re-confirm before seeing the live shell."""
        self.meeting.status = "IN_PROGRESS"
        self.meeting.save(update_fields=["status", "updated_at"])
        participant = MeetingParticipant.objects.get(meeting=self.meeting, membership=self.membership)
        self.client.force_login(self.user)

        response = self.client.get(reverse("meetings:meeting_live", args=[self.meeting.pk]))

        self.assertRedirects(response, reverse("meetings:meeting_reconfirm", args=[self.meeting.pk]))

        participant.last_self_confirmed_at = timezone.now()
        participant.attendance_status = MeetingParticipant.ATTENDANCE_PRESENT
        participant.save(update_fields=["last_self_confirmed_at", "attendance_status", "updated_at"])
        response = self.client.get(reverse("meetings:meeting_live", args=[self.meeting.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Live-Sitzung")
        self.assertNotContains(response, "Ich bin anwesend")
        self.assertContains(response, "Zwischendurch abwesend melden")

    def test_live_partials_require_loaded_participant_reconfirmation(self):
        """HTMX live partials must not bypass meeting re-confirmation."""
        self.meeting.status = "IN_PROGRESS"
        self.meeting.save(update_fields=["status", "updated_at"])
        self.client.force_login(self.user)

        response = self.client.get(reverse("meetings:meeting_live_status", args=[self.meeting.pk]))

        self.assertRedirects(response, reverse("meetings:meeting_reconfirm", args=[self.meeting.pk]))

    def test_absent_participant_without_substitute_cannot_enter_live_meeting(self):
        """A planned-absent original member must not re-enter and vote without being restored."""
        self.meeting.status = "IN_PROGRESS"
        self.meeting.save(update_fields=["status", "updated_at"])
        participant = MeetingParticipant.objects.get(meeting=self.meeting, membership=self.membership)
        participant.status = MeetingParticipant.STATUS_ABSENT
        participant.attendance_status = MeetingParticipant.ATTENDANCE_PRESENT
        participant.last_self_confirmed_at = timezone.now()
        participant.save(update_fields=["status", "attendance_status", "last_self_confirmed_at", "updated_at"])
        self.client.force_login(self.user)

        response = self.client.get(reverse("meetings:meeting_live", args=[self.meeting.pk]))

        self.assertRedirects(response, reverse("meetings:meeting_detail", args=[self.meeting.pk]))

    def test_detail_buttons_are_permission_aware_and_start_enters_reconfirm(self):
        """Only the chair sees start, and starting sends users to re-confirmation."""
        self.client.force_login(self.user)
        response = self.client.get(reverse("meetings:meeting_detail", args=[self.meeting.pk]))

        self.assertNotContains(response, "Sitzung starten")

        self.client.force_login(self.chair)
        response = self.client.get(reverse("meetings:meeting_detail", args=[self.meeting.pk]))

        self.assertContains(response, "Sitzung starten")

        response = self.client.post(reverse("meetings:meeting_start", args=[self.meeting.pk]))

        self.assertRedirects(response, reverse("meetings:meeting_reconfirm", args=[self.meeting.pk]))

    def test_completed_meeting_hides_and_blocks_agenda_mutations(self):
        """Completed meetings must not expose or allow TOP edit/delete actions."""
        self.meeting.status = "COMPLETED"
        self.meeting.actual_end_time = timezone.now()
        self.meeting.save(update_fields=["status", "actual_end_time", "updated_at"])
        self.client.force_login(self.chair)

        response = self.client.get(reverse("meetings:meeting_detail", args=[self.meeting.pk]))

        update_url = reverse("agendas:item_update", args=[self.agenda_item.pk])
        delete_url = reverse("agendas:item_delete", args=[self.agenda_item.pk])
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, update_url)
        self.assertNotContains(response, delete_url)

        update_response = self.client.get(update_url)
        delete_response = self.client.get(delete_url)

        self.assertRedirects(update_response, reverse("meetings:meeting_detail", args=[self.meeting.pk]))
        self.assertRedirects(delete_response, reverse("meetings:meeting_detail", args=[self.meeting.pk]))

    def test_meeting_detail_links_current_protocol_and_meeting_scoped_items(self):
        """Meeting detail links direct protocol and in-meeting elections/resolutions only."""
        protocol = Protocol.objects.create(meeting=self.meeting)
        self.meeting.status = "DRAFT"
        self.meeting.save(update_fields=["status", "updated_at"])
        election_item = AgendaItem.objects.create(
            agenda=self.meeting.agenda,
            title="Wahl Betriebsausschuss",
            item_type=AgendaItem.TYPE_ELECTION,
            sort_order=2,
        )
        election = Election.objects.create(agenda_item=election_item)
        resolution_item = AgendaItem.objects.create(
            agenda=self.meeting.agenda,
            title="Beschluss Budget",
            item_type=AgendaItem.TYPE_RESOLUTION,
            sort_order=3,
        )
        resolution = Resolution.objects.create(
            committee=self.committee,
            title="Budget freigeben",
            proposal="Der Betriebsrat beschließt das Budget.",
            status="PROPOSED",
            created_by=self.chair,
        )
        ResolutionAgendaItem.objects.create(
            agenda_item=resolution_item,
            resolution=resolution,
        )
        self.meeting.status = "COMPLETED"
        self.meeting.save(update_fields=["status", "updated_at"])
        self.client.force_login(self.chair)

        response = self.client.get(reverse("meetings:meeting_detail", args=[self.meeting.pk]))

        self.assertContains(response, reverse("protocols:protocol_detail", args=[protocol.pk]))
        self.assertContains(response, "Protokoll öffnen")
        self.assertNotContains(response, "bi-journals")
        self.assertContains(response, "#meeting-elections")
        self.assertContains(response, "#meeting-resolutions")
        self.assertContains(response, reverse("elections:election_detail", args=[election.pk]))
        self.assertContains(response, reverse("resolutions:resolution_detail", args=[resolution.pk]))
        self.assertContains(response, "<strong>3</strong> Budget freigeben", html=True)
        self.assertNotContains(response, "<strong>XXX</strong>")

    def test_meeting_list_groups_by_status_not_date(self):
        """Completed meetings are past; open workflow statuses are upcoming regardless of date."""
        future_completed = Meeting.objects.create(
            committee=self.committee,
            title="Zukünftig abgeschlossen",
            meeting_number="2026-22",
            date=date.today() + timedelta(days=30),
            start_time=time(10, 0),
            meeting_type="ONLINE",
            location_url="https://example.com/future-completed",
            created_by=self.chair,
            status="COMPLETED",
        )
        past_draft = Meeting.objects.create(
            committee=self.committee,
            title="Vergangener Entwurf",
            meeting_number="2026-23",
            date=date.today() - timedelta(days=30),
            start_time=time(10, 0),
            meeting_type="ONLINE",
            location_url="https://example.com/past-draft",
            created_by=self.chair,
            status="DRAFT",
        )
        self.client.force_login(self.chair)

        response = self.client.get(reverse("meetings:meeting_list"))

        self.assertIn(future_completed, response.context["past_meetings"])
        self.assertIn(past_draft, response.context["upcoming_meetings"])

    def test_live_controls_are_visible_for_chair_and_note_action_for_clerk(self):
        """Chair can activate TOPs and clerk can open protocol notes in live UI."""
        self.meeting.status = "IN_PROGRESS"
        self.meeting.save(update_fields=["status", "updated_at"])
        chair_participant = MeetingParticipant.objects.get(
            meeting=self.meeting,
            membership=self.chair_membership,
        )
        chair_participant.last_self_confirmed_at = timezone.now()
        chair_participant.save(update_fields=["last_self_confirmed_at", "updated_at"])
        self.client.force_login(self.chair)

        response = self.client.get(reverse("meetings:meeting_live", args=[self.meeting.pk]))

        self.assertContains(response, "Aktivieren")

        response = self.client.post(
            reverse("meetings:meeting_set_current_item", args=[self.meeting.pk, self.agenda_item.pk])
        )
        self.assertRedirects(response, reverse("meetings:meeting_live", args=[self.meeting.pk]))
        self.meeting.refresh_from_db()
        self.assertEqual(self.meeting.current_agenda_item, self.agenda_item)

        clerk_participant = MeetingParticipant.objects.get(meeting=self.meeting, membership=self.membership)
        clerk_participant.last_self_confirmed_at = timezone.now()
        clerk_participant.save(update_fields=["last_self_confirmed_at", "updated_at"])
        self.client.force_login(self.user)
        response = self.client.get(reverse("meetings:meeting_live", args=[self.meeting.pk]))

        self.assertContains(response, "Notiz")

    def test_live_view_uses_sse_without_polling_over_edit_fields(self):
        """Live refresh uses an event stream and never self-polls editable fragments."""
        self.meeting.status = "IN_PROGRESS"
        self.meeting.save(update_fields=["status", "updated_at"])
        participant = MeetingParticipant.objects.get(meeting=self.meeting, membership=self.membership)
        participant.last_self_confirmed_at = timezone.now()
        participant.save(update_fields=["last_self_confirmed_at", "updated_at"])
        self.client.force_login(self.user)

        response = self.client.get(reverse("meetings:meeting_live", args=[self.meeting.pk]))

        self.assertContains(response, reverse("meetings:meeting_live_events", args=[self.meeting.pk]))
        self.assertContains(response, "data-live-events")
        self.assertContains(response, "EventSource")
        self.assertContains(response, "suppressAgendaRefreshUntil")
        self.assertContains(response, "classList.add('ql-container', 'ql-snow')")
        self.assertContains(response, "markCurrentAgendaItem")
        self.assertContains(response, "current_agenda_item_id")
        self.assertContains(response, "br-live-refresh-agenda")
        self.assertContains(response, 'hx-trigger="br-live-refresh-agenda from:body"')
        self.assertContains(response, 'hx-trigger="br-live-refresh-status from:body"')
        self.assertContains(response, 'hx-trigger="br-live-refresh-participants from:body"')
        self.assertNotContains(response, 'hx-trigger="load, br-live-refresh')
        self.assertNotContains(response, "data-live-version-poller")
        self.assertNotContains(response, "every 5s")
        self.assertNotContains(response, "every 2s")

    def test_live_update_forms_are_htmx_fragment_posts(self):
        """Live actions must update fragments instead of causing full-page reloads."""
        self.meeting.status = "IN_PROGRESS"
        self.meeting.current_agenda_item = self.agenda_item
        self.meeting.save(update_fields=["status", "current_agenda_item", "updated_at"])
        participant = MeetingParticipant.objects.get(meeting=self.meeting, membership=self.membership)
        participant.last_self_confirmed_at = timezone.now()
        participant.save(update_fields=["last_self_confirmed_at", "updated_at"])
        self.client.force_login(self.user)

        response = self.client.get(reverse("meetings:meeting_live", args=[self.meeting.pk]))

        self.assertContains(response, 'hx-post="' + reverse("protocols:agenda_item_note_update", args=[self.meeting.pk, self.agenda_item.pk]) + '"')
        self.assertContains(response, 'hx-target="#live-agenda"')
        self.assertContains(response, 'hx-swap="outerHTML"')

    def test_clerk_can_edit_notes_for_non_current_live_top_with_rich_editor(self):
        """The clerk can write formatted notes for every TOP during the live meeting."""
        self.meeting.status = "DRAFT"
        self.meeting.save(update_fields=["status", "updated_at"])
        other_item = AgendaItem.objects.create(
            agenda=self.meeting.agenda,
            title="Zweiter TOP",
            sort_order=2,
        )
        self.meeting.status = "IN_PROGRESS"
        self.meeting.current_agenda_item = self.agenda_item
        self.meeting.save(update_fields=["status", "current_agenda_item", "updated_at"])
        participant = MeetingParticipant.objects.get(meeting=self.meeting, membership=self.membership)
        participant.last_self_confirmed_at = timezone.now()
        participant.save(update_fields=["last_self_confirmed_at", "updated_at"])
        self.client.force_login(self.user)

        response = self.client.get(reverse("meetings:meeting_live", args=[self.meeting.pk]))

        self.assertContains(response, f'aria-label="Formatierbare Notiz zu {other_item.title}"')
        self.assertContains(response, "data-quill-editor")
        self.assertContains(response, "data-quill-wrapper")
        self.assertContains(response, "protocol-quill-field")
        self.assertContains(response, "data-quill-input")
        self.assertContains(response, "d-none")
        self.assertContains(response, f'data-live-agenda-item-id="{other_item.pk}"')
        self.assertNotContains(response, 'type="hidden" name="body"')

    def test_live_events_endpoint_streams_current_version(self):
        """The live event endpoint is an SSE stream for cross-client updates."""
        self.meeting.status = "IN_PROGRESS"
        self.meeting.current_agenda_item = self.agenda_item
        self.meeting.save(update_fields=["status", "current_agenda_item", "updated_at"])
        participant = MeetingParticipant.objects.get(meeting=self.meeting, membership=self.membership)
        participant.attendance_status = MeetingParticipant.ATTENDANCE_PRESENT
        participant.last_self_confirmed_at = timezone.now()
        participant.save(update_fields=["attendance_status", "last_self_confirmed_at", "updated_at"])
        self.client.force_login(self.user)

        response = self.client.get(reverse("meetings:meeting_live_events", args=[self.meeting.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "text/event-stream")
        first_event = next(response.streaming_content).decode()
        self.assertIn("event: live-version", first_event)
        self.assertIn(str(self.agenda_item.pk), first_event)
        self.assertIn("current_agenda_item_id", first_event)

    def test_live_note_post_requires_reconfirmation(self):
        """Live TOP note updates must use the same re-confirmation gate as live actions."""
        self.meeting.status = "IN_PROGRESS"
        self.meeting.save(update_fields=["status", "updated_at"])
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("protocols:agenda_item_note_update", args=[self.meeting.pk, self.agenda_item.pk]),
            {"body": "<p>Nicht bestätigt</p>"},
        )

        self.assertRedirects(response, reverse("meetings:meeting_reconfirm", args=[self.meeting.pk]))
        protocol = Protocol.objects.filter(meeting=self.meeting).first()
        self.assertFalse(protocol and protocol.item_notes.filter(agenda_item=self.agenda_item).exists())

    def test_live_note_hx_post_returns_updated_agenda_fragment(self):
        """Saving a live note over HTMX returns the agenda fragment with formatted content."""
        self.meeting.status = "IN_PROGRESS"
        self.meeting.current_agenda_item = self.agenda_item
        self.meeting.save(update_fields=["status", "current_agenda_item", "updated_at"])
        participant = MeetingParticipant.objects.get(meeting=self.meeting, membership=self.membership)
        participant.attendance_status = MeetingParticipant.ATTENDANCE_PRESENT
        participant.last_self_confirmed_at = timezone.now()
        participant.save(update_fields=["attendance_status", "last_self_confirmed_at", "updated_at"])
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("protocols:agenda_item_note_update", args=[self.meeting.pk, self.agenda_item.pk]),
            {"body": "<p><strong>Formatierte Notiz</strong></p>"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Location", response.headers)
        self.assertIn("br-live-updated", response.headers.get("HX-Trigger"))
        self.assertIn("version", response.headers.get("HX-Trigger"))
        self.assertContains(response, 'id="live-agenda"')
        self.assertContains(response, "&lt;p&gt;&lt;strong&gt;Formatierte Notiz&lt;/strong&gt;&lt;/p&gt;", html=False)

    def test_live_version_changes_after_note_update(self):
        """Other clients can detect actual live changes through the compact version endpoint."""
        self.meeting.status = "IN_PROGRESS"
        self.meeting.current_agenda_item = self.agenda_item
        self.meeting.save(update_fields=["status", "current_agenda_item", "updated_at"])
        participant = MeetingParticipant.objects.get(meeting=self.meeting, membership=self.membership)
        participant.attendance_status = MeetingParticipant.ATTENDANCE_PRESENT
        participant.last_self_confirmed_at = timezone.now()
        participant.save(update_fields=["attendance_status", "last_self_confirmed_at", "updated_at"])
        self.client.force_login(self.user)
        before = self.client.get(reverse("meetings:meeting_live_version", args=[self.meeting.pk])).json()["version"]

        self.client.post(
            reverse("protocols:agenda_item_note_update", args=[self.meeting.pk, self.agenda_item.pk]),
            {"body": "<p>Neue Version</p>"},
            HTTP_HX_REQUEST="true",
        )
        after = self.client.get(reverse("meetings:meeting_live_version", args=[self.meeting.pk])).json()["version"]

        self.assertNotEqual(before, after)

    def test_current_top_hx_post_returns_updated_agenda_fragment(self):
        """Activating a TOP over HTMX updates live fragments without a full reload."""
        self.meeting.status = "IN_PROGRESS"
        self.meeting.save(update_fields=["status", "updated_at"])
        chair_participant = MeetingParticipant.objects.get(meeting=self.meeting, membership=self.chair_membership)
        chair_participant.attendance_status = MeetingParticipant.ATTENDANCE_PRESENT
        chair_participant.last_self_confirmed_at = timezone.now()
        chair_participant.save(update_fields=["attendance_status", "last_self_confirmed_at", "updated_at"])
        self.client.force_login(self.chair)

        response = self.client.post(
            reverse("meetings:meeting_set_current_item", args=[self.meeting.pk, self.agenda_item.pk]),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Location", response.headers)
        self.assertIn("br-live-updated", response.headers.get("HX-Trigger"))
        self.assertIn("version", response.headers.get("HX-Trigger"))
        self.assertIn("current_agenda_item_id", response.headers.get("HX-Trigger"))
        self.assertContains(response, "list-group-item-primary")

    def test_live_events_stream_detects_current_top_change(self):
        """The SSE stream must emit a new token when another user activates a TOP."""
        self.meeting.status = "DRAFT"
        self.meeting.save(update_fields=["status", "updated_at"])
        other_item = AgendaItem.objects.create(
            agenda=self.meeting.agenda,
            title="Zweiter TOP",
            sort_order=2,
        )
        self.meeting.status = "IN_PROGRESS"
        self.meeting.current_agenda_item = self.agenda_item
        self.meeting.save(update_fields=["status", "current_agenda_item", "updated_at"])
        participant = MeetingParticipant.objects.get(meeting=self.meeting, membership=self.membership)
        participant.attendance_status = MeetingParticipant.ATTENDANCE_PRESENT
        participant.last_self_confirmed_at = timezone.now()
        participant.save(update_fields=["attendance_status", "last_self_confirmed_at", "updated_at"])
        self.client.force_login(self.user)
        response = self.client.get(reverse("meetings:meeting_live_events", args=[self.meeting.pk]))
        events = response.streaming_content
        first_event = next(events).decode()

        self.meeting.current_agenda_item = other_item
        self.meeting.save(update_fields=["current_agenda_item", "updated_at"])
        second_event = next(events).decode()

        self.assertIn(str(self.agenda_item.pk), first_event)
        self.assertIn(str(other_item.pk), second_event)
        self.assertIn("current_agenda_item_id", second_event)

    def test_live_version_changes_after_current_top_update(self):
        """Other clients must detect TOP activation even when only current TOP changes."""
        self.meeting.status = "IN_PROGRESS"
        self.meeting.save(update_fields=["status", "updated_at"])
        chair_participant = MeetingParticipant.objects.get(meeting=self.meeting, membership=self.chair_membership)
        chair_participant.attendance_status = MeetingParticipant.ATTENDANCE_PRESENT
        chair_participant.last_self_confirmed_at = timezone.now()
        chair_participant.save(update_fields=["attendance_status", "last_self_confirmed_at", "updated_at"])
        self.client.force_login(self.chair)
        before = self.client.get(reverse("meetings:meeting_live_version", args=[self.meeting.pk])).json()["version"]

        self.client.post(
            reverse("meetings:meeting_set_current_item", args=[self.meeting.pk, self.agenda_item.pk]),
            HTTP_HX_REQUEST="true",
        )
        after = self.client.get(reverse("meetings:meeting_live_version", args=[self.meeting.pk])).json()["version"]

        self.assertNotEqual(before, after)
        self.assertIn(str(self.agenda_item.pk), after)

    def test_protocol_detail_note_post_requires_reconfirmation_during_live_meeting(self):
        """The protocol detail endpoint must not bypass live note re-confirmation."""
        self.meeting.status = "IN_PROGRESS"
        self.meeting.save(update_fields=["status", "updated_at"])
        protocol = Protocol.objects.create(meeting=self.meeting)
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("protocols:protocol_detail", args=[protocol.pk]),
            {
                "action": "agenda_note",
                "agenda_item_id": str(self.agenda_item.pk),
                "body": "<p>Detail ohne Bestätigung</p>",
            },
        )

        self.assertRedirects(response, reverse("meetings:meeting_reconfirm", args=[self.meeting.pk]))
        self.assertFalse(protocol.item_notes.filter(agenda_item=self.agenda_item).exists())

    def test_non_clerk_agenda_editor_cannot_edit_live_notes_or_results(self):
        """Agenda edit permission alone must not grant protocol-note or legal result editing."""
        self.meeting.status = "DRAFT"
        self.meeting.save(update_fields=["status", "updated_at"])
        resolution_item = AgendaItem.objects.create(
            agenda=self.meeting.agenda,
            title="Beschluss nur Protokollführung",
            item_type=AgendaItem.TYPE_RESOLUTION,
            sort_order=2,
        )
        resolution = Resolution.objects.create(
            committee=self.committee,
            title="Beschluss nur Protokollführung",
            proposal="Text",
            created_by=self.chair,
            status="PROPOSED",
        )
        ResolutionAgendaItem.objects.create(agenda_item=resolution_item, resolution=resolution)
        self.meeting.status = "IN_PROGRESS"
        self.meeting.current_agenda_item = resolution_item
        self.meeting.save(update_fields=["status", "current_agenda_item", "updated_at"])
        chair_participant = MeetingParticipant.objects.get(meeting=self.meeting, membership=self.chair_membership)
        chair_participant.attendance_status = MeetingParticipant.ATTENDANCE_PRESENT
        chair_participant.last_self_confirmed_at = timezone.now()
        chair_participant.save(update_fields=["attendance_status", "last_self_confirmed_at", "updated_at"])
        self.client.force_login(self.chair)

        note_response = self.client.post(
            reverse("protocols:agenda_item_note_update", args=[self.meeting.pk, self.agenda_item.pk]),
            {"body": "<p>Agenda-Editor-Notiz</p>"},
        )
        result_response = self.client.post(
            reverse("meetings:meeting_record_resolution_result", args=[self.meeting.pk, resolution_item.pk]),
            {
                "yes_votes": "1",
                "no_votes": "0",
                "abstentions": "0",
                "is_quorate": "on",
                "decision_text": "<p>Nicht erlaubt</p>",
            },
        )

        self.assertRedirects(note_response, reverse("meetings:meeting_live", args=[self.meeting.pk]))
        self.assertRedirects(result_response, reverse("meetings:meeting_live", args=[self.meeting.pk]))
        protocol = Protocol.objects.filter(meeting=self.meeting).first()
        self.assertFalse(protocol and protocol.item_notes.filter(agenda_item=self.agenda_item).exists())
        resolution.refresh_from_db()
        self.assertEqual(resolution.yes_votes, 0)
        self.assertEqual(resolution.decision_text, "")

    def test_external_present_participants_do_not_count_for_quorum(self):
        """Only present voting members/substitutes may influence live quorum suggestions."""
        external_user = User.objects.create_user(
            email="guest-live@example.com",
            password="testpass123",
            first_name="Gast",
            last_name="Live",
            gender="D",
        )
        external_membership = Membership.objects.create(
            user=external_user,
            committee=self.committee,
            member_type="EXTERNAL",
            start_date=date.today(),
            is_active=True,
        )
        MeetingParticipant.objects.create(
            meeting=self.meeting,
            membership=external_membership,
            participant_type=MeetingParticipant.PARTICIPANT_TYPE_EXTERNAL,
            status=MeetingParticipant.STATUS_INVITED,
            attendance_status=MeetingParticipant.ATTENDANCE_PRESENT,
            last_self_confirmed_at=timezone.now(),
        )
        other_committee = Committee.objects.create(
            name="Anderes Live-Gremium",
            committee_type="MAIN",
            total_seats=3,
        )
        other_membership = Membership.objects.create(
            user=User.objects.create_user(
                email="other-committee-live@example.com",
                password="testpass123",
                first_name="Anderes",
                last_name="Gremium",
                gender="D",
            ),
            committee=other_committee,
            member_type="REGULAR",
            start_date=date.today(),
            is_active=True,
        )
        MeetingParticipant.objects.create(
            meeting=self.meeting,
            membership=other_membership,
            participant_type=MeetingParticipant.PARTICIPANT_TYPE_INTERNAL,
            status=MeetingParticipant.STATUS_INVITED,
            attendance_status=MeetingParticipant.ATTENDANCE_PRESENT,
            last_self_confirmed_at=timezone.now(),
        )
        standalone_substitute = Membership.objects.create(
            user=User.objects.create_user(
                email="standalone-sub-live@example.com",
                password="testpass123",
                first_name="Standalone",
                last_name="Ersatz",
                gender="D",
            ),
            committee=self.committee,
            member_type="SUBSTITUTE",
            start_date=date.today(),
            is_active=True,
        )
        MeetingParticipant.objects.create(
            meeting=self.meeting,
            membership=standalone_substitute,
            participant_type=MeetingParticipant.PARTICIPANT_TYPE_SUBSTITUTE,
            status=MeetingParticipant.STATUS_INVITED,
            attendance_status=MeetingParticipant.ATTENDANCE_PRESENT,
            last_self_confirmed_at=timezone.now(),
        )
        self.meeting.status = "IN_PROGRESS"
        self.meeting.save(update_fields=["status", "updated_at"])
        participant = MeetingParticipant.objects.get(meeting=self.meeting, membership=self.membership)
        participant.attendance_status = MeetingParticipant.ATTENDANCE_PRESENT
        participant.last_self_confirmed_at = timezone.now()
        participant.save(update_fields=["attendance_status", "last_self_confirmed_at", "updated_at"])
        self.client.force_login(self.user)

        response = self.client.get(reverse("meetings:meeting_live_status", args=[self.meeting.pk]))

        self.assertContains(response, "Aktuell anwesend: 1")

    def test_resolution_result_form_uses_decision_editor_and_single_quorum_checkbox(self):
        """Live resolution recording shows Beschlussfassung and no override reason fields."""
        self.meeting.status = "DRAFT"
        self.meeting.save(update_fields=["status", "updated_at"])
        resolution_item = AgendaItem.objects.create(
            agenda=self.meeting.agenda,
            title="Beschluss TOP",
            item_type=AgendaItem.TYPE_RESOLUTION,
            sort_order=2,
        )
        resolution = Resolution.objects.create(
            committee=self.committee,
            title="Beschluss TOP",
            proposal="Text",
            created_by=self.chair,
            status="PROPOSED",
        )
        ResolutionAgendaItem.objects.create(agenda_item=resolution_item, resolution=resolution)
        self.meeting.status = "IN_PROGRESS"
        self.meeting.current_agenda_item = resolution_item
        self.meeting.save(update_fields=["status", "current_agenda_item", "updated_at"])
        participant = MeetingParticipant.objects.get(meeting=self.meeting, membership=self.membership)
        participant.last_self_confirmed_at = timezone.now()
        participant.save(update_fields=["last_self_confirmed_at", "updated_at"])
        self.client.force_login(self.user)

        response = self.client.get(reverse("meetings:meeting_live", args=[self.meeting.pk]))

        self.assertContains(response, "Beschlussfassung")
        self.assertContains(response, f'aria-label="Formatierbare Beschlussfassung zu {resolution_item.title}"')
        self.assertContains(response, ">Beschlussfähig<")
        self.assertNotContains(response, "Beschlussfähig laut Vorschlag/Prüfung")
        self.assertNotContains(response, "Beschlussfähigkeit manuell setzen")
        self.assertNotContains(response, "Begründung bei manueller Abweichung")

    def test_election_result_hx_post_returns_display_and_prefilled_edit_values(self):
        """Saved election results are shown to participants and prefilled for the clerk."""
        self.meeting.status = "DRAFT"
        self.meeting.save(update_fields=["status", "updated_at"])
        election_item = AgendaItem.objects.create(
            agenda=self.meeting.agenda,
            title="Wahl TOP",
            item_type=AgendaItem.TYPE_ELECTION,
            sort_order=2,
        )
        election = Election.objects.create(agenda_item=election_item)
        candidate = ElectionCandidate.objects.create(election=election, name="Kandidat A", sort_order=1)
        self.meeting.status = "IN_PROGRESS"
        self.meeting.current_agenda_item = election_item
        self.meeting.save(update_fields=["status", "current_agenda_item", "updated_at"])
        participant = MeetingParticipant.objects.get(meeting=self.meeting, membership=self.membership)
        participant.attendance_status = MeetingParticipant.ATTENDANCE_PRESENT
        participant.last_self_confirmed_at = timezone.now()
        participant.save(update_fields=["attendance_status", "last_self_confirmed_at", "updated_at"])
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("meetings:meeting_record_election_result", args=[self.meeting.pk, election_item.pk]),
            {
                f"candidate_{candidate.pk}": "1",
                f"elected_{candidate.pk}": "on",
                "invalid_votes": "0",
                "is_quorate": "on",
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Wahlergebnis")
        self.assertContains(response, "Kandidat A")
        self.assertContains(response, "1 Stimme")
        self.assertContains(response, 'value="1"')
        self.assertContains(response, f'id="elected-{candidate.pk}" checked')

    def test_current_agenda_item_must_belong_to_same_meeting(self):
        """A meeting cannot point to a current TOP from another meeting."""
        other_meeting = Meeting.objects.create(
            committee=self.committee,
            title="Andere Live Sitzung",
            meeting_number="2026-21",
            date=date.today() + timedelta(days=2),
            start_time=time(10, 0),
            meeting_type="ONLINE",
            location_url="https://example.com/other-live",
            created_by=self.chair,
            status="DRAFT",
        )
        foreign_item = other_meeting.agenda.items.create(title="Fremder TOP", sort_order=1)

        self.meeting.current_agenda_item = foreign_item

        with self.assertRaises(ValidationError):
            self.meeting.full_clean()
