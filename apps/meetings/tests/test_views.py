"""Tests for meeting workflow views."""

from datetime import date, time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.committees.models import Committee
from apps.meetings.models import Meeting


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
