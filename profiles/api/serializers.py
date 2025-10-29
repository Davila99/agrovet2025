from rest_framework import serializers
from profiles.models import SpecialistProfile, BusinessmanProfile, ConsumerProfile
from media.api.serializers import MediaSerializer


class BaseProfileSerializer(serializers.ModelSerializer):
    """Serializer base para perfiles que expone un identificador legible del user.

    Usa `user_display` en lugar de referenciar `user.username` ya que el modelo
    de usuario usa `phone_number` como USERNAME_FIELD.
    """
    user_display = serializers.SerializerMethodField(read_only=True)

    def get_user_display(self, obj):
        return getattr(obj.user, 'full_name', None) or getattr(obj.user, 'phone_number', None)

    def update(self, instance, validated_data):
        # Actualización sencilla: solo actualizamos los campos provistos del perfil.
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class SpecialistProfileSerializer(BaseProfileSerializer):
    work_images = serializers.SerializerMethodField(read_only=True)
    work_images_full = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SpecialistProfile
        fields = [
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
        try:
            return [m.url for m in instance.work_images.all()]
        except Exception:
            return []

    def get_work_images_full(self, instance):
        try:
            medias = instance.work_images.all()
            return MediaSerializer(medias, many=True, context=self.context).data
        except Exception:
            return []


class BusinessmanProfileSerializer(BaseProfileSerializer):
    products_and_services = serializers.SerializerMethodField(read_only=True)
    products_and_services_full = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = BusinessmanProfile
        fields = [
            'user_display',
            'business_name',
            'descriptions',
            'contact',
            'offers_local_products',
            'products_and_services',
            'products_and_services_full',
        ]
        read_only_fields = ()

    def get_products_and_services(self, instance):
        try:
            return [m.url for m in instance.products_and_services.all()]
        except Exception:
            return []

    def get_products_and_services_full(self, instance):
        try:
            medias = instance.products_and_services.all()
            return MediaSerializer(medias, many=True, context=self.context).data
        except Exception:
            return []


class ConsumerProfileSerializer(BaseProfileSerializer):
    class Meta:
        model = ConsumerProfile
        fields = ['user_display']
        read_only_fields = ()