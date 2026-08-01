from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from .models import Course, CourseRoster


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["code", "title", "semester", "ca_total_weight"]
        widgets = {
            "code": forms.TextInput(attrs={"placeholder": "CSC101"}),
            "semester": forms.TextInput(attrs={"placeholder": "2025/2026 Semester 1"}),
        }

    def clean_code(self):
        return self.cleaned_data["code"].strip().upper()

    def clean(self):
        cleaned_data = super().clean()
        code = cleaned_data.get("code")
        semester = cleaned_data.get("semester")
        if code and semester:
            qs = Course.objects.filter(code=code, semester=semester)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(
                    "This course code already exists for that semester. "
                    "Contact the lecturer who owns it if this is a mistake."
                )
        return cleaned_data

    def validate_unique(self):
        pass


class ExcelUploadForm(forms.Form):
    file = forms.FileField(label="Excel file (.xlsx)")

    def clean_file(self):
        f = self.cleaned_data["file"]
        if not f.name.lower().endswith(".xlsx"):
            raise forms.ValidationError("Only .xlsx files are supported.")
        return f


class RosterEditForm(forms.ModelForm):
    class Meta:
        model = CourseRoster
        fields = ["reg_number", "name"]

    def clean_reg_number(self):
        reg_number = self.cleaned_data["reg_number"].strip().upper()
        qs = CourseRoster.objects.filter(course=self.instance.course, reg_number=reg_number)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("This registration number is already on the roster.")
        return reg_number

    def clean_name(self):
        return self.cleaned_data["name"].strip()


class ResultEditForm(forms.Form):
    """
    Dynamically built: one field per ACTIVE assessment column in the
    batch (columns with no max score declared don't get a field at all —
    they stay permanently blank, matching upload behavior). Field names
    are index-based (score_0, score_1...) rather than derived from the
    column name, since column names are free text and could collide or
    contain characters that aren't safe as form field names.
    """

    def __init__(self, *args, active_columns=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.active_columns = active_columns or []
        for idx, (col_name, max_score) in enumerate(self.active_columns):
            self.fields[f"score_{idx}"] = forms.DecimalField(
                label=f"{col_name} (max {max_score:g})",
                required=False,
                min_value=0,
                max_value=Decimal(str(max_score)),
                max_digits=6,
                decimal_places=2,
            )