"""ASGI config mínimo para pruebas de WebSocket.

Configura:
- HTTP usando get_asgi_application()
- WebSocket usando AuthMiddlewareStack + URLRouter con
  `chat.routing.websocket_urlpatterns`.

Compatible con Django 4.x y Channels 4.x.
"""

import os

# Asegurar el módulo de settings antes de importar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "consultveterinarias.settings")

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

import chat.routing


# ASGI application: HTTP y WebSocket
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(URLRouter(chat.routing.websocket_urlpatterns)),
})
