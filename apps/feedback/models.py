from django.conf import settings
from django.db import models

from apps.courses.models import Result


class Thread(models.Model):
    """
    One thread per Result — a comment is always attached to a specific
    student+course result, never freeform. get_or_create'd lazily the
    first time either party opens the comment box on a result.
    """

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        LECTURER_RESPONDED = "LECTURER_RESPONDED", "Lecturer responded"
        RESOLVED = "RESOLVED", "Resolved"

    result = models.OneToOneField(Result, on_delete=models.CASCADE, related_name="thread")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Thread on {self.result} [{self.status}]"


class Comment(models.Model):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="comments")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender.email}: {self.body[:40]}"