# config/asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from communication.routing import websocket_urlpatterns
from communication.middlewares import WebSocketAuthMiddleware
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

django_asgi_app = get_asgi_application()

websocket_app = WebSocketAuthMiddleware(
    URLRouter(websocket_urlpatterns)
)

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        WebSocketAuthMiddleware( # Ton middleware personnalisé
            URLRouter(websocket_urlpatterns)
        )
    ),
})