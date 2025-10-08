from rest_framework import serializers
from profiles.models import SpecialistProfile, BusinessmanProfile, ConsumerProfile

class SpecialistProfileSerializer(serializers.ModelSerializer):
    # Campo de solo lectura para mostrar el nombre de usuario asociado
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = SpecialistProfile
        fields = [
            'user_username', 'profession', 'experience_years', 'about_us', 
            'can_give_consultations', 'can_offer_online_services', 
            'puntuations', 'point',
        ]
        # 'user' es asignado automáticamente en la vista, y los puntos son calculados
        read_only_fields = ('user', 'puntuations', 'point') 

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