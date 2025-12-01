from rest_framework import serializers
from profiles.models import SpecialistProfile, BusinessmanProfile, ConsumerProfile
import sys
import os

# Add common to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.http_clients.media_client import get_media_client


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
    # Expose verification hints for frontend (student / graduated / verified)
    verification_type = serializers.SerializerMethodField(read_only=True)
    is_verified = serializers.SerializerMethodField(read_only=True)

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
            'verification_type',
            'is_verified',
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
            return []
        try:
            media_client = get_media_client()
            return media_client.get_multiple_media(instance.work_images_ids)
        except Exception:
            return []

    def get_verification_type(self, instance):
        """Return 'graduated'|'student'|'title' or None depending on which verification doc exists."""
        if getattr(instance, 'verification_graduation_letter_id', None):
            return 'graduated'
        if getattr(instance, 'verification_student_card_id', None):
            return 'student'
        if getattr(instance, 'verification_title_id', None):
            return 'title'
        return None

    def get_is_verified(self, instance):
        return bool(self.get_verification_type(instance))


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

