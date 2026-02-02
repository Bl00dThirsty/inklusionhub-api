 # Logique WebSocket# communication/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Conversation, Message, UserStatus
from .serializers import MessageSerializer
from datetime import datetime
import uuid

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    """
    Consommateur pour le chat en temps réel
    """
    async def connect(self):
        """Établit la connexion WebSocket"""
        self.user = self.scope['user']
        
        if self.user.is_anonymous:
            await self.close()
            return
        
        # Récupère l'ID de conversation depuis l'URL
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        
        # Vérifie si l'utilisateur peut accéder à cette conversation
        if not await self.is_user_in_conversation():
            await self.close()
            return
        
        # Rejoindre le groupe de la conversation
        self.room_group_name = f'chat_{self.conversation_id}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # Mettre à jour le statut en ligne
        await self.update_user_status(online=True)
        
        await self.accept()
        
        # Notifier les autres utilisateurs de la connexion
        await self.send_user_status_update(online=True)
    
    async def disconnect(self, close_code):
        """Gère la déconnexion WebSocket"""
        if hasattr(self, 'room_group_name') and hasattr(self, 'user'):
            # Quitter le groupe
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            
            # Mettre à jour le statut hors ligne
            await self.update_user_status(online=False)
            
            # Notifier les autres utilisateurs de la déconnexion
            await self.send_user_status_update(online=False)
    
    async def receive(self, text_data):
        """
        Reçoit un message du WebSocket
        Format attendu:
        {
            "type": "chat_message",
            "message": "Contenu du message",
            "receiver_id": "uuid",
            "image": "base64 ou URL" (optionnel)
        }
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'typing':
                await self.handle_typing_status(data)
            elif message_type == 'read_receipt':
                await self.handle_read_receipt(data)
                
        except json.JSONDecodeError:
            await self.send_error("Format JSON invalide")
        except Exception as e:
            await self.send_error(f"Erreur: {str(e)}")
    
    async def handle_chat_message(self, data):
        """Gère l'envoi d'un message"""
        content = data.get('message', '').strip()
        receiver_id = data.get('receiver_id')
        image_data = data.get('image')
        
        if not content and not image_data:
            await self.send_error("Message ou image requis")
            return
        
        # Crée le message en base de données
        message = await self.create_message(
            content=content,
            receiver_id=receiver_id,
            image_data=image_data
        )
        
        if message:
            # Sérialise le message
            serializer = MessageSerializer(message)
            message_data = serializer.data
            
            # Envoie le message à tous les membres du groupe
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message_data,
                    'sender_id': str(self.user.id)
                }
            )
    
    async def handle_typing_status(self, data):
        """Gère les notifications de saisie en cours"""
        is_typing = data.get('is_typing', False)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_status',
                'user_id': str(self.user.id),
                'user_name': self.user.get_full_name(),
                'is_typing': is_typing
            }
        )
    
    async def handle_read_receipt(self, data):
        """Gère les accusés de lecture"""
        message_id = data.get('message_id')
        
        if message_id:
            message = await self.mark_message_as_read(message_id)
            if message:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'read_receipt',
                        'message_id': str(message_id),
                        'read_by': str(self.user.id),
                        'read_at': message.read_at.isoformat() if message.read_at else None
                    }
                )
    
    # Handlers pour les événements de groupe
    
    async def chat_message(self, event):
        """Envoie un message à tous les clients WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'data': event['message']
        }))
    
    async def typing_status(self, event):
        """Envoie une notification de saisie en cours"""
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'user_name': event['user_name'],
            'is_typing': event['is_typing']
        }))
    
    async def read_receipt(self, event):
        """Envoie un accusé de lecture"""
        await self.send(text_data=json.dumps({
            'type': 'read_receipt',
            'message_id': event['message_id'],
            'read_by': event['read_by'],
            'read_at': event['read_at']
        }))
    
    async def user_status_update(self, event):
        """Envoie une mise à jour de statut utilisateur"""
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'user_id': event['user_id'],
            'online': event['online']
        }))
    
    # Méthodes utilitaires
    
    @database_sync_to_async
    def is_user_in_conversation(self):
        """Vérifie si l'utilisateur fait partie de la conversation"""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            return conversation.participants.filter(id=self.user.id).exists()
        except Conversation.DoesNotExist:
            return False
    
    @database_sync_to_async
    def create_message(self, content, receiver_id=None, image_data=None):
        """Crée un message en base de données"""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            
            # Trouve le receiver si spécifié
            receiver = None
            if receiver_id:
                try:
                    receiver = User.objects.get(id=receiver_id)
                except User.DoesNotExist:
                    pass
            
            # Pour l'instant, on gère simplement le texte
            # L'upload d'images sera fait via API REST (étape 6)
            message = Message.objects.create(
                conversation=conversation,
                sender=self.user,
                receiver=receiver,
                content=content
            )
            
            return message
        except Exception as e:
            print(f"Erreur création message: {e}")
            return None
    
    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        """Marque un message comme lu"""
        try:
            message = Message.objects.get(
                id=message_id,
                conversation_id=self.conversation_id
            )
            if message.receiver == self.user or not message.receiver:
                message.mark_as_read()
                return message
        except Message.DoesNotExist:
            return None
    
    @database_sync_to_async
    def update_user_status(self, online=True):
        """Met à jour le statut en ligne/hors ligne"""
        status, created = UserStatus.objects.get_or_create(
            user=self.user,
            defaults={'online': online}
        )
        if not created:
            status.online = online
            status.save()
    
    async def send_user_status_update(self, online):
        """Envoie une mise à jour de statut à la conversation"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status_update',
                'user_id': str(self.user.id),
                'online': online
            }
        )
    
    async def send_error(self, error_message):
        """Envoie un message d'erreur au client"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': error_message
        }))

class NotificationConsumer(AsyncWebsocketConsumer):
    """
    Consommateur pour les notifications générales (nouveaux messages, etc.)
    """
    async def connect(self):
        self.user = self.scope['user']
        
        if self.user.is_anonymous:
            await self.close()
            return
        
        # Groupe personnel pour les notifications
        self.user_group_name = f'notifications_{self.user.id}'
        
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
    
    async def send_notification(self, event):
        """Envoie une notification au client"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'data': event['data']
        }))