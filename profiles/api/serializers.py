from rest_framework import serializers
from profiles.models import SpecialistProfile, BusinessmanProfile, ConsumerProfile
from media.api.serializers import MediaSerializer



class SpecialistProfileSerializer(serializers.ModelSerializer):
    # Campo de solo lectura para mostrar el nombre de usuario asociado
    user_username = serializers.CharField(source='user.username', read_only=True)
    # Lista de URLs de las imágenes asociadas al campo work_images (read-only)
    work_images = serializers.SerializerMethodField(read_only=True)
    # Opcional: información completa de los media (id, url, name...) si se necesita
    work_images_full = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SpecialistProfile
        fields = [
            'user_username','work_images', 'work_images_full', 'profession', 'experience_years', 'about_us', 
            'can_give_consultations', 'can_offer_online_services', 
            'puntuations', 'point',
        ]
        # 'user' es asignado automáticamente en la vista, y los puntos son calculados
        read_only_fields = ('user', 'puntuations', 'point') 

    def get_work_images(self, instance):
        # Retorna lista de URLs (strings)
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

class BusinessmanProfileSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = BusinessmanProfile
        fields = '__all__'
        read_only_fields = ('user',)

class ConsumerProfileSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = ConsumerProfile
        fields = '__all__'
        read_only_fields = ('user',)