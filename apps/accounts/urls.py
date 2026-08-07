from django.urls import path

from . import views

# Note: student_login, student_register, lecturer_login, and
# lecturer_register are deliberately NOT here — they're registered
# directly in config/urls.py so they can live at root ("/", "/register/")
# and under the "/lams/lecturer/" prefix respectively, instead of both
# being nested under "/accounts/".
urlpatterns = [
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
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard_redirect, name="dashboard"),
    path("dashboard/student/", views.student_dashboard, name="student_dashboard"),
    path("dashboard/lecturer/", views.lecturer_dashboard, name="lecturer_dashboard"),
    path("session-keepalive/", views.session_keepalive, name="session_keepalive"),

    path("admin-panel/", views.admin_user_list, name="admin_user_list"),
    path("admin-panel/<int:user_id>/edit/", views.admin_user_edit, name="admin_user_edit"),
    path("admin-panel/<int:user_id>/delete/", views.admin_user_delete, name="admin_user_delete"),
]