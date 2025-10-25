from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChatRoomViewSet, ChatMessageViewSet
from .. import views as chat_views

router = DefaultRouter()
router.register(r'rooms', ChatRoomViewSet, basename='chatroom')
router.register(r'messages', ChatMessageViewSet, basename='chatmessage')

urlpatterns = [
    path('', include(router.urls)),
    # demo page for manual websocket testing
    path('demo/', chat_views.demo_view, name='chat-demo'),
    path('test_client/', chat_views.test_client_view, name='chat-test-client'),
]
