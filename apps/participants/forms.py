"""Forms for meeting participant workflows."""

from django import forms

from apps.committees.models import Membership
from apps.participants.models import MeetingParticipant
from apps.participants.services import (
    available_substitutes_for_participant,
    related_committee_ids,
    suggest_substitute,
)


class AddParticipantForm(forms.Form):
    """Form for adding additional meeting participants."""

    membership = forms.ModelChoiceField(
        queryset=Membership.objects.none(),
        label="Mitglied aus Gremium/Ausschuss",
        required=True,
        widget=forms.HiddenInput(),
        help_text="Aktive Mitgliedschaft aus dem übergeordneten Gremium oder verbundenen Ausschüssen auswählen.",
    )

    def __init__(self, *args, meeting=None, **kwargs):
        """Limit membership choices to participants not already active in the meeting."""
        super().__init__(*args, **kwargs)
        if not meeting:
            self.candidate_memberships = []
            return

        used_membership_ids = meeting.participants.exclude(
            status=MeetingParticipant.STATUS_CANCELLED,
        ).filter(
            membership_id__isnull=False,
        ).values_list("membership_id", flat=True)
        used_substitute_ids = meeting.participants.exclude(
            status=MeetingParticipant.STATUS_CANCELLED,
        ).filter(
            substitute_membership_id__isnull=False,
        ).values_list("substitute_membership_id", flat=True)
        used_user_ids = meeting.participants.exclude(
            status=MeetingParticipant.STATUS_CANCELLED,
        ).values_list("membership__user_id", flat=True)
        used_substitute_user_ids = meeting.participants.exclude(
            status=MeetingParticipant.STATUS_CANCELLED,
        ).filter(
            substitute_membership_id__isnull=False,
        ).values_list("substitute_membership__user_id", flat=True)
        queryset = Membership.objects.filter(
            committee_id__in=related_committee_ids(meeting),
            is_active=True,
            deleted_at__isnull=True,
        ).exclude(
            id__in=used_membership_ids,
        ).exclude(
            id__in=used_substitute_ids,
        ).exclude(
            user_id__in=used_user_ids,
        ).exclude(
            user_id__in=used_substitute_user_ids,
        ).select_related("user", "role", "committee").order_by(
            "committee__name",
            "role__sort_order",
            "user__last_name",
            "user__first_name",
        )
        self.fields["membership"].queryset = queryset
        self.candidate_memberships = list(queryset)

class MarkAbsentForm(forms.Form):
    """Form for marking a participant absent."""

    absence_reason = forms.CharField(
        label="Abwesenheitsgrund",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )
    nachladefaehig = forms.BooleanField(
        label="Nachladefähig",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        help_text="Wenn aktiv, wird ein Ersatzvorschlag ermittelt.",
    )
    substitute_membership = forms.ModelChoiceField(
        queryset=Membership.objects.none(),
        label="Ersatzmitglied",
        required=False,
        widget=forms.HiddenInput(),
    )

    def __init__(self, *args, participant=None, **kwargs):
        """Initialize absence form with current state and replacement candidates."""
        super().__init__(*args, **kwargs)
        self.participant = participant
        self.all_substitutes = []
        self.suggested_substitute = None
        if not participant:
            return

        self.fields["absence_reason"].initial = participant.absence_reason
        self.fields["nachladefaehig"].initial = participant.nachladefaehig
        self.all_substitutes = available_substitutes_for_participant(participant)
        self.fields["substitute_membership"].queryset = Membership.objects.filter(
            id__in=[membership.id for membership in self.all_substitutes]
        )
        if participant.substitute_membership_id:
            self.suggested_substitute = participant.substitute_membership
            self.fields["substitute_membership"].initial = self.suggested_substitute
        else:
            self.suggested_substitute = suggest_substitute(
                participant.meeting,
                participant,
            )
        if self.suggested_substitute:
            self.fields["substitute_membership"].initial = self.suggested_substitute

    def clean(self):
        """Clear substitute selection when the participant is not replaceable."""
        cleaned_data = super().clean()
        if not cleaned_data.get("nachladefaehig"):
            cleaned_data["substitute_membership"] = None
        return cleaned_data

