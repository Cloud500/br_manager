"""Custom mixins for meetings app."""

from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect
from django.urls import reverse


class MeetingPermissionMixin(UserPassesTestMixin):
    """Mixin for checking meeting-related permissions."""
    
    permission_required = None  # Override in subclass
    
    def test_func(self):
        """Check if user has required permission."""
        if not self.permission_required:
            raise NotImplementedError('permission_required must be defined in subclass')
        
        meeting = self.get_object()
        user = self.request.user
        
        # Import Meeting model
        from apps.meetings.models import Meeting
        
        # Permission mapping
        permission_map = {
            'view': Meeting.user_can_view_meeting,
            'edit': lambda u, m: m.is_editable,
            'delete': lambda u, m: m.is_deletable,
            'send_invitation': Meeting.user_can_send_invitation,
            'start': Meeting.user_can_start_meeting,
            'complete': Meeting.user_can_complete_meeting,
        }
        
        check_func = permission_map.get(self.permission_required)
        if not check_func:
            return False
        
        return check_func(user, meeting)
    
    def handle_no_permission(self):
        """Handle case when user lacks permission."""
        messages.error(
            self.request,
            'Sie haben keine Berechtigung für diese Aktion.'
        )
        return redirect('meetings:meeting_list')


class MeetingCreatePermissionMixin(UserPassesTestMixin):
    """Mixin for checking meeting creation permission."""
    
    def test_func(self):
        """Check if user can create meetings."""
        user = self.request.user
        committee = self.get_committee()
        
        # Import Meeting model
        from apps.meetings.models import Meeting
        
        return Meeting.user_can_create(user, committee)
    
    def get_committee(self):
        """Get committee from request (override in subclass if needed)."""
        from apps.committees.models import Committee
        
        committee_id = self.request.GET.get('committee') or self.request.POST.get('committee')
        if committee_id:
            try:
                return Committee.objects.get(pk=committee_id)
            except Committee.DoesNotExist:
                pass
        return None
    
    def handle_no_permission(self):
        """Handle case when user lacks permission."""
        messages.error(
            self.request,
            'Sie haben keine Berechtigung, Sitzungen für dieses Gremium zu erstellen.'
        )
        return redirect('meetings:meeting_list')
