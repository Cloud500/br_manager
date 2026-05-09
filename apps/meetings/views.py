"""Views for meetings app."""

import json
import time
from datetime import date
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import close_old_connections
from django.db.models import Max, Q
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, UpdateView
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse

from apps.committees.models import Membership
from apps.meetings.forms import (
    ElectionResultForm,
    MeetingFilterForm,
    MeetingForm,
    MeetingSendInvitationForm,
    ResolutionResultForm,
)
from apps.meetings.mixins import MeetingCreatePermissionMixin, MeetingPermissionMixin
from apps.meetings.models import Meeting
from apps.meetings.services import MeetingWorkflowService
from apps.agendas.models import AgendaItem
from apps.participants.mixins import user_has_participant_permission
from apps.participants.models import MeetingParticipant
from apps.participants.services import (
    attendance_periods_by_participant,
    confirm_presence,
    current_voting_participants,
    loaded_participant_for_user,
    mark_self_left,
    mark_self_returned,
    reconfirm_presence,
    send_meeting_invitations,
    user_is_loaded_participant,
)
from apps.protocols.models import Protocol
from apps.protocols.services import ProtocolDraftService


class MeetingListView(LoginRequiredMixin, ListView):
    """List view for meetings with filtering."""
    
    model = Meeting
    template_name = 'meetings/meeting_list.html'
    context_object_name = 'meetings'
    paginate_by = 20
    
    def get_queryset(self):
        """Get filtered queryset based on filter form."""
        queryset = Meeting.objects.select_related(
            'committee', 'chair', 'clerk', 'created_by'
        ).all()
        
        # Apply filters from MeetingFilterForm
        committee = self.request.GET.get('committee')
        status = self.request.GET.get('status')
        meeting_type = self.request.GET.get('meeting_type')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if committee:
            queryset = queryset.filter(committee_id=committee)
        if status:
            queryset = queryset.filter(status=status)
        if meeting_type:
            queryset = queryset.filter(meeting_type=meeting_type)
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        
        return queryset.order_by('-date', '-start_time')
    
    def get_context_data(self, **kwargs):
        """Add filter form and grouped meetings to context."""
        context = super().get_context_data(**kwargs)
        
        # Add filter form
        context['filter_form'] = MeetingFilterForm(self.request.GET)
        
        # Group meetings by workflow status, not calendar date.
        queryset = self.get_queryset()
        context['upcoming_meetings'] = queryset.exclude(status='COMPLETED')
        context['past_meetings'] = queryset.filter(status='COMPLETED')
        
        return context


class MeetingDetailView(LoginRequiredMixin, MeetingPermissionMixin, DetailView):
    """Detail view for a single meeting."""
    
    model = Meeting
    template_name = 'meetings/meeting_detail.html'
    context_object_name = 'meeting'
    permission_required = 'view'
    
    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        
        # Add agenda permission flags
        if self.object.has_agenda:
            from apps.committees.models import Membership
            
            user = self.request.user
            committee = self.object.committee
            
            # Helper function to check permissions
            def user_has_agenda_permission(permission_codename: str) -> bool:
                """Check if user has agenda permission in committee."""
                # Guard: Superuser/staff always have permission
                if user.is_superuser or user.is_staff:
                    return True
                
                # Standard permission check in this committee
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
                
                # Special rule for MAIN committee: check BA membership
                if committee.committee_type == 'MAIN':
                    ba = committee.subcommittees.filter(
                        committee_type='COMMITTEE',
                        is_active=True
                    ).first()
                    
                    if ba:
                        ba_memberships = Membership.objects.filter(
                            user=user,
                            committee=ba,
                            is_active=True
                        ).select_related('role')
                        
                        for ba_membership in ba_memberships:
                            if ba_membership.role and ba_membership.role.permissions.filter(
                                codename=permission_codename
                            ).exists():
                                return True
                
                return False

            def user_has_resolution_permission(resolution, permission_codename: str) -> bool:
                """Check permission against the linked resolution's committee."""
                if user.is_superuser or user.is_staff:
                    return True

                memberships = Membership.objects.filter(
                    user=user,
                    committee=resolution.committee,
                    is_active=True,
                ).select_related('role')

                for membership in memberships:
                    if membership.role and membership.role.permissions.filter(
                        codename=permission_codename
                    ).exists():
                        return True

                return False

            def item_is_visible(item) -> bool:
                """Check if an agenda item may be shown in the meeting agenda."""
                item.can_view_resolution = False
                if item.item_type == 'ELECTION':
                    return context['user_can_view_election']
                if item.item_type == 'RESOLUTION':
                    try:
                        resolution = item.resolution_agenda_item.resolution
                    except Exception:
                        return False
                    item.can_view_resolution = user_has_resolution_permission(
                        resolution,
                        'resolution.view',
                    )
                    return item.can_view_resolution
                return True

            def with_visible_children(item):
                """Attach recursively filtered children for template rendering."""
                item.visible_children = [
                    with_visible_children(child)
                    for child in item.get_ordered_children()
                    if item_is_visible(child)
                ]
                return item
            
            agenda_is_editable = self.object.agenda.is_editable

            # Add permission flags to context. Agenda mutations must disappear once the meeting is completed.
            context['user_can_add_item'] = agenda_is_editable and user_has_agenda_permission('agenda.add_item_regular')
            context['user_can_add_resolution'] = agenda_is_editable and user_has_agenda_permission('agenda.add_item_resolution')
            context['user_can_add_election'] = agenda_is_editable and user_has_agenda_permission('election.create')
            context['user_can_view_election'] = user_has_agenda_permission('election.view')
            context['user_can_edit_election'] = agenda_is_editable and user_has_agenda_permission('election.edit')
            context['user_can_delete_election'] = agenda_is_editable and user_has_agenda_permission('election.delete')
            context['user_can_view_resolution'] = user_has_agenda_permission('resolution.view')
            context['user_can_edit_resolution_item'] = agenda_is_editable and user_has_agenda_permission('agenda.edit_item_resolution')
            context['user_can_delete_resolution_item'] = agenda_is_editable and user_has_agenda_permission('agenda.delete_item_resolution')
            context['user_can_edit_item'] = agenda_is_editable and user_has_agenda_permission('agenda.edit_item_regular')
            context['user_can_delete_item'] = agenda_is_editable and user_has_agenda_permission('agenda.delete_item_regular')
            context['user_can_reorder_items'] = agenda_is_editable and user_has_agenda_permission('agenda.reorder_items')
            context['agenda_items'] = [
                with_visible_children(item)
                for item in self.object.agenda.top_level_items
                if item_is_visible(item)
            ]
            visible_items = []

            def collect_visible_items(items):
                for item in items:
                    visible_items.append(item)
                    collect_visible_items(getattr(item, 'visible_children', []))

            collect_visible_items(context['agenda_items'])
            context['meeting_elections'] = [
                item.election_link
                for item in visible_items
                if item.item_type == 'ELECTION' and hasattr(item, 'election_link')
            ]
            context['meeting_resolutions'] = [
                self._resolution_with_agenda_item(item.resolution_link.resolution, item)
                for item in visible_items
                if item.item_type == 'RESOLUTION' and hasattr(item, 'resolution_link')
            ]
        else:
            # No agenda - set all permissions to False
            context['agenda_items'] = []
            context['user_can_add_item'] = False
            context['user_can_add_resolution'] = False
            context['user_can_add_election'] = False
            context['user_can_view_election'] = False
            context['user_can_edit_election'] = False
            context['user_can_delete_election'] = False
            context['user_can_view_resolution'] = False
            context['user_can_edit_resolution_item'] = False
            context['user_can_delete_resolution_item'] = False
            context['user_can_edit_item'] = False
            context['user_can_delete_item'] = False
            context['user_can_reorder_items'] = False
            context['meeting_elections'] = []
            context['meeting_resolutions'] = []
        
        # TODO: Add attendance statistics when attendance app is implemented
        # context['attendees_count'] = self.object.attendance_records.filter(status='PRESENT').count()
        participants = self.object.participants.select_related(
            'membership',
            'membership__user',
            'membership__role',
            'membership__committee',
            'substitute_membership',
            'substitute_membership__user',
            'substitute_membership__role',
            'substitute_membership__committee',
        ).order_by(
            'membership__role__sort_order',
            'membership__role__name',
            'membership__user__last_name',
            'membership__user__first_name',
        )
        if self.object.status == 'COMPLETED':
            attendance_periods = attendance_periods_by_participant(self.object)
            participants = [
                participant
                for participant in participants
                if participant.pk in attendance_periods
            ]
            for participant in participants:
                participant.attendance_periods = attendance_periods.get(participant.pk, [])
            context['participant_management_locked'] = True
        else:
            context['participant_management_locked'] = False
        context['participants'] = participants
        context['user_can_view_participants'] = user_has_participant_permission(
            self.request.user,
            self.object,
            'participant.view',
        )
        context['user_can_edit_participants'] = user_has_participant_permission(
            self.request.user,
            self.object,
            'participant.edit',
        ) and not context['participant_management_locked']
        context['user_can_mark_participant_absent'] = user_has_participant_permission(
            self.request.user,
            self.object,
            'participant.mark_absent',
        ) and not context['participant_management_locked']
        context['user_can_manage_participant_substitutes'] = user_has_participant_permission(
            self.request.user,
            self.object,
            'participant.manage_substitutes',
        ) and not context['participant_management_locked']
        context['user_can_send_participant_notifications'] = user_has_participant_permission(
            self.request.user,
            self.object,
            'participant.send_notifications',
        )
        context['user_can_reset_to_draft'] = (
            self.object.status == 'SENT'
            and (self.request.user.is_superuser or self.request.user.is_staff)
        )
        context['user_can_start_meeting'] = (
            self.object.status == 'SENT'
            and Meeting.user_can_start_meeting(self.request.user, self.object)
        )
        context['user_can_complete_meeting'] = (
            self.object.status == 'IN_PROGRESS'
            and self.object.can_complete
            and Meeting.user_can_complete_meeting(self.request.user, self.object)
        )
        context['user_can_enter_live_meeting'] = (
            self.object.status == 'IN_PROGRESS'
            and self.user_can_access_live_meeting_from_detail(self.request.user, self.object)
        )
        context['live_meeting_url'] = reverse('meetings:meeting_live', kwargs={'pk': self.object.pk})
        context['protocol'] = Protocol.objects.filter(meeting=self.object).first()
        context['can_view_protocol'] = bool(
            context['protocol']
            and (
                self.request.user.is_staff
                or self.request.user.is_superuser
                or self.object.committee.memberships.filter(user=self.request.user, is_active=True).exists()
                or _user_can_edit_protocol_notes(self.request.user, self.object)
            )
        )

        return context

    def _resolution_with_agenda_item(self, resolution, agenda_item):
        """Attach the meeting agenda item for template display."""
        resolution.agenda_item = agenda_item
        return resolution

    def user_can_access_live_meeting_from_detail(self, user, meeting: Meeting) -> bool:
        """Return whether the user can open the running live meeting."""
        if user.is_superuser or user.is_staff:
            return True
        return user_is_loaded_participant(meeting, user)


