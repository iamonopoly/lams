from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.decorators import role_required
from apps.accounts.models import PreRegisteredStudent, User

from . import excel_utils
from .forms import CourseForm, ExcelUploadForm, ResultEditForm, RosterEditForm
from .models import Course, CourseRoster, Result, UploadBatch


def _get_owned_course_or_403(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    if course.owner_id != request.user.id:
        raise PermissionDenied("You don't own this course.")
    return course


@role_required(User.Role.LECTURER)
def course_list(request):
    courses = Course.objects.filter(owner=request.user)
    return render(request, "courses/course_list.html", {"courses": courses})


@role_required(User.Role.LECTURER)
def course_create(request):
    if request.method == "POST":
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.owner = request.user
            course.save()
            messages.success(request, f"Course {course.code} created.")
            return redirect("course_detail", course_id=course.id)
    else:
        form = CourseForm()

    return render(request, "courses/course_form.html", {"form": form})


@role_required(User.Role.LECTURER)
def course_detail(request, course_id):
    course = _get_owned_course_or_403(request, course_id)
    roster_count = course.roster.count()
    batches = course.upload_batches.all()[:10]
    return render(
        request,
        "courses/course_detail.html",
        {"course": course, "roster_count": roster_count, "batches": batches},
    )


@role_required(User.Role.LECTURER)
def roster_template_download(request):
    wb = excel_utils.generate_roster_template()
    buffer = excel_utils.workbook_to_bytes(wb)
    return FileResponse(
        buffer,
        as_attachment=True,
        filename="roster_template.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@role_required(User.Role.LECTURER)
def result_template_download(request):
    wb = excel_utils.generate_result_template()
    buffer = excel_utils.workbook_to_bytes(wb)
    return FileResponse(
        buffer,
        as_attachment=True,
        filename="results_template.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@role_required(User.Role.LECTURER)
def roster_upload(request, course_id):
    course = _get_owned_course_or_403(request, course_id)

    if request.method == "POST":
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            valid_rows, errors, file_rejected = excel_utils.parse_roster_file(
                form.cleaned_data["file"]
            )

            if file_rejected:
                return render(
                    request,
                    "courses/upload_report.html",
                    {
                        "course": course,
                        "file_rejected": True,
                        "errors": errors,
                        "accepted_count": 0,
                        "upload_type": "roster",
                    },
                )

            # Upsert into both the course-specific roster AND the global
            # PreRegisteredStudent gate, so these newly-added students can
            # also go register an account.
            with transaction.atomic():
                for row in valid_rows:
                    CourseRoster.objects.update_or_create(
                        course=course,
                        reg_number=row["reg_number"],
                        defaults={"name": row["name"]},
                    )
                    PreRegisteredStudent.objects.update_or_create(
                        reg_number=row["reg_number"],
                        defaults={"full_name": row["name"]},
                    )

            return render(
                request,
                "courses/upload_report.html",
                {
                    "course": course,
                    "file_rejected": False,
                    "errors": errors,
                    "accepted_count": len(valid_rows),
                    "upload_type": "roster",
                },
            )
    else:
        form = ExcelUploadForm()

    return render(request, "courses/upload_form.html", {"course": course, "form": form, "upload_type": "roster"})


@role_required(User.Role.LECTURER)
def result_upload(request, course_id):
    course = _get_owned_course_or_403(request, course_id)
    known_reg_numbers = set(course.roster.values_list("reg_number", flat=True))
    ca_total = float(course.ca_total_weight) if course.ca_total_weight else excel_utils.DEFAULT_CA_TOTAL

    if request.method == "POST":
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            assessment_columns, valid_rows, errors, file_rejected = excel_utils.parse_result_file(
                form.cleaned_data["file"], known_reg_numbers=known_reg_numbers, ca_total=ca_total
            )

            if file_rejected:
                return render(
                    request,
                    "courses/upload_report.html",
                    {
                        "course": course,
                        "file_rejected": True,
                        "errors": errors,
                        "accepted_count": 0,
                        "upload_type": "results",
                    },
                )

            active_columns = [(n, m) for n, m in assessment_columns if m is not None]
            scaling_info = (
                f"Scores scaled to /{ca_total:g} based on {len(active_columns)} "
                f"graded column(s) totalling {sum(m for _, m in active_columns):g} raw marks."
                if valid_rows else None
            )

            with transaction.atomic():
                course.upload_batches.update(is_active=False)

                batch = UploadBatch.objects.create(
                    course=course,
                    uploaded_by=request.user,
                    original_filename=form.cleaned_data["file"].name,
                    assessment_columns=[
                        [n, float(m) if m is not None else None] for n, m in assessment_columns
                    ],
                    is_active=True,
                    accepted_row_count=len(valid_rows),
                    rejected_row_count=len(errors),
                )
                Result.objects.bulk_create([
                    Result(
                        batch=batch,
                        course=course,
                        reg_number=row["reg_number"],
                        name=row["name"],
                        scores=row["scores"],
                        raw_total_score=row["raw_total"],
                        raw_max_total=row["raw_max"],
                        total_score=row["ca_score"],
                        max_total=row["ca_total"],
                        low_fill_warning=row["low_fill_warning"],
                    )
                    for row in valid_rows
                ])

            return render(
                request,
                "courses/upload_report.html",
                {
                    "course": course,
                    "file_rejected": False,
                    "errors": errors,
                    "accepted_count": len(valid_rows),
                    "upload_type": "results",
                    "scaling_info": scaling_info,
                },
            )
    else:
        form = ExcelUploadForm()

    return render(
        request,
        "courses/upload_form.html",
        {"course": course, "form": form, "upload_type": "results"},
    )


@role_required(User.Role.STUDENT)
def my_results(request):
    reg_number = request.user.student_profile.reg_number
    results = (
        Result.objects.filter(reg_number=reg_number, batch__is_active=True)
        .select_related("course")
        .order_by("-course__created_at")
    )
    return render(request, "courses/my_results.html", {"results": results})


@role_required(User.Role.STUDENT)
def all_my_results(request):
    reg_number = request.user.student_profile.reg_number
    results = (
        Result.objects.filter(reg_number=reg_number, batch__is_active=True)
        .select_related("course")
        .order_by("-course__created_at")
    )
    return render(request, "courses/all_my_results.html", {"results": results})

@role_required(User.Role.STUDENT)
def my_result_detail(request, result_id):
    """Full CA breakdown for exactly ONE course's result — not the
    combined list. reg_number check stops a student opening someone
    else's result by guessing/incrementing the URL's id."""
    result = get_object_or_404(Result, pk=result_id, batch__is_active=True)
    if result.reg_number != request.user.student_profile.reg_number:
        raise PermissionDenied("This result doesn't belong to you.")
    return render(request, "courses/my_result_detail.html", {"result": result})



# ── Roster: view / edit / delete ─────────────────────────────────────────

@role_required(User.Role.LECTURER)
def roster_list(request, course_id):
    course = _get_owned_course_or_403(request, course_id)
    roster = course.roster.all()
    return render(request, "courses/roster_list.html", {"course": course, "roster": roster})


@role_required(User.Role.LECTURER)
def roster_edit(request, course_id, roster_id):
    course = _get_owned_course_or_403(request, course_id)
    entry = get_object_or_404(CourseRoster, pk=roster_id, course=course)

    if request.method == "POST":
        form = RosterEditForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            # Keep the account-registration gate consistent with an edited
            # name too — same upsert the Excel upload does.
            PreRegisteredStudent.objects.update_or_create(
                reg_number=entry.reg_number, defaults={"full_name": entry.name}
            )
            messages.success(request, "Roster entry updated.")
            return redirect("roster_list", course_id=course.id)
    else:
        form = RosterEditForm(instance=entry)

    return render(
        request, "courses/roster_edit.html", {"course": course, "form": form, "entry": entry}
    )


@role_required(User.Role.LECTURER)
def roster_delete(request, course_id, roster_id):
    course = _get_owned_course_or_403(request, course_id)
    entry = get_object_or_404(CourseRoster, pk=roster_id, course=course)

    if request.method == "POST":
        reg_number = entry.reg_number
        entry.delete()
        messages.success(request, f"Removed {reg_number} from the roster.")

    return redirect("roster_list", course_id=course.id)


# ── Upload batches: view / activate / delete ─────────────────────────────

@role_required(User.Role.LECTURER)
def batch_detail(request, course_id, batch_id):
    course = _get_owned_course_or_403(request, course_id)
    batch = get_object_or_404(UploadBatch, pk=batch_id, course=course)
    results = batch.results.all()
    return render(
        request,
        "courses/batch_detail.html",
        {"course": course, "batch": batch, "results": results},
    )


@role_required(User.Role.LECTURER)
def batch_activate(request, course_id, batch_id):
    course = _get_owned_course_or_403(request, course_id)
    batch = get_object_or_404(UploadBatch, pk=batch_id, course=course)

    if request.method == "POST":
        course.upload_batches.update(is_active=False)
        batch.is_active = True
        batch.save(update_fields=["is_active"])
        messages.success(
            request, f"'{batch.original_filename}' is now the active result set students see."
        )

    return redirect("batch_detail", course_id=course.id, batch_id=batch.id)


@role_required(User.Role.LECTURER)
def batch_delete(request, course_id, batch_id):
    course = _get_owned_course_or_403(request, course_id)
    batch = get_object_or_404(UploadBatch, pk=batch_id, course=course)

    if request.method == "POST":
        was_active = batch.is_active
        filename = batch.original_filename
        batch.delete()  # cascades to delete its Results too

        if was_active:
            # Don't leave students with nothing just because the newest
            # upload got deleted — fall back to the next most recent one.
            next_batch = course.upload_batches.order_by("-uploaded_at").first()
            if next_batch:
                next_batch.is_active = True
                next_batch.save(update_fields=["is_active"])

        messages.success(request, f"Deleted upload '{filename}'.")
        return redirect("course_detail", course_id=course.id)

    return redirect("batch_detail", course_id=course.id, batch_id=batch.id)


# ── Individual results within a batch: view / edit / delete ──────────────

@role_required(User.Role.LECTURER)
def result_edit(request, course_id, batch_id, result_id):
    course = _get_owned_course_or_403(request, course_id)
    batch = get_object_or_404(UploadBatch, pk=batch_id, course=course)
    result = get_object_or_404(Result, pk=result_id, batch=batch)
    active_columns = [(n, m) for n, m in batch.assessment_columns if m is not None]

    if request.method == "POST":
        form = ResultEditForm(request.POST, active_columns=active_columns)
        if form.is_valid():
            scores = dict(result.scores)  # preserves any inactive-column entries (always None)
            raw_total = Decimal("0")
            filled_count = 0

            for idx, (col_name, max_score) in enumerate(active_columns):
                value = form.cleaned_data[f"score_{idx}"]
                if value is None:
                    scores[col_name] = None
                else:
                    scores[col_name] = float(value)
                    raw_total += value
                    filled_count += 1

            raw_max = sum(Decimal(str(m)) for _, m in active_columns)
            result.scores = scores
            result.raw_total_score = raw_total
            result.raw_max_total = raw_max
            result.total_score = (
                round(float(raw_total) / float(raw_max) * float(result.max_total), 1)
                if raw_max
                else 0
            )
            low_fill_threshold = min(3, len(active_columns))
            result.low_fill_warning = filled_count < low_fill_threshold
            result.save()

            messages.success(request, f"Updated scores for {result.reg_number}.")
            return redirect("batch_detail", course_id=course.id, batch_id=batch.id)
    else:
        initial = {
            f"score_{idx}": result.scores.get(col_name)
            for idx, (col_name, _) in enumerate(active_columns)
        }
        form = ResultEditForm(initial=initial, active_columns=active_columns)

    return render(
        request,
        "courses/result_edit.html",
        {"course": course, "batch": batch, "result": result, "form": form},
    )


@role_required(User.Role.LECTURER)
def result_delete(request, course_id, batch_id, result_id):
    course = _get_owned_course_or_403(request, course_id)
    batch = get_object_or_404(UploadBatch, pk=batch_id, course=course)
    result = get_object_or_404(Result, pk=result_id, batch=batch)

    if request.method == "POST":
        reg_number = result.reg_number
        result.delete()
        messages.success(request, f"Removed {reg_number} from this upload.")

    return redirect("batch_detail", course_id=course.id, batch_id=batch.id)