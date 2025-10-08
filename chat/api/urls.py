from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import ChatMessageViewSet

# Inicializa el router de DRF
router = DefaultRouter()

# Registra el ViewSet. 
# La base es 'messages' y el 'basename' es necesario para generar nombres de URL.
router.register(r'messages', ChatMessageViewSet, basename='chat-messages')

# urlpatterns ahora contiene todas las rutas generadas por el router (GET, POST, etc.)
urlpatterns = router.urls