class MeetingLiveAccessMixin(LoginRequiredMixin):
    """Require meeting live access for loaded participants or privileged users."""

    def get_meeting(self) -> Meeting:
        """Return the meeting addressed by the URL."""
        if not hasattr(self, "_meeting"):
            self._meeting = get_object_or_404(
                Meeting.objects.select_related("committee", "chair", "clerk"),
                pk=self.kwargs["pk"],
            )
        return self._meeting

    def dispatch(self, request, *args, **kwargs):
        """Check live meeting access."""
        meeting = self.get_meeting()
        if not self.user_can_access_live_meeting(request.user, meeting):
            messages.error(request, "Sie sind für diese Sitzung nicht geladen.")
            return redirect("meetings:meeting_detail", pk=meeting.pk)
        return super().dispatch(request, *args, **kwargs)

    def user_can_access_live_meeting(self, user, meeting: Meeting) -> bool:
        """Return whether the user can access the live meeting."""
        if user.is_superuser or user.is_staff:
            return True
        return user_is_loaded_participant(meeting, user)


class MeetingLiveRuntimeMixin(MeetingLiveAccessMixin):
    """Require a running meeting and participant re-confirmation."""

    def user_can_access_live_meeting(self, user, meeting: Meeting) -> bool:
        """Return whether the user can access a running re-confirmed live meeting."""
        if not super().user_can_access_live_meeting(user, meeting):
            return False
        if meeting.status != "IN_PROGRESS":
            return False
        if user.is_superuser or user.is_staff:
            return True
        participant = loaded_participant_for_user(meeting, user)
        return bool(participant and participant.last_self_confirmed_at)

    def dispatch(self, request, *args, **kwargs):
        """Redirect non-running or unconfirmed access to the right workflow step."""
        if not request.user.is_authenticated:
            return super(MeetingLiveAccessMixin, self).dispatch(request, *args, **kwargs)
        meeting = self.get_meeting()
        if meeting.status != "IN_PROGRESS":
            if request.headers.get("HX-Request"):
                response = HttpResponse(status=204)
                response["HX-Redirect"] = reverse("meetings:meeting_detail", kwargs={"pk": meeting.pk})
                return response
            messages.error(request, "Live-Modus ist nur während einer laufenden Sitzung verfügbar.")
            return redirect("meetings:meeting_detail", pk=meeting.pk)
        if not self.user_can_access_live_meeting(request.user, meeting):
            if user_is_loaded_participant(meeting, request.user):
                if request.headers.get("HX-Request"):
                    response = HttpResponse(status=204)
                    response["HX-Redirect"] = reverse("meetings:meeting_reconfirm", kwargs={"pk": meeting.pk})
                    return response
                return redirect("meetings:meeting_reconfirm", pk=meeting.pk)
            messages.error(request, "Sie sind für diese Sitzung nicht geladen.")
            return redirect("meetings:meeting_detail", pk=meeting.pk)
        return super(MeetingLiveAccessMixin, self).dispatch(request, *args, **kwargs)


class MeetingLiveView(MeetingLiveRuntimeMixin, DetailView):
    """Live meeting shell with HTMX-polled fragments."""

    model = Meeting
    template_name = "meetings/meeting_live.html"
    context_object_name = "meeting"

    def get_object(self, queryset=None):
        """Return cached meeting."""
        return self.get_meeting()

    def get_context_data(self, **kwargs):
        """Add live meeting context."""
        context = super().get_context_data(**kwargs)
        meeting = self.object
        context["protocol"] = ProtocolDraftService.get_or_create_for_meeting(meeting, self.request.user)
        context["current_participant"] = loaded_participant_for_user(meeting, self.request.user)
        context.update(_live_context(meeting, self.request.user))
        return context


class MeetingReconfirmView(MeetingLiveAccessMixin, View):
    """Meeting-scoped password and 2FA re-confirmation."""

    template_name = "meetings/meeting_reconfirm.html"

    def get(self, request, *args, **kwargs):
        """Render re-confirmation form."""
        return render(request, self.template_name, {"meeting": self.get_meeting()})

    def post(self, request, *args, **kwargs):
        """Persist meeting-scoped re-confirmation."""
        meeting = self.get_meeting()
        try:
            reconfirm_presence(
                meeting,
                request.user,
                password=request.POST.get("password", ""),
                code=request.POST.get("code", "").strip(),
                use_recovery=bool(request.POST.get("use_recovery")),
            )
        except ValidationError as error:
            messages.error(request, error.messages[0])
            return render(request, self.template_name, {"meeting": meeting}, status=400)
        messages.success(request, "Sitzung wurde bestätigt.")
        return redirect("meetings:meeting_live", pk=meeting.pk)


class MeetingLivePartialView(MeetingLiveRuntimeMixin, View):
    """Render one live meeting HTMX partial."""

    partial_name = "status"
    template_name = "meetings/includes/live_status.html"

    def get(self, request, *args, **kwargs):
        """Render partial context."""
        meeting = self.get_meeting()
        context = {"meeting": meeting, **_live_context(meeting, request.user)}
        return render(request, self.template_name, context)


class MeetingLiveStatusPartialView(MeetingLivePartialView):
    """Render live status partial."""

    template_name = "meetings/includes/live_status.html"


class MeetingLiveAgendaPartialView(MeetingLivePartialView):
    """Render live agenda partial."""

    template_name = "meetings/includes/live_agenda.html"


