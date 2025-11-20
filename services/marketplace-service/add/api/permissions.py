from rest_framework.permissions import BasePermission
import sys
import os

# Add common to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.http_clients.auth_client import get_auth_client


class IsPublisherOrReadOnly(BasePermission):
    """
    Solo especialistas o empresarios pueden publicar; sólo el publisher puede modificar.
    Valida roles con Auth Service.
    """

    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        
        # Obtener información del usuario desde Auth Service
        token = request.META.get('HTTP_AUTHORIZATION', '').replace('Token ', '').replace('Bearer ', '')
        if not token:
            return False
        
        auth_client = get_auth_client()
        user = auth_client.verify_token(token)
        if not user:
            return False
        
        role = user.get('role', '').lower()
        return role in ['specialist', 'businessman']

    def has_object_permission(self, request, view, obj):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        
        # Verificar que el usuario es el publisher
        token = request.META.get('HTTP_AUTHORIZATION', '').replace('Token ', '').replace('Bearer ', '')
        if not token:
            return False
        
        auth_client = get_auth_client()
        user = auth_client.verify_token(token)
        if not user:
            return False
        
        return obj.publisher_id == user.get('id')

