"""Mixins for committees app."""

from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import get_object_or_404

from apps.committees.models import Committee


class CommitteePermissionMixin(UserPassesTestMixin):
    """
    Mixin to check committee permissions.
    
    Requires 'required_permission' attribute on the view.
    """
    
    required_permission = None
    
    def test_func(self) -> bool:
        """
        Test if user has required permission.
        
        Returns:
            True if user is superuser or staff (TODO: implement proper permission check)
        """
        user = self.request.user
        
        # Superuser always has access
        if user.is_superuser:
            return True
        
        # Staff has access (TODO: Later implement proper role/permission checking)
        if user.is_staff:
            return True
        
        return False


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
