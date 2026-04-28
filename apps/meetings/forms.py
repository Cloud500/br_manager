"""Forms for meetings app."""

from django import forms

from apps.accounts.models import User
from apps.meetings.models import Meeting


class MeetingForm(forms.ModelForm):
    """Form for creating and editing meetings."""
    
    class Meta:
        model = Meeting
        fields = [
            'committee',
            'title',
            'date',
            'start_time',
            'end_time',
            'meeting_type',
            'location_url',
            'location_name',
            'location_street',
            'location_zip',
            'location_city',
            'location_room',
            'chair',
            'clerk',
            'is_quorate',
        ]
        widgets = {
            'committee': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'},
                format='%Y-%m-%d'
            ),
            'start_time': forms.TimeInput(
                attrs={'class': 'form-control', 'type': 'time'}
            ),
            'end_time': forms.TimeInput(
                attrs={'class': 'form-control', 'type': 'time'}
            ),
            'meeting_type': forms.Select(attrs={'class': 'form-select'}),
            'location_url': forms.URLInput(attrs={'class': 'form-control'}),
            'location_name': forms.TextInput(attrs={'class': 'form-control'}),
            'location_street': forms.TextInput(attrs={'class': 'form-control'}),
            'location_zip': forms.TextInput(attrs={'class': 'form-control'}),
            'location_city': forms.TextInput(attrs={'class': 'form-control'}),
            'location_room': forms.TextInput(attrs={'class': 'form-control'}),
            'chair': forms.HiddenInput(attrs={'id': 'id_chair'}),
            'clerk': forms.HiddenInput(attrs={'id': 'id_clerk'}),
            'is_quorate': forms.Select(
                choices=[(None, '--------'), (True, 'Ja'), (False, 'Nein')],
                attrs={'class': 'form-select'}
            ),
        }
    
    def __init__(self, *args, **kwargs):
        """Initialize form with dynamic field visibility."""
        super().__init__(*args, **kwargs)
        
        # Don't set required attributes in __init__ - let JavaScript and clean() handle it
        # This prevents validation errors when user changes meeting_type
        self.fields['location_url'].required = False
        self.fields['location_name'].required = False
        self.fields['location_street'].required = False
        self.fields['location_zip'].required = False
        self.fields['location_city'].required = False
        self.fields['location_room'].required = False
        
        # Hide is_quorate field if not IN_PROGRESS or COMPLETED
        meeting_status = self.instance.status if self.instance.pk else 'DRAFT'
        if meeting_status not in ['IN_PROGRESS', 'COMPLETED']:
            self.fields['is_quorate'].widget = forms.HiddenInput()
            self.fields['is_quorate'].required = False
        
        # Filter chair/clerk choices to committee members and order by role sort_order
        self.committee_members = []
        self.chair_candidates = []
        self.clerk_candidates = []
        committee_id = None
        if self.instance.pk and hasattr(self.instance, 'committee') and self.instance.committee_id:
            committee_id = self.instance.committee_id
            try:
                from apps.committees.models import Membership
                from apps.roles.models import Permission
                
                # Get permissions
                is_chair_perm = Permission.objects.filter(codename='meeting.is_chair').first()
                is_clerk_perm = Permission.objects.filter(codename='meeting.is_clerk').first()
                
                # Get active memberships ordered by role sort_order
                memberships = Membership.objects.filter(
                    committee=self.instance.committee,
                    is_active=True
                ).select_related('user', 'user__profile', 'role').order_by('role__sort_order', 'user__last_name', 'user__first_name')
                
                # Build separate lists for chair and clerk
                for m in memberships:
                    member_data = {
                        'id': m.user.id,
                        'name': m.user.get_full_name(),
                        'role': m.role.name if m.role else '',
                        'department': m.user.profile.department if hasattr(m.user, 'profile') and m.user.profile.department else '',
                        'list_name': m.election_list_name or '',
                        'list_position': m.election_list_position or '',
                    }
                    
                    # Check if role has is_chair permission
                    if m.role and is_chair_perm and m.role.permissions.filter(id=is_chair_perm.id).exists():
                        self.chair_candidates.append(member_data)
                    
                    # Check if role has is_clerk permission
                    if m.role and is_clerk_perm and m.role.permissions.filter(id=is_clerk_perm.id).exists():
                        self.clerk_candidates.append(member_data)
                
            except Exception:
                pass
        
        # Add help texts
        self.fields['meeting_type'].help_text = 'Wählen Sie den Sitzungstyp. Die Formularfelder passen sich automatisch an.'
        self.fields['is_quorate'].help_text = 'Wird nach Anwesenheitsprüfung automatisch gesetzt'
        self.fields['location_url'].help_text = 'Online-Meeting-Link (z.B. Zoom, Teams)'
        self.fields['end_time'].help_text = 'Optional: Geplantes Ende der Sitzung'
    
    def clean(self):
        """Validate form data."""
        cleaned_data = super().clean()
        
        # Get meeting_type from cleaned data
        meeting_type = cleaned_data.get('meeting_type', 'IN_PERSON')
        
        # Validate based on meeting_type
        if meeting_type == 'ONLINE':
            # Online: location_url required, address fields not required
            if not cleaned_data.get('location_url'):
                self.add_error('location_url', 'Online-Link ist erforderlich für Online-Sitzungen')
            
            # Clear address field errors and values
            for field in ['location_name', 'location_street', 'location_zip', 'location_city', 'location_room']:
                if field in self.errors:
                    del self.errors[field]
                cleaned_data[field] = ''
        
        elif meeting_type == 'IN_PERSON':
            # In-person: address required, location_url not required
            required_address_fields = ['location_name', 'location_street', 'location_zip', 'location_city']
            for field in required_address_fields:
                if not cleaned_data.get(field):
                    field_label = self.fields[field].label
                    self.add_error(field, f'{field_label} ist erforderlich für Präsenzsitzungen')
            
            # Clear URL field error and value
            if 'location_url' in self.errors:
                del self.errors['location_url']
            cleaned_data['location_url'] = ''
        
        elif meeting_type == 'HYBRID':
            # Hybrid: both URL and address required
            if not cleaned_data.get('location_url'):
                self.add_error('location_url', 'Online-Link ist erforderlich für Hybrid-Sitzungen')
            
            required_address_fields = ['location_name', 'location_street', 'location_zip', 'location_city']
            for field in required_address_fields:
                if not cleaned_data.get(field):
                    field_label = self.fields[field].label
                    self.add_error(field, f'{field_label} ist erforderlich für Hybrid-Sitzungen')
        
        return cleaned_data


