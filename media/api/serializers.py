from rest_framework import serializers
from media.models import Media
from django.contrib.contenttypes.models import ContentType




class MediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Media
        # Incluimos content_type y object_id para poder relacionar la media con otro objeto
        fields = ("id", "name", "description", "price", "url", "created_at", "content_type", "object_id")
        read_only_fields = ("id", "created_at")

    def validate(self, data):
        # Si viene content_type/object_id, verificamos que sean de SpecialistProfile o BusinessmanProfile
        ct = data.get('content_type')
        oid = data.get('object_id')
        if ct and oid:
            model = ct.model_class()
            allowed = ['specialistprofile', 'businessmanprofile']
            if ct.model not in allowed:
                raise serializers.ValidationError('content_type must be SpecialistProfile or BusinessmanProfile')
        return data
