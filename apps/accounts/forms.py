"""Forms for accounts app."""

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .models import UserProfile

User = get_user_model()


class UserProfileUpdateForm(forms.ModelForm):
    department = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    employee_id = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))

    class Meta:
        model = User
        fields = ["first_name", "last_name", "gender", "phone"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "gender": forms.Select(attrs={"class": "form-select"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, "profile"):
            self.fields["department"].initial = self.instance.profile.department
            self.fields["employee_id"].initial = self.instance.profile.employee_id

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.department = self.cleaned_data.get("department", "")
            profile.employee_id = self.cleaned_data.get("employee_id", "")
            profile.save()
        return user


class PasswordChangeForm(forms.Form):
    current_password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))
    new_password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}), min_length=12)
    new_password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_current_password(self):
        if not self.user or not self.user.check_password(self.cleaned_data.get("current_password")):
            raise ValidationError("Das aktuelle Passwort ist falsch.")
        return self.cleaned_data["current_password"]

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("new_password") and cleaned_data.get("new_password_confirm") and cleaned_data["new_password"] != cleaned_data["new_password_confirm"]:
            raise ValidationError("Die neuen Passwörter stimmen nicht überein.")
        return cleaned_data
