"""Forms for agendas app."""

from django import forms
from django.db import models, transaction

from .models import AgendaItem


class AgendaItemRegularForm(forms.ModelForm):
    """Form for creating and editing regular agenda items."""

    class Meta:
        model = AgendaItem
        fields = ["title", "description", "parent"]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "z.B. Begrüßung und Feststellung der Beschlussfähigkeit",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Optional: Ausführliche Beschreibung des Tagesordnungspunktes",
                }
            ),
            "parent": forms.Select(attrs={"class": "form-select"}),
        }
        labels = {
            "title": "Titel",
            "description": "Beschreibung",
            "parent": "Übergeordneter TOP",
        }
        help_texts = {
            "title": "Kurztitel des Tagesordnungspunktes",
            "description": "Optional: Ausführliche Beschreibung",
            "parent": "Optional: Wählen Sie einen übergeordneten TOP für hierarchische Struktur (z.B. TOP 1.1)",
        }

    def __init__(self, *args, agenda=None, **kwargs):
        """Initialize form with agenda context."""
        super().__init__(*args, **kwargs)
        self.agenda = agenda
        if agenda:
            queryset = AgendaItem.objects.filter(agenda=agenda).order_by("sort_order")
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            self.fields["parent"].queryset = queryset
        self.fields["parent"].empty_label = "(Kein übergeordneter TOP - Hauptebene)"
        self.fields["description"].required = False

    def _post_clean(self) -> None:
        """Set agenda and regular type before model validation."""
        if self.agenda and not self.instance.pk:
            self.instance.agenda = self.agenda
        self.instance.item_type = AgendaItem.TYPE_REGULAR
        super()._post_clean()

    def save(self, commit=True):
        """Save the regular agenda item."""
        instance = super().save(commit=False)
        if self.agenda:
            instance.agenda = self.agenda
        instance.item_type = AgendaItem.TYPE_REGULAR
        if commit:
            instance.save()
        return instance


class AgendaItemResolutionForm(forms.ModelForm):
    """Form for creating resolution agenda items."""

    resolution = forms.ModelChoiceField(
        queryset=AgendaItem.objects.none(),
        label="Beschluss",
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text='Wählen Sie einen Beschluss im Status "Vorgeschlagen"',
    )

    class Meta:
        model = AgendaItem
        fields = ["resolution", "parent"]
        widgets = {
            "parent": forms.Select(attrs={"class": "form-select"}),
        }
        labels = {
            "parent": "Übergeordneter TOP",
        }
        help_texts = {
            "parent": "Optional: Wählen Sie einen übergeordneten TOP für hierarchische Struktur",
        }

    def __init__(self, *args, agenda=None, **kwargs):
        """Initialize form with agenda context."""
        super().__init__(*args, **kwargs)
        self.agenda = agenda

        if agenda:
            from apps.resolutions.models import Resolution

            meeting_committee = agenda.meeting.committee
            resolutions = (
                Resolution.objects.filter(status="PROPOSED")
                .filter(
                    models.Q(committee=meeting_committee)
                    | models.Q(
                        committee__parent=meeting_committee,
                        propose_to_main_committee=True,
                    )
                )
                .exclude(agenda_items__agenda_item__agenda=agenda)
                .select_related("committee")
            )
            self.fields["resolution"].queryset = resolutions
            self.fields["parent"].queryset = AgendaItem.objects.filter(
                agenda=agenda
            ).order_by("sort_order")

        self.fields["parent"].empty_label = "(Kein übergeordneter TOP - Hauptebene)"
        self.fields["parent"].required = False

    def _post_clean(self) -> None:
        """Set agenda and resolution type before model validation."""
        if self.agenda and not self.instance.pk:
            self.instance.agenda = self.agenda
        self.instance.item_type = AgendaItem.TYPE_RESOLUTION
        super()._post_clean()

    def save(self, commit=True):
        """Create the agenda item and its resolution wrapper."""
        agenda_item = super().save(commit=False)
        if self.agenda:
            agenda_item.agenda = self.agenda
        agenda_item.item_type = AgendaItem.TYPE_RESOLUTION
        resolution = self.cleaned_data.get("resolution")
        if resolution:
            agenda_item.title = resolution.title
            agenda_item.description = resolution.description

        if commit:
            from apps.resolutions.models import ResolutionAgendaItem

            with transaction.atomic():
                agenda_item.save()
                ResolutionAgendaItem.objects.create(
                    agenda_item=agenda_item, resolution=self.cleaned_data["resolution"]
                )

        return agenda_item


class AgendaItemResolutionUpdateForm(forms.ModelForm):
    """Form for editing hierarchy of resolution TOP snapshots."""

    class Meta:
        model = AgendaItem
        fields = ["parent"]
        widgets = {
            "parent": forms.Select(attrs={"class": "form-select"}),
        }
        labels = {
            "parent": "Übergeordneter TOP",
        }
        help_texts = {
            "parent": "Optional: Wählen Sie einen übergeordneten TOP für hierarchische Struktur",
        }

    def __init__(self, *args, agenda=None, **kwargs):
        """Initialize form with agenda context."""
        super().__init__(*args, **kwargs)
        self.agenda = agenda
        if agenda:
            queryset = AgendaItem.objects.filter(agenda=agenda).order_by("sort_order")
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            self.fields["parent"].queryset = queryset
        self.fields["parent"].empty_label = "(Kein übergeordneter TOP - Hauptebene)"
        self.fields["parent"].required = False

    def _post_clean(self) -> None:
        """Keep the resolution item type before model validation."""
        self.instance.item_type = AgendaItem.TYPE_RESOLUTION
        super()._post_clean()

    def save(self, commit=True):
        """Save the resolution agenda item metadata."""
        instance = super().save(commit=False)
        instance.item_type = AgendaItem.TYPE_RESOLUTION
        if commit:
            instance.save()
        return instance
