from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def superuser_required(view_func):
    """
    For the admin panel — gated on Django's built-in is_superuser flag,
    not on Role, since a superuser's `role` is just LECTURER (set that
    way by create_superuser) and isn't a third login type of its own.
    Sends anonymous visitors to the lecturer login, since that's the
    flow a superuser account actually authenticates through.
    """

    @wraps(view_func)
    @login_required(login_url="admin_login")
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied("This area is restricted to administrators.")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def role_required(role):
    """
    Restricts a view to users with a specific role. Stacks on top of
    login_required, so anonymous users get redirected to login (not a
    403) and only authenticated users of the wrong role get denied.

    Since login now lives on two SEPARATE pages (root "/" for students,
    "/lams/lecturer/login/" for lecturers) rather than one shared
    gateway, the redirect target is picked per-role here — an anonymous
    visit to a lecturer-only page sends them to the lecturer login, not
    the student one, and vice versa.
    """

    def decorator(view_func):
        login_url_name = "student_login" if role == "STUDENT" else "lecturer_login"

        @wraps(view_func)
        @login_required(login_url=login_url_name)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.role != role:
                raise PermissionDenied(
                    "You don't have permission to view this page."
                )
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator