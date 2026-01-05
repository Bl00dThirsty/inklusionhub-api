from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid

class Conversation(models.Model):
    """
    Une conversation entre deux utilisateurs (ou groupe plus tard).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='conversations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_group = models.BooleanField(default=False)
    name = models.CharField(max_length=255, blank=True, null=True)  # Pour les groupes
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        if self.is_group:
            return f"Group: {self.name or self.id}"
        participants = list(self.participants.all()[:2])
        return f"Chat: {participants[0]} & {participants[1] if len(participants) > 1 else '...'}"

class Message(models.Model):
    """
    Modèle pour les messages du chat.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_messages',
        null=True,  # Null pour les messages de groupe
        blank=True
    )
    content = models.TextField(blank=True)  # Texte du message
    image = models.ImageField(
        upload_to='chat_images/',
        blank=True,
        null=True,
        max_length=500
    )
    timestamp = models.DateTimeField(default=timezone.now)
    read = models.BooleanField(default=False)  # Statut "vu"
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['conversation', 'timestamp']),
            models.Index(fields=['sender', 'receiver']),
        ]
    
    def __str__(self):
        return f"{self.sender} -> {self.receiver or 'Group'}: {self.content[:50]}"
    
    def mark_as_read(self):
        if not self.read:
            self.read = True
            self.read_at = timezone.now()
            self.save()

# Pour les stats de présence en ligne (préparation pour la partie live)
class UserStatus(models.Model):
    """
    Suivi de la présence en ligne des utilisateurs.
    
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_status'
    )
    online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.user}: {'Online' if self.online else 'Offline'}"
