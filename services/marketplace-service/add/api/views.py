"""
API views for Marketplace service.
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
import sys
import os
import logging

from ..models import Add, Category, Follow
from .serializers import AddSerializer, CategorySerializer, FollowSerializer
from .permissions import IsPublisherOrReadOnly

# Add common to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.http_clients.auth_client import get_auth_client
from common.events.kafka_producer import get_producer

logger = logging.getLogger(__name__)


class AddViewSet(viewsets.ModelViewSet):
    queryset = Add.objects.all().select_related("category")
    serializer_class = AddSerializer
    permission_classes = [IsPublisherOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'condition', 'status']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'price']

    def perform_create(self, serializer):
        """Asignar publisher_id del usuario autenticado."""
        # Obtener user_id del token
        raw = self.request.META.get('HTTP_AUTHORIZATION', '')
        token = raw.replace('Token ', '').replace('Bearer ', '') if raw else ''
        # Log header presence and masked token for debugging
        try:
            masked = (token[:6] + '...' + token[-4:]) if token and len(token) > 10 else (token[:3] + '...' if token else '')
        except Exception:
            masked = ''
        logger.info(f"perform_create called path={self.request.path} method={self.request.method} Authorization_present={bool(raw)} token_mask={masked}")

        # Si no se provee Authorization, devolver error claro
        if not token:
            from rest_framework.exceptions import AuthenticationFailed
            logger.warning(f"perform_create: missing Authorization header for request to {self.request.path}")
            raise AuthenticationFailed('Se requiere Authorization header')

        auth_client = get_auth_client()
        try:
            logger.info(f"perform_create: contacting auth service at {auth_client.base_url}/api/auth/users/me/ to verify token")
        except Exception:
            pass
        user = auth_client.verify_token(token)
        if not user:
            from rest_framework.exceptions import AuthenticationFailed
            logger.warning(f"perform_create: token verification failed for token_mask={masked} path={self.request.path} - token may be invalid or Auth Service rejected it. Check auth-service logs for incoming verification requests.")
            raise AuthenticationFailed('Token inválido')
        
        serializer.save(publisher_id=user.get('id'))
        
        # Publicar evento
        try:
            producer = get_producer()
            producer.publish('marketplace.events', 'add.created', {
                'add_id': serializer.instance.id,
                'publisher_id': user.get('id'),
                'title': serializer.instance.title,
            })
        except Exception as e:
            logger.error(f"Failed to publish add.created event: {e}")
        logger.info(f"Add created id={serializer.instance.id} publisher_id={user.get('id')} title={serializer.instance.title}")

    def create(self, request, *args, **kwargs):
        """Override create para logging."""
        try:
            logger.info('AddViewSet.create called', extra={
                'user': getattr(request, 'user', None),
                'data_keys': list(request.data.keys())
            })
        except Exception:
            pass
        return super().create(request, *args, **kwargs)

    @action(detail=False, methods=["get"])
    def my_adds(self, request):
        """Anuncios del usuario autenticado."""
        raw = request.META.get('HTTP_AUTHORIZATION', '')
        token = raw.replace('Token ', '').replace('Bearer ', '') if raw else ''
        logger.debug(f"my_adds called Authorization_present={bool(raw)} path={request.path}")
        auth_client = get_auth_client()
        user = auth_client.verify_token(token)
        if not user:
            logger.info(f"my_adds: token verification failed for path={request.path}")
            return Response({'detail': 'No autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
        
        adds = Add.objects.filter(publisher_id=user.get('id'))
        return Response(self.get_serializer(adds, many=True).data)

    @action(detail=False, methods=["get"])
    def following_adds(self, request):
        """Anuncios de usuarios seguidos."""
        raw = request.META.get('HTTP_AUTHORIZATION', '')
        token = raw.replace('Token ', '').replace('Bearer ', '') if raw else ''
        logger.debug(f"following_adds called Authorization_present={bool(raw)} path={request.path}")
        auth_client = get_auth_client()
        user = auth_client.verify_token(token)
        if not user:
            logger.info(f"following_adds: token verification failed for path={request.path}")
            return Response({'detail': 'No autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
        
        user_id = user.get('id')
        followed_user_ids = Follow.objects.filter(follower_id=user_id).values_list('following_id', flat=True)
        adds = Add.objects.filter(publisher_id__in=followed_user_ids)
        return Response(self.get_serializer(adds, many=True).data)

    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """Anuncios cercanos por geolocalización."""
        try:
            lat = float(request.query_params.get('lat'))
            lon = float(request.query_params.get('lon'))
        except Exception:
            return Response({'detail': 'lat and lon are required params'}, status=400)
        
        radius_km = float(request.query_params.get('radius_km', 5))
        # Naive bounding box filter
        km_per_deg = 111
        delta = radius_km / km_per_deg
        adds = Add.objects.filter(
            latitude__gte=lat-delta,
            latitude__lte=lat+delta,
            longitude__gte=lon-delta,
            longitude__lte=lon+delta,
            status='active'
        )
        return Response(self.get_serializer(adds, many=True).data)

    def update(self, request, *args, **kwargs):
        """Override update para publicar evento."""
        response = super().update(request, *args, **kwargs)
        if response.status_code == 200:
            try:
                producer = get_producer()
                producer.publish('marketplace.events', 'add.updated', {
                    'add_id': self.get_object().id,
                })
            except Exception as e:
                logger.error(f"Failed to publish add.updated event: {e}")
        return response


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = []  # Public endpoint - no authentication required



class FollowViewSet(viewsets.ModelViewSet):
    queryset = Follow.objects.all()
    permission_classes = [IsPublisherOrReadOnly]
    serializer_class = FollowSerializer

    def create(self, request, *args, **kwargs):
        """Crear relación de seguimiento."""
        try:
            with transaction.atomic():
                raw = request.META.get('HTTP_AUTHORIZATION', '')
                token = raw.replace('Token ', '').replace('Bearer ', '') if raw else ''
                logger.debug(f"Follow.create called Authorization_present={bool(raw)} path={request.path}")
                auth_client = get_auth_client()
                user = auth_client.verify_token(token)
                if not user:
                    logger.info(f"Follow.create: token verification failed for path={request.path}")
                    return Response({'detail': 'No autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
                
                follower_id = user.get('id')
                following_id = request.data.get('following') or request.data.get('following_id')
                if not following_id:
                    return Response({'detail': 'following or following_id required'}, status=400)
                
                following_id = int(following_id)
                if following_id == follower_id:
                    return Response({'detail': 'No puedes seguirte a ti mismo.'}, status=400)
                
                follow, created = Follow.objects.get_or_create(
                    follower_id=follower_id,
                    following_id=following_id
                )
                if not created:
                    return Response({'detail': 'Ya sigues a este usuario.'}, status=400)
                
                return Response(self.get_serializer(follow).data, status=201)
        except Exception as e:
            return Response({'error': str(e)}, status=400)

    def destroy(self, request, *args, **kwargs):
        """Eliminar relación de seguimiento."""
        try:
            follow = self.get_object()
            raw = request.META.get('HTTP_AUTHORIZATION', '')
            token = raw.replace('Token ', '').replace('Bearer ', '') if raw else ''
            logger.debug(f"Follow.destroy called Authorization_present={bool(raw)} path={request.path}")
            auth_client = get_auth_client()
            user = auth_client.verify_token(token)
            if not user or follow.follower_id != user.get('id'):
                logger.info(f"Follow.destroy: permission denied user={user and user.get('id')} follower_id={follow.follower_id} path={request.path}")
                return Response({'detail': 'No tienes permiso para eliminar este seguimiento.'}, status=403)
            
            follow.delete()
            return Response({'detail': 'Has dejado de seguir a este usuario.'})
        except Exception as e:
            return Response({'error': str(e)}, status=400)

