"""Permission mixins for participants app."""

from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect


class ParticipantPermissionMixin(UserPassesTestMixin):
    """Check meeting-scoped participant permissions."""

    permission_required = None

    def test_func(self) -> bool:
        """Return whether the current user has the required permission."""
        if not self.permission_required:
            return False

        participant = self.get_object()
        return user_has_participant_permission(
            self.request.user,
            participant.meeting,
            self.permission_required,
        )

    def handle_no_permission(self):
        """Redirect users without permission to the meeting detail."""
        messages.error(
            self.request,
            "Sie haben keine Berechtigung für diese Teilnehmeraktion.",
        )
        try:
            participant = self.get_object()
        except Exception:
            return redirect("meetings:meeting_list")
        return redirect("meetings:meeting_detail", pk=participant.meeting.pk)


def user_has_participant_permission(user, meeting, permission_codename: str) -> bool:
    """Check custom RBAC permission in the meeting committee."""
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True

    from apps.committees.models import Membership

    memberships = Membership.objects.filter(
        user=user,
        committee=meeting.committee,
        is_active=True,
        deleted_at__isnull=True,
    ).select_related("role")

    for membership in memberships:
        if membership.role and membership.role.permissions.filter(
            codename=permission_codename,
        ).exists():
            return True

    return False
