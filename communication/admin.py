from django.contrib import admin
from .models import Conversation, Message, UserStatus

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'is_group', 'name', 'created_at', 'updated_at')
    filter_horizontal = ('participants',)
    list_filter = ('is_group', 'created_at')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'receiver', 'conversation', 
                    'content_preview', 'timestamp', 'read')
    list_filter = ('read', 'timestamp', 'conversation')
    search_fields = ('content', 'sender__username', 'receiver__username')
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'

@admin.register(UserStatus)
class UserStatusAdmin(admin.ModelAdmin):
    list_display = ('user', 'online', 'last_seen')
    list_filter = ('online',)

# Créer un superuser pour tester
# python manage.py createsuperuser