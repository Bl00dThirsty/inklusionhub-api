from django.urls import path
from communication.views import (
    ConversationFileHistoryAPIView,
    ConversationListView,
    CreateOrGetConversation,
    MessageListView,
    MessageListCreateView,
    MessageCreateView,
    MarkMessageReadView,
    UserListView,
    UserSearchView,
    UserStatusList,
)

urlpatterns = [
    # Conversations
    path("conversations/", ConversationListView.as_view(), name="conversation-list"),
    path(
        "conversations/create-or-get/",CreateOrGetConversation.as_view(),name="conversation-create-or-get"
    ),

    # Messages
    path(
        "conversations/<uuid:conversation_id>/messages/",MessageListView.as_view(),name="message-list"
    ),
    
     #  Liste des utilisateurs (excluant l’utilisateur connecté)
    path("users/", UserListView.as_view(), name="chat-users"),
    # Combinaison de la liste et de la création des messages
    path(
        "conversations/<uuid:conversation_id>/messages/list-create/",
        MessageListCreateView.as_view(),
        name="message-list-create"
    ),
    # Envoyer un message
    path("messages/", MessageCreateView.as_view(), name="message-create"),
    
    # Marquer un message comme lu
    path(
        "messages/<uuid:message_id>/read/",
        MarkMessageReadView.as_view(),
        name="message-read"
    ),
    
    #  Statut utilisateurs (liste)
   path("user-status/", UserStatusList.as_view(), name="user-status"),
#  Fichiers d’une conversation
   path(
        "conversations/<uuid:conversation_id>/files/",
        ConversationFileHistoryAPIView.as_view(),
        name="conversation-files"
    ),
   # Recherche d’utilisateurs
   path("users/search/", UserSearchView.as_view(), name="user-search"),
]
