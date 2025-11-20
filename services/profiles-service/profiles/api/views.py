"""
API views for Profiles service.
"""
from rest_framework import viewsets, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
import sys
import os
import logging

from ..models import SpecialistProfile, BusinessmanProfile, ConsumerProfile
from .serializers import (
    SpecialistProfileSerializer,
    BusinessmanProfileSerializer,
    ConsumerProfileSerializer
)

# Add common to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.http_clients.auth_client import get_auth_client
from common.http_clients.media_client import get_media_client
from common.events.kafka_producer import get_producer
from profiles.utils.supabase_utils import upload_image_to_supabase

logger = logging.getLogger(__name__)


class UserProfileViewSet(viewsets.ModelViewSet):
    """
    Clase base para ViewSets de perfiles.
    Asegura que un usuario solo pueda ver/modificar su propio perfil.
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filtrar por usuario autenticado."""
        if self.request.user.is_authenticated:
            # Obtener user_id del token (asumiendo que el token contiene user_id)
            # En producción, validar token con Auth Service
            user_id = getattr(self.request.user, 'id', None)
            if user_id:
                return self.queryset.filter(user_id=user_id)
        return self.queryset.none()

    def perform_create(self, serializer):
        """Asignar usuario actual al perfil."""
        # Verificar que el perfil no existe
        user_id = getattr(self.request.user, 'id', None)
        if not user_id:
            raise serializers.ValidationError("Usuario no autenticado correctamente.")
        
        if self.queryset.filter(user_id=user_id).exists():
            raise serializers.ValidationError(
                "Este usuario ya tiene un perfil de este tipo. Utilice PUT o PATCH para actualizarlo."
            )

        # Verificar que no tenga otro tipo de perfil
        has_spec = SpecialistProfile.objects.filter(user_id=user_id).exists()
        has_bus = BusinessmanProfile.objects.filter(user_id=user_id).exists()
        has_cons = ConsumerProfile.objects.filter(user_id=user_id).exists()

        if self.serializer_class == SpecialistProfileSerializer and (has_bus or has_cons):
            raise serializers.ValidationError(
                "El usuario ya tiene otro tipo de perfil. Sólo se permite un rol por usuario."
            )
        if self.serializer_class == BusinessmanProfileSerializer and (has_spec or has_cons):
            raise serializers.ValidationError(
                "El usuario ya tiene otro tipo de perfil. Sólo se permite un rol por usuario."
            )
        if self.serializer_class == ConsumerProfileSerializer and (has_spec or has_bus):
            raise serializers.ValidationError(
                "El usuario ya tiene otro tipo de perfil. Sólo se permite un rol por usuario."
            )

        # Guardar perfil
        instance = serializer.save(user_id=user_id)

        # Publicar evento
        try:
            producer = get_producer()
            producer.publish('profiles.events', 'profile.created', {
                'profile_id': instance.id,
                'user_id': user_id,
                'profile_type': self._get_profile_type(),
            })
        except Exception as e:
            logger.error(f"Failed to publish profile.created event: {e}")

        return instance

    def _get_profile_type(self):
        """Obtener tipo de perfil."""
        if self.serializer_class == SpecialistProfileSerializer:
            return 'specialist'
        elif self.serializer_class == BusinessmanProfileSerializer:
            return 'businessman'
        else:
            return 'consumer'


