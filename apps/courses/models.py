from django.conf import settings
from django.db import models

from apps.accounts.models import reg_number_validator


class Course(models.Model):
    """
    One course, scoped to a specific semester. `code` + `semester` are
    unique together — this is what stops a CSC101 upload from ever
    colliding with CSC201 data, and (with no Admin to referee) the
    lecturer who creates a code first is locked in as its only owner.
    """

    code = models.CharField(max_length=20)
    title = models.CharField(max_length=200)
    semester = models.CharField(
        max_length=30, help_text="e.g. 2025/2026 Semester 1"
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="courses",
        limit_choices_to={"role": "LECTURER"},
    )
    ca_total_weight = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Expected total CA marks (e.g. 30 or 40). Used only as a "
        "sanity-check warning when scores are uploaded — not enforced.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("code", "semester")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.code} ({self.semester})"


class CourseRoster(models.Model):
    """
    The per-course student list. Distinct from accounts.PreRegisteredStudent
    (which only gates account creation, globally): a student can register
    an account once, but must appear here, per course, before a result can
    be attributed to them on THIS course.
    """

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="roster")
    reg_number = models.CharField(max_length=20, validators=[reg_number_validator])
    name = models.CharField(max_length=150)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("course", "reg_number")
        ordering = ["reg_number"]

    def __str__(self):
        return f"{self.reg_number} — {self.course.code}"


class UploadBatch(models.Model):
    """
    Every result upload creates a NEW batch rather than overwriting scores
    in place. Only one batch per course is `is_active` at a time — that's
    the one students see — but older batches stay in the database as an
    audit trail of what changed and when.
    """

    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="upload_batches"
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    original_filename = models.CharField(max_length=255)
    assessment_columns = models.JSONField(
        help_text="Ordered list of [name, max_score] pairs used in this upload."
    )
    is_active = models.BooleanField(default=True)
    accepted_row_count = models.PositiveIntegerField(default=0)
    rejected_row_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.course.code} upload @ {self.uploaded_at:%Y-%m-%d %H:%M}"


class Result(models.Model):
    batch = models.ForeignKey(UploadBatch, on_delete=models.CASCADE, related_name="results")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="results")
    reg_number = models.CharField(max_length=20, validators=[reg_number_validator])
    name = models.CharField(max_length=150)
    scores = models.JSONField(help_text="{column_name: score_or_null}")

    # Raw, as-entered totals — kept for transparency/audit, not shown as
    # the headline number.
    raw_total_score = models.DecimalField(max_digits=7, decimal_places=2)
    raw_max_total = models.DecimalField(
        max_digits=7, decimal_places=2,
        help_text="Sum of max scores for columns that were actually graded this upload.",
    )

    # The headline number: raw score scaled to the course's CA total
    # (e.g. /40), regardless of how many of the possible assessment
    # columns were graded in this particular upload.
    total_score = models.DecimalField(max_digits=7, decimal_places=2)
    max_total = models.DecimalField(max_digits=7, decimal_places=2)

    low_fill_warning = models.BooleanField(
        default=False,
        help_text="Fewer than 3 (or fewer than the number of active columns, "
        "whichever is smaller) assessment columns had a score for this student.",
    )

    class Meta:
        ordering = ["reg_number"]

    def __str__(self):
        return f"{self.reg_number} — {self.course.code}"

    @property
    def percentage(self):
        if not self.max_total:
            return None
        return round((float(self.total_score) / float(self.max_total)) * 100, 1)