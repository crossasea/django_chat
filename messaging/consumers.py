from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Message, Group, GroupMessage

User = get_user_model()

class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
        else:
            # Join user's personal group
            await self.channel_layer.group_add(f"user_{self.user.id}", self.channel_name)
            await self.accept()

    async def disconnect(self, close_code):
        if self.user.is_authenticated:
            await self.channel_layer.group_discard(f"user_{self.user.id}", self.channel_name)

    async def receive_json(self, content):
        action = content.get("action")

        if action == "send_message":
            await self.handle_send_message(content)

        elif action == "mark_read":
            await self.handle_batch_mark_read(content)

        elif action == "typing":
            await self.handle_typing(content)

        elif action == "stop_typing":
            await self.handle_stop_typing(content)

        elif action == "join_group":
            await self.handle_join_group(content)

        elif action == "send_group_message":
            await self.handle_send_group_message(content)
        elif action == "add_admin":
            await self.handle_add_admin(content)

    # --- Real-time Message Sending ---
    @database_sync_to_async
    def save_message(self, recipient_id, message_text, media_id=None):
        recipient = User.objects.get(id=recipient_id)
        message = Message.objects.create(
            sender=self.user,
            recipient=recipient,
            content=message_text
        )

        if media_id:
            from .models import MediaStore
            media = MediaStore.objects.get(id=media_id)
            message.media = media
            message.save()

        return {
            "id": message.id,
            "sender_id": self.user.id,
            "recipient_id": recipient.id,
            "content": message.content,
            "timestamp": str(message.timestamp),
            "media_url": media.file.url if media_id else None
        }

    async def handle_send_message(self, content):
        recipient_id = content.get("recipient_id")
        message_text = content.get("content")

        message_data = await self.save_message(recipient_id, message_text)

        # Send to recipient
        await self.channel_layer.group_send(
            f"user_{recipient_id}",
            {
                "type": "chat.message",
                "message": message_data
            }
        )

        # Echo back to sender (optional)
        await self.send_json({
            "event": "message_sent",
            "message": message_data
        })

    async def chat_message(self, event):
        await self.send_json({
            "event": "new_message",
            "message": event["message"]
        })

    # --- Batch Mark Read ---
    @database_sync_to_async
    def mark_messages_as_read(self, message_ids):
        updated = []
        messages = Message.objects.filter(id__in=message_ids, recipient=self.user)
        for message in messages:
            if not message.is_read:
                message.is_read = True
                message.save()
                updated.append((message.id, message.sender.id))
        return updated

    async def handle_batch_mark_read(self, content):
        message_ids = content.get("message_ids", [])
        updated = await self.mark_messages_as_read(message_ids)

        for msg_id, sender_id in updated:
            await self.channel_layer.group_send(
                f"user_{sender_id}",
                {
                    "type": "message.read",
                    "message_id": msg_id,
                    "reader_id": self.user.id
                }
            )

    async def message_read(self, event):
        await self.send_json({
            "event": "message_read",
            "message_id": event["message_id"],
            "reader_id": event["reader_id"]
        })

    # --- Typing Indicator ---
    async def handle_typing(self, content):
        recipient_id = content.get("recipient_id")
        await self.channel_layer.group_send(
            f"user_{recipient_id}",
            {
                "type": "chat.typing",
                "sender_id": self.user.id
            }
        )

    async def handle_stop_typing(self, content):
        recipient_id = content.get("recipient_id")
        await self.channel_layer.group_send(
            f"user_{recipient_id}",
            {
                "type": "chat.stop_typing",
                "sender_id": self.user.id
            }
        )

    async def chat_typing(self, event):
        await self.send_json({
            "event": "typing",
            "sender_id": event["sender_id"]
        })

    async def chat_stop_typing(self, event):
        await self.send_json({
            "event": "stop_typing",
            "sender_id": event["sender_id"]
        })

    @database_sync_to_async
    def is_member(self, group_id):
        from .models import Group
        try:
            group = Group.objects.get(id=group_id)
            return self.user in group.members.all()
        except Group.DoesNotExist:
            return False

    async def handle_join_group(self, content):
        group_id = content.get("group_id")
        if await self.is_member(group_id):
            await self.channel_layer.group_add(f"group_{group_id}", self.channel_name)
            await self.send_json({"event": "joined_group", "group_id": group_id})
        else:
            await self.send_json({"event": "error", "detail": "Not a member of the group"})
    
    @database_sync_to_async
    def save_group_message(self, group_id, content):
        from .models import Group, GroupMessage
        group = Group.objects.get(id=group_id)
        return GroupMessage.objects.create(group=group, sender=self.user, content=content)

    async def handle_send_group_message(self, content):
        group_id = content.get("group_id")
        message_text = content.get("content")

        if not await self.is_member(group_id):
            await self.send_json({"event": "error", "detail": "Not a member of group"})
            return

        message = await self.save_group_message(group_id, message_text)

        # Broadcast to group
        await self.channel_layer.group_send(
            f"group_{group_id}",
            {
                "type": "group.message",
                "group_id": group_id,
                "message": {
                    "id": message.id,
                    "sender_id": self.user.id,
                    "content": message.content,
                    "timestamp": str(message.timestamp)
                }
            }
        )

    async def group_message(self, event):
        await self.send_json({
            "event": "group_message",
            "group_id": event["group_id"],
            "message": event["message"]
        })

    @database_sync_to_async
    def is_group_admin(self, group_id):
        from .models import Group
        try:
            group = Group.objects.get(id=group_id)
            return self.user in group.admins.all()
        except Group.DoesNotExist:
            return False
        
    @database_sync_to_async
    def add_admin_to_group(self, group_id, user_id):
        group = Group.objects.get(id=group_id)
        if self.user not in group.admins.all():
            return False
        user = User.objects.get(id=user_id)
        if user in group.members.all():
            group.admins.add(user)
            return True
        return False

    async def handle_add_admin(self, content):
        group_id = content.get("group_id")
        user_id = content.get("user_id")
        if await self.add_admin_to_group(group_id, user_id):
            await self.send_json({"event": "admin_added", "group_id": group_id, "user_id": user_id})
        else:
            await self.send_json({"event": "error", "detail": "Unauthorized or invalid member"})
