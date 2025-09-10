from rest_framework import serializers
from .models import User, Specialty, UserSpecialty, Profile


# -------------------------
# User Serializer
# -------------------------
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "full_name", "phone_number", "role", "profile_image", "is_online"]


# -------------------------
# Registro de usuario
# -------------------------
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["full_name", "phone_number", "role", "password"]

    def create(self, validated_data):
        user = User.objects.create_user(
            phone_number=validated_data["phone_number"],
            full_name=validated_data["full_name"],
            role=validated_data["role"],
            password=validated_data["password"],
        )
        return user


# -------------------------
# Perfil extendido
# -------------------------
class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["description", "years_experience"]


# -------------------------
# Veterinarios / Agrónomos
# -------------------------
class ProfessionalSerializer(serializers.ModelSerializer):
    specialties = serializers.SerializerMethodField()
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "full_name", "phone_number", "role", "profile_image", "specialties", "profile"]

    def get_specialties(self, obj):
        return [s.specialty.name for s in UserSpecialty.objects.filter(user=obj)]
