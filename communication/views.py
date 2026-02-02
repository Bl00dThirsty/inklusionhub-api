
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.shortcuts import get_object_or_404
from .models import Conversation, Message
from .serializers import (
    ConversationSerializer, 
    MessageSerializer,
    UserSerializer as UserChatSerializer
)
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class ConversationViewSet(viewsets.ModelViewSet):
    """
    API pour gérer les conversations
    """
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'participants__name', 'participants__forename']
    ordering_fields = ['updated_at', 'created_at']
    
    def get_queryset(self):
        """
        Retourne uniquement les conversations de l'utilisateur connecté
        """
        user = self.request.user
        return Conversation.objects.filter(participants=user).order_by('-updated_at')
    
    def perform_create(self, serializer):
        """Crée une conversation avec l'utilisateur courant comme participant"""
        conversation = serializer.save()
        conversation.participants.add(self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_conversations(self, request):
        """Récupère toutes les conversations de l'utilisateur"""
        conversations = self.get_queryset()
        serializer = self.get_serializer(conversations, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def with_user(self, request):
        """
        Récupère ou crée une conversation avec un utilisateur spécifique
        Query params: user_id=<user_id>
        """
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response(
                {'error': 'user_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            other_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Empêche une conversation avec soi-même
        if other_user.id == request.user.id:
            return Response(
                {'error': 'Cannot create conversation with yourself'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Recherche une conversation existante
        conversation = Conversation.objects.filter(
            participants=request.user
        ).filter(
            participants=other_user
        ).filter(
            is_group=False
        ).first()
        
        # Crée une nouvelle conversation si elle n'existe pas
        if not conversation:
            conversation = Conversation.objects.create(is_group=False)
            conversation.participants.add(request.user, other_user)
        
        serializer = self.get_serializer(conversation)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Récupère tous les messages d'une conversation"""
        conversation = self.get_object()
        
        # Vérifie que l'utilisateur fait partie de la conversation
        if request.user not in conversation.participants.all():
            return Response(
                {'error': 'You are not a participant of this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        messages = conversation.messages.all().order_by('timestamp')
        page = self.paginate_queryset(messages)
        
        if page is not None:
            serializer = MessageSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_all_as_read(self, request, pk=None):
        """Marque tous les messages non lus d'une conversation comme lus"""
        conversation = self.get_object()
        
        # Marquer tous les messages non lus comme lus
        unread_messages = conversation.messages.filter(
            read=False
        ).exclude(
            sender=request.user
        )
        
        for message in unread_messages:
            message.mark_as_read()
        
        return Response({
            'status': 'success',
            'message': f'{unread_messages.count()} messages marqués comme lus'
        })

class MessageViewSet(viewsets.ModelViewSet):
    """
    API pour gérer les messages
    """
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['content']
    ordering_fields = ['timestamp', 'read']
    
    def get_queryset(self):
        """
        Retourne les messages des conversations de l'utilisateur
        """
        user = self.request.user
        
        # Récupère les IDs des conversations de l'utilisateur
        conversation_ids = Conversation.objects.filter(
            participants=user
        ).values_list('id', flat=True)
        
        return Message.objects.filter(
            conversation_id__in=conversation_ids
        ).order_by('-timestamp')
    
    def perform_create(self, serializer):
        """Crée un message avec l'expéditeur courant"""
        serializer.save(sender=self.request.user)
    
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Récupère tous les messages non lus de l'utilisateur"""
        user = request.user
        
        # Messages reçus et non lus
        unread_messages = Message.objects.filter(
            receiver=user,
            read=False
        ).order_by('timestamp')
        
        serializer = self.get_serializer(unread_messages, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Marque un message comme lu"""
        message = self.get_object()
        
        # Vérifie que l'utilisateur est le destinataire
        if message.receiver != request.user:
            return Response(
                {'error': 'You are not the receiver of this message'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        message.mark_as_read()
        serializer = self.get_serializer(message)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Recherche dans les messages"""
        query = request.query_params.get('q', '').strip()
        
        if not query or len(query) < 2:
            return Response(
                {'error': 'Query must be at least 2 characters'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Recherche dans les messages des conversations de l'utilisateur
        user_conversations = Conversation.objects.filter(
            participants=request.user
        )
        
        messages = Message.objects.filter(
            conversation__in=user_conversations,
            content__icontains=query
        ).order_by('-timestamp')
        
        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)

class UserSearchViewSet(viewsets.GenericViewSet):
    """
    API pour rechercher des utilisateurs pour démarrer une conversation
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Recherche des utilisateurs par nom, prénom ou email
        Exclut l'utilisateur courant
        """
        query = request.query_params.get('q', '').strip()
        
        if not query or len(query) < 2:
            return Response(
                {'error': 'Query must be at least 2 characters'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        users = User.objects.filter(
            Q(name__icontains=query) |
            Q(forename__icontains=query) |
            Q(email__icontains=query)
        ).exclude(
            id=request.user.id
        ).filter(
            is_active=True
        )[:20]  # Limite à 20 résultats
        
        serializer = UserChatSerializer(users, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recent_contacts(self, request):
        """
        Retourne les contacts récents (utilisateurs avec qui on a déjà eu une conversation)
        """
        # Récupère toutes les conversations de l'utilisateur
        conversations = Conversation.objects.filter(
            participants=request.user,
            is_group=False
        )
        
        # Récupère tous les autres participants
        recent_contacts_ids = set()
        for conversation in conversations:
            for participant in conversation.participants.all():
                if participant.id != request.user.id:
                    recent_contacts_ids.add(participant.id)
        
        # Récupère les utilisateurs
        recent_contacts = User.objects.filter(
            id__in=list(recent_contacts_ids)[:20]  # Limite à 20 contacts
        )
        
        serializer = UserChatSerializer(recent_contacts, many=True)
        return Response(serializer.data)

class ChatStatsViewSet(viewsets.GenericViewSet):
    """
    API pour les statistiques du chat
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Retourne les statistiques du chat pour l'utilisateur"""
        user = request.user
        
        # Nombre total de conversations
        total_conversations = Conversation.objects.filter(
            participants=user
        ).count()
        
        # Nombre de conversations non lues
        conversations_with_unread = 0
        user_conversations = Conversation.objects.filter(participants=user)
        
        for conversation in user_conversations:
            unread_count = conversation.messages.filter(
                read=False
            ).exclude(
                sender=user
            ).count()
            if unread_count > 0:
                conversations_with_unread += 1
        
        # Dernière activité
        last_message = Message.objects.filter(
            conversation__in=user_conversations
        ).order_by('-timestamp').first()
        
        return Response({
            'total_conversations': total_conversations,
            'conversations_with_unread': conversations_with_unread,
            'last_activity': last_message.timestamp.isoformat() if last_message else None,
            'last_activity_content': last_message.content[:50] + '...' if last_message else None,
            'user': {
                'id': user.id,
                'name': user.get_full_name(),
                'email': user.email,
                'role': user.role
            }
        })

# Create your views here.
