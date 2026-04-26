"""Forms for roles app."""

from django import forms

from apps.roles.models import Role


class RoleForm(forms.ModelForm):
    """Form for creating and editing roles."""
    
    class Meta:
        model = Role
        fields = ['name', 'codename', 'description', 'role_type', 'sort_order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'codename': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'z.B. CUSTOM_ROLE'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'role_type': forms.Select(attrs={'class': 'form-select'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }
        help_texts = {
            'codename': 'Eindeutiger Code-Name für diese Rolle (nur Großbuchstaben und Unterstriche)',
            'sort_order': 'Niedrigere Werte erscheinen weiter oben in der Liste',
        }
