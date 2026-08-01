from django.contrib import admin

from .models import Course, CourseRoster, Result, UploadBatch


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "semester", "owner", "created_at")
    list_filter = ("semester",)
    search_fields = ("code", "title")


@admin.register(CourseRoster)
class CourseRosterAdmin(admin.ModelAdmin):
    list_display = ("reg_number", "name", "course", "added_at")
    list_filter = ("course",)
    search_fields = ("reg_number", "name")


@admin.register(UploadBatch)
class UploadBatchAdmin(admin.ModelAdmin):
    list_display = ("course", "uploaded_by", "uploaded_at", "is_active", "accepted_row_count", "rejected_row_count")
    list_filter = ("course", "is_active")


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ("reg_number", "name", "course", "total_score", "max_total", "low_fill_warning")
    list_filter = ("course", "low_fill_warning")
    search_fields = ("reg_number", "name")