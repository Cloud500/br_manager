"""Template tags and filters for committee permissions."""

from django import template
from django.contrib.auth import get_user_model

from apps.committees.models import Membership
from apps.roles.models import RolePermission

register = template.Library()

User = get_user_model()


@register.filter
def has_committee_permission(user, permission_codename):
    """
    Check if user has a specific committee permission.
    
    Usage in template:
        {% if user|has_committee_permission:"committee.edit" %}
    
    Args:
        user: User instance
        permission_codename: Permission codename (e.g., 'committee.edit')
    
    Returns:
        True if user has the permission through any of their roles
    """
    if not user or not user.is_authenticated:
        return False
    
    # Superuser always has all permissions
    if user.is_superuser:
        return True
    
    # Get all active memberships for the user
    user_memberships = Membership.objects.filter(
        user=user,
        is_active=True,
        deleted_at__isnull=True
    ).select_related('role')
    
    # Check if any of the user's roles has the required permission
    for membership in user_memberships:
        if membership.role:
            has_permission = RolePermission.objects.filter(
                role=membership.role,
                permission__codename=permission_codename
            ).exists()
            
            if has_permission:
                return True
    
    return False


@register.filter
def has_committee_permission_for(user, args):
    """
    Check if user has permission for a specific committee.
    
    Usage in template:
        {% if user|has_committee_permission_for:"committee.edit,committee_id" %}
    
    Args:
        user: User instance
        args: String with format "permission_codename,committee_id"
    
    Returns:
        True if user has the permission for this specific committee
    """
    if not user or not user.is_authenticated:
        return False
    
    # Superuser always has all permissions
    if user.is_superuser:
        return True
    
    try:
        permission_codename, committee_id = args.split(',')
        committee_id = committee_id.strip()
        permission_codename = permission_codename.strip()
    except ValueError:
        return False
    
    # Get memberships for this specific committee
    user_memberships = Membership.objects.filter(
        user=user,
        committee_id=committee_id,
        is_active=True,
        deleted_at__isnull=True
    ).select_related('role')
    
    # Check if any role in this committee has the permission
    for membership in user_memberships:
        if membership.role:
            has_permission = RolePermission.objects.filter(
                role=membership.role,
                permission__codename=permission_codename
            ).exists()
            
            if has_permission:
                return True
    
    return False


@register.simple_tag
def user_can_manage_members(user, committee):
    """
    Check if user can manage members for a specific committee.
    
    Usage in template:
        {% user_can_manage_members user committee as can_manage %}
        {% if can_manage %}...{% endif %}
    
    Args:
        user: User instance
        committee: Committee instance
    
    Returns:
        True if user has 'committee.manage_members' permission for this committee
    """
    if not user or not user.is_authenticated:
        return False
    
    # Superuser always has all permissions
    if user.is_superuser:
        return True
    
    # Get memberships for this specific committee
    user_memberships = Membership.objects.filter(
        user=user,
        committee=committee,
        is_active=True,
        deleted_at__isnull=True
    ).select_related('role')
    
    # Check if any role in this committee has manage_members permission
    for membership in user_memberships:
        if membership.role:
            has_permission = RolePermission.objects.filter(
                role=membership.role,
                permission__codename='committee.manage_members'
            ).exists()
            
            if has_permission:
                return True
    
    return False
