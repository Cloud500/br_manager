"""Forms for elections app."""

from django import forms
from django.db import transaction
from django.forms import BaseInlineFormSet, inlineformset_factory

from apps.agendas.models import AgendaItem
from apps.elections.models import Election, ElectionCandidate


class ElectionForm(forms.ModelForm):
    """Form for creating and editing election agenda items."""

    title = forms.CharField(
        label='Titel',
        max_length=500,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'z.B. Wahl der/des Vorsitzenden'
        })
    )
    description = forms.CharField(
        label='Beschreibung',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Optional: Beschreibung oder Kontext der Wahl'
        })
    )

    class Meta:
        model = Election
        fields = ['title', 'description', 'election_type', 'majority_type']
        widgets = {
            'election_type': forms.Select(attrs={'class': 'form-select'}),
            'majority_type': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'election_type': 'Wahlart',
            'majority_type': 'Mehrheitserfordernis',
        }

    def __init__(self, *args, agenda=None, **kwargs):
        """Initialize form with agenda context and agenda item values."""
        super().__init__(*args, **kwargs)
        self.agenda = agenda
        if self.instance.pk and self.instance.agenda_item_id:
            self.fields['title'].initial = self.instance.agenda_item.title
            self.fields['description'].initial = self.instance.agenda_item.description

    def save(self, commit=True):
        """Save form instance and its linked agenda item."""
        election = super().save(commit=False)
        title = self.cleaned_data['title']
        description = self.cleaned_data.get('description', '')

        if commit:
            with transaction.atomic():
                if not election._state.adding and election.agenda_item_id:
                    agenda_item = election.agenda_item
                    agenda_item.title = title
                    agenda_item.description = description
                    agenda_item.save()
                else:
                    agenda_item = AgendaItem.objects.create(
                        agenda=self.agenda,
                        title=title,
                        description=description,
                        sort_order=self.agenda.next_sort_order(),
                        item_type=AgendaItem.TYPE_ELECTION
                    )
                    election.agenda_item = agenda_item
                election.save()

        return election


class ElectionCandidateFormSet(BaseInlineFormSet):
    """Inline formset requiring at least one candidate."""

    def clean(self):
        """Validate candidate formset."""
        super().clean()
        active_forms = [
            form for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False)
        ]
        if not active_forms:
            raise forms.ValidationError('Mindestens eine kandidierende Person ist erforderlich.')

        names = []
        for form in active_forms:
            name = form.cleaned_data.get('name', '').strip()
            if not name:
                raise forms.ValidationError('Kandidierende Personen benötigen einen Namen.')
            if name in names:
                raise forms.ValidationError('Kandidierende Personen dürfen nicht doppelt erfasst werden.')
            names.append(name)


ElectionCandidateFormSetFactory = inlineformset_factory(
    Election,
    ElectionCandidate,
    formset=ElectionCandidateFormSet,
    fields=['name'],
    extra=3,
    min_num=1,
    validate_min=True,
    can_delete=True,
    widgets={
        'name': forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Name der kandidierenden Person'
        }),
    },
    labels={'name': 'Name'},
)
