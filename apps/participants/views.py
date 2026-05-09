"""Views for meeting participant workflows."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import FormView

from apps.meetings.models import Meeting
from apps.participants.forms import (
    AddParticipantForm,
    MarkAbsentForm,
)
from apps.participants.mixins import (
    ParticipantPermissionMixin,
    user_has_participant_permission,
)
from apps.participants.models import MeetingParticipant
from apps.participants.services import (
    add_participant,
    mark_absent,
    remove_absence,
    remove_substitute,
)


class ParticipantAddView(LoginRequiredMixin, FormView):
    """Add an additional participant to a meeting."""

    template_name = "participants/participant_add_form.html"
    form_class = AddParticipantForm

    def dispatch(self, request, *args, **kwargs):
        """Require participant edit permission in the meeting context."""
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        meeting = self.get_meeting()
        if meeting.status == "COMPLETED":
            messages.error(request, "Teilnehmer können nach Sitzungsabschluss nicht mehr geändert werden.")
            return redirect("meetings:meeting_detail", pk=meeting.pk)
        if not user_has_participant_permission(
            request.user,
            meeting,
            "participant.edit",
        ):
            messages.error(
                request,
                "Sie haben keine Berechtigung zum Hinzufügen von Teilnehmern.",
            )
            return redirect("meetings:meeting_detail", pk=meeting.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_meeting(self) -> Meeting:
        """Return the meeting addressed by the URL."""
        if not hasattr(self, "_meeting"):
            self._meeting = get_object_or_404(
                Meeting.objects.select_related("committee"),
                pk=self.kwargs["meeting_pk"],
            )
        return self._meeting

    def get_form_kwargs(self):
        """Pass the meeting to the form."""
        kwargs = super().get_form_kwargs()
        kwargs["meeting"] = self.get_meeting()
        return kwargs

    def get_context_data(self, **kwargs):
        """Add meeting context."""
        context = super().get_context_data(**kwargs)
        context["meeting"] = self.get_meeting()
        context["candidate_memberships"] = getattr(
            context["form"],
            "candidate_memberships",
            [],
        )
        return context

    def form_valid(self, form):
        """Create the additional participant."""
        participant = add_participant(
            meeting=self.get_meeting(),
            membership=form.cleaned_data.get("membership"),
            changed_by=self.request.user,
        )
        messages.success(
            self.request,
            f"{participant.display_name_for_display} wurde zur Sitzung hinzugefügt.",
        )
        return redirect(self.get_success_url())

    def get_success_url(self) -> str:
        """Return the meeting detail URL."""
        return reverse(
            "meetings:meeting_detail",
            kwargs={"pk": self.get_meeting().pk},
        )


class ParticipantActionMixin(LoginRequiredMixin, ParticipantPermissionMixin, FormView):
    """Base class for participant action views."""

    template_name = "participants/participant_action_form.html"
    title = "Teilnehmeraktion"
    submit_label = "Speichern"
    icon_class = "bi-person"

    def dispatch(self, request, *args, **kwargs):
        """Block participant action forms after meeting completion."""
        participant = self.get_object()
        if participant.meeting.status == "COMPLETED":
            messages.error(request, "Teilnehmer können nach Sitzungsabschluss nicht mehr geändert werden.")
            return redirect("meetings:meeting_detail", pk=participant.meeting.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_object(self) -> MeetingParticipant:
        """Return the participant addressed by the URL."""
        if not hasattr(self, "_participant"):
            self._participant = get_object_or_404(
                MeetingParticipant.objects.select_related(
                    "meeting",
                    "meeting__committee",
                    "membership",
                    "membership__user",
                    "membership__role",
                    "membership__committee",
                    "substitute_membership",
                    "substitute_membership__user",
                    "substitute_membership__role",
                    "substitute_membership__committee",
                ),
                pk=self.kwargs["pk"],
            )
        return self._participant

    def get_context_data(self, **kwargs):
        """Add participant action context."""
        context = super().get_context_data(**kwargs)
        participant = self.get_object()
        context.update({
            "participant": participant,
            "meeting": participant.meeting,
            "title": self.title,
            "submit_label": self.submit_label,
            "icon_class": self.icon_class,
        })
        return context

    def get_success_url(self) -> str:
        """Return the meeting detail URL."""
        return reverse(
            "meetings:meeting_detail",
            kwargs={"pk": self.get_object().meeting.pk},
        )


class ParticipantMarkAbsentView(ParticipantActionMixin):
    """Mark a participant absent."""

    template_name = "participants/participant_mark_absent_form.html"
    form_class = MarkAbsentForm
    permission_required = "participant.mark_absent"
    title = "Teilnehmer abwesend setzen"
    submit_label = "Abwesenheit speichern"
    icon_class = "bi-person-x"

    def get_form_kwargs(self):
        """Pass participant to absence form."""
        kwargs = super().get_form_kwargs()
        kwargs["participant"] = self.get_object()
        return kwargs

    def get_context_data(self, **kwargs):
        """Add replacement candidates to absence form context."""
        context = super().get_context_data(**kwargs)
        form = context["form"]
        participant = self.get_object()
        can_manage_substitutes = user_has_participant_permission(
            self.request.user,
            participant.meeting,
            "participant.manage_substitutes",
        )
        context["all_substitutes"] = getattr(form, "all_substitutes", [])
        context["suggested_substitute"] = getattr(form, "suggested_substitute", None)
        context["user_can_manage_participant_substitutes"] = can_manage_substitutes
        context["minority_info"] = self.get_minority_info(participant)
        return context

    def get_minority_info(self, participant: MeetingParticipant) -> dict | None:
        """Return minority gender quota status matching member replacement view."""
        committee = participant.meeting.committee
        if not committee.minority_gender or not committee.minority_min_count:
            return None
        current_minority_count = committee.memberships.filter(
            member_type="REGULAR",
            is_active=True,
            deleted_at__isnull=True,
            user__gender=committee.minority_gender,
        ).exclude(
            user=participant.membership.user,
        ).count()
        return {
            "gender": committee.minority_gender,
            "gender_display": committee.get_minority_gender_display(),
            "current_count": current_minority_count,
            "required_count": committee.minority_min_count,
            "quota_met": current_minority_count >= committee.minority_min_count,
        }

    def form_valid(self, form):
        """Persist absence and optional replacement in one step."""
        participant = self.get_object()
        substitute_membership = form.cleaned_data.get("substitute_membership")
        substitute_changed = (
            participant.substitute_membership_id
            != (substitute_membership.id if substitute_membership else None)
        )
        if substitute_changed and not user_has_participant_permission(
            self.request.user,
            participant.meeting,
            "participant.manage_substitutes",
        ):
            messages.error(
                self.request,
                "Sie haben keine Berechtigung zum Verwalten von Ersatzmitgliedern.",
            )
            return redirect(self.get_success_url())
        try:
            substitute = mark_absent(
                participant,
                form.cleaned_data["absence_reason"],
                form.cleaned_data["nachladefaehig"],
                substitute_membership=substitute_membership,
                changed_by=self.request.user,
            )
        except ValidationError as error:
            messages.error(self.request, error.messages[0])
            return redirect(self.get_success_url())
        if form.cleaned_data.get("nachladefaehig") and substitute_membership and substitute:
            messages.info(
                self.request,
                f"Ersatzmitglied: {substitute.user.get_full_name()}.",
            )
        messages.success(
            self.request,
            f"{participant.display_name_for_display} wurde als abwesend markiert.",
        )
        return redirect(self.get_success_url())


class ParticipantRemoveSubstituteView(
    LoginRequiredMixin,
    ParticipantPermissionMixin,
    View,
):
    """Remove a selected substitute directly from the participant row."""

    permission_required = "participant.manage_substitutes"

    def get_object(self) -> MeetingParticipant:
        """Return the participant addressed by the URL."""
        if not hasattr(self, "_participant"):
            self._participant = get_object_or_404(
                MeetingParticipant.objects.select_related(
                    "meeting",
                    "meeting__committee",
                    "membership",
                    "membership__user",
                    "substitute_membership",
                    "substitute_membership__user",
                ),
                pk=self.kwargs["pk"],
            )
        return self._participant

    def post(self, request, *args, **kwargs):
        """Remove substitute and restore the original participant."""
        participant = self.get_object()
        try:
            remove_substitute(participant, changed_by=request.user)
        except ValidationError as error:
            messages.error(request, error.messages[0])
            return redirect("meetings:meeting_detail", pk=participant.meeting.pk)
        messages.success(
            request,
            f"Ersatzmitglied für {participant.display_name_for_display} wurde entfernt.",
        )
        return redirect("meetings:meeting_detail", pk=participant.meeting.pk)


class ParticipantRemoveAbsenceView(
    LoginRequiredMixin,
    ParticipantPermissionMixin,
    View,
):
    """Remove an absence directly from the participant row."""

    permission_required = "participant.mark_absent"

    def get_object(self) -> MeetingParticipant:
        """Return the participant addressed by the URL."""
        if not hasattr(self, "_participant"):
            self._participant = get_object_or_404(
                MeetingParticipant.objects.select_related(
                    "meeting",
                    "meeting__committee",
                    "membership",
                    "membership__user",
                    "substitute_membership",
                    "substitute_membership__user",
                ),
                pk=self.kwargs["pk"],
            )
        return self._participant

    def post(self, request, *args, **kwargs):
        """Remove absence and restore the original participant."""
        participant = self.get_object()
        try:
            remove_absence(participant, changed_by=request.user)
        except ValidationError as error:
            messages.error(request, error.messages[0])
            return redirect("meetings:meeting_detail", pk=participant.meeting.pk)
        messages.success(
            request,
            f"Abwesenheit für {participant.display_name_for_display} wurde entfernt.",
        )
        return redirect("meetings:meeting_detail", pk=participant.meeting.pk)
