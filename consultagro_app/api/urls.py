from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'vet-profiles', VetProfileViewSet)
router.register(r'agronomo-profiles', AgronomoProfileViewSet)
router.register(r'propietario-profiles', PropietarioProfileViewSet)
router.register(r'specialties', SpecialtyViewSet)
router.register(r'user-specialties', UserSpecialtyViewSet)
router.register(r'work-images', WorkImageViewSet)
router.register(r'chats', ChatViewSet)
router.register(r'messages', MessageViewSet)
router.register(r'blocks', BlockViewSet)
router.register(r'calls', CallViewSet)
router.register(r'notifications', NotificationViewSet)
router.register(r'ads', AdViewSet)
router.register(r'ad-images', AdImageViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
