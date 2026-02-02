# communication/utils/websocket_auth.py
from urllib.parse import parse_qs
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import jwt
from django.conf import settings

User = get_user_model()

@database_sync_to_async
def get_user_from_token(token):
    """Récupère l'utilisateur à partir d'un token JWT"""
    try:
        # Vérifie et décode le token
        decoded_token = AccessToken(token)
        user_id = decoded_token['user_id']
        
        # Récupère l'utilisateur
        user = User.objects.get(id=user_id)
        return user
    except (InvalidToken, TokenError, jwt.DecodeError, User.DoesNotExist):
        return AnonymousUser()

class JWTAuthMiddleware:
    """
    Middleware pour authentifier les connexions WebSocket avec JWT
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Récupère le token depuis les query parameters
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        
        token = query_params.get('token', [None])[0]
        
        if token:
            scope['user'] = await get_user_from_token(token)
        else:
            scope['user'] = AnonymousUser()
        
        return await self.app(scope, receive, send)