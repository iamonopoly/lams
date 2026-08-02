"""
Root URL configuration.

Student and lecturer login/register deliberately live on two SEPARATE
URL trees rather than a shared gateway:
  - Students:  "/" (login) and "/register/"
  - Lecturers: "/lams/lecturer/login/" and "/lams/lecturer/register/"

Everything else (dashboards, courses, feedback, activation links, the
admin panel) stays under its existing app-prefixed path and is
unaffected by this split.
"""

from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from apps.accounts.views import (
    LecturerLoginView,
    StudentLoginView,
    lecturer_register,
    student_register,
)

urlpatterns = [
    # Student entry points — the primary/default audience, at root.
    path("", StudentLoginView.as_view(), name="student_login"),
    path("register/", student_register, name="student_register"),

    # Lecturer entry points — deliberately separate, under /lams/lecturer/.
    path("lams/lecturer/login/", LecturerLoginView.as_view(), name="lecturer_login"),
    path("lams/lecturer/register/", lecturer_register, name="lecturer_register"),

    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("courses/", include("apps.courses.urls")),
    path("feedback/", include("apps.feedback.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)