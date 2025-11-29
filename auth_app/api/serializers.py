from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from auth_app.models import User
from auth_app.utils.supabase_utils import upload_image_to_supabase
from profiles.api.serializers import (
    SpecialistProfileSerializer as SpecialistProfileReadSerializer,
    BusinessmanProfileSerializer as BusinessmanProfileReadSerializer,
    ConsumerProfileSerializer as ConsumerProfileReadSerializer,
)
from profiles.models import SpecialistProfile, BusinessmanProfile, ConsumerProfile


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
    # Campo temporal para recibir datos de specialist_profile desde el frontend
    specialist_profile_profession = serializers.CharField(required=False, allow_blank=True, write_only=True)
    # Campo temporal para recibir datos de businessman_profile desde el frontend
    businessman_profile_business_type = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = User
        fields = ['id', 'full_name', 'last_name', 'phone_number', 'password', 'role', 'bio', 'profile_picture', 'latitude', 'longitude', 'specialist_profile_profession', 'businessman_profile_business_type']

    def create(self, validated_data):
        image = validated_data.pop('profile_picture', None)
        password = validated_data.pop('password', None)
        profession = validated_data.pop('specialist_profile_profession', None)
        business_type = validated_data.pop('businessman_profile_business_type', None)

        # Asegurarnos de usar el manager para que el password quede hasheado
        phone_number = validated_data.pop('phone_number', None)

        # Crear usuario usando create_user para mantener la lógica del manager
        user = User.objects.create_user(phone_number=phone_number, password=password, **validated_data)

        # 🔹 Crear perfil automáticamente según el role del usuario
        try:
            role_value = (user.role or '').lower()
            if role_value == 'specialist' or role_value == 'specialista' or role_value == 'specialist':
                # Crear perfil con profesión si se proporcionó
                profile, created = SpecialistProfile.objects.get_or_create(user=user)
                if profession and profession.strip():
                    # Validar que la profesión sea una de las opciones permitidas
                    allowed_professions = ['Veterinario', 'Agrónomo', 'Zootecnista']
                    if profession in allowed_professions:
                        profile.profession = profession
                        profile.save()
            elif role_value == 'businessman' or role_value == 'business' or role_value == 'business_owner':
                # Crear perfil con tipo de negocio si se proporcionó
                profile, created = BusinessmanProfile.objects.get_or_create(user=user)
                if business_type and business_type.strip():
                    # Validar que el tipo de negocio sea una de las opciones permitidas
                    allowed_business_types = ['Agroveterinaria', 'Empresa Agropecuaria']
                    if business_type in allowed_business_types:
                        profile.business_type = business_type
                        profile.save()
            elif role_value == 'consumer' or role_value == 'client':
                ConsumerProfile.objects.get_or_create(user=user)
        except Exception as e:
            # No abortar el registro por fallo en la creación del perfil; registrar/log si se desea
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error creating profile for user {user.id}: {e}")

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
