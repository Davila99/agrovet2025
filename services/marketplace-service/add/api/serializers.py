from rest_framework import serializers
from add.models import Add, Category, Follow
import sys
import os

# Add common to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.http_clients.auth_client import get_auth_client
from common.http_clients.media_client import get_media_client


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class AddSerializer(serializers.ModelSerializer):
    publisher_name = serializers.SerializerMethodField(read_only=True)
    main_image = serializers.SerializerMethodField(read_only=True)
    secondary_images = serializers.SerializerMethodField(read_only=True)
    main_image_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    secondary_image_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = Add
        fields = [
            'id', 'publisher_id', 'publisher_name', 'title', 'description', 'price', 'category',
            'condition', 'location_name', 'latitude', 'longitude', 'main_image', 'secondary_images',
            'main_image_id', 'secondary_image_ids', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['publisher_id', 'status', 'created_at', 'updated_at']

    def get_publisher_name(self, obj):
        """Obtener nombre del publisher desde Auth Service."""
        try:
            auth_client = get_auth_client()
            user = auth_client.get_user(obj.publisher_id)
            if user:
                return user.get('full_name') or f"User {obj.publisher_id}"
        except Exception:
            pass
        return f"User {obj.publisher_id}"

    def get_main_image(self, obj):
        """Obtener imagen principal desde Media Service."""
        if not obj.main_image_id:
            return None
        try:
            media_client = get_media_client()
            media = media_client.get_media(obj.main_image_id)
            return media
        except Exception:
            return None

    def get_secondary_images(self, obj):
        """Obtener imágenes secundarias desde Media Service."""
        if not obj.secondary_image_ids:
            return []
        try:
            media_client = get_media_client()
            return media_client.get_multiple_media(obj.secondary_image_ids)
        except Exception:
            return []

    def validate_secondary_image_ids(self, value):
        if value and len(value) > 4:
            raise serializers.ValidationError('Solo se permiten hasta 4 imágenes secundarias.')
        return value

    def validate_price(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError('El precio no puede ser negativo.')
        return value

    def create(self, validated_data):
        """Crear anuncio con referencias a media."""
        main_id = validated_data.pop('main_image_id', None)
        sec_ids = validated_data.pop('secondary_image_ids', []) or []
        
        # Validar que las media existen
        if main_id:
            media_client = get_media_client()
            if not media_client.get_media(main_id):
                raise serializers.ValidationError({'main_image_id': 'Media principal no encontrada.'})
        
        if sec_ids:
            media_client = get_media_client()
            for media_id in sec_ids:
                if not media_client.get_media(media_id):
                    raise serializers.ValidationError({'secondary_image_ids': f'Media {media_id} no encontrada.'})
        
        add = Add(**validated_data)
        add.main_image_id = main_id
        add.secondary_image_ids = sec_ids
        add.save()
        return add

    def update(self, instance, validated_data):
        """Actualizar anuncio."""
        main_id = validated_data.pop('main_image_id', None)
        sec_ids = validated_data.pop('secondary_image_ids', None)
        
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        
        if main_id is not None:
            if main_id == 0:
                instance.main_image_id = None
            else:
                media_client = get_media_client()
                if not media_client.get_media(main_id):
                    raise serializers.ValidationError({'main_image_id': 'Media principal no encontrada.'})
                instance.main_image_id = main_id
        
        if sec_ids is not None:
            if len(sec_ids) > 4:
                raise serializers.ValidationError({'secondary_image_ids': 'Solo se permiten hasta 4 imágenes secundarias.'})
            # Validar que todas las media existen
            media_client = get_media_client()
            for media_id in sec_ids:
                if not media_client.get_media(media_id):
                    raise serializers.ValidationError({'secondary_image_ids': f'Media {media_id} no encontrada.'})
            instance.secondary_image_ids = sec_ids
        
        instance.save()
        return instance


class FollowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Follow
        fields = ['id', 'follower_id', 'following_id', 'created_at']
        read_only_fields = ['follower_id', 'created_at']

