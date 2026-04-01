
from asgiref.sync import async_to_sync
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from rest_framework.pagination import PageNumberPagination
from channels.layers import get_channel_layer
from datetime import timedelta
from django.utils import timezone

from .models import Call, Conversation, Message, UserStatus
from .serializers import CallSerializer, ConversationSerializer, FileHistorySerializer, MessageSerializer, UserSerializer, UserStatusSerializer

User = get_user_model()

#  Liste des conversations de l’utilisateur connecté
class ConversationListView(generics.ListAPIView):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Retourne uniquement les conversations où l'utilisateur courant
        est participant. Ne renvoie que les conversations existantes.
        """
        return Conversation.objects.filter(
            participants=self.request.user
        ).prefetch_related("participants", "messages").distinct()

    def get_serializer_context(self):
        return {"request": self.request}


#  Liste des utilisateurs (excluant l’utilisateur connecté)
class UserListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return User.objects.exclude(id=self.request.user.id)


#  Messages d’une conversation
class MessageListView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        conversation = get_object_or_404(
            Conversation,
            id=self.kwargs["conversation_id"],
            participants=self.request.user
        )
        
        return Message.objects.filter(
            conversation=conversation,
           
        ).select_related("sender", "receiver")

    def get_serializer_context(self):
        return {"request": self.request}

#  Marquer un message comme lu
class MarkMessageReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, message_id):
        message = get_object_or_404(
            Message,
            id=message_id,
            conversation__participants=request.user
        )

        if message.sender == request.user:
            return Response(
                {"detail": "Impossible de marquer son propre message"},
                status=403
            )

        message.mark_as_read()
        return Response({"status": "read"})
    
#  Créer ou obtenir une conversation entre deux utilisateurs
class CreateOrGetConversation(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_id = request.data.get("user_id")
        other_user = get_object_or_404(User, id=user_id)

        # Chercher une conversation existante entre les deux
        conversation = Conversation.objects.filter(
            is_group=False,
            participants=request.user
        ).filter(
            participants=other_user
        ).first()

        if not conversation:
            conversation = Conversation.objects.create()
            conversation.participants.set([request.user, other_user])
            conversation.save()

        serializer = ConversationSerializer(conversation, context={"request": request})
        return Response(serializer.data, status=200)
 #  Supprimer un message (soft delete)   
class DeleteMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, message_id):
        msg = get_object_or_404(Message, id=message_id)

        #  sécurité
        if msg.sender != request.user:
            raise PermissionDenied("Tu ne peux pas supprimer ce message")

        for_everyone = request.data.get("for_everyone", False)

        if for_everyone:
            msg.deleted_for_everyone = True
            msg.content = ""
        else:
            msg.is_deleted = True

        msg.save()

        #  WEBSOCKET BROADCAST
        channel_layer = get_channel_layer()
# On notifie tous les participants de la conversation (y compris le sender) pour que le message soit supprimé de leur interface
        async_to_sync(channel_layer.group_send)(
            f"conversation_{msg.conversation.id}",
            {
                "type": "message_deleted",
                "message_id": str(msg.id),
                "conversation_id": str(msg.conversation.id),
                "for_everyone": for_everyone,
            }
        )

        return Response({"success": True})
#  Combinaison liste / création messages d’une conversation
class MessageListCreateView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
#  GET : liste des messages
    def get_queryset(self):
        conversation_id = self.kwargs.get("conversation_id")
        conversation = get_object_or_404(
            Conversation,
            id=conversation_id,
            participants=self.request.user
        )
        return Message.objects.filter(conversation=conversation).order_by("timestamp")
#  POST : création d’un message
    def perform_create(self, serializer):
        conversation_id = self.kwargs.get("conversation_id")
        conversation = get_object_or_404(
            Conversation,
            id=conversation_id,
            participants=self.request.user
        )

        file_obj = self.request.FILES.get("file")
        image_obj = self.request.FILES.get("image")

        # Création du message
        message = serializer.save(
            sender=self.request.user,
            conversation=conversation,
            image=image_obj,
            file=file_obj,
            file_name=file_obj.name if file_obj else None,
            file_size=file_obj.size if file_obj else None,
            is_read=False,      
            is_delivered=False,
            expires_at=timezone.now() + timedelta(days=3)
        )

        # Broadcast WebSocket immédiatement après le save
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        participants = message.conversation.participants.exclude(id=message.sender.id)

        message_data = {
            "id": str(message.id),
            "content": message.content or "",
            "sender": {
                "id": str(message.sender.id),
                "name": message.sender.get_full_name() or message.sender.email,
                "avatar": message.sender.avatar.url if hasattr(message.sender, "avatar") and message.sender.avatar else None,
            },
            "timestamp": message.timestamp.isoformat(),
            "read": message.is_read,
            "conversation_id": str(message.conversation.id),
            "image": message.image.url if message.image else None,
            "file": message.file.url if message.file else None,
            "fileName": message.file_name,
            "fileSize": message.file_size,
        }

        for participant in participants:
             # 1. Envoi du message (pour le chat ouvert)
            async_to_sync(channel_layer.group_send)(
                f"user_{participant.id}",
                {
                    "type": "ws_send", # Appelle la méthode async def chat_message ci-dessous
                    "payload": {
                        "type": "chat_message",
                        "data": message_data # On met les données ici
                    }
                }
            )
            
            # 2. Envoi de la NOTIFICATION (pour le store de notifications)
            async_to_sync(channel_layer.group_send)(
                    f"user_{participant.id}",
                    {
                        "type": "ws_send",
                        "payload": {
                            "type": "notification",
                            "data": {
                                "id": str(message.id),
                                "type": "new_message",
                                "conversation_id": str(message.conversation.id),
                                "sender": {
                                    "id": str(message.sender.id),
                                    "name": message.sender.get_full_name() or message.sender.email
                                },
                                "preview": (message.content[:50] + "...") if message.content else "Nouveau fichier reçu",
                                "timestamp": message.timestamp.isoformat()
                            }
                        }
                    }
            ) 


# =========================
# CALL HISTORY
# =========================
class CallHistoryView(generics.ListAPIView):
    serializer_class = CallSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Call.objects.filter(
            caller=user
        ) | Call.objects.filter(receiver=user)

        
#  Liste des statuts des utilisateurs (online/offline)
class UserStatusList(APIView):
      permission_classes = [IsAuthenticated]

      def get(self, request):
        """
        Retourne le statut (online/offline) de tous les autres utilisateurs
        """
        statuses = UserStatus.objects.exclude(user=request.user)
        serializer = UserStatusSerializer(
            statuses,
            many=True,
            context={"request": request}
        )
        return Response(serializer.data) 
           
# Historique des fichiers partagés dans une conversation (non expirés)
class ConversationFileHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        now = timezone.now()

        files = Message.objects.filter(
            conversation_id=conversation_id,
            expires_at__gt=now   
        ).exclude(
            file__isnull=True,
            image__isnull=True
        ).order_by("-timestamp")

        serializer = FileHistorySerializer(files, many=True)
        return Response(serializer.data)
    
 # Serializer pour les détails d’une conversation (participants, dernier message, etc.)
class UserSearchView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination

    def get_queryset(self):
        q = self.request.query_params.get("q", "")
        return User.objects.filter(
    name__icontains=q
).exclude(id=self.request.user.id)
        
        
        
class CommunicationStatsView(APIView):
    permission_classes = [IsAuthenticated]
#  Statistiques de communication pour l’utilisateur connecté
    def get(self, request):
        user = request.user

        #  Messages non lus
        unread_messages = Message.objects.filter(
            conversation__participants=user,
            is_read=False
        ).exclude(sender=user).count()

        #  Conversations récentes (7 derniers jours)
        recent_conversations = Conversation.objects.filter(
            participants=user,
            updated_at__gte=timezone.now() - timedelta(days=7)
        ).count()

        #  Contacts (participants uniques)
        contacts = User.objects.filter(
        conversations__participants=user
    ).exclude(id=user.id).distinct().count()

        #  Groupes
        groups = Conversation.objects.filter(
            participants=user,
            is_group=True
        ).count()

        return Response({
            "unreadMessages": unread_messages,
            "recentConversations": recent_conversations,
            "activeUsers": contacts,
            "groups": groups
        })        

