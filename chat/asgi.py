import os

# Asegurar que el módulo de settings está establecido antes de importar
# cualquier cosa que pueda tocar Django o modelos.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "consultveterinarias.settings")

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

# Import routing y middleware tras asegurar settings. El middleware de
# consulta por token es opcional: si su import falla haremos un fallback
# que no interfiere con la autenticación por sesión/default.
import chat.routing

try:
    from .middleware import QueryAuthMiddlewareStack
except Exception:
    QueryAuthMiddlewareStack = None


# Construir la aplicación WebSocket con un fallback seguro.
websocket_app = AuthMiddlewareStack(URLRouter(chat.routing.websocket_urlpatterns))
if QueryAuthMiddlewareStack:
    websocket_app = QueryAuthMiddlewareStack(websocket_app)

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": websocket_app,
})