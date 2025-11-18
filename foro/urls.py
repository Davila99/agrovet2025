from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import PostViewSet, CommentViewSet, ReactionViewSet, NotificationViewSet

router = DefaultRouter()
router.register(r'posts', PostViewSet, basename='foro-posts')
router.register(r'comments', CommentViewSet, basename='foro-comments')
router.register(r'notifications', NotificationViewSet, basename='foro-notifications')

urlpatterns = [
    path('', include(router.urls)),
    # Reactions handled separately (custom ViewSet)
    path('reactions/', ReactionViewSet.as_view({'post': 'create'}), name='foro-reactions'),
    path('reactions/<int:pk>/remove/', ReactionViewSet.as_view({'delete': 'remove'}), name='foro-reaction-remove'),
]
