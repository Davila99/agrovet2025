from rest_framework import serializers
from media.models import Media
from django.contrib.contenttypes.models import ContentType


class MediaSerializer(serializers.ModelSerializer):
    # Make content_type/object_id optional at the serializer level so frontend
    # can upload a file first and attach later (e.g., reference from ChatMessage).
    content_type = serializers.PrimaryKeyRelatedField(queryset=ContentType.objects.all(), required=False, allow_null=True)
    object_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Media
        # Incluimos content_type y object_id para poder relacionar la media con otro objeto
        fields = ("id", "name", "description", "price", "url", "created_at", "content_type", "object_id")
        read_only_fields = ("id", "created_at")

    def validate(self, data):
        # Si viene content_type/object_id, verificamos que sean de SpecialistProfile o BusinessmanProfile
        ct = data.get('content_type')
        oid = data.get('object_id')
        try:
            print(f"[MediaSerializer.validate] received content_type={ct} object_id={oid}")
        except Exception:
            pass
        if ct and oid:
            try:
                model = ct.model_class()
                allowed = ['specialistprofile', 'businessmanprofile']
                try:
                    mname = getattr(model, '__name__', str(ct.model))
                except Exception:
                    mname = str(ct.model)
                try:
                    print(f"[MediaSerializer.validate] content_type.model={ct.model} resolved={mname}")
                except Exception:
                    pass
                if ct.model not in allowed:
                    raise serializers.ValidationError('content_type must be SpecialistProfile or BusinessmanProfile')
            except Exception as e:
                try: print(f"[MediaSerializer.validate] exception while validating content_type: {e}")
                except Exception: pass
                raise
        return data
