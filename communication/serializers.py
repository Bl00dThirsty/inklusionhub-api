from rest_framework import serializers
from .models import Conversation, Message, UserStatus
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """Sérializer léger pour les utilisateurs"""
    full_name = serializers.SerializerMethodField()
    role_display = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = [ 
            'id', 
            'email', 
            'name', 
            'forename',
            'role',
            'avatar'
        ]
    def get_full_name(self, obj):
        return obj.get_full_name()
    
    

class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    receiver = UserSerializer(read_only=True)
    sender_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='sender',
        write_only=True
    )
    receiver_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='receiver',
        write_only=True,
        required=False,
        allow_null=True
    )
    is_own = serializers.SerializerMethodField()
    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'receiver',
            'sender_id', 'receiver_id', 'content', 'image',
            'timestamp', 'read', 'read_at', 'is_own'
        ]
        read_only_fields = ['timestamp', 'read', 'read_at']
    def get_is_own(self, obj):
        """Vérifie si le message appartient à l'utilisateur courant"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            return obj.sender == request.user
        return False

class ConversationSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    other_participant = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 
            'participants', 
            'is_group', 
            'name',
            'created_at', 
            'updated_at', 
            'last_message', 
            'unread_count',
            'other_participant'
        ]
    
    def get_last_message(self, obj):
        last_msg = obj.messages.last()
        if last_msg:
            # CORRECTION : Utilise get_full_name() au lieu de username
            return {
                'content': last_msg.content,
                'sender': last_msg.sender.get_full_name(),  # ⬅️ CORRIGE ICI
                'timestamp': last_msg.timestamp
            }
        return None

class UserStatusSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserStatus
        fields = ['user', 'online', 'last_seen']