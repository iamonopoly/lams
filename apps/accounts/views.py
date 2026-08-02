from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from .decorators import role_required, superuser_required
from .forms import (
    AdminUserEditForm,
    LoginIdentifierForm,
    LecturerRegistrationForm,
    StudentRegistrationForm,
    StudentSetPasswordForm,
)
from .models import LecturerProfile, StudentProfile, User
from .tokens import account_activation_token


def _send_activation_email(request, user, url_name, subject, template_name):
    """
    Shared helper for both the lecturer-verification email and the
    student-password-setup email — same token mechanism, same email
    structure, different destination URL and copy.
    """
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = account_activation_token.make_token(user)
    activation_path = reverse(url_name, kwargs={"uidb64": uid, "token": token})
    activation_url = request.build_absolute_uri(activation_path)

    message = render_to_string(
        template_name, {"user": user, "activation_url": activation_url}
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=None,  # uses DEFAULT_FROM_EMAIL
        recipient_list=[user.email],
    )


def student_register(request):
    if request.method == "POST":
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            roster_entry = form.roster_entry
            user = User.objects.create_user(
                email=form.cleaned_data["email"],
                full_name=roster_entry.full_name,
                role=User.Role.STUDENT,
                is_active=False,
            )
            StudentProfile.objects.create(
                user=user, reg_number=form.cleaned_data["reg_number"]
            )
            _send_activation_email(
                request,
                user,
                url_name="student_set_password",
                subject="Set up your CA Result Portal password",
                template_name="registration/emails/student_setup_email.txt",
            )
            return redirect("check_email")
    else:
        form = StudentRegistrationForm()

    return render(request, "registration/student_register.html", {"form": form})


def lecturer_register(request):
    if request.method == "POST":
        form = LecturerRegistrationForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password1"],
                full_name=form.cleaned_data["full_name"],
                role=User.Role.LECTURER,
                is_active=False,
            )
            LecturerProfile.objects.create(user=user)
            _send_activation_email(
                request,
                user,
                url_name="activate_lecturer",
                subject="Verify your CA Result Portal lecturer account",
                template_name="registration/emails/lecturer_verify_email.txt",
            )
            return redirect("check_email")
    else:
        form = LecturerRegistrationForm()

    return render(request, "registration/lecturer_register.html", {"form": form})


def check_email(request):
    return render(request, "registration/check_email.html")


def activate_lecturer(request, uidb64, token):
    """Lecturer already set a password at sign-up — this link only proves
    they own the institutional email address."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid, role=User.Role.LECTURER)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save(update_fields=["is_active"])
        auth_login(request, user)
        messages.success(request, "Your account is verified. Welcome!")
        return redirect("dashboard")

    return render(request, "registration/activation_invalid.html")


def student_set_password(request, uidb64, token):
    """Student's first-ever password is set here. This link is the only
    thing standing between a roster entry and a usable login, so the token
    is single-use (validated via account_activation_token, which becomes
    invalid the instant is_active flips to True)."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid, role=User.Role.STUDENT)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    valid_link = user is not None and account_activation_token.check_token(user, token)

    if not valid_link:
        return render(request, "registration/activation_invalid.html")

    if request.method == "POST":
        form = StudentSetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()  # sets the password
            user.is_active = True
            user.save(update_fields=["is_active"])
            auth_login(request, user)
            messages.success(request, "Password set. Welcome!")
            return redirect("dashboard")
    else:
        form = StudentSetPasswordForm(user)

    return render(request, "registration/student_set_password.html", {"form": form})


class EmailLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = LoginIdentifierForm


def dashboard_redirect(request):
    """Single named URL ('dashboard') that LOGIN_REDIRECT_URL points to.
    Sends the user to the correct role-specific dashboard so templates and
    other views never need an if/else on role just to build a link."""
    if not request.user.is_authenticated:
        return redirect("login")
    if request.user.is_student:
        return redirect("student_dashboard")
    return redirect("lecturer_dashboard")


@role_required(User.Role.STUDENT)
def student_dashboard(request):
    # Read-only aggregates for the dashboard stat cards. No calculation
    # logic here duplicates or overrides anything in apps.courses — this
    # just reads existing Result/Thread rows for display.
    from apps.courses.models import Result
    from apps.feedback.models import Thread

    reg_number = request.user.student_profile.reg_number
    results = Result.objects.filter(reg_number=reg_number, batch__is_active=True).select_related("course")
    result_count = results.count()
    avg_percentage = None
    if result_count:
        percentages = [r.percentage for r in results if r.percentage is not None]
        if percentages:
            avg_percentage = round(sum(percentages) / len(percentages), 1)

    open_threads = Thread.objects.filter(
        result__reg_number=reg_number, result__batch__is_active=True
    ).exclude(status="RESOLVED").count()

    recent_results = results.order_by("-id")[:4]

    return render(request, "dashboard/student_dashboard.html", {
        "result_count": result_count,
        "avg_percentage": avg_percentage,
        "open_threads": open_threads,
        "recent_results": recent_results,
    })