class MeetingLiveParticipantsPartialView(MeetingLivePartialView):
    """Render live participants partial."""

    template_name = "meetings/includes/live_participants.html"


class MeetingSelfAttendanceView(MeetingLiveRuntimeMixin, View):
    """Self-service attendance action for the current user."""

    action = "present"

    def post(self, request, *args, **kwargs):
        """Persist a self-service attendance action."""
        meeting = self.get_meeting()
        try:
            if self.action == "left":
                mark_self_left(meeting, request.user)
                messages.success(request, "Sie wurden als abwesend markiert.")
            elif self.action == "returned":
                mark_self_returned(meeting, request.user)
                messages.success(request, "Sie wurden wieder als anwesend markiert.")
            else:
                confirm_presence(meeting, request.user)
                messages.success(request, "Ihre Anwesenheit wurde bestätigt.")
        except ValidationError as error:
            messages.error(request, error.messages[0])
        return redirect("meetings:meeting_live", pk=meeting.pk)


class MeetingSelfLeftView(MeetingSelfAttendanceView):
    """Mark current user absent."""

    action = "left"


class MeetingSelfReturnedView(MeetingSelfAttendanceView):
    """Mark current user present again."""

    action = "returned"


class MeetingSetCurrentAgendaItemView(MeetingLiveRuntimeMixin, View):
    """Set the current agenda item for live meeting navigation."""

    def post(self, request, *args, **kwargs):
        """Persist the current agenda item."""
        meeting = self.get_meeting()
        if not Meeting.user_can_start_meeting(request.user, meeting):
            messages.error(request, "Sie haben keine Berechtigung zur Sitzungssteuerung.")
            return redirect("meetings:meeting_live", pk=meeting.pk)
        if meeting.status != "IN_PROGRESS":
            messages.error(request, "TOP-Navigation ist nur während einer laufenden Sitzung möglich.")
            return redirect("meetings:meeting_detail", pk=meeting.pk)
        agenda_item = get_object_or_404(
            AgendaItem,
            pk=kwargs["item_pk"],
            agenda__meeting=meeting,
        )
        meeting.current_agenda_item = agenda_item
        meeting.save(update_fields=["current_agenda_item", "updated_at"])
        messages.success(request, f"Aktueller TOP: {agenda_item}.")
        if request.headers.get("HX-Request"):
            return _render_live_agenda_response(request, meeting)
        return redirect("meetings:meeting_live", pk=meeting.pk)


class MeetingRecordResolutionResultView(MeetingLiveRuntimeMixin, View):
    """Record voting results for the active resolution TOP."""

    def post(self, request, *args, **kwargs):
        """Persist resolution result from the live meeting."""
        meeting = self.get_meeting()
        if not _user_can_edit_protocol_notes(request.user, meeting):
            messages.error(request, "Nur die Protokollführung kann Beschlussergebnisse erfassen.")
            return redirect("meetings:meeting_live", pk=meeting.pk)
        agenda_item = get_object_or_404(
            AgendaItem,
            pk=kwargs["item_pk"],
            agenda__meeting=meeting,
            item_type=AgendaItem.TYPE_RESOLUTION,
        )
        try:
            resolution_link = agenda_item.resolution_agenda_item
        except Exception:
            messages.error(request, "Dieser TOP ist nicht mit einem Beschluss verknüpft.")
            return redirect("meetings:meeting_live", pk=meeting.pk)
        form = ResolutionResultForm(
            request.POST,
            quorum_suggestion=_quorum_suggestion_for_meeting(meeting),
        )
        if not form.is_valid():
            messages.error(request, "Bitte prüfen Sie die eingegebenen Beschlussdaten.")
            if request.headers.get("HX-Request"):
                return _render_live_agenda_response(request, meeting)
            return redirect("meetings:meeting_live", pk=meeting.pk)
        try:
            from apps.resolutions.services import ResolutionDecisionService

            ResolutionDecisionService.record_result(
                resolution_agenda_item=resolution_link,
                yes_votes=form.cleaned_data["yes_votes"],
                no_votes=form.cleaned_data["no_votes"],
                abstentions=form.cleaned_data["abstentions"],
                is_quorate=form.cleaned_data["is_quorate"],
                quorum_manually_overridden=form.cleaned_data["is_quorate"] != _quorum_suggestion_for_meeting(meeting),
                quorum_override_reason="",
                decision_text=form.cleaned_data["decision_text"],
                actor=request.user,
            )
        except ValidationError as error:
            messages.error(request, error.messages[0])
            if request.headers.get("HX-Request"):
                return _render_live_agenda_response(request, meeting)
            return redirect("meetings:meeting_live", pk=meeting.pk)
        messages.success(request, "Beschlussergebnis wurde im Protokoll erfasst.")
        if request.headers.get("HX-Request"):
            return _render_live_agenda_response(request, meeting)
        return redirect("meetings:meeting_live", pk=meeting.pk)


