from channels.generic.websocket import AsyncWebsocketConsumer
import json


class QueueConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "patients"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        print("WebSocket connection established.")
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def patient_alert(self, event):
        message = event['message']
        print(f"Sending patient alert: {message}")
        await self.send(text_data=json.dumps({'message': message}))