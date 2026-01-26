# Routes WebSocket
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # WebSocket unique par utilisateur (messages + présence)
    re_path(r'ws/user/$', consumers.UserConsumer.as_asgi()),
]