class MeetingRecordElectionResultView(MeetingLiveRuntimeMixin, View):
    """Record candidate vote results for the active election TOP."""

    def post(self, request, *args, **kwargs):
        """Persist election result from the live meeting."""
        meeting = self.get_meeting()
        if not _user_can_edit_protocol_notes(request.user, meeting):
            messages.error(request, "Nur die Protokollführung kann Wahlergebnisse erfassen.")
            return redirect("meetings:meeting_live", pk=meeting.pk)
        agenda_item = get_object_or_404(
            AgendaItem,
            pk=kwargs["item_pk"],
            agenda__meeting=meeting,
            item_type=AgendaItem.TYPE_ELECTION,
        )
        election = agenda_item.election
        form = ElectionResultForm(
            request.POST,
            candidates=election.candidates.all(),
            quorum_suggestion=_quorum_suggestion_for_meeting(meeting),
        )
        if not form.is_valid():
            messages.error(request, "Bitte prüfen Sie die eingegebenen Wahldaten.")
            if request.headers.get("HX-Request"):
                return _render_live_agenda_response(request, meeting)
            return redirect("meetings:meeting_live", pk=meeting.pk)
        try:
            from apps.elections.services import ElectionResultService

            ElectionResultService.record_result(
                election=election,
                candidate_votes=form.candidate_votes(),
                elected_candidate_ids=form.elected_candidate_ids(),
                is_quorate=form.cleaned_data["is_quorate"],
                quorum_manually_overridden=form.cleaned_data["is_quorate"] != _quorum_suggestion_for_meeting(meeting),
                quorum_override_reason="",
                invalid_votes=form.cleaned_data["invalid_votes"],
                actor=request.user,
            )
        except ValidationError as error:
            messages.error(request, error.messages[0])
            if request.headers.get("HX-Request"):
                return _render_live_agenda_response(request, meeting)
            return redirect("meetings:meeting_live", pk=meeting.pk)
        messages.success(request, "Wahlergebnis wurde im Protokoll erfasst.")
        if request.headers.get("HX-Request"):
            return _render_live_agenda_response(request, meeting)
        return redirect("meetings:meeting_live", pk=meeting.pk)



def _live_context(meeting: Meeting, user) -> dict:
    """Build context for live meeting views and partials."""
    from apps.protocols.models import Protocol

    protocol = Protocol.objects.filter(meeting=meeting).first()
    notes = ProtocolDraftService.visible_notes_for_user(meeting, user)
    eligible_voters = current_voting_participants(meeting).count()
    quorum_required = _quorum_required_count(meeting)
    quorum_suggested = eligible_voters >= quorum_required if quorum_required else eligible_voters > 0
    top_level_items = meeting.agenda.top_level_items if meeting.has_agenda else []
    agenda_items = [
        _attach_visible_children(item, notes, user, quorum_suggested=quorum_suggested)
        for item in top_level_items
        if _agenda_item_is_visible(item, user)
    ]
    participants = meeting.participants.select_related(
        "membership",
        "membership__user",
        "membership__role",
        "substitute_membership",
        "substitute_membership__user",
    ).order_by(
        "membership__role__sort_order",
        "membership__user__last_name",
        "membership__user__first_name",
    )
    return {
        "protocol": protocol,
        "agenda_items": agenda_items,
        "protocol_notes": notes,
        "participants": participants,
        "current_participant": loaded_participant_for_user(meeting, user),
        "current_agenda_item": meeting.current_agenda_item,
        "user_can_control_live_meeting": Meeting.user_can_start_meeting(user, meeting),
        "user_can_complete_live_meeting": Meeting.user_can_complete_meeting(user, meeting),
        "user_can_edit_protocol_notes": _user_can_edit_protocol_notes(user, meeting),
        "eligible_voters": eligible_voters,
        "quorum_required": quorum_required,
        "quorum_suggested": quorum_suggested,
        "live_version": _live_version_for_meeting(meeting),
    }


def _attach_visible_children(item, notes: dict, user, *, quorum_suggested: bool):
    """Attach notes and filtered children for live templates."""
    item.protocol_note = notes.get(item.pk)
    item.quorum_suggested = quorum_suggested
    item.resolution_result = None
    item.election_result = None
    if item.item_type == "RESOLUTION":
        try:
            resolution_link = item.resolution_agenda_item
            item.resolution_link = resolution_link
            item.resolution_result = resolution_link.resolution
            item.resolution_has_result = bool(
                resolution_link.resolution.yes_votes
                or resolution_link.resolution.no_votes
                or resolution_link.resolution.abstentions
                or resolution_link.resolution.decision_text
                or resolution_link.resolution.is_quorate is not None
            )
            item.resolution_quorum_checked = (
                resolution_link.resolution.is_quorate
                if resolution_link.resolution.is_quorate is not None
                else quorum_suggested
            )
        except Exception:
            item.resolution_link = None
            item.resolution_has_result = False
            item.resolution_quorum_checked = quorum_suggested
    elif item.item_type == "ELECTION":
        try:
            election = item.election
            item.election_result = getattr(election, "result", None)
            item.election_obj = election
            item.election_candidates = list(election.candidates.all())
            candidate_results = {}
            if item.election_result:
                candidate_results = {
                    result.candidate_id: result
                    for result in item.election_result.candidate_results.all()
                }
            for candidate in item.election_candidates:
                candidate_result = candidate_results.get(candidate.pk)
                candidate.result_votes = candidate_result.votes if candidate_result else 0
                candidate.result_elected = bool(candidate_result and candidate_result.elected)
            item.election_quorum_checked = (
                item.election_result.is_quorate
                if item.election_result and item.election_result.is_quorate is not None
                else quorum_suggested
            )
        except Exception:
            item.election_obj = None
            item.election_candidates = []
            item.election_quorum_checked = quorum_suggested
    item.visible_children = [
        _attach_visible_children(child, notes, user, quorum_suggested=quorum_suggested)
        for child in item.get_ordered_children()
        if _agenda_item_is_visible(child, user)
    ]
    return item


