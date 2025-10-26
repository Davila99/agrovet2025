# your_project_name/asgi.py

import os
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

# Importamos el routing de nuestra aplicación de chat
import chat.routing
from .middleware import QueryAuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'consultveterinarias.settings')

# Define el manejador ASGI principal
application = ProtocolTypeRouter({
    "http": get_asgi_application(), # Para las solicitudes HTTP normales (vistas)

    # Para las solicitudes WebSocket
    "websocket": QueryAuthMiddlewareStack(
        AuthMiddlewareStack(
            URLRouter(
                chat.routing.websocket_urlpatterns
            )
        )
    ),
})