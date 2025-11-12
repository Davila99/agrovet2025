from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AddViewSet, CategoryViewSet, FollowViewSet

router = DefaultRouter()
router.register(r'adds', AddViewSet, basename='adds')
router.register(r'categories', CategoryViewSet, basename='categories')
router.register(r'follows', FollowViewSet, basename='follows')

urlpatterns = [
    path('', include(router.urls)),
]