class MeetingFilterForm(forms.Form):
    """Filter form for meeting list view."""
    
    committee = forms.ModelChoiceField(
        queryset=None,
        required=False,
        label='Gremium',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=[('', '--------')] + Meeting.STATUS_CHOICES,
        required=False,
        label='Status',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    meeting_type = forms.ChoiceField(
        choices=[('', '--------')] + Meeting.MEETING_TYPE_CHOICES,
        required=False,
        label='Sitzungstyp',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False,
        label='Von Datum',
        widget=forms.DateInput(
            attrs={'class': 'form-control', 'type': 'date'},
            format='%Y-%m-%d'
        )
    )
    date_to = forms.DateField(
        required=False,
        label='Bis Datum',
        widget=forms.DateInput(
            attrs={'class': 'form-control', 'type': 'date'},
            format='%Y-%m-%d'
        )
    )
    
    def __init__(self, *args, **kwargs):
        """Initialize filter form."""
        super().__init__(*args, **kwargs)
        
        # Import here to avoid circular imports
        from apps.committees.models import Committee
        
        # Set committee queryset to active committees
        self.fields['committee'].queryset = Committee.objects.filter(is_active=True)


class MeetingSendInvitationForm(forms.Form):
    """Form for sending meeting invitations."""
    
    message = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        required=False,
        label='Zusätzliche Nachricht',
        help_text='Optional: Fügen Sie eine persönliche Nachricht zur Einladung hinzu'
    )
    include_agenda = forms.BooleanField(
        initial=True,
        required=False,
        label='Tagesordnung anhängen',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Tagesordnung als PDF anhängen (falls vorhanden)'
    )
