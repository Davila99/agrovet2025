# chat_app/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChatRoomViewSet

router = DefaultRouter()
router.register(r'rooms', ChatRoomViewSet, basename='chatroom')

urlpatterns = [
    # Las URLs generadas automáticamente son:
    # /api/chat/rooms/          -> GET (Listar salas), POST (Crear sala)
    # /api/chat/rooms/{id}/     -> GET (Detalle de sala)
    # /api/chat/rooms/{id}/messages/ -> GET (Listar mensajes de la sala)
    path('', include(router.urls)),
]