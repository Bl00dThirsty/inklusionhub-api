
# communication/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ConversationViewSet, 
    MessageViewSet, 
    UserSearchViewSet,
    ChatStatsViewSet
)

router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'messages', MessageViewSet, basename='message')
router.register(r'user-search', UserSearchViewSet, basename='user-search')
router.register(r'stats', ChatStatsViewSet, basename='chat-stats')

urlpatterns = [
    path('', include(router.urls)),
    
    # Routes supplémentaires
    path('conversations/<uuid:pk>/messages/', 
         ConversationViewSet.as_view({'get': 'messages'}), 
         name='conversation-messages'),
    
    path('conversations/<uuid:pk>/mark-all-read/', 
         ConversationViewSet.as_view({'post': 'mark_all_as_read'}), 
         name='conversation-mark-all-read'),
    
    path('messages/<uuid:pk>/mark-read/', 
         MessageViewSet.as_view({'post': 'mark_as_read'}), 
         name='message-mark-read'),
    path('messages/<uuid:pk>/mark-unread/', 
         MessageViewSet.as_view({'post': 'mark_as_unread'}), 
         name='message-mark-unread'),
    path('messages/<uuid:pk>/delete/', 
         MessageViewSet.as_view({'delete': 'delete_message'}), 
         name='message-delete'),
     
]