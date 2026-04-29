"""Tests for resolutions app."""

from django.test import TestCase

from apps.accounts.factories import UserFactory
from apps.committees.factories import MainCommitteeFactory
from apps.resolutions.models import Resolution


class ResolutionModelTest(TestCase):
    """Tests for Resolution model behavior."""

    def test_can_save_multiple_draft_resolutions_with_empty_number(self):
        """Draft resolutions can share an empty resolution number."""
        committee = MainCommitteeFactory.create(can_create_resolutions=True)
        user = UserFactory.create()

        first = Resolution(
            committee=committee,
            proposal='First draft resolution',
            created_by=user,
            status='DRAFT',
        )
        first.save()

        second = Resolution(
            committee=committee,
            proposal='Second draft resolution',
            created_by=user,
            status='DRAFT',
        )
        second.save()

        self.assertEqual(Resolution.objects.filter(committee=committee).count(), 2)
