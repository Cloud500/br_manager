"""Tests for committee election seat distribution."""

from datetime import date

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.committees.models import Committee, Membership
from apps.committees.seat_distribution import get_election_seat_distribution


class ElectionSeatDistributionTest(TestCase):
    """Tests for election result seat distribution helpers and views."""

    def setUp(self):
        """Create committee and memberships with election metadata."""
        self.admin = User.objects.create_superuser(
            email='admin@example.com',
            password='AdminPass123!',
            first_name='Admin',
            last_name='User',
            gender='M',
            two_factor_enabled=True,
        )
        self.committee = Committee.objects.create(
            name='Betriebsrat',
            committee_type='MAIN',
            total_seats=3,
            substitute_logic_enabled=True,
        )
        self.subcommittee = Committee.objects.create(
            name='Ausschuss',
            committee_type='SUBCOMMITTEE',
            parent=self.committee,
            total_seats=2,
        )

        self.member_a1 = self.create_membership('Anna', 'Ahrens', 'F', 'Liste A', 1, 90)
        self.member_a2 = self.create_membership('Anton', 'Albers', 'M', 'Liste A', 2, 70, 'SUBSTITUTE')
        self.member_b1 = self.create_membership('Berta', 'Berg', 'F', 'Liste B', 1, 100)
        self.member_b2 = self.create_membership('Bernd', 'Bauer', 'M', 'Liste B', 2, 80, 'SUBSTITUTE')
        self.member_c1 = self.create_membership('Clara', 'Cordes', 'F', 'Liste C', 1, 60, 'SUBSTITUTE')

    def create_membership(
        self,
        first_name: str,
        last_name: str,
        gender: str,
        list_name: str,
        position: int,
        votes: int,
        member_type: str = 'REGULAR',
    ) -> Membership:
        """Create a user and a committee membership."""
        user = User.objects.create_user(
            email=f'{first_name.lower()}@example.com',
            password='pass',
            first_name=first_name,
            last_name=last_name,
            gender=gender,
        )
        return Membership.objects.create(
            user=user,
            committee=self.committee,
            member_type=member_type,
            start_date=date.today(),
            election_list_name=list_name,
            election_list_position=position,
            election_votes=votes,
        )

    def test_distribution_groups_rows_by_list_and_assigns_seats_by_votes(self):
        """Rows stay in list order, while seat numbers follow highest votes."""
        distribution = get_election_seat_distribution(self.committee)

        self.assertEqual([group['list_name'] for group in distribution], ['Liste A', 'Liste B', 'Liste C'])
        self.assertEqual(
            [row['membership'] for row in distribution[0]['rows']],
            [self.member_a1, self.member_a2],
        )
        self.assertEqual(distribution[0]['rows'][0]['seat_number'], 2)
        self.assertIsNone(distribution[0]['rows'][1]['seat_number'])
        self.assertEqual(distribution[1]['rows'][0]['seat_number'], 1)
        self.assertEqual(distribution[1]['rows'][1]['seat_number'], 3)
        self.assertIsNone(distribution[2]['rows'][0]['seat_number'])

    def test_seat_distribution_view_renders_card(self):
        """The standalone committee view renders the reusable election result card."""
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse('committees:seat_distribution', kwargs={'committee_id': self.committee.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sitzverteilung nach Wahlergebnis')
        self.assertContains(response, 'Liste B')
        self.assertContains(response, 'Sitz 1')

    def test_committee_detail_links_to_seat_distribution(self):
        """The committee detail links to the distribution without embedding tables."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse('committees:committee_detail', kwargs={'pk': self.committee.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse('committees:seat_distribution', kwargs={'committee_id': self.committee.pk}),
        )
        self.assertContains(response, 'Sitzverteilung öffnen')
        self.assertNotContains(response, 'Sitz 1')

    def test_administration_overview_lists_committee_seat_cards(self):
        """The administration overview exposes reusable cards for committees."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse('committees:seat_distribution_overview'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sitzverteilung Verwaltung')
        self.assertContains(response, 'Betriebsrat')
        self.assertContains(response, 'Liste A')
        self.assertNotContains(response, 'Ausschuss')

    def test_seat_distribution_is_only_available_for_main_committees(self):
        """Committees without their own election results have no seat distribution."""
        self.client.force_login(self.admin)

        self.assertEqual(get_election_seat_distribution(self.subcommittee), [])
        response = self.client.get(
            reverse('committees:seat_distribution', kwargs={'committee_id': self.subcommittee.pk})
        )

        self.assertEqual(response.status_code, 404)
