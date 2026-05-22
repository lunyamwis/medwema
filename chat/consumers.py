import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

from .models import ChatRoom, ChatMessage

User = get_user_model()
logger = logging.getLogger(__name__)


def _display_name(user):
    return user.get_full_name().strip() or user.username


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope.get("user")

        if not self.user or not self.user.is_authenticated:
            logger.warning("Unauthenticated WebSocket connection rejected from %s", self.scope.get("client"))
            await self.close()
            return

        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.clinic = await self.get_clinic(self.user)

        # Each clinic gets its own isolated room and channel group
        clinic_id = self.clinic.id if self.clinic else "shared"
        self.room_group_name = f"chat_{clinic_id}_{self.room_name}"

        self.room = await self.get_or_create_room(self.room_name, self.clinic)

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        logger.info("Chat connected: user=%s room=%s clinic=%s", _display_name(self.user), self.room_name, clinic_id)
        history = await self.get_last_messages(self.room)
        await self.send(text_data=json.dumps({"type": "history", "messages": history}))

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            logger.debug("Chat disconnected: user=%s room=%s code=%s", getattr(self, "user", "?"), getattr(self, "room_name", "?"), close_code)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except (json.JSONDecodeError, ValueError):
            logger.warning("Chat receive: invalid JSON from user=%s", _display_name(self.user))
            return

        message = data.get("message", "").strip()
        if not message:
            return

        sender_name = _display_name(self.user)
        msg_obj = await self.save_message(self.room, self.user, message)

        logger.debug("Chat message saved: room=%s sender=%s msg_id=%s", self.room_name, sender_name, msg_obj.id)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat.message",
                "message": msg_obj.content,
                "sender": sender_name,
                "timestamp": msg_obj.created_at.isoformat(),
            },
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    # ── DB helpers ────────────────────────────────────────────────────────────

    @database_sync_to_async
    def get_clinic(self, user):
        return user.clinics.select_related().last()

    @database_sync_to_async
    def get_or_create_room(self, name, clinic):
        room, _ = ChatRoom.objects.get_or_create(name=name, clinic=clinic)
        return room

    @database_sync_to_async
    def save_message(self, room, user, content):
        return ChatMessage.objects.create(room=room, sender=user, content=content)

    @database_sync_to_async
    def get_last_messages(self, room, limit=50):
        return [
            {
                "sender": _display_name(msg.sender) if msg.sender else "System",
                "content": msg.content,
                "timestamp": msg.created_at.isoformat(),
            }
            for msg in room.messages.select_related("sender").order_by("-created_at")[:limit][::-1]
        ]
