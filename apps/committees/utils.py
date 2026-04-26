"""Helper functions for committees app."""

from typing import Optional

from django.db.models import QuerySet

from apps.committees.models import Committee, Membership
from apps.roles.models import Role


def get_substitute_suggestions(
    absent_member: Membership,
    meeting: Optional[object] = None
) -> QuerySet:
    """
    Get substitute member suggestions for absent member.
    
    Algorithm:
    1. Check if substitute logic is enabled
    2. Filter by same election list
    3. Sort by position and votes
    4. Consider minority gender quota
    5. TODO: Check availability in calendar
    
    Args:
        absent_member: Membership of absent member
        meeting: Optional meeting object for availability check
    
    Returns:
        QuerySet of suggested substitute memberships
    """
    committee = absent_member.committee
    
    # Check if substitute logic is enabled
    if not committee.substitute_logic_enabled:
        return Membership.objects.none()
    
    # Get substitutes from same election list
    substitutes = Membership.objects.filter(
        committee=committee,
        member_type='SUBSTITUTE',
        is_active=True,
        election_list_name=absent_member.election_list_name
    ).select_related('user', 'role')
    
    # Check minority gender quota
    if committee.minority_gender and committee.minority_min_count:
        # Count current minority gender members
        current_minority_count = committee.get_active_members().filter(
            user__gender=committee.minority_gender
        ).count()
        
        # If below quota, prioritize minority gender substitutes
        if current_minority_count < committee.minority_min_count:
            substitutes = substitutes.order_by(
                # Minority gender first
                f'-user__gender={committee.minority_gender}',
                'election_list_position',
                '-election_votes'
            )
        else:
            # Normal sorting
            substitutes = substitutes.order_by(
                'election_list_position',
                '-election_votes'
            )
    else:
        # Normal sorting
        substitutes = substitutes.order_by(
            'election_list_position',
            '-election_votes'
        )
    
    # TODO: Filter by availability (calendar integration in later phase)
    
    return substitutes


def check_external_member_access(user: 'User', resource: object) -> bool:
    """
    Check if external member has access to resource.
    
    Rules:
    - Superuser/staff always have access
    - Non-external members have access
    - External members only have access to their committee's resources
    
    Args:
        user: User to check access for
        resource: Resource object with 'committee' attribute
    
    Returns:
        True if user has access, False otherwise
    """
    # Superuser and staff always have access
    if user.is_superuser or user.is_staff:
        return True
    
    # Get user's memberships
    memberships = Membership.objects.filter(
        user=user,
        is_active=True
    ).select_related('committee')
    
    # Check if user is external member
    external_memberships = memberships.filter(member_type='EXTERNAL')
    
    # If not external, has access
    if not external_memberships.exists():
        return True
    
    # External members only have access to their committee
    if hasattr(resource, 'committee'):
        user_committees = external_memberships.values_list('committee', flat=True)
        return resource.committee.id in user_committees
    
    return False


def suggest_default_role(member_type: str) -> Optional[Role]:
    """
    Suggest default role based on member type.
    
    Args:
        member_type: Type of membership (REGULAR, SUBSTITUTE, EXTERNAL)
    
    Returns:
        Suggested Role object or None
    """
    role_mapping = {
        'REGULAR': 'MEMBER',
        'SUBSTITUTE': 'SUBSTITUTE',
        'EXTERNAL': 'EXTERNAL_MEMBER',
    }
    
    codename = role_mapping.get(member_type)
    if not codename:
        return None
    
    try:
        return Role.objects.get(codename=codename)
    except Role.DoesNotExist:
        return None
