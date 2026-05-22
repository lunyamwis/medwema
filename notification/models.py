from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications", null=True, blank=True)
    group_name = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    title = models.CharField(max_length=255)
    body = models.TextField()
    url = models.URLField(blank=True, null=True)
    icon = models.URLField(blank=True, null=True)
    is_read = models.BooleanField(default=False, db_index=True)
    data = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    send_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read"]),
            models.Index(fields=["created_at"]),
        ]

    def mark_read(self) -> None:
        self.is_read = True
        self.save(update_fields=["is_read"])

    def __str__(self) -> str:
        if self.user:
            return f"→ {self.user}: {self.title}"
        return f"Broadcast: {self.title}"
