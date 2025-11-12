from rest_framework.permissions import BasePermission


class IsPublisherOrReadOnly(BasePermission):
    """Solo especialistas o empresarios pueden publicar; sólo el publisher puede modificar."""

    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        user = request.user
        # allow authenticated users who are specialist or businessman
        return bool(user and user.is_authenticated and getattr(user, 'role', None) in ['specialist', 'businessman'])

    def has_object_permission(self, request, view, obj):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return obj.publisher == request.user
