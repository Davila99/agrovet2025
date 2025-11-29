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
    work_images_ids = serializers.JSONField(required=False, allow_null=True)
    
    # Campo de profesión con opciones limitadas
    profession = serializers.ChoiceField(
        choices=[('Veterinario', 'Veterinario'), ('Agrónomo', 'Agrónomo'), ('Zootecnista', 'Zootecnista')],
        required=True,
        help_text="Solo se permiten: Veterinario, Agrónomo o Zootecnista"
    )
    
    # Campos de verificación (solo si existen en el modelo)
    verification_title_id = serializers.IntegerField(required=False, allow_null=True, write_only=False)
    verification_student_card_id = serializers.IntegerField(required=False, allow_null=True, write_only=False)
    verification_graduation_letter_id = serializers.IntegerField(required=False, allow_null=True, write_only=False)
    
    # URLs de verificación (read-only)
    verification_title_url = serializers.SerializerMethodField(read_only=True)
    verification_student_card_url = serializers.SerializerMethodField(read_only=True)
    verification_graduation_letter_url = serializers.SerializerMethodField(read_only=True)
    
    # Información de verificación (read-only)
    verification_status = serializers.SerializerMethodField(read_only=True)
    verification_type = serializers.SerializerMethodField(read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Verificar qué campos existen en el modelo y excluir los que no existen
        # Usar el modelo directamente si no hay instancia
        model = self.Meta.model
        try:
            if self.instance is not None:
                model_fields = {f.name for f in self.instance._meta.get_fields()}
            else:
                # Si no hay instancia, usar el modelo directamente
                model_fields = {f.name for f in model._meta.get_fields()}
            
            verification_fields = ['verification_title_id', 'verification_student_card_id', 'verification_graduation_letter_id']
            for field_name in verification_fields:
                if field_name not in model_fields:
                    # Remover el campo del serializer si no existe en el modelo
                    self.fields.pop(field_name, None)
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Removed field {field_name} from serializer as it doesn't exist in model")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error checking model fields in serializer __init__: {e}")
            # Si hay error, simplemente no remover campos

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
            'work_images_ids',
            'work_images',
            'work_images_full',
            'verification_title_id',
            'verification_student_card_id',
            'verification_graduation_letter_id',
            'verification_title_url',
            'verification_student_card_url',
            'verification_graduation_letter_url',
            'verification_status',
            'verification_type',
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
    
    def get_verification_title_url(self, instance):
        """Obtener URL del título desde Media Service."""
        verification_title_id = getattr(instance, 'verification_title_id', None)
        if not verification_title_id:
            return None
        try:
            media_client = get_media_client()
            media = media_client.get_media(verification_title_id)
            return media.get('url') if media else None
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error getting verification_title_url for media_id {verification_title_id}: {e}")
            return None
    
    def get_verification_student_card_url(self, instance):
        """Obtener URL del carnet de estudiante desde Media Service."""
        verification_student_card_id = getattr(instance, 'verification_student_card_id', None)
        if not verification_student_card_id:
            return None
        try:
            media_client = get_media_client()
            media = media_client.get_media(verification_student_card_id)
            return media.get('url') if media else None
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error getting verification_student_card_url for media_id {verification_student_card_id}: {e}")
            return None
    
    def get_verification_graduation_letter_url(self, instance):
        """Obtener URL de la carta de egresado desde Media Service."""
        verification_graduation_letter_id = getattr(instance, 'verification_graduation_letter_id', None)
        if not verification_graduation_letter_id:
            return None
        try:
            media_client = get_media_client()
            media = media_client.get_media(verification_graduation_letter_id)
            return media.get('url') if media else None
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error getting verification_graduation_letter_url for media_id {verification_graduation_letter_id}: {e}")
            return None
    
    def get_verification_status(self, instance):
        """Obtener estado de verificación: 'verified_student' (verde), 'verified_professional' (azul), o None."""
        verification_student_card_id = getattr(instance, 'verification_student_card_id', None)
        verification_title_id = getattr(instance, 'verification_title_id', None)
        verification_graduation_letter_id = getattr(instance, 'verification_graduation_letter_id', None)
        
        if verification_student_card_id:
            return 'verified_student'
        if verification_title_id or verification_graduation_letter_id:
            return 'verified_professional'
        return None
    
    def get_verification_type(self, instance):
        """Obtener tipo de verificación para mostrar texto."""
        verification_student_card_id = getattr(instance, 'verification_student_card_id', None)
        verification_title_id = getattr(instance, 'verification_title_id', None)
        verification_graduation_letter_id = getattr(instance, 'verification_graduation_letter_id', None)
        
        if verification_student_card_id:
            return 'Estudiante'
        if verification_title_id:
            return 'Médico Titulado'
        if verification_graduation_letter_id:
            return 'Médico Titulado'
        return None
    
    def update(self, instance, validated_data):
        """Actualizar instancia preservando campos que no vienen en validated_data."""
        # Preservar work_images_ids si no viene en validated_data (importante para no borrar el portafolio)
        if 'work_images_ids' not in validated_data:
            # No hacer nada, preservar el valor existente
            pass
        
        # Solo actualizar campos que están en validated_data
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


class BusinessmanProfileSerializer(BaseProfileSerializer):
    products_and_services = serializers.SerializerMethodField(read_only=True)
    products_and_services_full = serializers.SerializerMethodField(read_only=True)
    
    # Campo de tipo de negocio con opciones limitadas
    business_type = serializers.ChoiceField(
        choices=[('Agroveterinaria', 'Agroveterinaria'), ('Empresa Agropecuaria', 'Empresa Agropecuaria')],
        required=True,
        help_text="Solo se permiten: Agroveterinaria o Empresa Agropecuaria"
    )

    class Meta:
        model = BusinessmanProfile
        fields = [
            'id',
            'user_id',
            'user_display',
            'business_type',
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

