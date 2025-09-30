from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SpecialitysViewSet, BusinessOwnerViewSet, ProfesionalPerfilViewSet

router = DefaultRouter()
router.register(r'specialitys', SpecialitysViewSet)
router.register(r'business-owners', BusinessOwnerViewSet)
router.register(r'profesional-perfiles', ProfesionalPerfilViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
