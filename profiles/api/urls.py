from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SpecialistProfileViewSet, 
    BusinessmanProfileViewSet, 
    ConsumerProfileViewSet
)

# Crea un router y registra todos los ViewSets.
router = DefaultRouter()
# Rutas: api/v1/profiles/specialists/
router.register(r'specialists', SpecialistProfileViewSet, basename='specialist-profile')
# Rutas: api/v1/profiles/businessmen/
router.register(r'businessmen', BusinessmanProfileViewSet, basename='businessman-profile')
# Rutas: api/v1/profiles/consumers/
router.register(r'consumers', ConsumerProfileViewSet, basename='consumer-profile')

# Las URLs finales de esta aplicación
urlpatterns = [
    path('', include(router.urls)),
]
