"""Custom mixins for agendas app."""

from typing import Optional
from uuid import UUID

from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from apps.committees.models import Committee, Membership


class AgendaPermissionMixin(UserPassesTestMixin):
    """
    Mixin for checking agenda-related permissions.
    
    Implements granular permission checks for agenda operations,
    including special handling for Betriebsausschuss (BA) members.
    
    Attributes:
        required_permission: Permission codename (e.g., 'agenda.edit_item_regular')
    """
    
    required_permission: Optional[str] = None
    
    def test_func(self) -> bool:
        """
        Check if user has required permission.
        
        Implements special logic for BA members: Regular MEMBER role has
        only 'agenda.view' permission, BUT if user is member of the
        Betriebsausschuss (committee_type='COMMITTEE'), they get extended
        permissions.
        
        Returns:
            True if user has permission
        """
        if not self.required_permission:
            raise NotImplementedError('required_permission must be defined in subclass')
        
        user = self.request.user
        
        # Guard clause: Superuser/Staff always have access
        if user.is_superuser or user.is_staff:
            return True
        
        # Get agenda and committee
        agenda = self.get_agenda()
        committee = agenda.meeting.committee
        
        # Standard permission check
        if self._user_has_permission_in_committee(user, committee, self.required_permission):
            return True
        
        # BA special rule (only for MAIN committees)
        if committee.committee_type == 'MAIN':
            betriebsausschuss = committee.subcommittees.filter(
                committee_type='COMMITTEE',
                is_active=True
            ).first()
            
            if betriebsausschuss:
                if self._user_has_permission_in_committee(
                    user,
                    betriebsausschuss,
                    self.required_permission
                ):
                    return True
        
        return False
    
    def _user_has_permission_in_committee(
        self,
        user,
        committee: Committee,
        permission_codename: str
    ) -> bool:
        """
        Check if user has permission via membership in committee.
        
        Args:
            user: User to check
            committee: Committee to check membership in
            permission_codename: Permission codename to check
        
        Returns:
            True if user has permission
        """
        memberships = Membership.objects.filter(
            user=user,
            committee=committee,
            is_active=True
        ).select_related('role')
        
        for membership in memberships:
            if membership.role:
                if membership.role.permissions.filter(
                    codename=permission_codename
                ).exists():
                    return True
        
        return False
    
    def get_agenda(self):
        """
        Get agenda from view context.
        
        Override this method in subclass if agenda is accessed differently.
        Default implementation assumes get_object() returns an AgendaItem.
        
        Returns:
            Agenda instance
        """
        # For item views: get agenda from item
        if hasattr(self, 'get_object'):
            obj = self.get_object()
            if hasattr(obj, 'agenda'):
                return obj.agenda
        
        # For agenda views: get agenda directly
        agenda_id = self.kwargs.get('agenda_id')
        if agenda_id:
            from .models import Agenda
            try:
                return Agenda.objects.get(pk=agenda_id)
            except Agenda.DoesNotExist:
                raise PermissionDenied('Tagesordnung nicht gefunden')
        
        raise NotImplementedError('get_agenda() must be implemented in subclass')
    
    def handle_no_permission(self):
        """Handle case when user lacks permission."""
        messages.error(
            self.request,
            'Sie haben keine Berechtigung für diese Aktion.'
        )
        
        # Try to redirect to meeting detail if possible
        try:
            agenda = self.get_agenda()
            return redirect('meetings:meeting_detail', pk=agenda.meeting.pk)
        except Exception:
            return redirect('meetings:meeting_list')
