from rest_framework import serializers
from media.models import Media
from django.contrib.contenttypes.models import ContentType


class MediaSerializer(serializers.ModelSerializer):
    """
    Serializer for Media model.
    Supports optional content_type/object_id for generic relations.
    """
    content_type = serializers.PrimaryKeyRelatedField(
        queryset=ContentType.objects.all(),
        required=False,
        allow_null=True
    )
    object_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Media
        fields = (
            "id", "name", "description", "price", "url",
            "created_at", "content_type", "object_id"
        )
        read_only_fields = ("id", "created_at")

    def validate(self, data):
        """Validate content_type and object_id if provided."""
        ct = data.get('content_type')
        oid = data.get('object_id')
        
        if ct and oid:
            # Validate that content_type is allowed
            allowed_models = ['specialistprofile', 'businessmanprofile']
            if ct.model not in allowed_models:
                raise serializers.ValidationError(
                    'content_type must be SpecialistProfile or BusinessmanProfile'
                )
        
        return data

