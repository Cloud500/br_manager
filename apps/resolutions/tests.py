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
            title='First draft resolution',
            proposal='First draft resolution',
            created_by=user,
            status='DRAFT',
        )
        first.save()

        second = Resolution(
            committee=committee,
            title='Second draft resolution',
            proposal='Second draft resolution',
            created_by=user,
            status='DRAFT',
        )
        second.save()

        self.assertEqual(Resolution.objects.filter(committee=committee).count(), 2)

    def test_resolution_str_uses_title(self):
        """Resolution string representation includes the title."""
        committee = MainCommitteeFactory.create(can_create_resolutions=True)
        user = UserFactory.create()

        resolution = Resolution.objects.create(
            committee=committee,
            title='Neuer Beschluss',
            proposal='Beschlusstext',
            created_by=user,
            status='DRAFT',
        )

        self.assertEqual(str(resolution), 'Entwurf - Neuer Beschluss')


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
            'title': 'Neuer Beschluss',
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

    def test_create_view_accepts_title(self):
        """The create view persists the submitted title."""
        payload = {
            'committee': str(self.committee.pk),
            'title': 'Titel aus dem Formular',
            'proposal': 'Draft resolution',
            'justification': '',
            'propose_to_main_committee': '',
        }

        response = self.client.post(self.url, payload)

        self.assertEqual(response.status_code, 302)
        resolution = Resolution.objects.latest('created_at')
        self.assertEqual(resolution.title, 'Titel aus dem Formular')

    def test_main_committee_without_resolution_flag_returns_form_error(self):
        """Invalid main committee selection renders a form error instead of a 500."""
        committee = MainCommitteeFactory.create(can_create_resolutions=False)
        payload = {
            'committee': str(committee.pk),
            'title': 'Draft resolution',
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
