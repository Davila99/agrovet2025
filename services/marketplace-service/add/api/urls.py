from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AddViewSet, CategoryViewSet, FollowViewSet

router = DefaultRouter()
router.register(r'adds', AddViewSet, basename='add')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'follows', FollowViewSet, basename='follow')

urlpatterns = [
    path('', include(router.urls)),
]

