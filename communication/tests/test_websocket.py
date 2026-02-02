# communication/tests/test_websocket.py
import asyncio
from channels.testing import WebsocketCommunicator
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from inklusionhub_api.asgi import application  # ⬅️ CORRIGE CE NOM !
import json

User = get_user_model()

class WebSocketTests(TestCase):
    def setUp(self):
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
        
        # Créer un token JWT
        self.token1 = str(AccessToken.for_user(self.user1))
        self.token2 = str(AccessToken.for_user(self.user2))
    
    async def test_websocket_connection_async(self):
        """Test de connexion WebSocket"""
        communicator = WebsocketCommunicator(
            application,
            f"ws/chat/test-conversation/?token={self.token1}"
        )
        
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        
        await communicator.disconnect()
    
    # Méthode de wrapper pour Django TestCase
    def test_websocket_connection(self):
        """Wrapper pour exécuter le test async dans Django"""
        asyncio.run(self.test_websocket_connection_async())
    
    async def test_websocket_authentication_fail_async(self):
        """Test d'échec d'authentification"""
        communicator = WebsocketCommunicator(
            application,
            "ws/chat/test-conversation/?token=invalid_token"
        )
        
        connected, subprotocol = await communicator.connect()
        self.assertFalse(connected)  # Devrait échouer
    
    def test_websocket_authentication_fail(self):
        """Wrapper pour exécuter le test async dans Django"""
        asyncio.run(self.test_websocket_authentication_fail_async())