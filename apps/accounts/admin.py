from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import LecturerProfile, PreRegisteredStudent, StudentProfile, User


class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("email", "full_name", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active")
    search_fields = ("email", "full_name")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("full_name", "role")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "full_name", "role", "password1", "password2"),
            },
        ),
    )


@admin.register(PreRegisteredStudent)
class PreRegisteredStudentAdmin(admin.ModelAdmin):
    list_display = ("reg_number", "full_name", "added_at")
    search_fields = ("reg_number", "full_name")


admin.site.register(User, UserAdmin)
admin.site.register(StudentProfile)
admin.site.register(LecturerProfile)