
from rest_framework import permissions
# Permissions personnalisées pour les conversations et les messages, vérifiant que l'utilisateur est bien participant de la conversation ou expéditeur/destinataire du message avant d'autoriser l'accès.
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
# Permission pour les messages - seul l'expéditeur ou le destinataire peut accéder
class IsMessageSenderOrReceiver(permissions.BasePermission):
    """
    Permission pour les messages - seul l'expéditeur ou le destinataire peut accéder
    """
    def has_object_permission(self, request, view, obj):
        return obj.sender == request.user or obj.receiver == request.user