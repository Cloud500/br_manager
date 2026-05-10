"""Views for protocol draft actions."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, FormView, ListView

from apps.agendas.models import AgendaItem
from apps.meetings.models import Meeting
from apps.meetings.views import MeetingLiveRuntimeMixin, _render_live_agenda_response, _user_can_edit_protocol_notes
from apps.participants.models import MeetingParticipant
from apps.participants.services import attendance_periods_by_participant, loaded_participant_for_user
from apps.protocols.forms import ProtocolAgendaItemNoteForm, ProtocolBodyForm
from apps.protocols.models import Protocol, ProtocolEntry
from apps.protocols.services import ProtocolDraftService


class ProtocolListView(LoginRequiredMixin, ListView):
    """List protocols visible to the current user."""

    model = Protocol
    template_name = "protocols/protocol_list.html"
    context_object_name = "protocols"
    paginate_by = 20

    def get_queryset(self):
        """Return protocols for committees the user can access."""
        queryset = Protocol.objects.select_related("meeting", "meeting__committee", "updated_by")
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return queryset
        return queryset.filter(
            Q(meeting__committee__memberships__user=user, meeting__committee__memberships__is_active=True)
            | Q(meeting__clerk=user)
            | Q(meeting__chair=user)
        ).distinct()


class ProtocolDetailView(LoginRequiredMixin, DetailView):
    """Show and edit a protocol draft/final document."""

    model = Protocol
    template_name = "protocols/protocol_detail.html"
    context_object_name = "protocol"

    def dispatch(self, request, *args, **kwargs):
        """Require committee membership or privileged access."""
        protocol = self.get_object()
        user = request.user
        if not (
            user.is_staff
            or user.is_superuser
            or protocol.meeting.clerk_id == user.id
            or protocol.meeting.chair_id == user.id
            or protocol.meeting.committee.memberships.filter(user=user, is_active=True).exists()
        ):
            messages.error(request, "Sie haben keine Berechtigung zur Anzeige dieses Protokolls.")
            return redirect("protocols:protocol_list")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Add readable protocol sections instead of raw snapshot JSON."""
        context = super().get_context_data(**kwargs)
        protocol = self.object
        agenda_items = self._agenda_items_for_protocol(protocol)
        participant_context = self._participant_context(protocol.meeting)
        context["body_form"] = ProtocolBodyForm(initial={"body": protocol.body})
        context["can_edit_protocol"] = _user_can_edit_protocol_notes(self.request.user, protocol.meeting) and protocol.is_editable
        context["agenda_items"] = agenda_items
        context["discussion_items"] = agenda_items
        context["meeting_start_display"] = self._meeting_start_display(protocol.meeting)
        context["meeting_end_display"] = self._meeting_end_display(protocol.meeting)
        context.update(participant_context)
        context["election_entries"] = self._result_entries(protocol, ProtocolEntry.ENTRY_ELECTION)
        context["resolution_entries"] = self._result_entries(protocol, ProtocolEntry.ENTRY_RESOLUTION)
        return context

    def post(self, request, *args, **kwargs):
        """Update editable protocol text or one TOP note."""
        self.object = self.get_object()
        if not _user_can_edit_protocol_notes(request.user, self.object.meeting):
            messages.error(request, "Nur die Protokollführung kann das Protokoll bearbeiten.")
            return redirect("protocols:protocol_detail", pk=self.object.pk)
        if self._live_reconfirmation_required(request.user, self.object.meeting):
            return redirect("meetings:meeting_reconfirm", pk=self.object.meeting.pk)
        if request.POST.get("action") == "agenda_note":
            return self._post_agenda_note(request)
        form = ProtocolBodyForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Bitte prüfen Sie den Protokolltext.")
            return self.get(request, *args, **kwargs)
        try:
            ProtocolDraftService.update_body(self.object, form.cleaned_data["body"], actor=request.user)
        except ValidationError as error:
            messages.error(request, error.messages[0])
            return redirect("protocols:protocol_detail", pk=self.object.pk)
        messages.success(request, "Protokoll wurde gespeichert.")
        return redirect("protocols:protocol_detail", pk=self.object.pk)

    def _live_reconfirmation_required(self, user, meeting: Meeting) -> bool:
        """Return whether editing during a live meeting needs meeting re-confirmation."""
        if meeting.status != "IN_PROGRESS" or user.is_staff or user.is_superuser:
            return False
        participant = loaded_participant_for_user(meeting, user)
        return not bool(participant and participant.last_self_confirmed_at)

    def _post_agenda_note(self, request):
        """Persist one TOP note from the structured protocol view."""
        agenda_item = get_object_or_404(
            AgendaItem,
            pk=request.POST.get("agenda_item_id"),
            agenda__meeting=self.object.meeting,
        )
        form = ProtocolAgendaItemNoteForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Bitte prüfen Sie die TOP-Notiz.")
            return redirect("protocols:protocol_detail", pk=self.object.pk)
        try:
            ProtocolDraftService.update_item_note(
                self.object,
                agenda_item,
                form.cleaned_data["body"],
                actor=request.user,
            )
        except ValidationError as error:
            messages.error(request, error.messages[0])
            return redirect("protocols:protocol_detail", pk=self.object.pk)
        messages.success(request, "TOP-Notiz wurde gespeichert.")
        return redirect("protocols:protocol_detail", pk=self.object.pk)

    def _agenda_items_for_protocol(self, protocol: Protocol) -> list[dict]:
        """Return final agenda order with current editable protocol notes."""
        notes_by_item_id = {
            str(note.agenda_item_id): note.body
            for note in protocol.item_notes.select_related("agenda_item")
        }
        agenda_item_map = {
            str(item.pk): item
            for item in protocol.meeting.agenda.items.all()
        } if protocol.meeting.has_agenda else {}
        snapshot = protocol.agenda_snapshot or []
        if not snapshot and protocol.meeting.has_agenda:
            snapshot = [
                {
                    "agenda_item_id": str(item.pk),
                    "item_number": item.item_number,
                    "title": item.title,
                    "description": item.description,
                    "item_type": item.item_type,
                }
                for item in protocol.meeting.agenda.all_items
            ]
        return [
            {
                "agenda_item_id": item_data.get("agenda_item_id", ""),
                "agenda_item": agenda_item_map.get(item_data.get("agenda_item_id", "")),
                "item_number": item_data.get("item_number", ""),
                "indent_class": self._indent_class(item_data.get("item_number", "")),
                "number_display": self._number_display(item_data.get("item_number", "")),
                "title": item_data.get("title", ""),
                "description": item_data.get("description", ""),
                "item_type": item_data.get("item_type", ""),
                "note_body": notes_by_item_id.get(
                    item_data.get("agenda_item_id", ""),
                    item_data.get("note", ""),
                ),
            }
            for item_data in snapshot
        ]

    def _indent_class(self, item_number: str) -> str:
        """Return a Bootstrap margin class for hierarchical agenda items."""
        depth = max(len(str(item_number).split(".")) - 1, 0) if item_number else 0
        return f"ms-{min(depth * 3, 5)}"

    def _number_display(self, item_number: str) -> str:
        """Return agenda number with final dot for protocol display."""
        number = str(item_number or "").strip()
        if not number:
            return ""
        return number if number.endswith(".") else f"{number}."

    def _meeting_start_display(self, meeting: Meeting) -> str:
        """Return the most precise available meeting start display."""
        if meeting.actual_start_time:
            actual_start_date = meeting.actual_start_date or meeting.date
            return f"{actual_start_date:%d.%m.%Y} {meeting.actual_start_time:%H:%M} Uhr"
        if meeting.start_time:
            return f"{meeting.date:%d.%m.%Y} {meeting.start_time:%H:%M} Uhr"
        return f"{meeting.date:%d.%m.%Y}"

    def _meeting_end_display(self, meeting: Meeting) -> str:
        """Return the most precise available meeting end display."""
        if meeting.actual_end_time:
            actual_end_date = meeting.actual_end_date or meeting.actual_start_date or meeting.date
            return f"{actual_end_date:%d.%m.%Y} {meeting.actual_end_time:%H:%M} Uhr"
        if meeting.end_time:
            return f"{meeting.date:%d.%m.%Y} {meeting.end_time:%H:%M} Uhr"
        return "Noch nicht erfasst."

    def _participant_context(self, meeting: Meeting) -> dict:
        """Group participants for a readable protocol attendance section."""
        participants = list(meeting.participants.select_related(
            "membership",
            "membership__user",
            "membership__role",
            "substitute_membership",
            "substitute_membership__user",
            "substitute_membership__role",
        ).order_by("membership__user__last_name", "membership__user__first_name"))
        periods_by_participant = attendance_periods_by_participant(meeting)
        present = []
        excused_absent = []
        unexcused_absent = []
        guests = []
        substitutes = []
        for participant in participants:
            periods = periods_by_participant.get(participant.pk, [])
            participant.protocol_periods = periods
            if participant.participant_type == MeetingParticipant.PARTICIPANT_TYPE_EXTERNAL:
                guests.append(participant)
            if participant.substitute_membership_id:
                substitutes.append(participant)
            if periods:
                present.append(participant)
            elif participant.status in [
                MeetingParticipant.STATUS_ABSENT,
                MeetingParticipant.STATUS_SUBSTITUTE_PROPOSED,
            ]:
                excused_absent.append(participant)
            elif participant.participant_type != MeetingParticipant.PARTICIPANT_TYPE_EXTERNAL:
                unexcused_absent.append(participant)
        return {
            "present_participants": present,
            "excused_absent_participants": excused_absent,
            "unexcused_absent_participants": unexcused_absent,
            "guest_participants": guests,
            "substitute_participants": substitutes,
        }

    def _result_entries(self, protocol: Protocol, entry_type: str) -> list[dict]:
        """Return result entries with their associated protocol note text."""
        notes_by_item_id = {
            note.agenda_item_id: note.body
            for note in protocol.item_notes.select_related("agenda_item")
        }
        entries = protocol.entries.select_related("agenda_item").filter(
            entry_type=entry_type,
        ).order_by("agenda_item__sort_order", "created_at", "id")
        return [
            {
                "entry": entry,
                "data": entry.data,
                "note_body": notes_by_item_id.get(entry.agenda_item_id, ""),
            }
            for entry in entries
        ]


