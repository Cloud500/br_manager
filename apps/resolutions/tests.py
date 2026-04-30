"""Tests for resolutions app."""

from datetime import date, time

from django.test import TestCase
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.agendas.forms import AgendaItemResolutionForm
from apps.agendas.models import AgendaItem
from apps.committees.factories import (
    MainCommitteeFactory,
    RegularMembershipFactory,
    SubcommitteeFactory,
)
from apps.meetings.models import Meeting
from apps.resolutions.models import Resolution
from apps.roles.models import Permission, Role, RolePermission


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


class AgendaItemResolutionFormTest(TestCase):
    """Tests for resolution TOP form behavior."""

    def setUp(self):
        self.user = UserFactory.create(is_superuser=True, is_staff=True)
        self.committee = MainCommitteeFactory.create(can_create_resolutions=True)
        self.meeting = Meeting.objects.create(
            committee=self.committee,
            title='Sitzung',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://example.org/meeting',
            created_by=self.user,
        )
        self.agenda = self.meeting.agenda

    def test_blank_title_uses_resolution_title(self):
        """An empty TOP title falls back to the resolution title."""
        resolution = Resolution.objects.create(
            committee=self.committee,
            title='Beschluss-Titel',
            proposal='Beschlusstext',
            created_by=self.user,
            status='PROPOSED',
        )

        form = AgendaItemResolutionForm(
            data={
                'resolution': str(resolution.pk),
                'title': '',
                'description': '',
                'parent': '',
            },
            agenda=self.agenda,
        )

        self.assertTrue(form.is_valid(), form.errors)
        item = form.save()
        self.assertEqual(item.title, 'Beschluss-Titel')