def _render_live_agenda_response(request, meeting: Meeting) -> HttpResponse:
    """Render the live agenda fragment for HTMX writes and notify sibling fragments."""
    response = render(
        request,
        "meetings/includes/live_agenda.html",
        {"meeting": meeting, **_live_context(meeting, request.user)},
    )
    response["HX-Trigger"] = json.dumps({"br-live-updated": _live_event_payload(meeting)})
    return response


def _live_event_payload(meeting: Meeting) -> dict:
    """Return client payload for live meeting change events."""
    return {
        "version": _live_version_for_meeting(meeting),
        "current_agenda_item_id": str(meeting.current_agenda_item_id or ""),
    }


def _live_version_for_meeting(meeting: Meeting) -> str:
    """Return a compact version token for live-fragment change detection."""
    timestamps = [meeting.updated_at]
    if meeting.has_agenda:
        agenda_updated = meeting.agenda.items.aggregate(latest=Max("updated_at"))["latest"]
        if agenda_updated:
            timestamps.append(agenda_updated)
    participant_updated = meeting.participants.aggregate(latest=Max("updated_at"))["latest"]
    if participant_updated:
        timestamps.append(participant_updated)
    protocol = ProtocolDraftService.get_for_meeting(meeting)
    if protocol:
        timestamps.append(protocol.updated_at)
        note_updated = protocol.item_notes.aggregate(latest=Max("updated_at"))["latest"]
        if note_updated:
            timestamps.append(note_updated)
        entry_updated = protocol.entries.aggregate(latest=Max("updated_at"))["latest"]
        if entry_updated:
            timestamps.append(entry_updated)
    current_item_id = meeting.current_agenda_item_id or ""
    return f"{max(timestamps).isoformat()}:{current_item_id}"


class MeetingLiveVersionView(MeetingLiveRuntimeMixin, View):
    """Return the latest live-change version for cheap client-side refresh checks."""

    def get(self, request, *args, **kwargs):
        """Return live version JSON without rendering all fragments."""
        meeting = self.get_meeting()
        return JsonResponse(_live_event_payload(meeting))


class MeetingLiveEventsView(MeetingLiveRuntimeMixin, View):
    """Stream live meeting version events for cross-client updates."""

    def get(self, request, *args, **kwargs):
        """Return a Server-Sent Events stream for live changes."""
        meeting = self.get_meeting()

        def event_stream():
            last_version = None
            while True:
                close_old_connections()
                live_meeting = Meeting.objects.get(pk=meeting.pk)
                version = _live_version_for_meeting(live_meeting)
                if version != last_version:
                    last_version = version
                    payload = json.dumps(_live_event_payload(live_meeting))
                    yield f"event: live-version\ndata: {payload}\n\n"
                time.sleep(1)

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


