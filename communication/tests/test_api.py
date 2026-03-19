# communication/tests/test_api.py
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from communication.models import Conversation, Message
import json

User = get_user_model()

class ConversationAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Créer des utilisateurs
        self.user1 = User.objects.create_user(
            email='user1@test.com',
            name='User1',
            forename='Test',
            password='test123'
        )
        
        self.user2 = User.objects.create_user(
            email='user2@test.com',
            name='User2',
            forename='Test',
            password='test123'
        )
        
        self.user3 = User.objects.create_user(
            email='user3@test.com',
            name='User3',
            forename='Test',
            password='test123'
        )
        
        # Créer une conversation
        self.conversation = Conversation.objects.create()
        self.conversation.participants.add(self.user1, self.user2)
        
        # Créer quelques messages
        self.message1 = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            receiver=self.user2,
            content="Hello User2!"
        )
        
        self.message2 = Message.objects.create(
            conversation=self.conversation,
            sender=self.user2,
            receiver=self.user1,
            content="Hi User1!"
        )
        
        # URLs
        self.conversations_url = reverse('conversation-list')
        self.conversation_detail_url = reverse('conversation-detail', args=[self.conversation.id])
        self.conversation_messages_url = reverse('conversation-messages', args=[self.conversation.id])
    
    def test_get_conversations_authenticated(self):
        """Test récupération des conversations avec authentification"""
        # Authentifier user1
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.get(self.conversations_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_get_conversations_unauthenticated(self):
        """Test récupération des conversations sans authentification"""
        response = self.client.get(self.conversations_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_get_conversation_messages(self):
        """Test récupération des messages d'une conversation"""
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.get(self.conversation_messages_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_create_conversation_with_user(self):
        """Test création d'une conversation avec un autre utilisateur"""
        self.client.force_authenticate(user=self.user1)
        
        url = reverse('conversation-with-user') + f'?user_id={self.user3.id}'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('id', response.data)
        
        # Vérifie que la conversation a bien 2 participants
        conversation_id = response.data['id']
        conversation = Conversation.objects.get(id=conversation_id)
        self.assertEqual(conversation.participants.count(), 2)
        self.assertIn(self.user1, conversation.participants.all())
        self.assertIn(self.user3, conversation.participants.all())
    
    def test_mark_all_as_read(self):
        """Test marquer tous les messages comme lus"""
        self.client.force_authenticate(user=self.user1)
        
        # Créer un message non lu
        Message.objects.create(
            conversation=self.conversation,
            sender=self.user2,
            receiver=self.user1,
            content="Unread message",
            read=False
        )
        
        url = reverse('conversation-mark-all-read', args=[self.conversation.id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')

class MessageAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        self.user1 = User.objects.create_user(
            email='sender@test.com',
            name='Sender',
            forename='Test',
            password='test123'
        )
        
        self.user2 = User.objects.create_user(
            email='receiver@test.com',
            name='Receiver',
            forename='Test',
            password='test123'
        )
        
        self.conversation = Conversation.objects.create()
        self.conversation.participants.add(self.user1, self.user2)
        
        self.messages_url = reverse('message-list')
    
    def test_create_message(self):
        """Test création d'un message"""
        self.client.force_authenticate(user=self.user1)
        
        data = {
            'conversation': str(self.conversation.id),
            'content': 'Test message from API',
            'receiver_id': str(self.user2.id)
        }
        
        response = self.client.post(self.messages_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], 'Test message from API')
        self.assertEqual(response.data['sender']['email'], 'sender@test.com')
    
    def test_get_unread_messages(self):
        """Test récupération des messages non lus"""
        self.client.force_authenticate(user=self.user2)
        
        # Créer un message non lu
        Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            receiver=self.user2,
            content="Unread message",
            read=False
        )
        
        url = reverse('message-unread')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['content'], "Unread message")
    
    def test_mark_message_as_read(self):
        """Test marquer un message comme lu"""
        self.client.force_authenticate(user=self.user2)
        
        # Créer un message non lu
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            receiver=self.user2,
            content="Message to mark as read",
            read=False
        )
        
        url = reverse('message-mark-read', args=[message.id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['read'])
        
        # Rafraîchir l'objet depuis la base
        message.refresh_from_db()
        self.assertTrue(message.read)

class UserSearchAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        self.user = User.objects.create_user(
            email='searchuser@test.com',
            name='Search',
            forename='User',
            password='test123'
        )
        
        # Créer d'autres utilisateurs pour la recherche
        User.objects.create_user(
            email='john@test.com',
            name='Doe',
            forename='John',
            password='test123'
        )
        
        User.objects.create_user(
            email='jane@test.com',
            name='Smith',
            forename='Jane',
            password='test123'
        )
        
        self.search_url = reverse('user-search-search')
    
    def test_search_users(self):
        """Test recherche d'utilisateurs"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.search_url + '?q=john')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['forename'], 'John')
    
    def test_search_with_short_query(self):
        """Test recherche avec une requête trop courte"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.search_url + '?q=j')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)