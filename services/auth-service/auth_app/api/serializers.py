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
    Serializer básico para User.
    Nota: Los perfiles (specialist_profile, businessman_profile, consumer_profile)
    están en profiles-service y se pueden obtener vía HTTP o eventos Kafka.
    """
    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'last_name', 'phone_number', 'role', 'bio',
            'profile_picture', 'latitude', 'longitude', 'date_joined', 'is_active'
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

