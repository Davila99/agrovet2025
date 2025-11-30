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
        """Filtrar por usuario autenticado."""
        user_id = self.kwargs.get('pk')

        # Verificar permisos
        try:
            auth_user_id = getattr(self.request.user, 'id', None)
            if not (self.request.user.is_staff or auth_user_id == int(user_id)):
                raise PermissionDenied('No tiene permiso para acceder a este recurso.')

            # Verificar que el usuario existe en Auth Service
            auth_client = get_auth_client()
            # Pass through Authorization token so Auth Service can authenticate the request
            raw = self.request.META.get('HTTP_AUTHORIZATION', '')
            token = raw.replace('Token ', '').replace('Bearer ', '') if raw else None
            user = auth_client.get_user(int(user_id), token=token)
            if not user:
                from rest_framework.exceptions import NotFound
                raise NotFound('Usuario no encontrado en Auth Service.')

            profile, created = SpecialistProfile.objects.get_or_create(user_id=int(user_id))
            return profile
        except PermissionDenied:
            raise
        except Exception as e:
            # Log full traceback for debugging and return a clear API error instead of HTML 500
            logger = logging.getLogger('profiles.views')
            logger.error(f"get_object error for user_id={user_id}: {e}")
            logger.error(traceback.format_exc())
            from rest_framework.exceptions import APIException
            raise APIException('Error interno al procesar la solicitud. Revisa logs del servicio.')

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
        is_own_profile = auth_user_id and int(auth_user_id) == int(user_id)
        is_staff = self.request.user.is_staff
        
        # Para GET: permitir a cualquier usuario autenticado ver perfiles de otros (datos públicos)
        # Para PUT/PATCH/DELETE: solo permitir si es el propio perfil o staff
        if self.request.method == 'GET':
            # Cualquier usuario autenticado puede ver perfiles de otros
            pass
        else:
            # Para modificar, solo el propio perfil o staff
            if not (is_staff or is_own_profile):
                raise PermissionDenied('No tiene permiso para modificar este recurso.')

        # Verificar que el usuario existe en Auth Service
        auth_client = get_auth_client()
        raw = self.request.META.get('HTTP_AUTHORIZATION', '')
        token = raw.replace('Token ', '').replace('Bearer ', '') if raw else None
        user = auth_client.get_user(int(user_id), token=token)
        if not user:
            from rest_framework.exceptions import NotFound
            raise NotFound('Usuario no encontrado en Auth Service.')

        profile, created = SpecialistProfile.objects.get_or_create(user_id=int(user_id))
        return profile

    def partial_update(self, request, *args, **kwargs):
        """Actualizar parcialmente el perfil, asegurando que work_images_ids y campos de verificación se guarden correctamente."""
        try:
            instance = self.get_object()
            logger.info(f"PATCH request for specialist profile user_id={instance.user_id}, data={request.data}")
            
            # Filtrar campos de verificación si no existen en el modelo antes de validar
            model_fields = {f.name for f in instance._meta.get_fields()}
            filtered_data = request.data.copy()
            verification_fields = ['verification_title_id', 'verification_student_card_id', 'verification_graduation_letter_id']
            for field_name in verification_fields:
                if field_name not in model_fields and field_name in filtered_data:
                    logger.warning(f"Removing {field_name} from request data as it doesn't exist in model")
                    filtered_data.pop(field_name, None)
            
            serializer = self.get_serializer(instance, data=filtered_data, partial=True)
            serializer.is_valid(raise_exception=True)
            
            # Guardar primero con el serializer (solo campos válidos)
            # IMPORTANTE: No guardar work_images_ids si no viene en el request para preservar el portafolio existente
            saved_instance = serializer.save()
            
            # Campos a actualizar
            update_fields = []
            
            # Asegurar que work_images_ids se guarde correctamente SOLO si viene explícitamente en el request
            # Si no viene, NO tocar work_images_ids para preservar el portafolio existente
            if 'work_images_ids' in request.data:
                work_images_ids = request.data.get('work_images_ids')
                if work_images_ids is not None:
                    # Normalizar a lista si viene como string o número único
                    if isinstance(work_images_ids, (str, int)):
                        work_images_ids = [work_images_ids]
                    elif not isinstance(work_images_ids, list):
                        work_images_ids = []
                    # Filtrar valores None y convertir a enteros
                    try:
                        work_images_ids = [int(id) for id in work_images_ids if id is not None]
                        saved_instance.work_images_ids = work_images_ids
                        update_fields.append('work_images_ids')
                        logger.info(f"Updated work_images_ids for specialist profile {saved_instance.id}: {work_images_ids}")
                    except (ValueError, TypeError) as e:
                        logger.error(f"Error converting work_images_ids to integers: {e}, received: {work_images_ids}")
            
            # Manejar campos de verificación (solo si existen en el modelo)
            verification_fields = ['verification_title_id', 'verification_student_card_id', 'verification_graduation_letter_id']
            # Verificar qué campos existen realmente en el modelo
            model_fields = {f.name for f in saved_instance._meta.get_fields()}
            
            for field_name in verification_fields:
                if field_name in request.data:
                    # Verificar que el campo existe en el modelo antes de intentar establecerlo
                    if field_name in model_fields:
                        value = request.data.get(field_name)
                        if value is None or value == '':
                            setattr(saved_instance, field_name, None)
                            update_fields.append(field_name)
                            logger.info(f"Cleared {field_name} for specialist profile {saved_instance.id}")
                        else:
                            try:
                                int_value = int(value)
                                setattr(saved_instance, field_name, int_value)
                                update_fields.append(field_name)
                                logger.info(f"Updated {field_name} for specialist profile {saved_instance.id}: {int_value}")
                            except (ValueError, TypeError) as e:
                                logger.error(f"Error converting {field_name} to integer: {e}, received: {value}")
                    else:
                        logger.warning(f"Field {field_name} does not exist on SpecialistProfile model. Migration may not have been applied. Skipping this field.")
            
            # Guardar todos los campos actualizados de una vez (solo si hay campos válidos)
            if update_fields:
                try:
                    # Filtrar solo campos que realmente existen en el modelo antes de guardar
                    valid_update_fields = [f for f in update_fields if f in model_fields]
                    if valid_update_fields:
                        saved_instance.save(update_fields=valid_update_fields)
                        logger.info(f"Saved update_fields: {valid_update_fields}")
                    else:
                        logger.warning(f"No valid fields to save from {update_fields}. Fields may not exist in database.")
                except Exception as save_error:
                    logger.error(f"Error saving update_fields {update_fields}: {save_error}", exc_info=True)
                    # Intentar guardar sin los campos de verificación si fallan
                    non_verification_fields = [f for f in update_fields if not f.startswith('verification_') and f in model_fields]
                    if non_verification_fields:
                        try:
                            saved_instance.save(update_fields=non_verification_fields)
                            logger.info(f"Saved non-verification fields: {non_verification_fields}")
                        except Exception as e2:
                            logger.error(f"Error saving even non-verification fields: {e2}", exc_info=True)
                            raise
                    else:
                        # Si no hay campos no-verificación para guardar, puede ser que solo se intentaron guardar campos de verificación que no existen
                        logger.warning(f"Could not save any fields. This may be because verification fields don't exist in the database.")
                        # No lanzar error si solo eran campos de verificación que no existen - simplemente continuar
                        if not any(f.startswith('verification_') for f in update_fields):
                            raise
            
            # Recargar el serializer con los datos actualizados
            serializer = self.get_serializer(saved_instance)
            
            # Publicar evento
            try:
                producer = get_producer()
                producer.publish('profiles.events', 'profile.updated', {
                    'profile_id': saved_instance.id,
                    'user_id': saved_instance.user_id,
                    'profile_type': 'specialist',
                })
            except Exception as e:
                logger.error(f"Failed to publish profile.updated event: {e}")
            
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error in partial_update: {e}", exc_info=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

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
            # Filtrar campos de verificación si no existen en el modelo antes de validar
            model_fields = {f.name for f in profile._meta.get_fields()}
            filtered_data = request.data.copy()
            verification_fields = ['verification_title_id', 'verification_student_card_id', 'verification_graduation_letter_id']
            for field_name in verification_fields:
                if field_name not in model_fields and field_name in filtered_data:
                    logger.warning(f"Removing {field_name} from request data as it doesn't exist in model")
                    filtered_data.pop(field_name, None)
            
            serializer = self.get_serializer(profile, data=filtered_data, partial=True)
            serializer.is_valid(raise_exception=True)
            saved_instance = serializer.save()
            
            # Campos a actualizar
            update_fields = []
            
            # Asegurar que work_images_ids se guarde correctamente
            if 'work_images_ids' in request.data:
                work_images_ids = request.data.get('work_images_ids')
                if work_images_ids is not None:
                    # Normalizar a lista si viene como string o número único
                    if isinstance(work_images_ids, (str, int)):
                        work_images_ids = [work_images_ids]
                    elif not isinstance(work_images_ids, list):
                        work_images_ids = []
                    # Filtrar valores None y convertir a enteros
                    try:
                        work_images_ids = [int(id) for id in work_images_ids if id is not None]
                        saved_instance.work_images_ids = work_images_ids
                        update_fields.append('work_images_ids')
                        logger.info(f"Updated work_images_ids for specialist profile {saved_instance.id}: {work_images_ids}")
                    except (ValueError, TypeError) as e:
                        logger.error(f"Error converting work_images_ids to integers: {e}, received: {work_images_ids}")
            
            # Manejar campos de verificación (solo si existen en el modelo)
            verification_fields = ['verification_title_id', 'verification_student_card_id', 'verification_graduation_letter_id']
            # Verificar qué campos existen realmente en el modelo
            model_fields = {f.name for f in saved_instance._meta.get_fields()}
            
            for field_name in verification_fields:
                if field_name in request.data:
                    # Verificar que el campo existe en el modelo antes de intentar establecerlo
                    if field_name in model_fields:
                        value = request.data.get(field_name)
                        if value is None or value == '':
                            setattr(saved_instance, field_name, None)
                            update_fields.append(field_name)
                            logger.info(f"Cleared {field_name} for specialist profile {saved_instance.id}")
                        else:
                            try:
                                int_value = int(value)
                                setattr(saved_instance, field_name, int_value)
                                update_fields.append(field_name)
                                logger.info(f"Updated {field_name} for specialist profile {saved_instance.id}: {int_value}")
                            except (ValueError, TypeError) as e:
                                logger.error(f"Error converting {field_name} to integer: {e}, received: {value}")
                    else:
                        logger.warning(f"Field {field_name} does not exist on SpecialistProfile model. Migration may not have been applied. Skipping this field.")
            
            # Guardar todos los campos actualizados de una vez (solo si hay campos válidos)
            if update_fields:
                try:
                    # Filtrar solo campos que realmente existen en el modelo antes de guardar
                    valid_update_fields = [f for f in update_fields if f in model_fields]
                    if valid_update_fields:
                        saved_instance.save(update_fields=valid_update_fields)
                        logger.info(f"Saved update_fields: {valid_update_fields}")
                    else:
                        logger.warning(f"No valid fields to save from {update_fields}. Fields may not exist in database.")
                except Exception as save_error:
                    logger.error(f"Error saving update_fields {update_fields}: {save_error}", exc_info=True)
                    # Intentar guardar sin los campos de verificación si fallan
                    non_verification_fields = [f for f in update_fields if not f.startswith('verification_') and f in model_fields]
                    if non_verification_fields:
                        try:
                            saved_instance.save(update_fields=non_verification_fields)
                            logger.info(f"Saved non-verification fields: {non_verification_fields}")
                        except Exception as e2:
                            logger.error(f"Error saving even non-verification fields: {e2}", exc_info=True)
                            raise
                    else:
                        # Si no hay campos no-verificación para guardar, puede ser que solo se intentaron guardar campos de verificación que no existen
                        logger.warning(f"Could not save any fields. This may be because verification fields don't exist in the database.")
                        # No lanzar error si solo eran campos de verificación que no existen - simplemente continuar
                        if not any(f.startswith('verification_') for f in update_fields):
                            raise
            
            # Recargar el serializer con los datos actualizados
            serializer = self.get_serializer(saved_instance)
            
            # Publicar evento
            try:
                producer = get_producer()
                producer.publish('profiles.events', 'profile.updated', {
                    'profile_id': saved_instance.id,
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

    def get_object(self):
        """Obtener el BusinessmanProfile para el usuario indicado en la URL."""
        user_id = self.kwargs.get('pk')
        
        # Verificar permisos
        auth_user_id = getattr(self.request.user, 'id', None)
        is_own_profile = auth_user_id and int(auth_user_id) == int(user_id)
        is_staff = self.request.user.is_staff
        
        # Para GET: permitir a cualquier usuario autenticado ver perfiles de otros (datos públicos)
        # Para PUT/PATCH/DELETE: solo permitir si es el propio perfil o staff
        if self.request.method == 'GET':
            # Cualquier usuario autenticado puede ver perfiles de otros
            pass
        else:
            # Para modificar, solo el propio perfil o staff
            if not (is_staff or is_own_profile):
                raise PermissionDenied('No tiene permiso para modificar este recurso.')

        # Verificar que el usuario existe en Auth Service
        auth_client = get_auth_client()
        raw = self.request.META.get('HTTP_AUTHORIZATION', '')
        token = raw.replace('Token ', '').replace('Bearer ', '') if raw else None
        user = auth_client.get_user(int(user_id), token=token)
        if not user:
            from rest_framework.exceptions import NotFound
            raise NotFound('Usuario no encontrado en Auth Service.')

        profile, created = BusinessmanProfile.objects.get_or_create(user_id=int(user_id))
        return profile

    @action(detail=False, methods=['get', 'patch'], url_path=r'by-user/(?P<user_id>[^/.]+)')
    def by_user(self, request, user_id=None):
        """Endpoint semántico para obtener/actualizar el perfil por user id."""
        user_id_int = int(user_id)
        auth_user_id = getattr(request.user, 'id', None)

        # Security: allow only staff or the user themselves
        if not (request.user.is_staff or auth_user_id == user_id_int):
            raise PermissionDenied('No tiene permiso para acceder a este recurso.')

        profile, _ = BusinessmanProfile.objects.get_or_create(user_id=user_id_int)

        if request.method == 'PATCH':
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            saved_instance = serializer.save()
            
            # Campos a actualizar
            update_fields = []
            
            # Asegurar que products_and_services_ids se guarde correctamente
            if 'products_and_services_ids' in request.data:
                products_and_services_ids = request.data.get('products_and_services_ids')
                if products_and_services_ids is not None:
                    # Normalizar a lista si viene como string o número único
                    if isinstance(products_and_services_ids, (str, int)):
                        products_and_services_ids = [products_and_services_ids]
                    elif not isinstance(products_and_services_ids, list):
                        products_and_services_ids = []
                    # Filtrar valores None y convertir a enteros
                    try:
                        products_and_services_ids = [int(id) for id in products_and_services_ids if id is not None]
                        saved_instance.products_and_services_ids = products_and_services_ids
                        update_fields.append('products_and_services_ids')
                        logger.info(f"Updated products_and_services_ids for businessman profile {saved_instance.id}: {products_and_services_ids}")
                    except (ValueError, TypeError) as e:
                        logger.error(f"Error converting products_and_services_ids to integers: {e}, received: {products_and_services_ids}")
            
            # Guardar todos los campos actualizados de una vez (solo si hay campos válidos)
            if update_fields:
                try:
                    saved_instance.save(update_fields=update_fields)
                    logger.info(f"Saved update_fields: {update_fields}")
                except Exception as save_error:
                    logger.error(f"Error saving update_fields {update_fields}: {save_error}", exc_info=True)
                    raise
            
            # Recargar el serializer con los datos actualizados
            serializer = self.get_serializer(saved_instance)
            
            # Publicar evento
            try:
                producer = get_producer()
                producer.publish('profiles.events', 'profile.updated', {
                    'profile_id': saved_instance.id,
                    'user_id': user_id_int,
                    'profile_type': 'businessman',
                })
            except Exception as e:
                logger.error(f"Failed to publish profile.updated event: {e}")
            
            return Response(serializer.data)

        serializer = self.get_serializer(profile)
        return Response(serializer.data)

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


