"""
ASGI config for chat-service project.
Includes WebSocket routing for real-time chat.
"""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chat_service.settings')

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

# Import routing and middleware after Django setup
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from chat.middleware import QueryAuthMiddlewareStack
from chat import routing

# ProtocolTypeRouter delegates between HTTP and WebSocket
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": QueryAuthMiddlewareStack(
        AuthMiddlewareStack(
            URLRouter(
                routing.websocket_urlpatterns
            )
        )
    ),
})

