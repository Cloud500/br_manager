"""Tests for meeting actual start/end date-time handling."""

from datetime import date, time, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models import User
from apps.committees.models import Committee
from apps.meetings.models import Meeting


class MeetingActualTimesTest(TestCase):
    """Test actual date/time validation and duration calculations."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="actual-times@example.com",
            password="testpass123",
            first_name="Actual",
            last_name="Times",
            gender="F",
        )
        cls.committee = Committee.objects.create(
            name="BR Actual Times",
            committee_type="MAIN",
            total_seats=5,
        )

    def _meeting(self, **overrides):
        values = {
            "committee": self.committee,
            "title": "Sitzung über Mitternacht",
            "meeting_number": "2026-01",
            "date": date(2026, 5, 10),
            "start_time": time(23, 0),
            "meeting_type": "ONLINE",
            "location_url": "https://example.com/meeting",
            "created_by": self.user,
            "status": "COMPLETED",
            "actual_start_date": date(2026, 5, 10),
            "actual_start_time": time(23, 30),
            "actual_end_date": date(2026, 5, 11),
            "actual_end_time": time(0, 30),
        }
        values.update(overrides)
        return Meeting(**values)

    def test_actual_end_time_can_be_on_next_calendar_day(self):
        """Actual end validation compares dates and times together."""
        self._meeting().full_clean()

    def test_actual_end_time_still_must_be_after_start_on_same_day(self):
        """Same-day actual end must still be after actual start."""
        meeting = self._meeting(actual_end_date=date(2026, 5, 10))

        with self.assertRaises(ValidationError) as context:
            meeting.full_clean()

        self.assertIn("actual_end_time", context.exception.message_dict)

    def test_actual_duration_uses_actual_dates(self):
        """Actual duration includes time across the calendar boundary."""
        self.assertEqual(self._meeting().get_actual_duration(), timedelta(hours=1))
