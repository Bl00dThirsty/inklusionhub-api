import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer,AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from asgiref.sync import sync_to_async

from .models import Conversation, Message, UserStatus, VoiceMessage

User = get_user_model()


class UserConsumer(AsyncJsonWebsocketConsumer):
    """
    Consumer centralisé pour chat :
    - Messages
    - Notifications
    - Typing indicator
    - Read receipts
    - Présence online/offline
    """

    async def connect(self):
        self.user = self.scope["user"]

        if self.user.is_anonymous:
            print(" WS rejected: unauthenticated")
            # accepter AVANT de fermer
            await self.accept()
            await self.close(code=4001)
            return

        self.user_group = f"user_{self.user.id}"

        await self.channel_layer.group_add(
            self.user_group,
            self.channel_name
        )

        await self.accept()
        print(" WS accepted for", self.user.id)

        await self.increment_presence()
        await self.broadcast_presence(is_online=True)

        await self.send_json({
            "type": "connection",
            "status": "joined",
            "user_id": str(self.user.id)
        })
        print("WS USER:", self.scope["user"])


    async def disconnect(self, close_code):
        print(" WS DISCONNECT:", close_code)
        if not hasattr(self, "user") or self.user.is_anonymous:
         return  

        await self.decrement_presence()
        await self.broadcast_presence(is_online=False)

        await self.channel_layer.group_discard(
            f"user_{self.user.id}", self.channel_name
    )


    async def receive_json(self, content):
        event_type = content.get("type")

        if event_type == "send_message" or event_type == "chat_message":
            await self.handle_chat_message(content)
        elif event_type == "typing":
            await self.handle_typing(content)
        elif event_type == "read_receipt":
            await self.handle_read_receipt(content)
        elif event_type == "join_conversation":
            await self.handle_join_conversation(content)
        elif event_type == "leave_conversation":
            await self.handle_leave_conversation(content)
        elif event_type == "ping":
            await self.send_json({"type": "pong"})
        else:
            await self.send_json({"type": "error", "message": f"Unknown event type: {event_type}"})

    # ─── CHAT ─────────────────────────────────────────────
    async def handle_chat_message(self, data):
        conversation_id = data.get("conversation_id")
        content = data.get("content")

        if not conversation_id or not content:
            return
        
        if not await self.is_user_in_conversation(conversation_id):
          return
        conversation = await self.get_conversation(conversation_id)

        is_participant = await self.is_user_in_conversation(conversation)
        if not is_participant:
            return

        new_msg = await self.create_message(conversation_id, content)

        payload = {
            "type": "chat_message",
            "data": {
                "id": str(new_msg.id),
                "conversation_id": str(conversation_id),
                "content": new_msg.content,
                "sender": {
                    "id": str(self.user.id),
                    "name": self.user.get_full_name() or self.user.username
                },
                "timestamp": new_msg.timestamp.isoformat(),
                "is_read": False,
                "is_delivered": False,
            }
        }

        participants = await self.get_conversation_participants(conversation_id)
        
        #  Un seul envoi par participant via son user_group
        for participant in participants:
            print(f"[WS] Envoi message à participant: {participant.id}")
    # 1. message
            await self.channel_layer.group_send(
                f"user_{participant.id}",
                {
                    "type": "ws_send",
                    "payload": payload
                }
            )

            # 2. notification 
            if participant.id != self.user.id:  
                print(f"[WS] Envoi NOTIFICATION à: {participant.id}")
                await self.channel_layer.group_send(
                    f"user_{participant.id}",
                    {
                        "type": "ws_send",
                        "payload": {
                            "type": "notification",
                            "data": {
                                "id": str(new_msg.id),
                                "type": "new_message",
                                "conversation_id": str(conversation_id),
                                "sender": {
                                    "id": str(self.user.id),
                                    "name": self.user.get_full_name() or self.user.username
                                },
                                "preview": content[:50],
                                "timestamp": new_msg.timestamp.isoformat()
                            }
                        }
                    }
                )
                
        #  STATUT LIVRÉ : si le destinataire est en ligne, marquer livré immédiatement
            is_online = await self.is_user_online(participant.id)
            if is_online:
                await self.mark_as_delivered(new_msg.id)
                await self.channel_layer.group_send(
                    f"user_{self.user.id}",
                        {
                        "type": "ws_send",
                            "payload": {
                            "type": "delivered_receipt",
                            "data": {
                            "message_id": str(new_msg.id),
                            "conversation_id": str(conversation_id),
                                    }
                            }
                        }
                )
         
        # Push Celery
        try:
            from .tasks import async_send_push_notifications
            async_send_push_notifications.delay(str(new_msg.id))
        except Exception as e:
            print(f"DEBUG: Push ignoré ({e})")


       # ─── HANDLERS DE GROUPE (Indispensables pour le temps réel) ──────

    async def ws_send(self, event):
        """
        Ce handler reçoit les messages envoyés via :
        self.channel_layer.group_send(..., {"type": "ws_send", "payload": ...})
        """
        print(" WS SEND:", event["payload"]["type"])
        await self.send_json(event["payload"])

    async def presence(self, event):
        await self.send_json({
            "type": "presence",
            "data": event["data"]
        })

   # ─── TYPING ───────────────────────────────────────────
    async def handle_typing(self, data):
        conversation_id = data.get("conversation_id")
        is_typing = data.get("is_typing", False)

        if not conversation_id:
            return

        payload = {
            "type": "typing",
            "data": {
                "conversation_id": conversation_id,
                "user_id": str(self.user.id),
                "is_typing": is_typing,
                "timestamp": timezone.now().isoformat()
            }
        }

        await self.channel_layer.group_send(
            f"conversation_{conversation_id}",
            {
                "type": "ws_send",
                "payload": payload
            }
        )


    # ─── READ RECEIPT ─────────────────────────────────────
    async def handle_read_receipt(self, data):
        message_id = data.get("message_id")
        if not message_id:
            return

        result = await self.mark_message_read(message_id)
        if not result:
            return

        message = result["message"]
        #sender_id = result["sender_id"]
        conversation_id = result["conversation_id"]

        payload = {
            "type": "read_receipt",
            "data": {
                "message_id": str(message.id),
                "conversation_id": str(conversation_id),
                "reader_id": str(self.user.id),
                "read_at": message.read_at.isoformat()
            }
        }
        
        #conversation_id = await self.get_conversation_id(message)
      
      # Broadcast à tous les participants
        await self.channel_layer.group_send(
            f"conversation_{conversation_id}",
            {"type": "ws_send", "payload": payload}
        )

        # Notification à l'expéditeur
        
        await self.channel_layer.group_send(
            f"user_{message.sender.id}",
            {"type": "ws_send", "payload": payload}
        )

    async def handle_join_conversation(self, data):
        conv_id = data.get("conversation_id")
        group_name = f"conversation_{conv_id}"

        # Ajouter au groupe seulement si pas déjà dedans
        if not hasattr(self, '_joined_conversations'):
            self._joined_conversations = set()
        
        if conv_id in self._joined_conversations:
            return  # ← STOP si déjà joint
        
        self._joined_conversations.add(conv_id)
        await self.channel_layer.group_add(group_name, self.channel_name)

        last_messages = await self.get_last_messages(conv_id, limit=60)
        await self.send_json({
            "type": "conversation_history",
            "conversation_id": conv_id,
            "messages": last_messages
        })
        await self.send_json({
            "type": "join_success",
            "conversation_id": conv_id,
            "message_count": len(last_messages),
        })


        # Confirmer le join (optionnel : tu peux y mettre unread_count, participants, etc.)
        await self.send_json({
            "type": "join_success",
            "conversation_id": conv_id,
            # Bonus WhatsApp-like
            "message_count": len(last_messages),
            # "unread_count": await self.get_unread_count(conv_id)  # si tu implémentes
        })  


    async def handle_leave_conversation(self, data):
        conv_id = data.get("conversation_id")

        await self.channel_layer.group_discard(
            f"conversation_{conv_id}",
            self.channel_name
        )

        await self.send_json({
            "type": "leave_success",
            "conversation_id": conv_id
        })


    # ─── PRESENCE ─────────────────────────────────────────
    async def broadcast_presence(self, is_online: bool):
        contacts = await self.get_contacts()
        for contact in contacts:
            await self.channel_layer.group_send(
                f"user_{contact.id}",
                {
                    "type": "ws_send",
                    "payload": {
                        "type": "presence",
                        "data": {
                            "user_id": str(self.user.id),
                            "is_online": is_online,
                            "last_seen": None if is_online else timezone.now().isoformat()
                        }
                    }
                }
            )
    
    async def message_deleted(self, event):
        await self.send_json({
            "type": "message_deleted",
            "message_id": event["message_id"],
            "conversation_id": event["conversation_id"],
            "for_everyone": event["for_everyone"],
        })        

    # ─── DATABASE METHODS ──────────────────────────────────
    @database_sync_to_async
    def is_participant(self, conversation_id):
        try:
            conv = Conversation.objects.get(id=conversation_id)
            return conv.participants.filter(id=self.user.id).exists()
        except Conversation.DoesNotExist:
            return False
        
    @database_sync_to_async
    def is_user_in_conversation(self, conversation_id):
        return Conversation.objects.filter(
            id=conversation_id,
            participants__id=self.user.id
        ).exists()
 
    @database_sync_to_async
    def is_user_online(self, user_id):
        """ Vérifie si un utilisateur est connecté pour le statut livré"""
        try:
            status = UserStatus.objects.get(user_id=user_id)
            return status.online and status.connections > 0
        except UserStatus.DoesNotExist:
            return False
 
    @database_sync_to_async
    def mark_as_delivered(self, message_id):
        """ Marque le message comme livré (double coche)"""
        try:
            Message.objects.filter(id=message_id).update(is_delivered=True)
            return True
        except Exception:
            return False
 
    @database_sync_to_async
    def get_undelivered_messages(self):
        """
         RECONNEXION SYNC : récupère les messages reçus mais non livrés
        pendant que l'utilisateur était déconnecté
        """
        try:
            messages = Message.objects.filter(
                receiver=self.user,
                is_delivered=False,
            ).select_related('sender', 'conversation').order_by('timestamp')[:50]
 
            result = []
            for msg in messages:
                result.append({
                    "id": str(msg.id),
                    "conversation_id": str(msg.conversation.id),
                    "content": msg.content or "",
                    "sender": {
                        "id": str(msg.sender.id),
                        "name": msg.sender.get_full_name() or msg.sender.username,
                    },
                    "timestamp": msg.timestamp.isoformat(),
                    "is_read": msg.is_read,
                    "is_delivered": False,
                    "image": msg.image.url if msg.image else None,
                    "file": msg.file.url if msg.file else None,
                    "fileName": msg.file_name,
                    "fileSize": msg.file_size,
                })
 
            # Marquer comme livrés maintenant qu'on les envoie
            Message.objects.filter(
                receiver=self.user,
                is_delivered=False
            ).update(is_delivered=True)
 
            return result
        except Exception as e:
            print(f"[WS] get_undelivered_messages error: {e}")
            return []
    @database_sync_to_async
    def create_message(self, conversation_id, content):
        conversation = Conversation.objects.get(id=conversation_id)
        receiver = conversation.participants.exclude(id=self.user.id).first()
        return Message.objects.create(
            conversation=conversation,
            sender=self.user,
            receiver=receiver,
            content=content
        )

    @database_sync_to_async
    def mark_message_read(self, message_id):
        try:
            message = Message.objects.select_related("sender", "conversation").get(id=message_id)
            message.is_read = True
            message.read_at = timezone.now()
            message.save()
            return {
                "message": message,
                "sender_id": message.sender.id,
                "sender_email": message.sender.email,
                "conversation_id": message.conversation.id
            }
        except Message.DoesNotExist:
            return None


    @database_sync_to_async
    def get_conversation_participants(self, conversation_id):
        conversation = Conversation.objects.get(id=conversation_id)
        return list(conversation.participants.all())

    @database_sync_to_async
    def get_contacts(self):
        return list(
            User.objects.filter(conversations__participants=self.user)
                .exclude(id=self.user.id)
                .distinct()
        )
        
    @database_sync_to_async
    def get_conversation_id(self, message):
        return message.conversation.id
    
    @database_sync_to_async
    def get_conversation(self, conversation_id):
        return Conversation.objects.get(id=conversation_id)

    @database_sync_to_async
    def increment_presence(self):
        status, _ = UserStatus.objects.get_or_create(user=self.user)
        status.connections += 1
        status.online = True
        status.save()

    @database_sync_to_async
    def decrement_presence(self):
        status = UserStatus.objects.get(user=self.user)
        status.connections -= 1
        if status.connections <= 0:
            status.online = False
            status.last_seen = timezone.now()
        status.save()
    
    
    @database_sync_to_async
    def create_voice_message(self, conversation_id, voice_file, duration):
        conversation = Conversation.objects.get(id=conversation_id)
        receiver = conversation.participants.exclude(id=self.user.id).first()
        message = Message.objects.create(
            conversation=conversation,
            sender=self.user,
            receiver=receiver,
        )
        VoiceMessage.objects.create(
            message=message,
            audio=voice_file,
            duration=duration or 0
        )
        return message

    @database_sync_to_async
    def get_last_messages(self, conversation_id: str, limit: int = 50):
        from .models import Message
        
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            messages = Message.objects.filter(conversation=conversation)\
                                    .select_related('sender')\
                                    .order_by('-timestamp')[:limit]
            
            # Inverser pour avoir le plus ancien en premier (chronologique)
            messages = list(reversed(messages))
            
            return [
                {
                    "id": str(msg.id),
                    "conversation_id": str(msg.conversation.id),
                    "content": msg.content,
                    "sender": {
                        "id": str(msg.sender.id),
                        "name": msg.sender.get_full_name() or msg.sender.username or msg.sender.email,
                        "avatar": getattr(msg.sender, 'avatar_url', None)  # si tu as un champ avatar
                    },
                    "timestamp": msg.timestamp.isoformat(),
                    "read": msg.is_read,
                    # Ajoute si besoin : "voice": ..., "image": ..., etc.
                }
                for msg in messages
            ]
        except Conversation.DoesNotExist:
            return []
    
# Consumer dédié pour les appels (WebRTC signaling)
class ChatConsumer(AsyncWebsocketConsumer):
    async def receive_json(self, content):
        event_type = content.get("type")

        if event_type == "call.offer":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "call_offer",
                    "data": content
                }
            )

        elif event_type == "call.answer":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "call_answer",
                    "data": content
                }
            )

        elif event_type == "call.ice":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "call_ice",
                    "data": content
                }
            )

    async def call_offer(self, event):
        await self.send_json(event["data"])

    async def call_answer(self, event):
        await self.send_json(event["data"])

    async def call_ice(self, event):
        await self.send_json(event["data"])
    
    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            content = json.loads(text_data)
            await self.receive_json(content)
    