class SpecialistProfileViewSet(UserProfileViewSet):
    queryset = SpecialistProfile.objects.all()
    serializer_class = SpecialistProfileSerializer

    def create(self, request, *args, **kwargs):
        """Crear SpecialistProfile asignado al usuario autenticado."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def get_object(self):
        """Obtener el SpecialistProfile para el usuario indicado en la URL."""
        user_id = self.kwargs.get('pk')
        
        # Verificar permisos
        auth_user_id = getattr(self.request.user, 'id', None)
        if not (self.request.user.is_staff or auth_user_id == int(user_id)):
            raise PermissionDenied('No tiene permiso para acceder a este recurso.')

        # Verificar que el usuario existe en Auth Service
        auth_client = get_auth_client()
        user = auth_client.get_user(int(user_id))
        if not user:
            from rest_framework.exceptions import NotFound
            raise NotFound('Usuario no encontrado en Auth Service.')

        profile, created = SpecialistProfile.objects.get_or_create(user_id=int(user_id))
        return profile

    @action(detail=False, methods=['get', 'patch'], url_path=r'by-user/(?P<user_id>[^/.]+)')
    def by_user(self, request, user_id=None):
        """Endpoint semántico para obtener/actualizar el perfil por user id."""
        user_id_int = int(user_id)
        auth_user_id = getattr(request.user, 'id', None)

        # Security: allow only staff or the user themselves
        if not (request.user.is_staff or auth_user_id == user_id_int):
            raise PermissionDenied('No tiene permiso para acceder a este recurso.')

        profile, _ = SpecialistProfile.objects.get_or_create(user_id=user_id_int)

        if request.method == 'PATCH':
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            
            # Publicar evento
            try:
                producer = get_producer()
                producer.publish('profiles.events', 'profile.updated', {
                    'profile_id': profile.id,
                    'user_id': user_id_int,
                    'profile_type': 'specialist',
                })
            except Exception as e:
                logger.error(f"Failed to publish profile.updated event: {e}")
            
            return Response(serializer.data)

        serializer = self.get_serializer(profile)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def upload_work_images(self, request, pk=None):
        """Upload one or multiple images for this specialist profile."""
        profile = self.get_object()
        files = request.FILES.getlist('images') or [request.FILES.get('image')] if request.FILES.get('image') else []
        if not files:
            return Response({'detail': 'No files provided.'}, status=status.HTTP_400_BAD_REQUEST)

        created_media_ids = []
        media_client = get_media_client()

        for f in files:
            # Upload to Supabase
            url = upload_image_to_supabase(f, folder='media')
            if url:
                # Create Media record in Media Service via HTTP
                try:
                    import requests
                    media_service_url = os.getenv('MEDIA_SERVICE_URL', 'http://localhost:8001')
                    response = requests.post(
                        f"{media_service_url}/api/media/",
                        files={'image': f},
                        data={'name': f.name, 'description': request.data.get('description', '')},
                        timeout=10
                    )
                    if response.status_code == 201:
                        media_data = response.json()
                        created_media_ids.append(media_data.get('id'))
                except Exception as e:
                    logger.error(f"Failed to create media in Media Service: {e}")

        # Update profile with media IDs
        if created_media_ids:
            profile.work_images_ids = list(set(profile.work_images_ids + created_media_ids))
            profile.save()

        # Get full media objects
        media_list = media_client.get_multiple_media(created_media_ids) if created_media_ids else []
        return Response(media_list, status=status.HTTP_201_CREATED)


class BusinessmanProfileViewSet(UserProfileViewSet):
    queryset = BusinessmanProfile.objects.all()
    serializer_class = BusinessmanProfileSerializer

    def perform_create(self, serializer):
        """Override para publicar evento."""
        instance = super().perform_create(serializer)
        try:
            producer = get_producer()
            producer.publish('profiles.events', 'profile.created', {
                'profile_id': instance.id,
                'user_id': instance.user_id,
                'profile_type': 'businessman',
            })
        except Exception as e:
            logger.error(f"Failed to publish profile.created event: {e}")
        return instance


class ConsumerProfileViewSet(UserProfileViewSet):
    queryset = ConsumerProfile.objects.all()
    serializer_class = ConsumerProfileSerializer

    def perform_create(self, serializer):
        """Override para publicar evento."""
        instance = super().perform_create(serializer)
        try:
            producer = get_producer()
            producer.publish('profiles.events', 'profile.created', {
                'profile_id': instance.id,
                'user_id': instance.user_id,
                'profile_type': 'consumer',
            })
        except Exception as e:
            logger.error(f"Failed to publish profile.created event: {e}")
        return instance

