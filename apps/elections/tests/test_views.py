"""View and permission tests for elections."""

import json
from datetime import date, time

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.agendas.models import AgendaItem
from apps.committees.factories import MainCommitteeFactory
from apps.committees.models import Membership
from apps.elections.models import Election, ElectionCandidate
from apps.meetings.models import Meeting
from apps.resolutions.models import Resolution, ResolutionAgendaItem
from apps.roles.models import Permission, Role, RolePermission


class ElectionViewTests(TestCase):
    """Tests for election views and permissions."""

    def setUp(self):
        """Create users, roles, meeting and permissions."""
        self.chair_user = UserFactory.create()
        self.member_user = UserFactory.create()
        self.committee = MainCommitteeFactory.create()
        self.chair_role = self._role('CHAIR', 'Vorsitz')
        self.member_role = self._role('MEMBER', 'Mitglied')
        self._permission('election.create', self.chair_role)
        self._permission('election.view', self.chair_role, self.member_role)
        self._permission('election.edit', self.chair_role)
        self._permission('election.delete', self.chair_role)
        self._permission('agenda.reorder_items', self.chair_role)
        self._permission('meeting.view', self.chair_role, self.member_role)
        self._membership(self.chair_user, self.chair_role)
        self._membership(self.member_user, self.member_role)
        self.meeting = Meeting.objects.create(
            committee=self.committee,
            title='Betriebsratssitzung',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://example.org/meeting',
            created_by=self.chair_user,
        )
        self.agenda = self.meeting.agenda

    def test_chair_can_create_election_from_agenda_context(self):
        """Authorized users can create election TOPs with free-text candidates."""
        self.client.force_login(self.chair_user)
        response = self.client.post(
            reverse('elections:election_create', kwargs={'agenda_id': self.agenda.pk}),
            {
                'title': 'Wahl des Vorsitzes',
                'description': '',
                'election_type': Election.ELECTION_TYPE_PERSON,
                'majority_type': Election.MAJORITY_ABSOLUTE,
                'candidates-TOTAL_FORMS': '3',
                'candidates-INITIAL_FORMS': '0',
                'candidates-MIN_NUM_FORMS': '1',
                'candidates-MAX_NUM_FORMS': '1000',
                'candidates-0-name': 'Max Mustermann',
                'candidates-1-name': '',
                'candidates-2-name': '',
            },
        )

        self.assertRedirects(response, reverse('meetings:meeting_detail', kwargs={'pk': self.meeting.pk}))
        election = Election.objects.get()
        self.assertEqual(election.agenda, self.agenda)
        self.assertEqual(election.candidates.get().name, 'Max Mustermann')

    def test_member_can_view_but_not_create_or_edit_election(self):
        """View permission does not grant preparatory write permissions."""
        election = self._election(title='Wahl des Vorsitzes')
        ElectionCandidate.objects.create(election=election, name='Max Mustermann')
        self.client.force_login(self.member_user)

        detail_response = self.client.get(reverse('elections:election_detail', kwargs={'pk': election.pk}))
        self.assertEqual(detail_response.status_code, 200)

        create_response = self.client.get(reverse('elections:election_create', kwargs={'agenda_id': self.agenda.pk}))
        self.assertEqual(create_response.status_code, 302)

        edit_response = self.client.get(reverse('elections:election_update', kwargs={'pk': election.pk}))
        self.assertEqual(edit_response.status_code, 302)

    def test_published_election_is_read_only_in_views(self):
        """Published election blocks edit/delete even for users with write permission."""
        election = self._election(title='Wahl des Vorsitzes')
        ElectionCandidate.objects.create(election=election, name='Max Mustermann')
        election.publish()
        self.client.force_login(self.chair_user)

        edit_response = self.client.get(reverse('elections:election_update', kwargs={'pk': election.pk}))
        delete_response = self.client.get(reverse('elections:election_delete', kwargs={'pk': election.pk}))

        self.assertEqual(edit_response.status_code, 403)
        self.assertEqual(delete_response.status_code, 403)

    def test_meeting_detail_hides_elections_without_election_view_permission(self):
        """Meeting visibility alone must not leak election TOP details."""
        user = UserFactory.create()
        role = self._role('NO_ELECTION_VIEW', 'Sitzungsansicht ohne Wahlrecht')
        self._permission('meeting.view', role)
        self._membership(user, role)
        regular = self._regular(title='Bericht', sort_order=1)
        election = self._election(title='Vertrauliche Wahl', sort_order=2)
        election.agenda_item.parent = regular
        election.agenda_item.save()
        self.client.force_login(user)

        response = self.client.get(reverse('meetings:meeting_detail', kwargs={'pk': self.meeting.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Vertrauliche Wahl')

    def test_reorder_blocks_published_election_changes(self):
        """Published election TOPs cannot be moved through AJAX reorder."""
        regular = self._regular(title='Bericht', sort_order=1)
        election = self._election(title='Wahl', sort_order=2)
        ElectionCandidate.objects.create(election=election, name='Max Mustermann')
        election.publish()
        self.client.force_login(self.chair_user)

        response = self.client.post(
            reverse('agendas:reorder_items', kwargs={'agenda_id': self.agenda.pk}),
            data=json.dumps({
                'item_order': [
                    {'id': str(election.agenda_item.pk), 'type': 'ELECTION', 'parent_id': None},
                    {'id': str(regular.pk), 'type': 'REGULAR', 'parent_id': None},
                ]
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        election.agenda_item.refresh_from_db()
        self.assertEqual(election.sort_order, 2)

    def test_resolution_agenda_item_requires_proposed_resolution(self):
        """Only proposed resolutions can be linked to agenda TOPs."""
        resolution = Resolution.objects.create(
            committee=self.committee,
            proposal='Entwurf',
            status='DRAFT',
            created_by=self.chair_user,
        )
        agenda_item = AgendaItem.objects.create(
            agenda=self.agenda,
            title='Beschluss-Entwurf',
            sort_order=1,
            item_type=AgendaItem.TYPE_RESOLUTION,
        )

        with self.assertRaises(ValidationError):
            ResolutionAgendaItem.objects.create(agenda_item=agenda_item, resolution=resolution)

    def test_deleting_resolution_removes_resolution_agenda_item_top(self):
        """Direct resolution deletion removes the owning agenda TOP too."""
        resolution = Resolution.objects.create(
            committee=self.committee,
            proposal='Anschaffung neuer Hardware',
            status='PROPOSED',
            created_by=self.chair_user,
        )
        agenda_item = AgendaItem.objects.create(
            agenda=self.agenda,
            title='Beschluss Hardware',
            sort_order=1,
            item_type=AgendaItem.TYPE_RESOLUTION,
        )
        ResolutionAgendaItem.objects.create(agenda_item=agenda_item, resolution=resolution)

        resolution.delete()

        self.assertFalse(AgendaItem.objects.filter(pk=agenda_item.pk).exists())

    def test_reorder_allows_draft_election_below_regular_top(self):
        """Draft elections can be nested below regular TOPs and get sub numbering."""
        regular = self._regular(title='Bericht', sort_order=1)
        election = self._election(title='Wahl', sort_order=2)
        self.client.force_login(self.chair_user)

        response = self.client.post(
            reverse('agendas:reorder_items', kwargs={'agenda_id': self.agenda.pk}),
            data=json.dumps({
                'item_order': [
                    {'id': str(regular.pk), 'type': 'REGULAR', 'parent_id': None},
                    {
                        'id': str(election.agenda_item.pk),
                        'type': 'ELECTION',
                        'parent_id': str(regular.pk),
                        'parent_type': 'REGULAR',
                    },
                ]
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        election.agenda_item.refresh_from_db()
        self.assertEqual(election.agenda_item.parent, regular)
        self.assertEqual(election.item_number, '1.1')
        self.assertEqual(response.json()['item_numbers'][str(election.agenda_item.pk)], '1.1')

    def test_reorder_allows_resolution_below_regular_top(self):
        """Resolution TOPs can be nested below regular TOPs and get sub numbering."""
        regular = self._regular(title='Bericht', sort_order=1)
        resolution = Resolution.objects.create(
            committee=self.committee,
            proposal='Anschaffung neuer Hardware',
            status='PROPOSED',
            created_by=self.chair_user,
        )
        agenda_item = AgendaItem.objects.create(
            agenda=self.agenda,
            title='Beschluss Hardware',
            sort_order=2,
            item_type=AgendaItem.TYPE_RESOLUTION,
        )
        resolution_item = ResolutionAgendaItem.objects.create(agenda_item=agenda_item, resolution=resolution)
        self.client.force_login(self.chair_user)

        response = self.client.post(
            reverse('agendas:reorder_items', kwargs={'agenda_id': self.agenda.pk}),
            data=json.dumps({
                'item_order': [
                    {'id': str(regular.pk), 'type': 'REGULAR', 'parent_id': None},
                    {
                        'id': str(agenda_item.pk),
                        'type': 'RESOLUTION',
                        'parent_id': str(regular.pk),
                        'parent_type': 'REGULAR',
                    },
                ]
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        agenda_item.refresh_from_db()
        self.assertEqual(agenda_item.parent, regular)
        self.assertEqual(resolution_item.item_number, '1.1')
        self.assertEqual(response.json()['item_numbers'][str(agenda_item.pk)], '1.1')

    def test_reorder_rejects_cycles(self):
        """AJAX reorder rejects self-parenting/cyclic TOP hierarchies."""
        regular = self._regular(title='Bericht')
        self.client.force_login(self.chair_user)

        response = self.client.post(
            reverse('agendas:reorder_items', kwargs={'agenda_id': self.agenda.pk}),
            data=json.dumps({
                'item_order': [
                    {
                        'id': str(regular.pk),
                        'type': 'REGULAR',
                        'parent_id': str(regular.pk),
                    },
                ]
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)

    def _regular(self, title='TOP', sort_order=1):
        """Create a regular agenda item."""
        return AgendaItem.objects.create(
            agenda=self.agenda,
            title=title,
            sort_order=sort_order,
            item_type=AgendaItem.TYPE_REGULAR,
        )

    def _election(self, title='Wahl', sort_order=1):
        """Create an election with linked agenda item."""
        agenda_item = AgendaItem.objects.create(
            agenda=self.agenda,
            title=title,
            sort_order=sort_order,
            item_type=AgendaItem.TYPE_ELECTION,
        )
        return Election.objects.create(agenda_item=agenda_item)

    def _role(self, codename, name):
        """Return or create a committee role."""
        role, _ = Role.objects.get_or_create(
            codename=codename,
            defaults={
                'name': name,
                'description': name,
                'role_type': 'COMMITTEE',
                'is_system_role': True,
            }
        )
        return role

    def _permission(self, codename, *roles):
        """Create permission and assign it to roles."""
        permission, _ = Permission.objects.get_or_create(
            codename=codename,
            defaults={
                'name': codename,
                'description': codename,
                'category': 'election',
            }
        )
        for role in roles:
            RolePermission.objects.get_or_create(role=role, permission=permission)
        return permission

    def _membership(self, user, role):
        """Create a committee membership with explicit election defaults."""
        return Membership.objects.create(
            user=user,
            committee=self.committee,
            role=role,
            is_active=True,
            member_type='REGULAR',
            start_date=date.today(),
            election_list_name='',
        )
