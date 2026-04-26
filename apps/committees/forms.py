"""Forms for committees app."""

from django import forms

from apps.committees.models import Committee, Membership
from apps.committees.utils import suggest_default_role


class MembershipForm(forms.ModelForm):
    """Form for creating and editing memberships."""
    
    class Meta:
        model = Membership
        fields = [
            'user',
            'role',
            'member_type',
            'start_date',
            'end_date',
            'election_list_name',
            'election_list_position',
            'election_votes',
        ]
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'member_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'},
                format='%Y-%m-%d'
            ),
            'end_date': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'},
                format='%Y-%m-%d'
            ),
            'election_list_name': forms.TextInput(attrs={'class': 'form-control'}),
            'election_list_position': forms.NumberInput(attrs={'class': 'form-control'}),
            'election_votes': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, committee=None, *args, **kwargs):
        """
        Initialize form with committee context.
        
        Args:
            committee: Committee object to filter roles
        """
        super().__init__(*args, **kwargs)
        
        self.committee = committee
        
        # Filter roles to committee roles only
        if 'role' in self.fields:
            self.fields['role'].queryset = self.fields['role'].queryset.filter(
                role_type='COMMITTEE'
            )
            
            # Set default role based on member_type if creating new membership
            if not self.instance.pk and self.initial.get('member_type'):
                default_role = suggest_default_role(self.initial['member_type'])
                if default_role:
                    self.fields['role'].initial = default_role
        
        # Add help texts
        self.fields['election_list_name'].help_text = 'Nur für reguläre Mitglieder und Ersatzmitglieder'
        self.fields['election_list_position'].help_text = 'Listenplatz bei Listenwahl'
        self.fields['election_votes'].help_text = 'Erhaltene Stimmen'
    
    def clean(self):
        """Validate form data."""
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        
        # Check if user already member of committee (if creating new)
        if self.committee and user and not self.instance.pk:
            if Membership.objects.filter(
                user=user,
                committee=self.committee
            ).exists():
                raise forms.ValidationError(
                    f'{user.get_full_name()} ist bereits Mitglied dieses Gremiums'
                )
        
        return cleaned_data
