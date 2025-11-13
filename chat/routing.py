# chat/routing.py
from chat import consumers
from django.urls import re_path

websocket_urlpatterns = [
    re_path(r"ws/test/$", consumers.TestConsumer.as_asgi()),
]

if getattr(consumers, "ChatConsumer", None):
    websocket_urlpatterns.append(
        re_path(r"ws/chat/(?P<room_id>[^/]+)/$", consumers.ChatConsumer.as_asgi())
    )

if getattr(consumers, "PresenceConsumer", None):
    websocket_urlpatterns.append(
        re_path(r"ws/presence/$", consumers.PresenceConsumer.as_asgi())
    )
