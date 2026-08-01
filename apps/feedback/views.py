from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.decorators import role_required
from apps.accounts.models import User
from apps.courses.models import Result

from .forms import CommentForm
from .models import Comment, Thread


def _get_thread_for_result(result):
    thread, _ = Thread.objects.get_or_create(result=result)
    return thread


def _check_access(request, result):
    """
    A student may only open a thread on their OWN result. A lecturer may
    only open a thread on a result belonging to a course they own. This
    is the boundary that stops one student from ever reading another
    student's comment thread.
    """
    user = request.user
    if user.is_student:
        if result.reg_number != user.student_profile.reg_number:
            raise PermissionDenied("This result doesn't belong to you.")
    elif user.is_lecturer:
        if result.course.owner_id != user.id:
            raise PermissionDenied("You don't own this course.")


def thread_detail(request, result_id):
    result = get_object_or_404(Result, pk=result_id)
    _check_access(request, result)
    thread = _get_thread_for_result(result)

    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            Comment.objects.create(
                thread=thread, sender=request.user, body=form.cleaned_data["body"]
            )
            # Status lifecycle: a lecturer reply marks the thread responded;
            # a student message (including reopening a resolved thread)
            # always puts it back in front of the lecturer as OPEN.
            if request.user.is_lecturer:
                thread.status = Thread.Status.LECTURER_RESPONDED
            else:
                thread.status = Thread.Status.OPEN
            thread.save(update_fields=["status", "updated_at"])
            messages.success(request, "Message sent.")
            return redirect("thread_detail", result_id=result.id)
    else:
        form = CommentForm()

    comments = thread.comments.select_related("sender")
    return render(
        request,
        "feedback/thread_detail.html",
        {"result": result, "thread": thread, "comments": comments, "form": form},
    )


def resolve_thread(request, result_id):
    result = get_object_or_404(Result, pk=result_id)
    _check_access(request, result)
    thread = _get_thread_for_result(result)

    if request.method == "POST":
        thread.status = Thread.Status.RESOLVED
        thread.save(update_fields=["status", "updated_at"])
        messages.success(request, "Thread marked as resolved.")

    return redirect("thread_detail", result_id=result.id)


@role_required(User.Role.LECTURER)
def lecturer_inbox(request):
    """
    Summary view — one clickable card per course, showing thread counts
    only. The full list of students who commented on a given course lives
    on course_inbox, reached by clicking that course's card.
    """
    from apps.courses.models import Course

    status_filter = request.GET.get("status")
    threads = Thread.objects.filter(result__course__owner=request.user).select_related(
        "result", "result__course"
    ).order_by("-updated_at")
    if status_filter in Thread.Status.values:
        threads = threads.filter(status=status_filter)

    courses_map = {}
    for thread in threads:
        course = thread.result.course
        courses_map.setdefault(course, []).append(thread)

    course_summaries = []
    for course, course_threads in courses_map.items():
        course_summaries.append({
            "course": course,
            "thread_count": len(course_threads),
            "latest_activity": course_threads[0].updated_at,  # newest first, from the order_by above
        })

    course_summaries.sort(key=lambda item: item["latest_activity"], reverse=True)

    return render(
        request,
        "feedback/lecturer_inbox.html",
        {
            "course_summaries": course_summaries,
            "status_filter": status_filter,
            "statuses": Thread.Status.choices,
        },
    )


@role_required(User.Role.LECTURER)
def course_inbox(request, course_id):
    """All students who've commented on ONE specific course — reached by
    clicking that course's card on the main inbox."""
    from apps.courses.models import Course

    course = get_object_or_404(Course, pk=course_id)
    if course.owner_id != request.user.id:
        raise PermissionDenied("You don't own this course.")

    status_filter = request.GET.get("status")
    threads = Thread.objects.filter(result__course=course).select_related(
        "result"
    ).order_by("-updated_at")
    if status_filter in Thread.Status.values:
        threads = threads.filter(status=status_filter)

    return render(
        request,
        "feedback/course_inbox.html",
        {
            "course": course,
            "threads": threads,
            "status_filter": status_filter,
            "statuses": Thread.Status.choices,
        },
    )