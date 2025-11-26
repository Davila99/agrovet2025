from rest_framework import serializers
from profiles.models import SpecialistProfile, BusinessmanProfile, ConsumerProfile
import sys
import os
import logging

# Add common to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.http_clients.media_client import get_media_client

logger = logging.getLogger(__name__)


class BaseProfileSerializer(serializers.ModelSerializer):
    """Serializer base para perfiles."""
    user_display = serializers.SerializerMethodField(read_only=True)

    def get_user_display(self, obj):
        # Obtener información del usuario desde Auth Service
        try:
            from common.http_clients.auth_client import get_auth_client
            auth_client = get_auth_client()
            # If possible, reuse the request's Authorization header to help Auth Service authenticate
            request = self.context.get('request') if hasattr(self, 'context') else None
            token = None
            if request is not None:
                raw = getattr(request, 'META', {}).get('HTTP_AUTHORIZATION', '')
                token = raw.replace('Token ', '').replace('Bearer ', '') if raw else None
            user = auth_client.get_user(obj.user_id, token=token)
            if user:
                return user.get('full_name') or user.get('phone_number')
        except Exception:
            pass
        return f"User {obj.user_id}"


class SpecialistProfileSerializer(BaseProfileSerializer):
    work_images = serializers.SerializerMethodField(read_only=True)
    work_images_full = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SpecialistProfile
        fields = [
            'id',
            'user_id',
            'user_display',
            'profession',
            'experience_years',
            'about_us',
            'can_give_consultations',
            'can_offer_online_services',
            'work_images',
            'work_images_full',
            'puntuations',
            'point',
        ]
        read_only_fields = ('puntuations', 'point')

    def get_work_images(self, instance):
        """Obtener URLs de imágenes desde Media Service."""
        if not instance.work_images_ids:
            return []
        try:
            media_client = get_media_client()
            media_list = media_client.get_multiple_media(instance.work_images_ids)
            return [m.get('url') for m in media_list if m.get('url')]
        except Exception:
            return []

    def get_work_images_full(self, instance):
        """Obtener objetos completos de media desde Media Service."""
        if not instance.work_images_ids:
            logger.debug(f"get_work_images_full: No work_images_ids for specialist {instance.id}")
            return []
        try:
            media_client = get_media_client()
            media_list = media_client.get_multiple_media(instance.work_images_ids)
            logger.info(f"get_work_images_full: Retrieved {len(media_list)} media items for specialist {instance.id}, IDs: {instance.work_images_ids}")
            # Asegurar que cada item tenga los campos necesarios y normalizar
            normalized_list = []
            for media in media_list:
                if not media:
                    continue
                # Normalizar el objeto de media para asegurar que tenga todos los campos necesarios
                normalized_media = {
                    'id': media.get('id'),
                    'name': media.get('name') or '',
                    'description': media.get('description') or '',
                    'url': media.get('url') or None,
                    'created_at': media.get('created_at') or None,
                    'price': media.get('price') or None,
                }
                # Solo agregar si tiene ID y URL válidos
                if normalized_media.get('id') and normalized_media.get('url'):
                    normalized_list.append(normalized_media)
                else:
                    logger.warning(f"get_work_images_full: Media {media.get('id')} missing required fields (id: {normalized_media.get('id')}, url: {normalized_media.get('url')})")
            logger.info(f"get_work_images_full: Returning {len(normalized_list)} normalized media items")
            return normalized_list
        except Exception as e:
            logger.error(f"get_work_images_full: Error retrieving media for specialist {instance.id}: {e}", exc_info=True)
            return []


class BusinessmanProfileSerializer(BaseProfileSerializer):
    products_and_services = serializers.SerializerMethodField(read_only=True)
    products_and_services_full = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = BusinessmanProfile
        fields = [
            'id',
            'user_id',
            'user_display',
            'business_name',
            'descriptions',
            'contact',
            'offers_local_products',
            'products_and_services',
            'products_and_services_full',
        ]

    def get_products_and_services(self, instance):
        """Obtener URLs de productos/servicios desde Media Service."""
        if not instance.products_and_services_ids:
            return []
        try:
            media_client = get_media_client()
            media_list = media_client.get_multiple_media(instance.products_and_services_ids)
            return [m.get('url') for m in media_list if m.get('url')]
        except Exception:
            return []

    def get_products_and_services_full(self, instance):
        """Obtener objetos completos de media desde Media Service."""
        if not instance.products_and_services_ids:
            return []
        try:
            media_client = get_media_client()
            return media_client.get_multiple_media(instance.products_and_services_ids)
        except Exception:
            return []


class ConsumerProfileSerializer(BaseProfileSerializer):
    class Meta:
        model = ConsumerProfile
        fields = ['id', 'user_id', 'user_display']

