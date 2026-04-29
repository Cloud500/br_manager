"""Forms for resolutions app."""

from django import forms
from django.core.exceptions import ValidationError

from apps.resolutions.models import Resolution


class ResolutionForm(forms.ModelForm):
    """Form for creating and editing resolutions."""
    
    class Meta:
        model = Resolution
        fields = [
            'committee',
            'proposal',
            'justification',
            'propose_to_main_committee',
        ]
        widgets = {
            'committee': forms.Select(attrs={'class': 'form-select'}),
            'proposal': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Der zur Abstimmung zu stellende Beschlusstext...'
            }),
            'justification': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Begründung für den Beschlussvorschlag...'
            }),
            'propose_to_main_committee': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, user=None, *args, **kwargs):
        """
        Initialize form with user context.
        
        Args:
            user: Current user for permission filtering
        """
        super().__init__(*args, **kwargs)
        
        self.user = user
        
        # Filter committees to those where user can create resolutions
        if user and 'committee' in self.fields:
            from apps.committees.models import Committee, Membership
            
            if user.is_superuser or user.is_staff:
                # Superuser: All committees except BA
                allowed_committees = Committee.objects.filter(
                    is_active=True
                ).exclude(committee_type='COMMITTEE')
            else:
                memberships = Membership.objects.filter(
                    user=user,
                    is_active=True
                ).select_related('committee', 'role')
                
                allowed_committee_ids = set()
                
                for membership in memberships:
                    committee = membership.committee
                    
                    has_permission = (
                        membership.role and 
                        membership.role.permissions.filter(
                            codename='resolution.create'
                        ).exists()
                    )
                    
                    if not has_permission:
                        continue
                    
                    # BA: Only parent BR
                    if committee.committee_type == 'COMMITTEE':
                        if committee.parent:
                            allowed_committee_ids.add(committee.parent.id)
                    # Sub-Committee: Always parent + self if can_create_resolutions
                    elif committee.parent:
                        allowed_committee_ids.add(committee.parent.id)
                        if committee.can_create_resolutions:
                            allowed_committee_ids.add(committee.id)
                    # MAIN or no parent: Only if can_create_resolutions
                    elif committee.can_create_resolutions:
                        allowed_committee_ids.add(committee.id)
                
                allowed_committees = Committee.objects.filter(
                    id__in=allowed_committee_ids,
                    is_active=True
                )
            
            self.fields['committee'].queryset = allowed_committees
        
        # Handle propose_to_main_committee field visibility
        # Only for existing instances (with pk and committee set)
        if self.instance.pk and hasattr(self.instance, 'committee_id') and self.instance.committee_id:
            committee = self.instance.committee
            
            # Betriebsausschuss: always True, disabled
            if committee.committee_type == 'COMMITTEE':
                self.fields['propose_to_main_committee'].initial = True
                self.fields['propose_to_main_committee'].disabled = True
                self.fields['propose_to_main_committee'].help_text = (
                    'Betriebsausschuss erstellt nur Beschlussvorschläge für das Hauptgremium (§ 27 BetrVG)'
                )
            # Committee without parent: hide field
            elif not committee.parent:
                self.fields['propose_to_main_committee'].widget = forms.HiddenInput()
                self.fields['propose_to_main_committee'].initial = False
            else:
                self.fields['propose_to_main_committee'].help_text = (
                    'Beschluss kann in TOP des Hauptgremiums aufgenommen werden (§ 28 BetrVG)'
                )
        else:
            # New instance - show help text
            self.fields['propose_to_main_committee'].help_text = (
                'Beschluss kann in TOP des Hauptgremiums aufgenommen werden (§ 28 BetrVG)'
            )
    
    def clean(self):
        """Validate form data."""
        cleaned_data = super().clean()
        committee = cleaned_data.get('committee')
        propose_to_main_committee = cleaned_data.get('propose_to_main_committee')
        
        # Validate committee can create resolutions
        if committee and not committee.can_create_resolutions:
            raise ValidationError({
                'committee': 'Dieses Gremium darf keine Beschlüsse erstellen'
            })
        
        # Validate user has permission
        if self.user and committee:
            if not Resolution.user_can_create(self.user, committee):
                raise ValidationError({
                    'committee': 'Sie haben keine Berechtigung Beschlüsse für dieses Gremium zu erstellen'
                })
        
        # Betriebsausschuss must propose to main committee
        if committee and committee.committee_type == 'COMMITTEE':
            cleaned_data['propose_to_main_committee'] = True
        
        # propose_to_main_committee only for committees with parent
        if propose_to_main_committee and committee and not committee.parent:
            raise ValidationError({
                'propose_to_main_committee': 
                'Nur Beschlüsse von Ausschüssen können dem Hauptgremium vorgeschlagen werden'
            })
        
        return cleaned_data


class ResolutionStatusForm(forms.Form):
    """Form for changing resolution status (propose/withdraw)."""
    
    action = forms.ChoiceField(
        choices=[
            ('propose', 'Vorschlagen'),
            ('withdraw', 'Zurückziehen'),
        ],
        widget=forms.HiddenInput()
    )
    
    def __init__(self, resolution, *args, **kwargs):
        """
        Initialize form with resolution context.
        
        Args:
            resolution: Resolution instance
        """
        super().__init__(*args, **kwargs)
        self.resolution = resolution
    
    def clean_action(self):
        """Validate action is allowed."""
        action = self.cleaned_data['action']
        
        if action == 'propose':
            if not self.resolution.can_be_proposed:
                raise ValidationError('Beschluss kann nicht vorgeschlagen werden')
        elif action == 'withdraw':
            if not self.resolution.can_be_withdrawn:
                raise ValidationError('Beschluss kann nicht zurückgezogen werden')
        
        return action
