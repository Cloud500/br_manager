"""Mixins for committees app."""

from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import get_object_or_404

from apps.committees.models import Committee


class CommitteePermissionMixin(UserPassesTestMixin):
    """
    Mixin to check committee permissions with scope support.
    
    Requires 'required_permission' attribute on the view.
    Checks if user has the permission through their roles.
    
    Scope logic:
    - If user has 'committee.view_all': Can see all committees
    - Otherwise: Only committees where user is a member (or child committees)
    """
    
    required_permission = None
    
    def test_func(self) -> bool:
        """
        Test if user has required permission.
        
        Returns:
            True if user is superuser or has permission through their roles
        """
        user = self.request.user
        
        # Superuser always has access
        if user.is_superuser:
            return True
        
        # Check if required_permission is set
        if not self.required_permission:
            # If no permission is required, deny access (fail-safe)
            return False
        
        # Check if user has permission through their roles in any committee
        # User memberships give them roles, which have permissions
        from apps.committees.models import Membership
        from apps.roles.models import RolePermission
        
        # Get all active memberships for the user
        user_memberships = Membership.objects.filter(
            user=user,
            is_active=True,
            deleted_at__isnull=True
        ).select_related('role')
        
        # Check if any of the user's roles has the required permission
        for membership in user_memberships:
            if membership.role:
                # Check if this role has the required permission
                has_permission = RolePermission.objects.filter(
                    role=membership.role,
                    permission__codename=self.required_permission
                ).exists()
                
                if has_permission:
                    return True
        
        return False
    
    def has_view_all_permission(self) -> bool:
        """
        Check if user has 'committee.view_all' permission.
        
        Returns:
            True if user can see all committees regardless of membership
        """
        user = self.request.user
        
        # Superuser always has view_all
        if user.is_superuser:
            return True
        
        from apps.committees.models import Membership
        from apps.roles.models import RolePermission
        
        # Get all active memberships for the user
        user_memberships = Membership.objects.filter(
            user=user,
            is_active=True,
            deleted_at__isnull=True
        ).select_related('role')
        
        # Check if any role has 'committee.view_all' permission
        for membership in user_memberships:
            if membership.role:
                has_view_all = RolePermission.objects.filter(
                    role=membership.role,
                    permission__codename='committee.view_all'
                ).exists()
                
                if has_view_all:
                    return True
        
        return False
    
    def get_user_committees(self):
        """
        Get committees that user is a member of.
        
        Returns:
            QuerySet of Committee objects where user is an active member
        """
        from apps.committees.models import Membership
        
        user = self.request.user
        
        # Get all committees where user is an active member
        committee_ids = Membership.objects.filter(
            user=user,
            is_active=True,
            deleted_at__isnull=True
        ).values_list('committee_id', flat=True)
        
        return Committee.objects.filter(id__in=committee_ids)
    
    def get_user_committees_with_children(self):
        """
        Get committees that user is a member of, including child committees.
        
        Returns:
            QuerySet of Committee objects (user's committees + their children)
        """
        user_committees = self.get_user_committees()
        
        # Get all committee IDs (parents + children)
        committee_ids = set(user_committees.values_list('id', flat=True))
        
        # Add all children of user's committees
        for committee in user_committees:
            # Get all subcommittees (children)
            child_ids = Committee.objects.filter(
                parent=committee
            ).values_list('id', flat=True)
            committee_ids.update(child_ids)
        
        return Committee.objects.filter(id__in=committee_ids)


class CommitteeContextMixin:
    """Mixin to add committee to context."""
    
    def get_committee(self) -> Committee:
        """
        Get committee from URL kwargs.
        
        Returns:
            Committee object from committee_id or pk
        """
        committee_id = self.kwargs.get('committee_id') or self.kwargs.get('pk')
        return get_object_or_404(Committee, id=committee_id)
    
    def get_context_data(self, **kwargs):
        """Add committee to context."""
        context = super().get_context_data(**kwargs)
        if 'committee' not in context:
            context['committee'] = self.get_committee()
        return context
