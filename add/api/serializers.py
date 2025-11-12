from rest_framework import serializers
from ..models import Add, Category, Follow
from media.api.serializers import MediaSerializer


class MediaRefSerializer(serializers.Serializer):
    id = serializers.IntegerField()


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class AddSerializer(serializers.ModelSerializer):
    publisher_name = serializers.CharField(source='publisher.full_name', read_only=True)
    main_image = MediaSerializer(read_only=True)
    secondary_images = MediaSerializer(many=True, read_only=True)
    main_image_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    secondary_image_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)

    class Meta:
        model = Add
        fields = [
            'id', 'publisher', 'publisher_name', 'title', 'description', 'price', 'category', 'condition',
            'location_name', 'latitude', 'longitude', 'main_image', 'secondary_images', 'main_image_id', 'secondary_image_ids',
            'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['publisher', 'status', 'created_at', 'updated_at']

    def validate_secondary_image_ids(self, value):
        if len(value) > 4:
            raise serializers.ValidationError('Solo se permiten hasta 4 imágenes secundarias.')
        return value

    def validate_price(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError('El precio no puede ser negativo.')
        return value

    def create(self, validated_data):
        main_id = validated_data.pop('main_image_id', None)
        sec_ids = validated_data.pop('secondary_image_ids', []) or []
        # Create instance without saving to avoid model validation that requires main_image
        # (we'll assign main_image before the final save)
        from media.models import Media
        adds = Add(**validated_data)
        if main_id:
            try:
                adds.main_image = Media.objects.get(pk=main_id)
            except Media.DoesNotExist:
                raise serializers.ValidationError({'main_image_id': 'Media principal no encontrada.'})
        # Save first so we can assign m2m relationships
        adds.save()
        if sec_ids:
            medias = Media.objects.filter(pk__in=sec_ids)
            adds.secondary_images.set(medias)
        return adds

    def update(self, instance, validated_data):
        main_id = validated_data.pop('main_image_id', None)
        sec_ids = validated_data.pop('secondary_image_ids', None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        from media.models import Media
        if main_id is not None:
            if main_id == 0:
                instance.main_image = None
            else:
                try:
                    instance.main_image = Media.objects.get(pk=main_id)
                except Media.DoesNotExist:
                    raise serializers.ValidationError({'main_image_id': 'Media principal no encontrada.'})
        if sec_ids is not None:
            if len(sec_ids) > 4:
                raise serializers.ValidationError({'secondary_image_ids': 'Solo se permiten hasta 4 imágenes secundarias.'})
            medias = Media.objects.filter(pk__in=sec_ids)
            instance.secondary_images.set(medias)
        instance.save()
        return instance


class FollowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Follow
        fields = ['id', 'follower', 'following', 'created_at']
        read_only_fields = ['follower', 'created_at']
