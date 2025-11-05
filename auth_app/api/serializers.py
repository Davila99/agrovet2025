from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from auth_app.models import User
from auth_app.utils.supabase_utils import upload_image_to_supabase
from profiles.api.serializers import (
    SpecialistProfileSerializer as SpecialistProfileReadSerializer,
    BusinessmanProfileSerializer as BusinessmanProfileReadSerializer,
    ConsumerProfileSerializer as ConsumerProfileReadSerializer,
)


class UserSerializer(serializers.ModelSerializer):
    specialist_profile = serializers.SerializerMethodField(read_only=True)
    businessman_profile = serializers.SerializerMethodField(read_only=True)
    consumer_profile = serializers.SerializerMethodField(read_only=True)

    def get_specialist_profile(self, obj):
        try:
            profile = obj.specialist_profile
        except Exception:
            return None
        if profile is None:
            return None
        return SpecialistProfileReadSerializer(profile).data

    def get_businessman_profile(self, obj):
        try:
            profile = obj.businessman_profile
        except Exception:
            return None
        if profile is None:
            return None
        return BusinessmanProfileReadSerializer(profile).data

    def get_consumer_profile(self, obj):
        try:
            profile = obj.consumer_profile
        except Exception:
            return None
        if profile is None:
            return None
        return ConsumerProfileReadSerializer(profile).data

    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'last_name', 'phone_number', 'role', 'bio', 'profile_picture', 'latitude', 'longitude',
            'specialist_profile', 'businessman_profile', 'consumer_profile'
        ]


class UserProfileImageUploadSerializer(serializers.Serializer):
    image = serializers.ImageField()

    def update(self, instance, validated_data):
        image = validated_data['image']
        url = upload_image_to_supabase(image, folder="profiles")
        if url:
            instance.profile_picture = url
            instance.save()
        return instance

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True, use_url=True)  # Acepta imagen opcional

    class Meta:
        model = User
        fields = ['id', 'full_name', 'last_name', 'phone_number', 'password', 'role', 'bio', 'profile_picture', 'latitude', 'longitude']

    def create(self, validated_data):
        image = validated_data.pop('profile_picture', None)
        password = validated_data.pop('password', None)

        # Asegurarnos de usar el manager para que el password quede hasheado
        phone_number = validated_data.pop('phone_number', None)

        # Crear usuario usando create_user para mantener la lógica del manager
        user = User.objects.create_user(phone_number=phone_number, password=password, **validated_data)

        if image:
            try:
                url = upload_image_to_supabase(image, folder="profiles")
                if url:
                    user.profile_picture = url
                    user.save()
            except Exception:
                # No abortamos el registro por fallo de upload; dejamos sin imagen y registramos el error
                pass

        return user

    def validate_role(self, value):
        if value in (None, ''):
            return value
        # Normalizar valores entrantes para evitar errores por mayúsculas/minúsculas
        mapping = {
            'specialist': 'Specialist',
            'businessman': 'businessman',
            'consumer': 'consumer',
        }
        try:
            return mapping.get(value.lower(), value)
        except Exception:
            return value

    def validate_phone_number(self, value):
        # Limpieza básica: eliminar espacios y dejar '+' si existe
        if not isinstance(value, str):
            raise serializers.ValidationError('Ingrese un número válido')
        s = value.strip()
        # conservar '+' inicial y dígitos
        if s.startswith('+'):
            digits = '+' + ''.join(ch for ch in s[1:] if ch.isdigit())
        else:
            digits = ''.join(ch for ch in s if ch.isdigit())

        if not digits or len(digits.replace('+', '')) < 7:
            raise serializers.ValidationError('Ingrese un número válido')

        return digits

class UserLoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    password = serializers.CharField(write_only=True)


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer usado solo para actualizaciones de usuario (PUT/PATCH).
    Hace que password y profile_picture sean opcionales para no requerirlos en updates.
    """
    password = serializers.CharField(write_only=True, required=False, allow_null=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True, use_url=True)

    class Meta:
        model = User
        fields = ['id', 'full_name', 'last_name', 'phone_number', 'password', 'role', 'bio', 'profile_picture', 'latitude', 'longitude']

    def validate_password(self, value):
        # Si se proporciona password, deberá procesarse (hash) en la vista o en create/update
        return value


class PhoneResetRequestSerializer(serializers.Serializer):
    phone = serializers.CharField()


class PhoneResetVerifySerializer(serializers.Serializer):
    phone = serializers.CharField()
    code = serializers.CharField()
    new_password = serializers.CharField()
