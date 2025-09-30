from rest_framework import serializers
from profiles.models import Specialitys, BusinessOwner, ProfesionalPerfil
from auth_app.models import CustomUser

class SpecialitysSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialitys
        fields = ['id', 'name', 'type']

class BusinessOwnerSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = BusinessOwner
        fields = ['id', 'user', 'user_full_name']

class ProfesionalPerfilSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)
    specialitys = SpecialitysSerializer(many=True, read_only=True)
    specialitys_ids = serializers.PrimaryKeyRelatedField(
        queryset=Specialitys.objects.all(),
        many=True,
        source='specialitys',
        write_only=True
    )

    class Meta:
        model = ProfesionalPerfil
        fields = ['id', 'user', 'user_full_name', 'year_experience', 'specialitys', 'specialitys_ids']