def _quorum_required_count(meeting: Meeting) -> int:
    """Return a simple statutory quorum proposal based on active regular members."""
    regular_members = Membership.objects.filter(
        committee=meeting.committee,
        member_type="REGULAR",
        is_active=True,
        deleted_at__isnull=True,
    ).count()
    return (regular_members // 2) + 1 if regular_members else 0


def _quorum_suggestion_for_meeting(meeting: Meeting) -> bool:
    """Return whether current present voting participants meet the proposed quorum."""
    required = _quorum_required_count(meeting)
    present = current_voting_participants(meeting).count()
    return present >= required if required else present > 0


def _agenda_item_is_visible(item, user) -> bool:
    """Return whether an agenda item may be shown to the user in live mode."""
    item.can_view_resolution = False
    meeting = item.agenda.meeting
    if item.item_type == "ELECTION":
        return _user_has_committee_permission(user, meeting.committee, "election.view")
    if item.item_type == "RESOLUTION":
        try:
            resolution = item.resolution_agenda_item.resolution
        except Exception:
            return False
        item.can_view_resolution = _user_has_resolution_permission(user, resolution, "resolution.view")
        return item.can_view_resolution
    return True


def _user_has_committee_permission(user, committee, permission_codename: str) -> bool:
    """Check committee role permission with BA special-case support."""
    if user.is_superuser or user.is_staff:
        return True
    memberships = Membership.objects.filter(
        user=user,
        committee=committee,
        is_active=True,
    ).select_related("role")
    for membership in memberships:
        if membership.role and membership.role.permissions.filter(codename=permission_codename).exists():
            return True
    if committee.committee_type == "MAIN":
        ba = committee.subcommittees.filter(committee_type="COMMITTEE", is_active=True).first()
        if ba:
            ba_memberships = Membership.objects.filter(
                user=user,
                committee=ba,
                is_active=True,
            ).select_related("role")
            for membership in ba_memberships:
                if membership.role and membership.role.permissions.filter(codename=permission_codename).exists():
                    return True
    return False


def _user_has_resolution_permission(user, resolution, permission_codename: str) -> bool:
    """Check permission against the linked resolution's committee."""
    if user.is_superuser or user.is_staff:
        return True
    memberships = Membership.objects.filter(
        user=user,
        committee=resolution.committee,
        is_active=True,
    ).select_related("role")
    return any(
        membership.role and membership.role.permissions.filter(codename=permission_codename).exists()
        for membership in memberships
    )


def _user_can_edit_protocol_notes(user, meeting: Meeting) -> bool:
    """Return whether the user can edit live protocol notes."""
    if user.is_superuser or user.is_staff:
        return True
    if meeting.clerk_id and meeting.clerk_id == getattr(user, "id", None):
        return True
    return False


class MeetingCreateView(LoginRequiredMixin, MeetingCreatePermissionMixin, CreateView):
    """Create view for meetings."""
    
    model = Meeting
    template_name = 'meetings/meeting_form.html'
    form_class = MeetingForm
    
    def get_form(self, form_class=None):
        """Limit committee choices to committees the user may create meetings for."""
        form = super().get_form(form_class)
        form.fields['committee'].queryset = Meeting.creatable_committees_for_user(self.request.user)
        return form
    
    def get_context_data(self, **kwargs):
        """Add committee_members to context."""
        context = super().get_context_data(**kwargs)
        if hasattr(context['form'], 'chair_candidates'):
            context['chair_candidates'] = context['form'].chair_candidates
        if hasattr(context['form'], 'clerk_candidates'):
            context['clerk_candidates'] = context['form'].clerk_candidates
        return context
    
    def form_valid(self, form):
        """Set created_by and status on new meeting."""
        form.instance.created_by = self.request.user
        form.instance.status = 'DRAFT'
        messages.success(
            self.request,
            f'Sitzung "{form.instance.title}" wurde erstellt.'
        )
        return super().form_valid(form)
    
    def get_success_url(self):
        """Redirect to meeting detail page."""
        return reverse('meetings:meeting_detail', kwargs={'pk': self.object.pk})


class MeetingUpdateView(LoginRequiredMixin, MeetingPermissionMixin, UpdateView):
    """Update view for meetings."""
    
    model = Meeting
    template_name = 'meetings/meeting_form.html'
    form_class = MeetingForm
    permission_required = 'edit'
    
    def get_context_data(self, **kwargs):
        """Add committee_members to context."""
        context = super().get_context_data(**kwargs)
        if hasattr(context['form'], 'chair_candidates'):
            context['chair_candidates'] = context['form'].chair_candidates
        if hasattr(context['form'], 'clerk_candidates'):
            context['clerk_candidates'] = context['form'].clerk_candidates
        return context
    
    def dispatch(self, request, *args, **kwargs):
        """Check if meeting is editable before allowing update."""
        meeting = self.get_object()
        if not meeting.is_editable:
            messages.error(
                request,
                'Sitzung kann nicht mehr bearbeitet werden (Status ist nicht DRAFT).'
            )
            return redirect('meetings:meeting_detail', pk=meeting.pk)
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        """Show success message on update."""
        messages.success(
            self.request,
            f'Sitzung "{form.instance.title}" wurde aktualisiert.'
        )
        return super().form_valid(form)
    
    def get_success_url(self):
        """Redirect to meeting detail page."""
        return reverse('meetings:meeting_detail', kwargs={'pk': self.object.pk})


class MeetingDeleteView(LoginRequiredMixin, MeetingPermissionMixin, DeleteView):
    """Delete view for meetings."""
    
    model = Meeting
    template_name = 'meetings/meeting_confirm_delete.html'
    permission_required = 'delete'
    success_url = reverse_lazy('meetings:meeting_list')
    
    def dispatch(self, request, *args, **kwargs):
        """Check if meeting is deletable before allowing deletion."""
        meeting = self.get_object()
        if not meeting.is_deletable:
            messages.error(
                request,
                'Nur Entwürfe können gelöscht werden.'
            )
            return redirect('meetings:meeting_detail', pk=meeting.pk)
        return super().dispatch(request, *args, **kwargs)
    
    def delete(self, request, *args, **kwargs):
        """Show success message on deletion."""
        meeting = self.get_object()
        meeting_title = meeting.title
        response = super().delete(request, *args, **kwargs)
        messages.success(
            request,
            f'Sitzung "{meeting_title}" wurde gelöscht.'
        )
        return response


class MeetingSendInvitationView(LoginRequiredMixin, MeetingPermissionMixin, FormView):
    """View for sending meeting invitations."""
    
    template_name = 'meetings/meeting_send_invitation.html'
    form_class = MeetingSendInvitationForm
    permission_required = 'send_invitation'
    
    def get_meeting(self):
        """Get meeting object from URL."""
        if not hasattr(self, '_meeting'):
            self._meeting = Meeting.objects.get(pk=self.kwargs['pk'])
        return self._meeting
    
    def get_object(self):
        """Get meeting object for permission mixin."""
        return self.get_meeting()
    
    def dispatch(self, request, *args, **kwargs):
        """Check if invitation can be sent before displaying form."""
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        meeting = self.get_meeting()
        if not meeting.can_send_invitation:
            messages.error(
                request,
                'Einladung kann nur für Entwürfe versendet werden.'
            )
            return redirect('meetings:meeting_detail', pk=meeting.pk)
        if not user_has_participant_permission(
            request.user,
            meeting,
            'participant.send_notifications',
        ):
            messages.error(
                request,
                'Sie haben keine Berechtigung zum Benachrichtigen der Teilnehmer.'
            )
            return redirect('meetings:meeting_detail', pk=meeting.pk)
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        """Add meeting to context."""
        context = super().get_context_data(**kwargs)
        meeting = self.get_meeting()
        context['meeting'] = meeting
        context['invitation_participants'] = meeting.participants.filter(
            Q(status__in=MeetingParticipant.ACTIVE_STATUSES)
            | Q(
                status=MeetingParticipant.STATUS_ABSENT,
                nachladefaehig=True,
                substitute_membership__isnull=False,
            )
        ).select_related(
            'membership',
            'membership__user',
            'membership__role',
            'membership__committee',
            'substitute_membership',
            'substitute_membership__user',
        )
        return context
    
    def form_valid(self, form):
        """Send invitation and update meeting status."""
        meeting = self.get_meeting()
        
        message = form.cleaned_data.get('message', '')
        sent_count = send_meeting_invitations(meeting, message)
        
        # Update meeting status
        meeting.status = 'SENT'
        meeting.sent_at = timezone.now()
        meeting.save()
        
        messages.success(
            self.request,
            f'Einladung für "{meeting.title}" wurde an {sent_count} Teilnehmer versendet.'
        )
        return redirect('meetings:meeting_detail', pk=meeting.pk)


class MeetingResetToDraftView(LoginRequiredMixin, DetailView):
    """View for administrators to reset a sent meeting to draft."""

    model = Meeting

    def get(self, request, *args, **kwargs):
        """Redirect GET requests to the detail page."""
        meeting = self.get_object()
        return redirect('meetings:meeting_detail', pk=meeting.pk)

    def post(self, request, *args, **kwargs):
        """Reset SENT meetings to DRAFT for staff or superusers."""
        meeting = self.get_object()

        if not (request.user.is_superuser or request.user.is_staff):
            messages.error(
                request,
                'Nur Administratoren können eine versendete Einladung zurücksetzen.'
            )
            return redirect('meetings:meeting_detail', pk=meeting.pk)

        if meeting.status != 'SENT':
            messages.error(
                request,
                'Nur Sitzungen mit versendeter Einladung können zurück auf Entwurf gesetzt werden.'
            )
            return redirect('meetings:meeting_detail', pk=meeting.pk)

        meeting.status = 'DRAFT'
        meeting.save(update_fields=['status', 'updated_at'])

        messages.success(
            request,
            f'Sitzung "{meeting.title}" wurde auf Entwurf zurückgesetzt.'
        )
        return redirect('meetings:meeting_detail', pk=meeting.pk)


class MeetingStartView(LoginRequiredMixin, MeetingPermissionMixin, DetailView):
    """View for starting a meeting."""
    
    model = Meeting
    permission_required = 'start'
    
    def get(self, request, *args, **kwargs):
        """Handle GET request (should not be used, redirect to detail)."""
        meeting = self.get_object()
        return redirect('meetings:meeting_detail', pk=meeting.pk)
    
    def post(self, request, *args, **kwargs):
        """Start the meeting."""
        meeting = self.get_object()
        
        # Check if meeting can be started
        if meeting.status != 'SENT':
            messages.error(
                request,
                'Sitzung kann nur aus dem Status SENT gestartet werden.'
            )
            return redirect('meetings:meeting_detail', pk=meeting.pk)
        
        try:
            MeetingWorkflowService.start_meeting(meeting, actor=request.user)
        except ValidationError as error:
            messages.error(request, error.messages[0])
            return redirect('meetings:meeting_detail', pk=meeting.pk)
        
        messages.success(
            request,
            f'Sitzung "{meeting.title}" wurde gestartet.'
        )
        return redirect('meetings:meeting_reconfirm', pk=meeting.pk)


class MeetingCompleteView(LoginRequiredMixin, MeetingPermissionMixin, DetailView):
    """View for completing a meeting."""
    
    model = Meeting
    permission_required = 'complete'
    
    def get(self, request, *args, **kwargs):
        """Handle GET request (should not be used, redirect to detail)."""
        meeting = self.get_object()
        return redirect('meetings:meeting_detail', pk=meeting.pk)
    
    def post(self, request, *args, **kwargs):
        """Complete the meeting."""
        meeting = self.get_object()
        
        # Check if meeting can be completed
        if not meeting.can_complete:
            messages.error(
                request,
                'Sitzung kann nur aus dem Status IN_PROGRESS abgeschlossen werden.'
            )
            return redirect('meetings:meeting_detail', pk=meeting.pk)
        
        try:
            MeetingWorkflowService.complete_meeting(meeting, actor=request.user)
        except ValidationError as error:
            messages.error(request, error.messages[0])
            return redirect('meetings:meeting_detail', pk=meeting.pk)
        
        messages.success(
            request,
            f'Sitzung "{meeting.title}" wurde abgeschlossen.'
        )
        return redirect('meetings:meeting_detail', pk=meeting.pk)


def get_committee_members_ajax(request, committee_id):
    """AJAX view to get committee members for dropdowns."""
    try:
        from apps.committees.models import Committee, Membership
        from apps.roles.models import Permission
        
        committee = get_object_or_404(Committee, pk=committee_id)
        
        # Get permissions
        is_chair_perm = Permission.objects.filter(codename='meeting.is_chair').first()
        is_clerk_perm = Permission.objects.filter(codename='meeting.is_clerk').first()
        
        # Get active memberships ordered by role sort_order
        memberships = Membership.objects.filter(
            committee=committee,
            is_active=True
        ).select_related('user', 'user__profile', 'role').prefetch_related('role__permissions').order_by('role__sort_order', 'user__last_name', 'user__first_name')
        
        # Build separate lists for chair and clerk
        chair_candidates = []
        clerk_candidates = []
        
        for m in memberships:
            member_data = {
                'id': m.user.id,
                'name': m.user.get_full_name(),
                'role': m.role.name if m.role else '',
            }
            
            # Check if role has is_chair permission
            if m.role and is_chair_perm and m.role.permissions.filter(id=is_chair_perm.id).exists():
                chair_candidates.append(member_data)
            
            # Check if role has is_clerk permission
            if m.role and is_clerk_perm and m.role.permissions.filter(id=is_clerk_perm.id).exists():
                clerk_candidates.append(member_data)
        
        return JsonResponse({
            'chair_candidates': chair_candidates,
            'clerk_candidates': clerk_candidates
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
