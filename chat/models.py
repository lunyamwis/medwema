from django.conf import settings
from django.db import models

from clinicmanager.models import Clinic


class ChatRoom(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="chat_rooms", null=True, blank=True)
    name = models.CharField(max_length=255, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("clinic", "name")]

    def __str__(self) -> str:
        return self.name


class ChatMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="chat_messages")
    content = models.TextField()
    is_bot = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["room", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.room} | {self.content[:40]}"
