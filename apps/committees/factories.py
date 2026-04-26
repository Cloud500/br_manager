"""Factories for creating committee test data."""

from datetime import date, timedelta

from factory import LazyAttribute, SubFactory, post_generation
from factory.django import DjangoModelFactory
from factory.faker import Faker

from apps.committees.models import Committee, Membership


class CommitteeFactory(DjangoModelFactory):
    """
    Factory for creating test committees.
    
    Creates realistic committee structures with proper hierarchies.
    
    Example:
        >>> main_committee = CommitteeFactory.create(committee_type='MAIN')
        >>> subcommittee = CommitteeFactory.create(
        ...     committee_type='SUBCOMMITTEE',
        ...     parent=main_committee
        ... )
    """
    
    class Meta:
        model = Committee
    
    name = Faker(
        'random_element',
        elements=[
            'Betriebsrat',
            'Gesamtbetriebsrat',
            'Konzernbetriebsrat',
        ]
    )
    committee_type = 'MAIN'
    parent = None
    description = Faker('text', max_nb_chars=200, locale='de_DE')
    is_active = True
    total_seats = Faker('random_int', min=5, max=15)
    quorum_type = 'SIMPLE_MAJORITY'
    personnel_enabled = Faker('boolean', chance_of_getting_true=50)
    substitute_logic_enabled = Faker('boolean', chance_of_getting_true=70)
    minority_gender = None
    minority_min_count = None


class MainCommitteeFactory(CommitteeFactory):
    """
    Factory for main committee (Betriebsrat).
    
    Always creates a MAIN committee without parent.
    Often includes minority gender quota configuration.
    
    Example:
        >>> br = MainCommitteeFactory.create(name='Betriebsrat Werk München')
        >>> br.committee_type
        'MAIN'
        >>> br.parent is None
        True
    """
    
    name = Faker(
        'random_element',
        elements=[
            'Betriebsrat',
            'Betriebsrat Werk Nord',
            'Betriebsrat Werk Süd',
            'Betriebsrat Zentrale',
            'Betriebsrat Produktion',
            'Gesamtbetriebsrat',
        ]
    )
    committee_type = 'MAIN'
    parent = None
    total_seats = Faker('random_int', min=7, max=15)
    substitute_logic_enabled = True
    
    @post_generation
    def set_minority_quota(self, create, extracted, **kwargs):
        """Set minority gender quota (§ 15 Abs. 2 BetrVG)."""
        if create and self.total_seats >= 5:
            # 50% chance to set minority quota
            import random
            if random.random() < 0.5:
                self.minority_gender = random.choice(['M', 'F'])
                # Minimum 1/3 of seats for minority gender
                self.minority_min_count = max(1, self.total_seats // 3)
                self.save()


class SubcommitteeFactory(CommitteeFactory):
    """
    Factory for subcommittees.
    
    Creates committees that are subordinate to a main committee.
    Automatically sets appropriate committee_type.
    
    Example:
        >>> br = MainCommitteeFactory.create()
        >>> economic = SubcommitteeFactory.create(
        ...     name='Wirtschaftsausschuss',
        ...     parent=br
        ... )
    """
    
    name = Faker(
        'random_element',
        elements=[
            'Wirtschaftsausschuss',
            'Personalausschuss',
            'Arbeitsschutzausschuss',
            'Gleichstellungsausschuss',
            'Gesundheitsausschuss',
            'Bildungsausschuss',
            'IT-Ausschuss',
            'Sozialausschuss',
        ]
    )
    committee_type = Faker(
        'random_element',
        elements=['COMMITTEE', 'SUBCOMMITTEE']
    )
    total_seats = Faker('random_int', min=3, max=9)
    # parent must be set when creating subcommittee


class MembershipFactory(DjangoModelFactory):
    """
    Factory for committee memberships.
    
    Creates realistic membership data with proper validation.
    
    Example:
        >>> committee = MainCommitteeFactory.create()
        >>> user = UserFactory.create()
        >>> membership = MembershipFactory.create(
        ...     user=user,
        ...     committee=committee,
        ...     member_type='REGULAR'
        ... )
    """
    
    class Meta:
        model = Membership
    
    # user and committee must be provided
    member_type = 'REGULAR'
    is_active = True
    start_date = LazyAttribute(
        lambda o: date.today() - timedelta(days=Faker('random_int', min=30, max=365).evaluate(None, None, {'locale': None}))
    )
    end_date = None
    
    # Election info (only for REGULAR and SUBSTITUTE)
    election_list_name = None
    election_list_position = None
    election_votes = None


class RegularMembershipFactory(MembershipFactory):
    """
    Factory for regular committee members.
    
    Includes election information (list name, position, votes).
    
    Example:
        >>> membership = RegularMembershipFactory.create(
        ...     user=user,
        ...     committee=committee
        ... )
        >>> membership.member_type
        'REGULAR'
        >>> membership.election_list_name
        'Liste 1'
    """
    
    member_type = 'REGULAR'
    election_list_name = Faker(
        'random_element',
        elements=['Liste 1', 'Liste 2', 'Liste 3', 'Gewerkschaftsliste', 'Unabhängige Liste']
    )
    election_list_position = Faker('random_int', min=1, max=15)
    election_votes = Faker('random_int', min=50, max=500)


class SubstituteMembershipFactory(MembershipFactory):
    """
    Factory for substitute members (Ersatzmitglieder).
    
    Includes election information for proper substitute logic.
    
    Example:
        >>> substitute = SubstituteMembershipFactory.create(
        ...     user=user,
        ...     committee=committee,
        ...     election_list_name='Liste 1'
        ... )
        >>> substitute.member_type
        'SUBSTITUTE'
    """
    
    member_type = 'SUBSTITUTE'
    election_list_name = Faker(
        'random_element',
        elements=['Liste 1', 'Liste 2', 'Liste 3', 'Gewerkschaftsliste', 'Unabhängige Liste']
    )
    election_list_position = Faker('random_int', min=1, max=20)
    election_votes = Faker('random_int', min=20, max=300)


class ExternalMembershipFactory(MembershipFactory):
    """
    Factory for external committee members.
    
    External members have no election information and are typically
    used for specialized subcommittees.
    
    Example:
        >>> subcommittee = SubcommitteeFactory.create(parent=main)
        >>> external = ExternalMembershipFactory.create(
        ...     user=external_expert,
        ...     committee=subcommittee
        ... )
    """
    
    member_type = 'EXTERNAL'
    election_list_name = ''
    election_list_position = None
    election_votes = None
