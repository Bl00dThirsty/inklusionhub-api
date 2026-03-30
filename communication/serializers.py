from ast import Call
from rest_framework import serializers
from .models import Conversation, Message, UserStatus, VoiceMessage
from django.contrib.auth import get_user_model

User = get_user_model()
# Serializer léger pour les utilisateurs
class UserSerializer(serializers.ModelSerializer):
    """Sérializer léger pour les utilisateurs"""
    full_name = serializers.SerializerMethodField()
    role_display = serializers.SerializerMethodField()
    online = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = [ 
            'id', 
            'email', 
            'name', 
            'forename',
            'full_name', 
            'role',
            'role_display',
            'avatar',
            'online'
        ]
     # Affiche le nom complet de l’utilisateur (en se basant sur la méthode get_full_name du modèle User)   
    def get_full_name(self, obj):
        return obj.get_full_name()
    # Affiche le rôle de l’utilisateur en français (en se basant sur la méthode get_role_display_fr du modèle User)
    def get_role_display(self, obj):
        return obj.get_role_display_fr()
    # Indique si l’utilisateur est en ligne (en se basant sur le statut utilisateur lié)
    def get_online(self, obj):
        return getattr(obj, "status", None) and obj.status.online
    
# =========================
# VOICE MESSAGE
# =========================
class VoiceMessageSerializer(serializers.ModelSerializer):
    audio = serializers.SerializerMethodField()


    class Meta:
        model = VoiceMessage
        fields = ["id", "audio", "duration"]

    def get_audio(self, obj):
        request = self.context.get("request")
        if obj.audio and request:
            return request.build_absolute_uri(obj.audio.url)
        return None
# =========================    
# Serializer pour les messages

class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    receiver = UserSerializer(read_only=True)
    voice = VoiceMessageSerializer(read_only=True)
    deleted_for_everyone = serializers.BooleanField(read_only=True)
    is_deleted = serializers.BooleanField(read_only=True)
    receiver_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='receiver',
        write_only=True,
        required=False,
        allow_null=True
    )
    file = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    file_name = serializers.CharField(read_only=True)
    file_size = serializers.IntegerField(read_only=True)
    is_own = serializers.SerializerMethodField()
    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'receiver',
            'sender_id', 'receiver_id', 'content', 'image', 'file',
            'file_name', 'file_size', 'timestamp', 'is_read', 'read_at', "voice", 'is_own','is_delivered',
            "deleted_for_everyone","is_deleted"
        ]
        read_only_fields = ['timestamp', 'is_read', 'read_at', 'file_name', 'file_size','is_delivered']
#  Indique si le message a été envoyé par l’utilisateur connecté (pour l’affichage côté client)
    def get_is_own(self, obj):
        user = self.context.get("user")
        return obj.sender == user if user else False

    # Retourne URL complète
    def get_file(self, obj):
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None
# Retourne URL complète
    def get_image(self, obj):
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None
    
    
# Serializer pour les conversations
class ConversationSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    other_participant = serializers.SerializerMethodField()
   #constraint : pour les conversations individuelles, on affiche uniquement les messages de l’autre participant (pour éviter de spoiler le dernier message envoyé par l’utilisateur lui-même) 
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
    # Affiche le dernier message de la conversation (pour les conversations individuelles, on affiche uniquement ceux de l’autre participant)
    def get_last_message(self, obj):
        last_msg = obj.messages.last()
        if last_msg:
            # CORRECTION : Utilise get_full_name() au lieu de username
            return {
                'content': last_msg.content,
                'sender': last_msg.sender.get_full_name(),
                'sender_id': last_msg.sender.id,
                'timestamp': last_msg.timestamp,
                'read': last_msg.is_read,         
                'delivered': last_msg.is_delivered
            }
        return None
#  Affiche l’autre participant (pour les conversations individuelles) ou None pour les groupes
    def get_other_participant(self, obj):
        request = self.context.get('request')
        if not request:
            return None

        user = request.user

        if obj.is_group:
            return None  # ou liste des autres

        other = obj.participants.exclude(id=user.id).first()

        return UserSerializer(other, context=self.context).data if other else None
#  Compte des messages non lus (pour les conversations individuelles, on compte uniquement ceux de l’autre participant)
    def get_unread_count(self, obj):
        user = self.context.get('request').user
        return obj.messages.filter(is_read=False).exclude(sender=user).count()
    
# =========================
# CALL (AUDIO / VIDEO)
# =========================
class CallSerializer(serializers.ModelSerializer):
    caller = UserSerializer(read_only=True)
    receiver = UserSerializer(read_only=True)
    duration = serializers.SerializerMethodField()

    class Meta:
        model = Call
        fields = [
            "id", "conversation",
            "caller", "receiver",
            "call_type",
            "started_at", "ended_at",
            "is_missed", "duration"
        ]

    def get_duration(self, obj):
        return obj.duration()    
# Serializer pour le statut utilisateur
class UserStatusSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserStatus
        fields = ['user', 'online', 'last_seen']
  # Serializer pour l'historique des fichiers dans les messages      
class FileHistorySerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.name")
    sender_id = serializers.CharField(source="sender.id")

    class Meta:
        model = Message
        fields = [
            "id",
            "file",
            "image",
            "timestamp",
            "sender_name",
            "sender_id",
        ]        