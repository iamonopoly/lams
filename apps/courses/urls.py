from django.urls import path

from . import views

urlpatterns = [
    path("", views.course_list, name="course_list"),
    path("create/", views.course_create, name="course_create"),
    path("<int:course_id>/", views.course_detail, name="course_detail"),

    path("roster/template/", views.roster_template_download, name="roster_template_download"),
    path("<int:course_id>/roster/upload/", views.roster_upload, name="roster_upload"),
    path("<int:course_id>/roster/", views.roster_list, name="roster_list"),
    path("<int:course_id>/roster/<int:roster_id>/edit/", views.roster_edit, name="roster_edit"),
    path("<int:course_id>/roster/<int:roster_id>/delete/", views.roster_delete, name="roster_delete"),

    path("results/template/", views.result_template_download, name="result_template_download"),
    path("<int:course_id>/results/upload/", views.result_upload, name="result_upload"),
    path("<int:course_id>/results/<int:batch_id>/", views.batch_detail, name="batch_detail"),
    path("<int:course_id>/results/<int:batch_id>/activate/", views.batch_activate, name="batch_activate"),
    path("<int:course_id>/results/<int:batch_id>/delete/", views.batch_delete, name="batch_delete"),
    path(
        "<int:course_id>/results/<int:batch_id>/<int:result_id>/edit/",
        views.result_edit,
        name="result_edit",
    ),
    path(
        "<int:course_id>/results/<int:batch_id>/<int:result_id>/delete/",
        views.result_delete,
        name="result_delete",
    ),

    path("my-results/", views.my_results, name="my_results"),

    path("all-my-results/", views.all_my_results, name="all_my_results"),

    path("my-results/<int:result_id>/", views.my_result_detail, name="my_result_detail"), 
]