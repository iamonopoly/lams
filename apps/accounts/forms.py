from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import (
    LecturerProfile,
    PreRegisteredStudent,
    StudentProfile,
    User,
    reg_number_validator,
)

class StudentRegistrationForm(forms.Form):
    """
    Step 1 of student sign-up: identity check only. No password here — that
    happens later via the emailed setup link, so a stolen/guessed reg number
    alone can never be enough to create a usable login.
    """

    reg_number = forms.CharField(
        label="Registration Number",
        max_length=20,
        widget=forms.TextInput(attrs={"placeholder": "PS/CSC/22/0001", "autocomplete": "off", "class": "input-mono"}),
    )
    reg_number_confirm = forms.CharField(
        label="Confirm Registration Number",
        max_length=20,
        widget=forms.TextInput(attrs={
            "placeholder": "Re-enter PS/CSC/22/0001",
            "autocomplete": "off",
            "class": "input-mono",
            "onpaste": "return false",
            "oncopy": "return false",
            "oncut": "return false",
            "ondrop": "return false",
        }),
        help_text="Type it again — pasting is disabled here so a typo above can't slip through unnoticed.",
    )
    email = forms.EmailField(label="Email address")

    def clean_reg_number(self):
        reg_number = self.cleaned_data["reg_number"].strip().upper()

        # Check format FIRST and separately from the roster lookup, so a
        # typo gets "wrong format" rather than being misreported as
        # "not on the roster" (which was a real bug caught during testing).
        reg_number_validator(reg_number)

        try:
            roster_entry = PreRegisteredStudent.objects.get(reg_number=reg_number)
        except PreRegisteredStudent.DoesNotExist:
            raise ValidationError(
                "This registration number was not found on any course "
                "roster. Ask your lecturer to confirm you've been added."
            )

        if StudentProfile.objects.filter(reg_number=reg_number).exists():
            raise ValidationError(
                "An account already exists for this registration number. "
                "Try logging in, or use 'Forgot password'."
            )

        self.roster_entry = roster_entry
        return reg_number

    def clean_reg_number_confirm(self):
        return self.cleaned_data["reg_number_confirm"].strip().upper()

    def clean(self):
        cleaned_data = super().clean()
        reg_number = cleaned_data.get("reg_number")
        reg_number_confirm = cleaned_data.get("reg_number_confirm")

        # Only compare if both individually passed their own validation —
        # otherwise a mismatch error would mask the more useful "wrong
        # format" or "not on roster" error already attached to reg_number.
        if reg_number and reg_number_confirm and reg_number != reg_number_confirm:
            self.add_error(
                "reg_number_confirm",
                "This doesn't match the registration number above. Please re-type it carefully.",
            )
        return cleaned_data

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email



class LecturerRegistrationForm(forms.Form):
    full_name = forms.CharField(label="Full name", max_length=150)
    email = forms.EmailField(label="Institutional email")
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        # This is now the ONLY gate on who can register as a lecturer,
        # since there's no Admin to approve accounts individually — so
        # it's enforced strictly, not just a UI hint.
        allowed_domain = settings.ALLOWED_LECTURER_EMAIL_DOMAIN
        if allowed_domain and not email.endswith("@" + allowed_domain):
            raise ValidationError(
                f"Lecturer accounts require an institutional email "
                f"ending in @{allowed_domain}."
            )

        if User.objects.filter(email=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean_password1(self):
        password1 = self.cleaned_data.get("password1")
        validate_password(password1)
        return password1

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password1")
        p2 = cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise ValidationError("Passwords do not match.")
        return cleaned_data


class StudentSetPasswordForm(SetPasswordForm):
    """Reuses Django's built-in password-strength validation and confirm
    field, just relabelled for the activation-link context."""

    new_password1 = forms.CharField(
        label="New password", widget=forms.PasswordInput, strip=False
    )
    new_password2 = forms.CharField(
        label="Confirm new password", widget=forms.PasswordInput, strip=False
    )

class LoginIdentifierForm(AuthenticationForm):
    """
    Accepts either a student's registration number or a lecturer's email
    in the same field — RegNumberOrEmailBackend (in backends.py) does the
    actual lookup/detection. This form just relaxes the field from a
    strict EmailField to plain text and relabels it, plus gives a
    clearer error message that doesn't assume the identifier was an email.
    """

    username = forms.CharField(
        label="Registration Number or Email",
        widget=forms.TextInput(attrs={"class": "input-mono", "autocomplete": "username"}),
    )

    error_messages = {
        "invalid_login": (
            "Please enter a correct registration number (or email) and "
            "password. Both may be case-sensitive."
        ),
        "inactive": "This account is inactive.",
    }

    def clean_username(self):
        return self.cleaned_data["username"].strip()


class AdminUserEditForm(forms.ModelForm):
    """Superuser-only: edit a user's name/email. Deliberately does NOT
    expose role, password, or reg_number here — this is name/contact
    detail cleanup, not account re-provisioning."""

    class Meta:
        model = User
        fields = ["full_name", "email"]

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        qs = User.objects.filter(email=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Another account already uses this email.")
        return email




    