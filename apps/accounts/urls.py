from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path("register/student/", views.student_register, name="student_register"),
    path("register/lecturer/", views.lecturer_register, name="lecturer_register"),
    path("register/check-email/", views.check_email, name="check_email"),
    path(
        "activate/lecturer/<uidb64>/<token>/",
        views.activate_lecturer,
        name="activate_lecturer",
    ),
    path(
        "activate/student/<uidb64>/<token>/",
        views.student_set_password,
        name="student_set_password",
    ),
    path("login/student/", views.StudentLoginView.as_view(), name="student_login"),
    path("login/lecturer/", views.LecturerLoginView.as_view(), name="lecturer_login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard_redirect, name="dashboard"),
    path("dashboard/student/", views.student_dashboard, name="student_dashboard"),
    path("dashboard/lecturer/", views.lecturer_dashboard, name="lecturer_dashboard"),

    path("admin-panel/", views.admin_user_list, name="admin_user_list"),
    path("admin-panel/<int:user_id>/edit/", views.admin_user_edit, name="admin_user_edit"),
    path("admin-panel/<int:user_id>/delete/", views.admin_user_delete, name="admin_user_delete"),

    path("session-keepalive/", views.session_keepalive, name="session_keepalive"),
]