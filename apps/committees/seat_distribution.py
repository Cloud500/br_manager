"""Election seat distribution helpers for committee memberships."""

from __future__ import annotations

from collections import defaultdict

from apps.committees.models import Committee, Membership


def get_election_seat_distribution(committee: Committee) -> list[dict]:
    """
    Return active regular and substitute memberships grouped by election list.

    Seat numbers are assigned across all election lists by vote count. Only the
    first ``committee.total_seats`` memberships receive a seat number; further
    memberships stay without a seat number and therefore represent substitutes.
    Rows inside each list stay ordered by their list position.
    """
    if committee.committee_type != 'MAIN':
        return []

    memberships = list(
        Membership.objects.filter(
            committee=committee,
            is_active=True,
            member_type__in=['REGULAR', 'SUBSTITUTE'],
        )
        .select_related('user', 'role')
        .order_by(
            'election_list_name',
            'election_list_position',
            '-election_votes',
            'user__last_name',
            'user__first_name',
        )
    )

    seat_numbers = {}
    ranked_memberships = sorted(
        memberships,
        key=lambda membership: (
            -(membership.election_votes or 0),
            membership.election_list_name or '',
            membership.election_list_position or 999_999,
            membership.user.last_name,
            membership.user.first_name,
        ),
    )
    for seat_number, membership in enumerate(ranked_memberships[: committee.total_seats], start=1):
        seat_numbers[membership.pk] = seat_number

    grouped = defaultdict(list)
    for membership in memberships:
        list_name = membership.election_list_name or 'Ohne Liste'
        grouped[list_name].append({
            'membership': membership,
            'seat_number': seat_numbers.get(membership.pk),
        })

    return [
        {
            'list_name': list_name,
            'rows': rows,
        }
        for list_name, rows in sorted(grouped.items(), key=lambda item: item[0].lower())
    ]
