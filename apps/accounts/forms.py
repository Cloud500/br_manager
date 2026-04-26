"""Forms for accounts app."""

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .models import UserInvitation, UserProfile

User = get_user_model()


class UserInviteForm(forms.ModelForm):
    """Form for inviting new users via email."""
    
    class Meta:
        model = UserInvitation
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'user@example.com'
            })
        }
    
    def clean_email(self):
        """Validate that email is not already registered or invited."""
        email = self.cleaned_data['email']
        
        # Check if user already exists
        if User.objects.filter(email=email).exists():
            raise ValidationError('Ein Benutzer mit dieser E-Mail-Adresse existiert bereits.')
        
        # Check if there's already a pending invitation
        if UserInvitation.objects.filter(email=email, is_used=False).exists():
            raise ValidationError('Für diese E-Mail-Adresse existiert bereits eine ausstehende Einladung.')
        
        return email


class UserRegistrationForm(forms.ModelForm):
    """Form for user registration via invitation link."""
    
    password = forms.CharField(
        label='Passwort',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=12,
        help_text='Mindestens 12 Zeichen'
    )
    password_confirm = forms.CharField(
        label='Passwort bestätigen',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    department = forms.CharField(
        label='Abteilung',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'z.B. IT, Produktion, ...'})
    )
    employee_id = forms.CharField(
        label='Mitarbeiter-ID',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'z.B. EMP-12345'})
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'gender', 'phone']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+49 ...'}),
        }
    
    def __init__(self, *args, email=None, **kwargs):
        """Initialize form with email from invitation."""
        super().__init__(*args, **kwargs)
        self.email = email
    
    def clean(self):
        """Validate that passwords match."""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            raise ValidationError('Die Passwörter stimmen nicht überein.')
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save user with hashed password and create profile."""
        user = super().save(commit=False)
        user.email = self.email
        user.set_password(self.cleaned_data['password'])
        user.is_active = True
        
        if commit:
            user.save()
            # Create UserProfile with department and employee_id
            UserProfile.objects.create(
                user=user,
                department=self.cleaned_data.get('department', ''),
                employee_id=self.cleaned_data.get('employee_id', '')
            )
        
        return user


class UserUpdateForm(forms.ModelForm):
    """Form for updating existing users (Admin use)."""
    
    # UserProfile fields
    department = forms.CharField(
        label='Abteilung',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'z.B. IT, Produktion, ...'})
    )
    employee_id = forms.CharField(
        label='Mitarbeiter-ID',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'z.B. EMP-12345'})
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'gender', 'phone', 'is_active']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        """Initialize form with profile data."""
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'profile'):
            self.fields['department'].initial = self.instance.profile.department
            self.fields['employee_id'].initial = self.instance.profile.employee_id
    
    def save(self, commit=True):
        """Save user and update profile."""
        user = super().save(commit=commit)
        
        if commit:
            # Get or create UserProfile
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.department = self.cleaned_data.get('department', '')
            profile.employee_id = self.cleaned_data.get('employee_id', '')
            profile.save()
        
        return user


class UserProfileUpdateForm(forms.ModelForm):
    """Form for users to update their own profile."""
    
    # UserProfile fields
    department = forms.CharField(
        label='Abteilung',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'z.B. IT, Produktion, ...'})
    )
    employee_id = forms.CharField(
        label='Mitarbeiter-ID',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'z.B. EMP-12345'})
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'gender', 'phone']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+49 ...'}),
        }
    
    def __init__(self, *args, **kwargs):
        """Initialize form with profile data."""
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'profile'):
            self.fields['department'].initial = self.instance.profile.department
            self.fields['employee_id'].initial = self.instance.profile.employee_id
    
    def save(self, commit=True):
        """Save user and update profile."""
        user = super().save(commit=commit)
        
        if commit:
            # Get or create UserProfile
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.department = self.cleaned_data.get('department', '')
            profile.employee_id = self.cleaned_data.get('employee_id', '')
            profile.save()
        
        return user


class PasswordChangeForm(forms.Form):
    """Form for changing user password."""
    
    current_password = forms.CharField(
        label='Aktuelles Passwort',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='Geben Sie Ihr aktuelles Passwort ein'
    )
    new_password = forms.CharField(
        label='Neues Passwort',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=12,
        help_text='Mindestens 12 Zeichen'
    )
    new_password_confirm = forms.CharField(
        label='Neues Passwort bestätigen',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, user=None, **kwargs):
        """
        Initialize form with user instance.
        
        Args:
            user: User instance for password validation
        """
        super().__init__(*args, **kwargs)
        self.user = user
    
    def clean_current_password(self) -> str:
        """
        Validate that current password is correct.
        
        Returns:
            The validated current password
            
        Raises:
            ValidationError: If current password is incorrect
        """
        current_password = self.cleaned_data.get('current_password')
        
        if not self.user.check_password(current_password):
            raise ValidationError('Das aktuelle Passwort ist falsch.')
        
        return current_password
    
    def clean(self) -> dict:
        """
        Validate that new passwords match.
        
        Returns:
            Cleaned form data
            
        Raises:
            ValidationError: If passwords don't match
        """
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        new_password_confirm = cleaned_data.get('new_password_confirm')
        
        if new_password and new_password_confirm:
            if new_password != new_password_confirm:
                raise ValidationError('Die neuen Passwörter stimmen nicht überein.')
        
        return cleaned_data
