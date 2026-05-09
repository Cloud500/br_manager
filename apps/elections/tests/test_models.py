"""Model tests for elections."""

from datetime import date, time

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.factories import UserFactory
from apps.agendas.models import AgendaItem
from apps.committees.factories import MainCommitteeFactory, RegularMembershipFactory
from apps.elections.models import Election, ElectionCandidate, ElectionResult
from apps.elections.services import ElectionResultService
from apps.meetings.models import Meeting
from apps.participants.models import MeetingParticipant
from apps.protocols.models import ProtocolEntry


class ElectionModelTests(TestCase):
    """Tests for election model behavior."""

    def setUp(self):
        """Create shared committee, meeting and agenda."""
        self.user = UserFactory.create()
        self.committee = MainCommitteeFactory.create()
        self.meeting = Meeting.objects.create(
            committee=self.committee,
            title='Betriebsratssitzung',
            date=date.today(),
            start_time=time(10, 0),
            meeting_type='ONLINE',
            location_url='https://example.org/meeting',
            created_by=self.user,
        )
        self.agenda = self.meeting.agenda

    def test_election_is_dedicated_agenda_item_with_candidates(self):
        """Election stores Wahl-specific data and free-text candidates."""
        election = self._election(title='Wahl des Vorsitzes', majority_type=Election.MAJORITY_ABSOLUTE)
        candidate = ElectionCandidate.objects.create(election=election, name='Max Mustermann')

        election.refresh_from_db()
        self.assertEqual(election.agenda_item.item_type, AgendaItem.TYPE_ELECTION)
        self.assertEqual(election.agenda_item.get_type_display(), 'Wahl')
        self.assertEqual(election.election_type, Election.ELECTION_TYPE_PERSON)
        self.assertEqual(candidate.name, 'Max Mustermann')
        self.assertFalse(hasattr(candidate, 'user_id'))

    def test_publish_requires_candidate_and_makes_election_read_only(self):
        """Published elections cannot be edited, deleted, or changed through candidates."""
        election = self._election(title='Wahl des Vorsitzes', majority_type=Election.MAJORITY_RELATIVE)

        with self.assertRaises(ValidationError):
            election.publish()

        candidate = ElectionCandidate.objects.create(election=election, name='Erika Musterfrau')
        election.publish()
        election.refresh_from_db()
        self.assertEqual(election.status, Election.STATUS_PUBLISHED)
        self.assertFalse(election.is_editable)
        self.assertFalse(election.is_deletable)

        election.agenda_item.title = 'Geänderter Titel'
        with self.assertRaises(ValidationError):
            election.agenda_item.save()

        candidate.name = 'Neue Person'
        with self.assertRaises(ValidationError):
            candidate.save()

        with self.assertRaises(ValidationError):
            election.delete()

    def test_agenda_counts_and_numbers_all_top_types(self):
        """Regular TOPs and election TOPs share agenda numbering."""
        AgendaItem.objects.create(
            agenda=self.agenda,
            title='Begrüßung',
            sort_order=1,
            item_type=AgendaItem.TYPE_REGULAR,
        )
        election = self._election(title='Wahl des Vorsitzes', sort_order=2)

        self.assertEqual(self.agenda.item_count, 2)
        election.agenda_item.refresh_from_db()
        self.assertEqual(election.item_number, '2')
        self.assertEqual([item.title for item in self.agenda.top_level_items], ['Begrüßung', 'Wahl des Vorsitzes'])

    def test_deleting_election_cascades_candidates(self):
        """Deleting a draft election deletes its free-text candidates."""
        election = self._election(title='Wahl')
        ElectionCandidate.objects.create(election=election, name='Max Mustermann')

        election.delete()

        self.assertFalse(ElectionCandidate.objects.exists())

    def test_parent_top_with_published_election_child_cannot_be_deleted(self):
        """Deleting a parent TOP must not cascade-delete a published election."""
        parent = AgendaItem.objects.create(
            agenda=self.agenda,
            title='Wahlblock',
            sort_order=1,
            item_type=AgendaItem.TYPE_REGULAR,
        )
        election = self._election(title='Wahl des Vorsitzes', sort_order=2)
        election.agenda_item.parent = parent
        election.agenda_item.save()
        ElectionCandidate.objects.create(election=election, name='Max Mustermann')
        election.publish()

        with self.assertRaises(ValidationError):
            parent.delete()

        self.assertTrue(Election.objects.filter(pk=election.pk).exists())

    def test_record_result_persists_candidate_results_and_protocol_entry(self):
        """Election results are stored separately and mirrored to protocol."""
        membership = RegularMembershipFactory.create(user=self.user, committee=self.committee)
        self.meeting.status = "IN_PROGRESS"
        self.meeting.save(update_fields=["status", "updated_at"])
        participant, _created = MeetingParticipant.objects.get_or_create(
            meeting=self.meeting,
            membership=membership,
        )
        participant.attendance_status = MeetingParticipant.ATTENDANCE_PRESENT
        participant.save(update_fields=["attendance_status", "updated_at"])
        election = self._election(title='Wahl des Vorsitzes')
        candidate = ElectionCandidate.objects.create(election=election, name='Max Mustermann')
        election.publish()

        with self.assertRaises(ValidationError):
            ElectionResultService.record_result(
                election=election,
                candidate_votes={candidate.pk: 2},
                elected_candidate_ids={candidate.pk},
                is_quorate=True,
                actor=self.user,
            )

        self.meeting.current_agenda_item = election.agenda_item
        self.meeting.save(update_fields=["current_agenda_item", "updated_at"])
        result = ElectionResultService.record_result(
            election=election,
            candidate_votes={str(candidate.pk): 1},
            elected_candidate_ids={candidate.pk},
            is_quorate=True,
            quorum_manually_overridden=True,
            quorum_override_reason='Manuelle Prüfung',
            actor=self.user,
        )

        self.assertIsInstance(result, ElectionResult)
        self.assertEqual(result.candidate_results.get(candidate=candidate).votes, 1)
        self.assertTrue(result.candidate_results.get(candidate=candidate).elected)
        entry = ProtocolEntry.objects.get(object_ref=f"election:{election.pk}")
        self.assertEqual(entry.entry_type, ProtocolEntry.ENTRY_ELECTION)
        self.assertEqual(entry.data["candidate_results"][0]["votes"], 1)

    def _election(self, title='Wahl', sort_order=1, majority_type=Election.MAJORITY_ABSOLUTE):
        """Create an election with its linked agenda item."""
        agenda_item = AgendaItem.objects.create(
            agenda=self.agenda,
            title=title,
            sort_order=sort_order,
            item_type=AgendaItem.TYPE_ELECTION,
        )
        return Election.objects.create(
            agenda_item=agenda_item,
            majority_type=majority_type,
        )
