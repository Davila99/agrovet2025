"""
WebSocket URL routing for chat service.
"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Chat room WebSocket
    re_path(r'ws/chat/(?P<room_id>[^/]+)/$', consumers.ChatConsumer.as_asgi()),
    # Presence WebSocket
    re_path(r'ws/presence/$', consumers.PresenceConsumer.as_asgi()),
]

