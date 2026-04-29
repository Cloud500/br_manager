"""Tests for resolutions app."""

from django.test import TestCase
from django.urls import reverse

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


class ResolutionCreateViewTest(TestCase):
    """Tests for resolution creation view."""

    def setUp(self):
        self.user = UserFactory.create(is_superuser=True, is_staff=True)
        self.client.force_login(self.user)
        self.committee = MainCommitteeFactory.create(can_create_resolutions=True)
        self.url = reverse('resolutions:resolution_create')

    def test_superuser_can_create_multiple_draft_resolutions(self):
        """A superuser can create multiple draft resolutions for one committee."""
        payload = {
            'committee': str(self.committee.pk),
            'proposal': 'Draft resolution',
            'justification': '',
            'propose_to_main_committee': '',
        }

        first_response = self.client.post(self.url, payload)
        second_response = self.client.post(self.url, payload)

        self.assertEqual(first_response.status_code, 302)
        self.assertEqual(second_response.status_code, 302)
        self.assertEqual(
            Resolution.objects.filter(committee=self.committee).count(),
            2,
        )

    def test_main_committee_without_resolution_flag_returns_form_error(self):
        """Invalid main committee selection renders a form error instead of a 500."""
        committee = MainCommitteeFactory.create(can_create_resolutions=False)
        payload = {
            'committee': str(committee.pk),
            'proposal': 'Draft resolution',
            'justification': '',
            'propose_to_main_committee': '',
        }

        response = self.client.post(self.url, payload)

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'],
            'committee',
            'Dieses Gremium darf keine Beschlüsse erstellen',
        )
        self.assertFalse(Resolution.objects.filter(committee=committee).exists())
