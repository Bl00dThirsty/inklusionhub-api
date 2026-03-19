# middlewares.py
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import AccessToken, TokenError # Ajout TokenError
from urllib.parse import parse_qs
from django.contrib.auth import get_user_model

User = get_user_model()

@database_sync_to_async
def get_user_from_db(user_id):
    try:
        return User.objects.get(id=user_id)
    except Exception:
        return AnonymousUser()

class WebSocketAuthMiddleware:
    def __init__(self, inner): # inner au lieu de app est la convention Channels
        self.inner = inner

    async def __call__(self, scope, receive, send):
        # 1. On récupère le token proprement
        query_string = scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)
        token = query_params.get("token", [None])[0]

        # 2. On initialise par défaut à Anonymous
        scope["user"] = AnonymousUser()

        if token:
            try:
                # Validation du Token
                access_token = AccessToken(token)
                user_id = access_token.get("user_id")
                
                if user_id:
                    # On récupère l'utilisateur en base
                    scope["user"] = await get_user_from_db(user_id)
                    print(f"[WS Auth] Succès: {scope['user']}")
            except (TokenError, Exception) as e:
                print(f"[WS Auth] Erreur Token: {e}")

        # 3. ON PASSE LE SCOPE À L'APPLICATION SUIVANTE
        return await self.inner(scope, receive, send)
