# communication/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Conversation, Message, UserStatus
from .serializers import MessageSerializer
from django.utils import timezone

User = get_user_model()

class UserConsumer(AsyncWebsocketConsumer):
    """
    Gestion centralisée :
    - messages (par conversation)
    - statut en ligne/hors ligne
    - notifications
    """

    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
            return

        # Groupe unique pour l'utilisateur → notifications + présence
        self.user_group_name = f"user_{self.user.id}"
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)

        await self.accept()

        # Mettre l'utilisateur en ligne
        await self.set_online(True)

        # Notifier tous ses interlocuteurs qu'il est en ligne
        await self.broadcast_presence(True)

    async def disconnect(self, close_code):
        await self.set_online(False)
        await self.broadcast_presence(False)
        await self.channel_layer.group_discard(self.user_group_name, self.channel_name)

    async def receive(self, text_data):
        """
        Reçoit tous les messages WS
        type peut être :
        - "chat_message"
        - "read_receipt"
        - "typing"
        """
        try:
            data = json.loads(text_data)
            msg_type = data.get("type")

            if msg_type == "chat_message":
                await self.handle_chat_message(data)
            elif msg_type == "read_receipt":
                await self.handle_read_receipt(data)
            elif msg_type == "typing":
                await self.handle_typing(data)
            elif msg_type == "notification":
                await self.handle_notification(data)
        except Exception as e:
            await self.send(text_data=json.dumps({"type": "error", "message": str(e)}))

    # -----------------------
    # Gestion messages
    # -----------------------
    async def handle_chat_message(self, data):
        conversation_id = data.get("conversation_id")
        content = data.get("message", "").strip()
        receiver_id = data.get("receiver_id")

        if not content:
            return

        message = await self.create_message(conversation_id, content, receiver_id)
        if message:
            serializer = MessageSerializer(message, context={"user": self.user})
            msg_data = serializer.data

            # Envoie uniquement aux participants de la conversation
            participants = await self.get_participants(conversation_id)
            for user_id in participants:
                await self.channel_layer.group_send(
                    f"user_{user_id}",
                    {
                        "type": "chat.message",
                        "message": msg_data
                    }
                )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({"type": "chat_message", "data": event["message"]}))

    # -----------------------
    # Gestion présence
    # -----------------------
    @database_sync_to_async
    def set_online(self, online: bool):
        status, _ = UserStatus.objects.get_or_create(user=self.user)
        status.online = online
        status.last_seen = timezone.now()
        status.save()

    async def broadcast_presence(self, online: bool):
        # Prévenir uniquement les utilisateurs des conversations partagées
        conversations = await self.get_user_conversations()
        for conv in conversations:
            participants = await self.get_participants(conv.id)
            for user_id in participants:
                if user_id != self.user.id:
                    await self.channel_layer.group_send(
                        f"user_{user_id}",
                        {
                            "type": "user.presence",
                            "user_id": str(self.user.id),
                            "online": online
                        }
                    )

    async def user_presence(self, event):
        await self.send(text_data=json.dumps({"type": "user_status", "user_id": event["user_id"], "online": event["online"]}))

    # -----------------------
    # Gestion lecture et typing
    # -----------------------
    async def handle_read_receipt(self, data):
        message_id = data.get("message_id")
        message = await self.mark_message_read(message_id)
        if message:
            participants = await self.get_participants(message.conversation.id)
            for user_id in participants:
                await self.channel_layer.group_send(
                    f"user_{user_id}",
                    {
                        "type": "read.receipt",
                        "message_id": str(message.id),
                        "reader_id": str(self.user.id)
                    }
                )

    async def read_receipt(self, event):
        await self.send(text_data=json.dumps({
            "type": "read_receipt",
            "message_id": event["message_id"],
            "reader_id": event["reader_id"]
        }))

    async def handle_typing(self, data):
        conversation_id = data.get("conversation_id")
        participants = await self.get_participants(conversation_id)
        for user_id in participants:
            if user_id != self.user.id:
                await self.channel_layer.group_send(
                    f"user_{user_id}",
                    {
                        "type": "user.typing",
                        "user_id": str(self.user.id),
                        "conversation_id": conversation_id,
                        "is_typing": data.get("is_typing", False)
                    }
                )

    async def user_typing(self, event):
        await self.send(text_data=json.dumps({
            "type": "typing",
            "user_id": event["user_id"],
            "conversation_id": event["conversation_id"],
            "is_typing": event["is_typing"]
        }))

    # -----------------------
    # Gestion notifications
    # -----------------------
    async def handle_notification(self, data):
        receiver_id = data.get("receiver_id")
        await self.channel_layer.group_send(
            f"user_{receiver_id}",
            {
                "type": "notification",
                "data": data.get("data")
            }
        )

    async def notification(self, event):
        await self.send(text_data=json.dumps({"type": "notification", "data": event["data"]}))

    # -----------------------
    # Méthodes DB
    # -----------------------
    @database_sync_to_async
    def create_message(self, conversation_id, content, receiver_id=None):
        conv = Conversation.objects.get(id=conversation_id)
        receiver = User.objects.filter(id=receiver_id).first() if receiver_id else None
        return Message.objects.create(conversation=conv, sender=self.user, receiver=receiver, content=content)

    @database_sync_to_async
    def get_user_conversations(self):
        return list(self.user.conversations.all())

    @database_sync_to_async
    def get_participants(self, conversation_id):
        conv = Conversation.objects.get(id=conversation_id)
        return [str(u.id) for u in conv.participants.all()]

    @database_sync_to_async
    def mark_message_read(self, message_id):
        try:
            msg = Message.objects.get(id=message_id)
            msg.mark_as_read()
            return msg
        except Message.DoesNotExist:
            return None
