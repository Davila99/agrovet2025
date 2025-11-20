from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SpecialistProfileViewSet, 
    BusinessmanProfileViewSet, 
    ConsumerProfileViewSet
)

router = DefaultRouter()
router.register(r'specialists', SpecialistProfileViewSet, basename='specialist-profile')
router.register(r'businessmen', BusinessmanProfileViewSet, basename='businessman-profile')
router.register(r'consumers', ConsumerProfileViewSet, basename='consumer-profile')

urlpatterns = [
    path('', include(router.urls)),
]

