
from rest_framework import permissions

class IsConversationParticipant(permissions.BasePermission):
    """
    Permission personnalisée pour vérifier si l'utilisateur est un participant de la conversation
    """
    def has_object_permission(self, request, view, obj):
        # Pour les objets Conversation
        if hasattr(obj, 'participants'):
            return request.user in obj.participants.all()
        
        # Pour les objets Message
        if hasattr(obj, 'conversation'):
            return request.user in obj.conversation.participants.all()
        
        return False

class IsMessageSenderOrReceiver(permissions.BasePermission):
    """
    Permission pour les messages - seul l'expéditeur ou le destinataire peut accéder
    """
    def has_object_permission(self, request, view, obj):
        return obj.sender == request.user or obj.receiver == request.user