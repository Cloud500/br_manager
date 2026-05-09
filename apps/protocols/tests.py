"""Tests for protocol services."""

from datetime import date, time

from django.test import TestCase
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.agendas.models import AgendaItem
from apps.audit.models import AuditEntry
from apps.committees.factories import MainCommitteeFactory, RegularMembershipFactory
from apps.meetings.models import Meeting
from apps.protocols.forms import sanitize_protocol_note_html
from apps.protocols.models import Protocol, ProtocolEntry, ProtocolRevision
from apps.protocols.services import ProtocolDraftService


class ProtocolDraftServiceTest(TestCase):
    """Tests for protocol draft creation, notes and snapshots."""

    def setUp(self):
        self.actor = UserFactory.create()
        self.committee = MainCommitteeFactory.create()
        self.membership = RegularMembershipFactory.create(user=self.actor, committee=self.committee)
        self.meeting = Meeting.objects.create(
            committee=self.committee,
            title="Protokoll-Sitzung",
            date=date(2026, 5, 9),
            start_time=time(10, 0),
            meeting_type="ONLINE",
            location_url="https://example.org/protocol",
            created_by=self.actor,
            clerk=self.actor,
            status="IN_PROGRESS",
        )
        self.item = AgendaItem.objects.create(
            agenda=self.meeting.agenda,
            title="Bericht",
            description="Beschreibung zum Bericht",
            sort_order=1,
        )

    def test_update_item_note_creates_revision_and_audit_entry(self):
        """Protocol note changes are auditable and visible to loaded participants."""
        protocol = ProtocolDraftService.get_or_create_for_meeting(self.meeting, actor=self.actor)

        note = ProtocolDraftService.update_item_note(protocol, self.item, "Notiz", actor=self.actor)

        self.assertEqual(note.body, "Notiz")
        self.assertTrue(
            ProtocolRevision.objects.filter(
                protocol=protocol,
                change_type="agenda_item_note_updated",
            ).exists()
        )
        self.assertTrue(
            AuditEntry.objects.filter(
                object_id=str(protocol.pk),
                change_type="agenda_item_note_updated",
            ).exists()
        )
        self.assertIn(self.item.pk, ProtocolDraftService.visible_notes_for_user(self.meeting, self.actor))

    def test_generate_from_meeting_stores_attendance_and_agenda_snapshots(self):
        """Protocol generation snapshots meeting metadata, attendance and agenda."""
        protocol = ProtocolDraftService.generate_from_meeting(self.meeting, actor=self.actor)

        protocol.refresh_from_db()
        self.assertEqual(protocol.status, Protocol.STATUS_DRAFT)
        self.assertEqual(protocol.metadata_snapshot["meeting_id"], str(self.meeting.pk))
        self.assertEqual(protocol.agenda_snapshot[0]["title"], "Bericht")
        self.assertIn("participants", protocol.attendance_snapshot)

    def test_protocol_detail_shows_start_and_end_times_without_general_body(self):
        """Protocol detail shows concrete session times and no generic supplement block."""
        protocol = ProtocolDraftService.generate_from_meeting(self.meeting, actor=self.actor)
        self.meeting.status = "COMPLETED"
        self.meeting.actual_start_time = time(8, 31)
        self.meeting.actual_end_time = time(9, 3)
        self.meeting.end_time = time(12, 0)
        self.meeting.save(update_fields=[
            "status",
            "actual_start_time",
            "actual_end_time",
            "end_time",
            "updated_at",
        ])
        self.client.force_login(self.actor)

        response = self.client.get(reverse("protocols:protocol_detail", args=[protocol.pk]))

        self.assertContains(response, "09.05.2026 08:31 Uhr")
        self.assertContains(response, "09.05.2026 09:03 Uhr")
        self.assertNotContains(response, "01.01.1900")
        self.assertNotContains(response, "Allgemeine Ergänzungen")

    def test_protocol_list_and_detail_are_visible_to_committee_members(self):
        """Protocols are discoverable through list and detail views."""
        protocol = ProtocolDraftService.generate_from_meeting(self.meeting, actor=self.actor)
        self.client.force_login(self.actor)

        list_response = self.client.get(reverse("protocols:protocol_list"))
        detail_response = self.client.get(reverse("protocols:protocol_detail", args=[protocol.pk]))

        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, self.meeting.meeting_number)
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "Sitzung")

    def test_protocol_detail_renders_readable_sections_without_json_dump(self):
        """Protocol detail presents legal protocol sections instead of raw JSON."""
        protocol = ProtocolDraftService.generate_from_meeting(self.meeting, actor=self.actor)
        ProtocolDraftService.update_item_note(protocol, self.item, "Diskussionsergebnis", actor=self.actor)
        ProtocolEntry.objects.create(
            protocol=protocol,
            agenda_item=self.item,
            entry_type=ProtocolEntry.ENTRY_RESOLUTION,
            title="Beschluss Test",
            object_ref="resolution:test",
            data={
                "resolution_number": "20260509-001",
                "yes_votes": 3,
                "no_votes": 1,
                "abstentions": 0,
                "eligible_voters": 4,
                "status": "APPROVED",
                "is_quorate": True,
            },
        )
        self.client.force_login(self.actor)

        response = self.client.get(reverse("protocols:protocol_detail", args=[protocol.pk]))

        self.assertEqual(response.status_code, 200)
        for heading in [
            "Sitzung",
            "Teilnehmer",
            "Tagesordnung",
            "Diskussion und Maßnahmen",
            "Wahlen",
            "Beschlussfassungen",
            "Ende der Sitzung",
        ]:
            self.assertContains(response, heading)
        self.assertContains(response, "Diskussionsergebnis")
        self.assertContains(response, "1.")
        self.assertContains(response, "Beschreibung zum Bericht")
        self.assertContains(response, f'href="#top-note-{self.item.pk}"')
        self.assertContains(response, f'id="top-note-{self.item.pk}"')
        self.assertContains(response, "scroll-behavior: smooth")
        self.assertContains(response, "quill.snow.css")
        self.assertContains(response, "data-quill-editor")
        self.assertContains(response, "allowedHeaders")
        self.assertContains(response, "allowedSizes")
        self.assertContains(response, "Ja:")
        self.assertNotContains(response, "&#x27;yes_votes&#x27;")

    def test_protocol_note_sanitizer_keeps_quill_sizes_and_bullet_lists(self):
        """Quill size classes and bullet list markers survive sanitizing."""
        html = (
            '<p><span class="ql-size-large" onclick="alert(1)">Groß</span></p>'
            '<ol><li data-list="bullet"><span class="ql-ui" contenteditable="false"></span>Punkt</li></ol>'
            '<script>alert(1)</script>'
        )

        sanitized = sanitize_protocol_note_html(html)

        self.assertIn('class="ql-size-large"', sanitized)
        self.assertIn('data-list="bullet"', sanitized)
        self.assertIn('class="ql-ui"', sanitized)
        self.assertNotIn("onclick", sanitized)
        self.assertNotIn("contenteditable", sanitized)
        self.assertNotIn("script", sanitized)

    def test_protocol_detail_allows_clerk_to_edit_top_note_after_completion(self):
        """The clerk can edit TOP notes in the protocol view after completion."""
        protocol = ProtocolDraftService.generate_from_meeting(self.meeting, actor=self.actor)
        self.meeting.status = "COMPLETED"
        self.meeting.save(update_fields=["status", "updated_at"])
        self.client.force_login(self.actor)

        response = self.client.post(
            reverse("protocols:protocol_detail", args=[protocol.pk]),
            {
                "action": "agenda_note",
                "agenda_item_id": str(self.item.pk),
                "body": (
                    '<strong>Nachbearbeitete TOP-Notiz</strong>'
                    '<span class="ql-size-large">Groß</span>'
                    '<ol><li data-list="bullet">Punkt</li></ol>'
                    '<script>alert(1)</script>'
                ),
            },
        )

        self.assertRedirects(response, reverse("protocols:protocol_detail", args=[protocol.pk]))
        note_body = protocol.item_notes.get(agenda_item=self.item).body
        self.assertIn("<strong>Nachbearbeitete TOP-Notiz</strong>", note_body)
        self.assertIn('class="ql-size-large"', note_body)
        self.assertIn('data-list="bullet"', note_body)
        self.assertNotIn("script", note_body)
