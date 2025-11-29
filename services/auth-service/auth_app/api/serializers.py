from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from auth_app.models import User
from auth_app.utils.supabase_utils import upload_image_to_supabase
import sys
import os

# Add common to path for events
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer para User que incluye perfiles completos.
    Los perfiles se obtienen desde profiles-service.
    """
    specialist_profile = serializers.SerializerMethodField(read_only=True)
    businessman_profile = serializers.SerializerMethodField(read_only=True)
    consumer_profile = serializers.SerializerMethodField(read_only=True)

    def get_specialist_profile(self, obj):
        """Obtener perfil de especialista desde profiles-service vía HTTP."""
        try:
            import requests
            import os
            import logging
            logger = logging.getLogger(__name__)
            
            profiles_service_url = os.getenv('PROFILES_SERVICE_URL', 'http://127.0.0.1:8003')
            # Obtener token del request si está disponible
            request = self.context.get('request') if hasattr(self, 'context') else None
            headers = {}
            if request:
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')
                if auth_header:
                    headers['Authorization'] = auth_header
            
            url = f'{profiles_service_url}/api/profiles/specialists/{obj.id}/'
            logger.info(f"Fetching specialist profile for user {obj.id} from {url}")
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Successfully fetched specialist profile for user {obj.id}: {data.get('verification_status', 'no status')}")
                return data
            elif response.status_code == 403:
                # Si es 403, es normal - no tenemos permisos para ver el perfil de otros usuarios
                logger.warning(f"403 Forbidden for specialist profile user {obj.id} - this should not happen after the fix")
            else:
                logger.warning(f"Failed to fetch specialist profile for user {obj.id}: {response.status_code} - {response.text[:200]}")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Exception fetching specialist profile for user {obj.id}: {str(e)}", exc_info=True)
        return None

    def get_businessman_profile(self, obj):
        """Obtener perfil de empresario desde profiles-service vía HTTP."""
        try:
            import requests
            import os
            profiles_service_url = os.getenv('PROFILES_SERVICE_URL', 'http://127.0.0.1:8003')
            request = self.context.get('request') if hasattr(self, 'context') else None
            headers = {}
            if request:
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')
                if auth_header:
                    headers['Authorization'] = auth_header
            
            response = requests.get(
                f'{profiles_service_url}/api/profiles/businessmen/{obj.id}/',
                headers=headers,
                timeout=2
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return None

    def get_consumer_profile(self, obj):
        """Obtener perfil de consumidor desde profiles-service vía HTTP."""
        try:
            import requests
            import os
            profiles_service_url = os.getenv('PROFILES_SERVICE_URL', 'http://127.0.0.1:8003')
            request = self.context.get('request') if hasattr(self, 'context') else None
            headers = {}
            if request:
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')
                if auth_header:
                    headers['Authorization'] = auth_header
            
            response = requests.get(
                f'{profiles_service_url}/api/profiles/consumers/{obj.id}/',
                headers=headers,
                timeout=2
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return None

    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'last_name', 'phone_number', 'role', 'bio',
            'profile_picture', 'latitude', 'longitude', 'date_joined', 'is_active',
            'specialist_profile', 'businessman_profile', 'consumer_profile'
        ]
        read_only_fields = ('id', 'date_joined')


class UserProfileImageUploadSerializer(serializers.Serializer):
    """Serializer para subir imagen de perfil."""
    image = serializers.ImageField()

    def update(self, instance, validated_data):
        image = validated_data['image']
        url = upload_image_to_supabase(image, folder="profiles")
        if url:
            instance.profile_picture = url
            instance.save()
        return instance


class UserRegisterSerializer(serializers.ModelSerializer):
    """Serializer para registro de usuarios."""
    password = serializers.CharField(write_only=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True, use_url=True)

    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'last_name', 'phone_number', 'password', 'role',
            'bio', 'profile_picture', 'latitude', 'longitude'
        ]

    def create(self, validated_data):
        image = validated_data.pop('profile_picture', None)
        password = validated_data.pop('password', None)
        phone_number = validated_data.pop('phone_number', None)

        # Crear usuario usando create_user para mantener la lógica del manager
        user = User.objects.create_user(phone_number=phone_number, password=password, **validated_data)

        # Nota: La creación automática de perfiles según el role se maneja en profiles-service
        # vía eventos Kafka (user.created)

        if image:
            try:
                url = upload_image_to_supabase(image, folder="profiles")
                if url:
                    user.profile_picture = url
                    user.save()
            except Exception:
                # No abortamos el registro por fallo de upload
                pass

        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer para login."""
    phone_number = serializers.CharField()
    password = serializers.CharField(write_only=True)


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer usado solo para actualizaciones de usuario (PUT/PATCH).
    Hace que password y profile_picture sean opcionales.
    """
    password = serializers.CharField(write_only=True, required=False, allow_null=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True, use_url=True)

    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'last_name', 'phone_number', 'password', 'role',
            'bio', 'profile_picture', 'latitude', 'longitude'
        ]

    def validate_password(self, value):
        # Si se proporciona password, deberá procesarse (hash) en la vista
        return value


class PhoneResetRequestSerializer(serializers.Serializer):
    """Serializer para solicitar reset de contraseña."""
    phone = serializers.CharField()


class PhoneResetVerifySerializer(serializers.Serializer):
    """Serializer para verificar código y resetear contraseña."""
    phone = serializers.CharField()
    code = serializers.CharField()
    new_password = serializers.CharField()

