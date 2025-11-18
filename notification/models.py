from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Notification(models.Model):
    """
    Stores a notification that will be sent through WebPush + displayed in UI.
    Flexible enough for app notifications, reminders, alerts, etc.
    """

    # Who receives it — nullable for broadcast notifications
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="notifications", null=True, blank=True
    )

    # Optional grouping (e.g. "lab", "doctors", "admins")
    group_name = models.CharField(max_length=100, blank=True, null=True)

    # Notification content
    title = models.CharField(max_length=255)
    body = models.TextField()

    # Optional target URL for click actions
    url = models.URLField(blank=True, null=True)

    # Optional icon displayed in notification
    icon = models.URLField(blank=True, null=True)

    # Whether the user already interacted with the notification
    is_read = models.BooleanField(default=False)

    # Additional metadata/payload for the service worker
    data = models.JSONField(blank=True, null=True)

    # When it was created
    created_at = models.DateTimeField(default=timezone.now)

    # For scheduling (optional)
    send_at = models.DateTimeField(blank=True, null=True)

    def mark_read(self):
        self.is_read = True
        self.save()

    def __str__(self):
        if self.user:
            return f"Notification → {self.user.username}: {self.title}"
        return f"Broadcast Notification: {self.title}"
