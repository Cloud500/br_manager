"""Permission mixins for elections app."""

from typing import Optional

from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from apps.committees.models import Committee, Membership


class ElectionPermissionMixin(UserPassesTestMixin):
    """Committee-scoped permission checks for election actions."""

    required_permission: Optional[str] = None

    def test_func(self) -> bool:
        """Return whether the user has the required election permission."""
        if not self.required_permission:
            raise NotImplementedError('required_permission must be defined in subclass')

        user = self.request.user
        if user.is_superuser or user.is_staff:
            return True

        committee = self.get_committee()
        if self._user_has_permission_in_committee(user, committee, self.required_permission):
            return True

        if committee.committee_type == 'MAIN':
            betriebsausschuss = committee.subcommittees.filter(
                committee_type='COMMITTEE',
                is_active=True
            ).first()
            if betriebsausschuss:
                return self._user_has_permission_in_committee(
                    user,
                    betriebsausschuss,
                    self.required_permission
                )

        return False

    def get_committee(self) -> Committee:
        """Resolve committee from election or agenda context."""
        if hasattr(self, 'get_election'):
            election = self.get_election()
            return election.agenda.meeting.committee

        if hasattr(self, 'get_agenda'):
            agenda = self.get_agenda()
            return agenda.meeting.committee

        raise NotImplementedError('get_committee() requires get_election() or get_agenda()')

    def _user_has_permission_in_committee(
        self,
        user,
        committee: Committee,
        permission_codename: str
    ) -> bool:
        """Check whether user has permission via active committee membership."""
        memberships = Membership.objects.filter(
            user=user,
            committee=committee,
            is_active=True
        ).select_related('role')

        for membership in memberships:
            if membership.role and membership.role.permissions.filter(
                codename=permission_codename
            ).exists():
                return True
        return False

    def handle_no_permission(self):
        """Redirect unauthorized users back to the meeting when possible."""
        messages.error(self.request, 'Sie haben keine Berechtigung für diese Aktion.')
        try:
            if hasattr(self, 'get_election'):
                election = self.get_election()
                return redirect('meetings:meeting_detail', pk=election.agenda.meeting.pk)
            if hasattr(self, 'get_agenda'):
                agenda = self.get_agenda()
                return redirect('meetings:meeting_detail', pk=agenda.meeting.pk)
        except Exception:
            pass
        raise PermissionDenied('Sie haben keine Berechtigung für diese Aktion.')
