from django.urls import path

from . import views

urlpatterns = [
    path("thread/<int:result_id>/", views.thread_detail, name="thread_detail"),
    path("thread/<int:result_id>/resolve/", views.resolve_thread, name="resolve_thread"),
    path("inbox/", views.lecturer_inbox, name="lecturer_inbox"),
    path("inbox/<int:course_id>/", views.course_inbox, name="course_inbox"),
]