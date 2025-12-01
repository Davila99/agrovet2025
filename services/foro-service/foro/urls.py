from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import PostViewSet, CommentViewSet, ReactionViewSet, NotificationViewSet, CommunityViewSet
from .views import internal_add_user_to_communities

router = DefaultRouter()
router.register(r'posts', PostViewSet, basename='foro-posts')
router.register(r'comments', CommentViewSet, basename='foro-comments')
router.register(r'notifications', NotificationViewSet, basename='foro-notifications')
router.register(r'communities', CommunityViewSet, basename='foro-communities')

urlpatterns = [
    path('', include(router.urls)),
    path('internal/add_user/', internal_add_user_to_communities, name='internal-add-user'),
    path('reactions/', ReactionViewSet.as_view({'post': 'create'}), name='foro-reactions'),
    path('reactions/<int:pk>/remove/', ReactionViewSet.as_view({'delete': 'remove'}), name='foro-reaction-remove'),
]

