import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

from .models import ChatRoom, ChatMessage

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"chat_{self.room_name}"
        self.user = self.scope.get("user")

        self.room = await self.get_or_create_room(self.room_name)

        await self.channel_layer.group_add(
            self.room_group_name, self.channel_name
        )
        await self.accept()

        # Send last messages on connect
        history = await self.get_last_messages(self.room)
        await self.send(text_data=json.dumps({
            "type": "history",
            "messages": history,
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name, self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data["message"]

        msg_obj = await self.save_message(
            room=self.room,
            user=self.user if self.user.is_authenticated else None,
            content=message,
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat.message",
                "message": msg_obj.content,
                "sender": self.user.username if self.user.is_authenticated else "anonymous",
                "timestamp": msg_obj.created_at.isoformat(),
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    # ---------- DB helpers ----------

    @database_sync_to_async
    def get_or_create_room(self, name):
        return ChatRoom.objects.get_or_create(name=name)[0]

    @database_sync_to_async
    def save_message(self, room, user, content):
        return ChatMessage.objects.create(
            room=room,
            sender=user,
            content=content,
            is_bot=False,
        )

    @database_sync_to_async
    def get_last_messages(self, room, limit=50):
        return [
            {
                "sender": msg.sender.username if msg.sender else "bot",
                "content": msg.content,
                "is_bot": msg.is_bot,
                "timestamp": msg.created_at.isoformat(),
            }
            for msg in room.messages.all()[:limit]
        ]
