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
import traceback

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
        """Retornar queryset base según el tipo de perfil."""
        if self.serializer_class == SpecialistProfileSerializer:
            return SpecialistProfile.objects.all()
        elif self.serializer_class == BusinessmanProfileSerializer:
            return BusinessmanProfile.objects.all()
        else:
            return ConsumerProfile.objects.all()

    def _get_profile_type(self):
        """Obtener tipo de perfil."""
        if self.serializer_class == SpecialistProfileSerializer:
            return 'specialist'
        elif self.serializer_class == BusinessmanProfileSerializer:
            return 'businessman'
        else:
            return 'consumer'

    def perform_create(self, serializer):
        """Guardar el perfil con el user_id del usuario autenticado."""
        # El user_id debe venir en los datos validados o del request
        user_id = serializer.validated_data.get('user_id')
        if not user_id:
            # Si no viene en los datos, intentar obtenerlo del usuario autenticado
            user_id = getattr(self.request.user, 'id', None)
        if user_id:
            instance = serializer.save(user_id=user_id)
        else:
            instance = serializer.save()
        
        # Publicar evento
        try:
            producer = get_producer()
            producer.publish('profiles.events', 'profile.created', {
                'profile_id': instance.id,
                'user_id': instance.user_id,
                'profile_type': self._get_profile_type(),
            })
        except Exception as e:
            logger.error(f"Failed to publish profile.created event: {e}")
        
        return instance


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
        
        try:
            user_id_int = int(user_id)
        except (ValueError, TypeError):
            from rest_framework.exceptions import NotFound
            raise NotFound('ID de usuario inválido.')
        
        # Verificar permisos
        auth_user_id = getattr(self.request.user, 'id', None)
        if not (self.request.user.is_staff or auth_user_id == user_id_int):
            raise PermissionDenied('No tiene permiso para acceder a este recurso.')

        # Verificar que el usuario existe en Auth Service
        try:
            auth_client = get_auth_client()
            # Pass through Authorization token so Auth Service can authorize the request
            raw = self.request.META.get('HTTP_AUTHORIZATION', '')
            token = raw.replace('Token ', '').replace('Bearer ', '') if raw else None
            user = auth_client.get_user(user_id_int, token=token)
            if not user:
                from rest_framework.exceptions import NotFound
                raise NotFound('Usuario no encontrado en Auth Service.')
        except Exception as e:
            logger.error(f"Error verificando usuario en Auth Service: {e}")
            logger.error(traceback.format_exc())
            from rest_framework.exceptions import APIException
            raise APIException('Error al verificar usuario. Revisa logs del servicio.')

        profile, created = SpecialistProfile.objects.get_or_create(user_id=user_id_int)
        return profile

    def update(self, request, *args, **kwargs):
        """Actualizar perfil (PUT/PATCH)."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        logger.info(f"Updating specialist profile ID={instance.id}, user_id={instance.user_id}")
        logger.debug(f"Request data: {request.data}")
        
        # Crear copia mutable de los datos, filtrando campos read_only
        # DRF ignora automáticamente campos read_only, pero es mejor ser explícito
        data = {}
        read_only_fields = ['id', 'user_id', 'user_display', 'work_images', 'work_images_full', 
                           'puntuations', 'point']
        
        # Copiar solo los campos que no son read_only
        for key, value in request.data.items():
            if key not in read_only_fields:
                data[key] = value
        
        logger.debug(f"Filtered data: {data}")
        
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated_instance = serializer.save()
        
        logger.info(f"Profile updated successfully. ID={updated_instance.id}, profession={updated_instance.profession}, about_us={updated_instance.about_us[:50] if updated_instance.about_us else None}")
        
        # Refrescar la instancia desde la base de datos para asegurar que tenemos los datos más recientes
        updated_instance.refresh_from_db()
        
        # Publicar evento
        try:
            producer = get_producer()
            producer.publish('profiles.events', 'profile.updated', {
                'profile_id': updated_instance.id,
                'user_id': updated_instance.user_id,
                'profile_type': 'specialist',
            })
        except Exception as e:
            logger.error(f"Failed to publish profile.updated event: {e}")
        
        # Serializar nuevamente con los datos actualizados
        response_serializer = self.get_serializer(updated_instance)
        return Response(response_serializer.data)

    def partial_update(self, request, *args, **kwargs):
        """Actualizar perfil parcialmente (PATCH)."""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        """Listar todos los especialistas."""
        queryset = SpecialistProfile.objects.all()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """Obtener un especialista específico."""
        instance = self.get_object()
        logger.info(f"Retrieving specialist profile ID={instance.id}, user_id={instance.user_id}, profession={instance.profession}")
        serializer = self.get_serializer(instance)
        logger.debug(f"Serialized data: {serializer.data}")
        return Response(serializer.data)

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

