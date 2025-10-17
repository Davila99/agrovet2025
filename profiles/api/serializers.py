from rest_framework import serializers
from profiles.models import SpecialistProfile, BusinessmanProfile, ConsumerProfile


class BaseProfileSerializer(serializers.ModelSerializer):
    # Mostrar un identificador legible del usuario (no existe 'username' en User)
    user_display = serializers.SerializerMethodField(read_only=True)

    def get_user_display(self, obj):
        return obj.user.full_name or obj.user.phone_number

    def update(self, instance, validated_data):
        # Actualización superficial segura: solo campos del perfil se actualizan.
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class SpecialistProfileSerializer(BaseProfileSerializer):
    class Meta:
        model = SpecialistProfile
        fields = [
            'user_display', 'profession', 'experience_years', 'about_us',
            'can_give_consultations', 'can_offer_online_services',
            'puntuations', 'point',
        ]
        read_only_fields = ('puntuations', 'point')


class BusinessmanProfileSerializer(BaseProfileSerializer):
    class Meta:
        model = BusinessmanProfile
        # Exponemos campos relevantes y protegemos 'user'
        fields = ['user_display', 'business_name', 'descriptions', 'offers_local_products']
        read_only_fields = ()


class ConsumerProfileSerializer(BaseProfileSerializer):
    class Meta:
        model = ConsumerProfile
        fields = ['user_display']
        read_only_fields = ()