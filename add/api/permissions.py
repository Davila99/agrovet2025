from rest_framework.permissions import BasePermission


class IsPublisherOrReadOnly(BasePermission):
    """Solo especialistas o empresarios pueden publicar; sólo el publisher puede modificar."""

    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        user = request.user
        # allow authenticated users who are specialist or businessman
        # Role values in User model may be capitalized or vary in case (e.g. 'Specialist').
        # Normalize to lowercase before checking to avoid accidental mismatch.
        role = getattr(user, 'role', None)
        if not (user and user.is_authenticated and role):
            return False
        return role.lower() in ['specialist', 'businessman']

    def has_object_permission(self, request, view, obj):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return obj.publisher == request.user
