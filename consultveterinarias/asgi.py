"""
ASGI config for consultveterinarias project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

# Set the DJANGO_SETTINGS_MODULE early so imports that access Django settings
# or models (like chat.routing -> consumers -> models) won't fail during import.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'consultveterinarias.settings')

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Default Django ASGI app for standard HTTP requests
django_asgi_app = get_asgi_application()

# Import routing and middleware after Django setup to avoid importing models
# (chat.routing -> consumers -> models) before apps are loaded.
import chat.routing
from chat.middleware import QueryAuthMiddlewareStack


# ProtocolTypeRouter delegates between HTTP and WebSocket
application = ProtocolTypeRouter({
	"http": django_asgi_app,
	"websocket": QueryAuthMiddlewareStack(
		AuthMiddlewareStack(
			URLRouter(
				chat.routing.websocket_urlpatterns
			)
		)
	),
})
