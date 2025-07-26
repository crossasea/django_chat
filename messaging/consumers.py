from channels.generic.websocket import AsyncJsonWebsocketConsumer
from .models import Message, User

class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if self.user.is_authenticated:
            await self.accept()
        else:
            await self.close()

    async def receive_json(self, content):
        recipient_id = content.get('recipient_id')
        message = content.get('message')

        recipient = await User.objects.aget(id=recipient_id)
        msg = await Message.objects.acreate(
            sender=self.user, recipient=recipient, content=message
        )

        await self.send_json({
            'status': 'sent',
            'message_id': msg.id,
            'recipient': recipient.username,
            'content': msg.content,
        })

    async def disconnect(self, close_code):
        pass
