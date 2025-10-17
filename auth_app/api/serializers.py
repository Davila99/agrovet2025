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
        image = validated_data.pop('profile_picture', None)  # Extraemos la imagen si viene
        validated_data['password'] = make_password(validated_data['password'])

        user = User.objects.create(**validated_data)

        if image:
            # Subimos a Supabase y guardamos la URL
            url = upload_image_to_supabase(image, folder="profiles")
            user.profile_picture = url
            user.save()

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
