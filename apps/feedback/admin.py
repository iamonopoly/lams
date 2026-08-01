from django.contrib import admin

from .models import Comment, Thread


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ("sender", "body", "created_at")


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ("result", "status", "updated_at")
    list_filter = ("status",)
    inlines = [CommentInline]