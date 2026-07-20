from django import forms
from django.contrib.auth.models import User

from accounts.models import Profile
from common import validators
from common.exceptions import HealthPulseException


class RegistrationForm(forms.Form):
    role = forms.ChoiceField(choices=Profile.ROLE_CHOICES, initial=Profile.ROLE_PATIENT)
    full_name = forms.CharField(max_length=120)
    username = forms.CharField(max_length=30)
    email = forms.CharField(max_length=120)
    phone = forms.CharField(max_length=15)
    aadhaar = forms.CharField(max_length=12, required=False)
    gender = forms.ChoiceField(choices=[("M", "Male"), ("F", "Female"), ("O", "Other")])
    dob = forms.CharField(max_length=10)  # validated as YYYY-MM-DD
    address = forms.CharField(widget=forms.Textarea, required=False)
    specialization = forms.CharField(max_length=120, required=False)  # doctors only
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    confirm_password = forms.CharField(widget=forms.PasswordInput, min_length=8)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("That username is already taken.")
        return username

    def clean_email(self):
        try:
            email = validators.validate_email(self.cleaned_data["email"])
        except HealthPulseException as exc:
            raise forms.ValidationError(exc.message)
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with that email already exists.")
        return email

    def clean_phone(self):
        try:
            return validators.validate_phone(self.cleaned_data["phone"])
        except HealthPulseException as exc:
            raise forms.ValidationError(exc.message)

    def clean_aadhaar(self):
        value = self.cleaned_data.get("aadhaar", "")
        if self.data.get("role") == Profile.ROLE_DOCTOR:
            return value  # not required for doctors
        try:
            return validators.validate_aadhaar(value)
        except HealthPulseException as exc:
            raise forms.ValidationError(exc.message)

    def clean_dob(self):
        try:
            return validators.validate_date(self.cleaned_data["dob"])
        except HealthPulseException as exc:
            raise forms.ValidationError(exc.message)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") and cleaned.get("confirm_password"):
            if cleaned["password"] != cleaned["confirm_password"]:
                self.add_error("confirm_password", "Passwords do not match.")
        return cleaned
