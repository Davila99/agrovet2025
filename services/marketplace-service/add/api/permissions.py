from rest_framework.permissions import BasePermission
import sys
import os
import logging

# Add common to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.http_clients.auth_client import get_auth_client

logger = logging.getLogger(__name__)


class IsPublisherOrReadOnly(BasePermission):
    """
    Solo especialistas o empresarios pueden publicar; sólo el publisher puede modificar.
    Valida roles con Auth Service.
    """

    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        
        # Obtener información del usuario desde Auth Service
        raw = request.META.get('HTTP_AUTHORIZATION', '')
        token = raw.replace('Token ', '').replace('Bearer ', '') if raw else ''
        if not token:
            logger.info(f"Permission denied: no Authorization header present for path={request.path} method={request.method}")
            return False

        auth_client = get_auth_client()
        user = auth_client.verify_token(token)
        if not user:
            logger.info(f"Permission denied: token verification failed for path={request.path} method={request.method}")
            return False

        role = user.get('role', '').lower()
        allowed = role in ['specialist', 'businessman']
        logger.debug(f"has_permission: user_id={user.get('id')} role={role} allowed={allowed} path={request.path}")
        return allowed

    def has_object_permission(self, request, view, obj):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        
        # Verificar que el usuario es el publisher
        raw = request.META.get('HTTP_AUTHORIZATION', '')
        token = raw.replace('Token ', '').replace('Bearer ', '') if raw else ''
        if not token:
            logger.info(f"Object permission denied: no Authorization header for path={request.path}")
            return False

        auth_client = get_auth_client()
        user = auth_client.verify_token(token)
        if not user:
            logger.info(f"Object permission denied: token verification failed for path={request.path}")
            return False

        allowed = obj.publisher_id == user.get('id')
        logger.debug(f"has_object_permission: user_id={user.get('id')} publisher_id={obj.publisher_id} allowed={allowed}")
        return allowed

