# chat_app/routing.py

from django.urls import re_path
from . import consumers as consumers

websocket_urlpatterns = [
    # Mapea la URL ws://.../ws/chat/1/ a ChatConsumer
    # <room_id> será capturado por el Consumer
    re_path(r'ws/chat/(?P<room_id>[^/]+)/$', consumers.ChatConsumer.as_asgi()),
    # Dedicated presence socket for background subscriptions
    re_path(r'ws/presence/$', consumers.PresenceConsumer.as_asgi()),
]