@role_required(User.Role.LECTURER)
def lecturer_dashboard(request):
    # Same principle as above: read-only counts, no changes to how
    # courses/rosters/results actually work.
    from django.db.models import Count

    from apps.courses.models import Course
    from apps.feedback.models import Thread

    courses = Course.objects.filter(owner=request.user).annotate(
        roster_size=Count("roster", distinct=True)
    ).order_by("-created_at")

    course_count = courses.count()
    student_total = sum(c.roster_size for c in courses)
    pending_threads = Thread.objects.filter(
        result__course__owner=request.user, status="OPEN"
    ).count()

    recent_courses = courses[:4]

    return render(request, "dashboard/lecturer_dashboard.html", {
        "course_count": course_count,
        "student_total": student_total,
        "pending_threads": pending_threads,
        "recent_courses": recent_courses,
    })


class RoleLoginView(LoginView):
    """
    Shared machinery for the two role-specific login pages below. A
    student landing on the LECTURER page (or vice versa) with otherwise
    correct credentials is still rejected — the separation is enforced,
    not just cosmetic. extra_context feeds the template's role-based
    styling and copy.
    """

    template_name = "registration/login.html"
    authentication_form = LoginIdentifierForm
    redirect_authenticated_user = True
    expected_role = None  # set on each subclass

    def form_valid(self, form):
        user = form.get_user()
        if user.role != self.expected_role:
            wrong_way = "student" if self.expected_role == User.Role.LECTURER else "lecturer"
            right_way = "lecturer" if self.expected_role == User.Role.LECTURER else "student"
            form.add_error(
                None,
                f"That login belongs to a {wrong_way} account — this is the "
                f"{right_way} sign-in page.",
            )
            return self.form_invalid(form)
        return super().form_valid(form)


class StudentLoginView(RoleLoginView):
    expected_role = User.Role.STUDENT
    extra_context = {
        "role": "student",
        "role_label": "Student",
        "other_role_login_url": "lecturer_login",
        "register_url": "student_register",
    }


class LecturerLoginView(RoleLoginView):
    expected_role = User.Role.LECTURER
    extra_context = {
        "role": "lecturer",
        "role_label": "Lecturer",
        "other_role_login_url": "student_login",
        "register_url": "lecturer_register",
    }


def dashboard_redirect(request):
    """Single named URL ('dashboard') that LOGIN_REDIRECT_URL points to.
    Sends the user to the correct role-specific dashboard so templates and
    other views never need an if/else on role just to build a link."""
    if not request.user.is_authenticated:
        # Root ("/") is the student login now that student/lecturer no
        # longer share one gateway page — used as the sane generic
        # fallback here since this view doesn't know which role someone
        # was trying to reach.
        return redirect("student_login")
    if request.user.is_student:
        return redirect("student_dashboard")
    return redirect("lecturer_dashboard")

# ── Admin panel (superuser only) ─────────────────────────────────────────

@superuser_required
def admin_user_list(request):
    """Lecturers as a flat list; students grouped by the course they're
    on the roster for. A student enrolled in 3 courses appears once
    under each of those 3 course groups — that's intentional, since this
    view is organized by course, not by student."""
    from django.db.models import Count

    from apps.courses.models import Course

    lecturers = (
        User.objects.filter(role=User.Role.LECTURER)
        .annotate(course_count=Count("courses"))
        .order_by("full_name")
    )

    course_groups = []
    for course in Course.objects.select_related("owner").order_by("code"):
        reg_numbers = list(course.roster.values_list("reg_number", flat=True))
        students = (
            User.objects.filter(role=User.Role.STUDENT, student_profile__reg_number__in=reg_numbers)
            .select_related("student_profile")
            .order_by("full_name")
        )
        course_groups.append({
            "course": course,
            "students": students,
            "unregistered_count": len(reg_numbers) - students.count(),
        })

    return render(request, "accounts/admin_user_list.html", {
        "lecturers": lecturers,
        "course_groups": course_groups,
    })


@superuser_required
def admin_user_edit(request, user_id):
    user_obj = get_object_or_404(User, pk=user_id)

    if request.method == "POST":
        form = AdminUserEditForm(request.POST, instance=user_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f"Updated details for {user_obj.email}.")
            return redirect("admin_user_list")
    else:
        form = AdminUserEditForm(instance=user_obj)

    return render(request, "accounts/admin_user_edit.html", {"form": form, "edited_user": user_obj})


@superuser_required
def admin_user_delete(request, user_id):
    user_obj = get_object_or_404(User, pk=user_id)

    if user_obj.pk == request.user.pk:
        messages.error(request, "You can't delete your own account from here.")
        return redirect("admin_user_list")
    if user_obj.is_superuser:
        messages.error(request, "Other administrator accounts can't be deleted from this panel.")
        return redirect("admin_user_list")

    if request.method == "POST":
        email = user_obj.email
        user_obj.delete()
        messages.success(request, f"Deleted account: {email}.")

    return redirect("admin_user_list")


@login_required
def session_keepalive(request):
    """
    Hit by the idle-warning toast's 'Stay signed in' button. Doing
    nothing except returning 200 is enough — SESSION_SAVE_EVERY_REQUEST
    means Django resets the session's expiry on any authenticated
    request, including this one. If the session had ALREADY expired
    server-side, @login_required kicks the request to the login page
    instead of here, which the frontend treats as "already logged out."
    """
    return JsonResponse({"ok": True})