class ProtocolAgendaItemNoteUpdateView(MeetingLiveRuntimeMixin, FormView):
    """Update one protocol note from the live meeting."""

    form_class = ProtocolAgendaItemNoteForm
    template_name = "protocols/protocol_note_form.html"

    def dispatch(self, request, *args, **kwargs):
        """Require the meeting clerk or privileged user."""
        meeting = self.get_meeting()
        if not _user_can_edit_protocol_notes(request.user, meeting):
            messages.error(request, "Nur die Protokollführung kann TOP-Notizen bearbeiten.")
            return redirect("meetings:meeting_live", pk=meeting.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_meeting(self) -> Meeting:
        """Return meeting addressed by the URL."""
        if not hasattr(self, "_meeting"):
            self._meeting = get_object_or_404(Meeting, pk=self.kwargs["meeting_pk"])
        return self._meeting

    def get_agenda_item(self) -> AgendaItem:
        """Return agenda item addressed by the URL."""
        if not hasattr(self, "_agenda_item"):
            self._agenda_item = get_object_or_404(
                AgendaItem,
                pk=self.kwargs["item_pk"],
                agenda__meeting=self.get_meeting(),
            )
        return self._agenda_item

    def get_initial(self):
        """Pre-fill existing note."""
        protocol = ProtocolDraftService.get_or_create_for_meeting(self.get_meeting(), self.request.user)
        note = protocol.item_notes.filter(agenda_item=self.get_agenda_item()).first()
        return {"body": note.body if note else ""}

    def get_context_data(self, **kwargs):
        """Add meeting and agenda item context."""
        context = super().get_context_data(**kwargs)
        context["meeting"] = self.get_meeting()
        context["agenda_item"] = self.get_agenda_item()
        return context

    def form_valid(self, form):
        """Persist note through protocol service."""
        meeting = self.get_meeting()
        protocol = ProtocolDraftService.get_or_create_for_meeting(meeting, self.request.user)
        try:
            ProtocolDraftService.update_item_note(
                protocol,
                self.get_agenda_item(),
                form.cleaned_data["body"],
                actor=self.request.user,
            )
        except ValidationError as error:
            messages.error(self.request, error.messages[0])
            if self.request.headers.get("HX-Request"):
                return _render_live_agenda_response(self.request, meeting)
            return redirect("meetings:meeting_live", pk=meeting.pk)
        messages.success(self.request, "TOP-Notiz wurde gespeichert.")
        if self.request.headers.get("HX-Request"):
            return _render_live_agenda_response(self.request, meeting)
        return redirect("meetings:meeting_live", pk=meeting.pk)

# Create your views here.
