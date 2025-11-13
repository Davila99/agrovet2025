from django.urls import re_path
from . import consumers

# Rutas WebSocket mínimas para pruebas y las rutas existentes.
websocket_urlpatterns = [
    # Ruta de prueba: ws://<host>/ws/test/
    re_path(r"ws/test/$", consumers.TestConsumer.as_asgi()),
]

# Añadir las rutas existentes (chat / presence) si los consumidores están
# disponibles para mantener compatibilidad con el proyecto.
if getattr(consumers, "ChatConsumer", None):
    websocket_urlpatterns.append(
        re_path(r"ws/chat/(?P<room_id>[^/]+)/$", consumers.ChatConsumer.as_asgi())
    )

if getattr(consumers, "PresenceConsumer", None):
    websocket_urlpatterns.append(re_path(r"ws/presence/$", consumers.PresenceConsumer.as_asgi()))