class AgendaItemResolutionViewTest(TestCase):
    """Tests for resolution agenda item update/delete flows."""

    def setUp(self):
        self.user = UserFactory.create(is_superuser=True, is_staff=True)
        self.client.force_login(self.user)
        self.committee = MainCommitteeFactory.create(can_create_resolutions=True)
        self.meeting = Meeting.objects.create(
            committee=self.committee,
            title='Sitzung',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://example.org/meeting',
            created_by=self.user,
        )
        self.agenda = self.meeting.agenda
        self.resolution = Resolution.objects.create(
            committee=self.committee,
            title='Beschluss-Titel',
            proposal='Beschlusstext',
            created_by=self.user,
            status='PROPOSED',
        )
        self.item = AgendaItem.objects.create(
            agenda=self.agenda,
            title='Beschluss-Titel',
            description='Alt',
            sort_order=1,
            item_type=AgendaItem.TYPE_RESOLUTION,
        )
        self.resolution.agenda_items.create(agenda_item=self.item)

    def _create_role(self, codename, permission_codenames):
        """Create a committee role with the requested permissions."""
        role = Role.objects.create(
            name=codename,
            codename=codename,
            role_type='COMMITTEE',
            is_system_role=False,
        )
        for permission_codename in permission_codenames:
            permission, _created = Permission.objects.get_or_create(
                codename=permission_codename,
                defaults={
                    'name': permission_codename,
                    'category': permission_codename.split('.')[0],
                },
            )
            RolePermission.objects.create(role=role, permission=permission)
        return role

    def test_resolution_item_update_and_delete_keep_resolution(self):
        """Resolution TOPs can be updated and deleted without deleting the resolution."""
        update_url = reverse('agendas:item_update', kwargs={'pk': self.item.pk})
        delete_url = reverse('agendas:item_delete', kwargs={'pk': self.item.pk})

        update_response = self.client.post(
            update_url,
            {
                'title': 'Neuer TOP-Titel',
                'description': 'Neue Beschreibung',
                'parent': '',
            },
        )

        self.assertEqual(update_response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(self.item.title, 'Neuer TOP-Titel')
        self.assertEqual(self.item.description, 'Neue Beschreibung')

        delete_response = self.client.post(delete_url)

        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(AgendaItem.objects.filter(pk=self.item.pk).exists())
        self.assertTrue(Resolution.objects.filter(pk=self.resolution.pk).exists())

    def test_regular_item_permissions_do_not_allow_resolution_item_update(self):
        """Regular TOP edit permissions must not allow resolution TOP updates."""
        role = self._create_role(
            'REGULAR_TOP_EDITOR',
            ['agenda.edit_item_regular'],
        )
        user = UserFactory.create()
        RegularMembershipFactory.create(user=user, committee=self.committee, role=role)
        self.client.force_login(user)

        response = self.client.post(
            reverse('agendas:item_update', kwargs={'pk': self.item.pk}),
            {
                'title': 'Unerlaubte Änderung',
                'description': 'Nicht erlaubt',
                'parent': '',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(self.item.title, 'Beschluss-Titel')
        self.assertEqual(self.item.description, 'Alt')

    def test_regular_item_permissions_do_not_allow_resolution_item_delete(self):
        """Regular TOP delete permissions must not allow resolution TOP deletion."""
        role = self._create_role(
            'REGULAR_TOP_DELETER',
            ['agenda.delete_item_regular'],
        )
        user = UserFactory.create()
        RegularMembershipFactory.create(user=user, committee=self.committee, role=role)
        self.client.force_login(user)

        response = self.client.post(reverse('agendas:item_delete', kwargs={'pk': self.item.pk}))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(AgendaItem.objects.filter(pk=self.item.pk).exists())
        self.assertTrue(Resolution.objects.filter(pk=self.resolution.pk).exists())

    def test_meeting_detail_hides_resolution_items_without_resolution_view(self):
        """Meeting detail must not leak resolution TOPs without resolution.view."""
        role = self._create_role(
            'MEETING_AGENDA_VIEWER',
            ['meeting.view', 'agenda.view'],
        )
        user = UserFactory.create()
        RegularMembershipFactory.create(user=user, committee=self.committee, role=role)
        self.client.force_login(user)

        response = self.client.get(reverse('meetings:meeting_detail', kwargs={'pk': self.meeting.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Beschluss-Titel')

    def test_meeting_detail_uses_linked_resolution_committee_for_visibility(self):
        """Main meeting must not leak subcommittee resolutions without subcommittee rights."""
        subcommittee = SubcommitteeFactory.create(
            parent=self.committee,
            can_create_resolutions=True,
        )
        sub_resolution = Resolution.objects.create(
            committee=subcommittee,
            title='Vertraulicher Ausschuss-Beschluss',
            proposal='Beschlusstext',
            created_by=self.user,
            status='PROPOSED',
            propose_to_main_committee=True,
        )
        sub_item = AgendaItem.objects.create(
            agenda=self.agenda,
            title='Vertraulicher Ausschuss-Beschluss',
            description='Nicht sichtbar',
            sort_order=2,
            item_type=AgendaItem.TYPE_RESOLUTION,
        )
        sub_resolution.agenda_items.create(agenda_item=sub_item)
        role = self._create_role(
            'MAIN_RESOLUTION_VIEWER',
            ['meeting.view', 'agenda.view', 'resolution.view'],
        )
        user = UserFactory.create()
        RegularMembershipFactory.create(user=user, committee=self.committee, role=role)
        self.client.force_login(user)

        response = self.client.get(reverse('meetings:meeting_detail', kwargs={'pk': self.meeting.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Beschluss-Titel')
        self.assertNotContains(response, 'Vertraulicher Ausschuss-Beschluss')

    def test_resolution_item_permission_allows_resolution_item_update(self):
        """The dedicated resolution TOP edit permission allows TOP metadata edits."""
        role = self._create_role(
            'RESOLUTION_TOP_EDITOR',
            ['agenda.edit_item_resolution'],
        )
        user = UserFactory.create()
        RegularMembershipFactory.create(user=user, committee=self.committee, role=role)
        self.client.force_login(user)

        response = self.client.post(
            reverse('agendas:item_update', kwargs={'pk': self.item.pk}),
            {
                'title': 'Erlaubte Änderung',
                'description': 'Erlaubt',
                'parent': '',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(self.item.title, 'Erlaubte Änderung')
        self.assertEqual(self.item.description, 'Erlaubt')

    def test_resolution_item_permission_allows_resolution_item_delete(self):
        """The dedicated resolution TOP delete permission deletes only the TOP link."""
        role = self._create_role(
            'RESOLUTION_TOP_DELETER',
            ['agenda.delete_item_resolution'],
        )
        user = UserFactory.create()
        RegularMembershipFactory.create(user=user, committee=self.committee, role=role)
        self.client.force_login(user)

        response = self.client.post(reverse('agendas:item_delete', kwargs={'pk': self.item.pk}))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(AgendaItem.objects.filter(pk=self.item.pk).exists())
        self.assertTrue(Resolution.objects.filter(pk=self.resolution.pk).exists())
