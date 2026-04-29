"""Forms for elections app."""

from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

from apps.elections.models import Election, ElectionCandidate


class ElectionForm(forms.ModelForm):
    """Form for creating and editing election agenda items."""

    class Meta:
        model = Election
        fields = ['title', 'description', 'election_type', 'majority_type']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'z.B. Wahl der/des Vorsitzenden'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Optional: Beschreibung oder Kontext der Wahl'
            }),
            'election_type': forms.Select(attrs={'class': 'form-select'}),
            'majority_type': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'title': 'Titel',
            'description': 'Beschreibung',
            'election_type': 'Wahlart',
            'majority_type': 'Mehrheitserfordernis',
        }

    def __init__(self, *args, agenda=None, **kwargs):
        """Initialize form with agenda context."""
        super().__init__(*args, **kwargs)
        self.agenda = agenda
        self.fields['description'].required = False

    def _post_clean(self):
        """Set agenda on instance before model validation."""
        if self.agenda and not self.instance.pk:
            self.instance.agenda = self.agenda
        super()._post_clean()

    def save(self, commit=True):
        """Save form instance."""
        instance = super().save(commit=False)
        if self.agenda:
            instance.agenda = self.agenda
        if commit:
            instance.save()
        return instance


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
