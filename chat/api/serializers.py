from rest_framework import serializers
from django.contrib.auth import get_user_model
from chat.models import ChatRoom, ChatMessage
from chat.models import get_or_create_private_chat

User = get_user_model()


class SenderSerializer(serializers.ModelSerializer):
    """Minimal user serializer used inside chat serializers."""
    profile_picture = serializers.SerializerMethodField()
    profile_picture_url = serializers.SerializerMethodField()
    class Meta:
        model = User
        # The custom User model in this project doesn't have `username`.
        # Use `full_name` for display when available, otherwise fall back to phone_number.
        # include profile picture helpers so frontend can render avatars directly
        fields = ['id', 'full_name', 'phone_number', 'profile_picture', 'profile_picture_url']
        read_only_fields = fields

    def _build_media_url(self, media_attr):
        """Return an absolute URL for a FileField-like attribute when possible."""
        if not media_attr:
            return None
        # media_attr may be a FieldFile with `.url` or a string already
        try:
            url = getattr(media_attr, 'url', media_attr)
        except Exception:
            url = media_attr
        request = self.context.get('request')
        if request and hasattr(request, 'build_absolute_uri') and url:
            try:
                return request.build_absolute_uri(url)
            except Exception:
                return url
        return url

    def get_profile_picture(self, obj):
        # keep a short name that some frontend code expects (may be None)
        return self._build_media_url(getattr(obj, 'profile_picture', None))

    def get_profile_picture_url(self, obj):
        # explicit long-form name used in other places
        return self._build_media_url(getattr(obj, 'profile_picture', None))


class ChatMessageSerializer(serializers.ModelSerializer):
    sender = SenderSerializer(read_only=True)
    media_url = serializers.SerializerMethodField()
    # Include receipt summary for clients to show delivered/read status
    receipts = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ChatMessage
        fields = ['id', 'room', 'sender', 'content', 'media', 'media_url', 'timestamp', 'receipts', 'delivered', 'delivered_at', 'read', 'read_at']
        read_only_fields = ['id', 'sender', 'timestamp']

    def get_media_url(self, obj):
        if obj.media:
            return getattr(obj.media, 'url', None)
        return None

    def get_receipts(self, obj):
        try:
            # Avoid N+1: if receipts are prefetched use them, otherwise query
            receipts = getattr(obj, 'receipts', None)
            out = []
            if receipts is None:
                receipts = obj.receipts.all()
            for r in receipts:
                out.append({
                    'user_id': getattr(r.user, 'id', None),
                    'delivered': bool(r.delivered),
                    'delivered_at': r.delivered_at.isoformat() if getattr(r, 'delivered_at', None) else None,
                    'read': bool(r.read),
                    'read_at': r.read_at.isoformat() if getattr(r, 'read_at', None) else None,
                })
            return out
        except Exception:
            return []


class ChatRoomSerializer(serializers.ModelSerializer):
    # Allow optional room name and accept writable participant ids on create/update
    name = serializers.CharField(required=False, allow_blank=True)
    # For reads, return nested participant objects; for writes accept a list of ids
    participants = SenderSerializer(many=True, read_only=True)
    participants_ids = serializers.PrimaryKeyRelatedField(many=True, queryset=User.objects.all(), write_only=True, source='participants')
    participants_usernames = serializers.SerializerMethodField(read_only=True)
    # For private 1:1 chats, helpful to return the OTHER participant's display name
    other_participant = serializers.SerializerMethodField(read_only=True)

    # Include a small recent messages preview so clients can show persisted
    # messages when rendering the room list (helps persistence across reloads)
    messages = serializers.SerializerMethodField(read_only=True)
    last_message = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ChatRoom
        fields = ['id', 'name', 'participants', 'participants_ids', 'participants_usernames', 'other_participant', 'is_private', 'created_at', 'last_activity', 'messages', 'last_message']
        read_only_fields = ['id', 'created_at', 'last_activity', 'messages', 'last_message']

    def get_participants_usernames(self, obj):
        # Participants may be User instances; ensure we return a readable name.
        names = []
        for u in obj.participants.all():
            # Some earlier code paths passed user PKs into serializer representation;
            # guard against unexpected types.
            try:
                full = getattr(u, 'full_name', None) or getattr(u, 'phone_number', None)
            except Exception:
                # If `u` is not a User instance (e.g., an int), convert to str
                full = str(u)
            names.append(full)
        return names

    def get_other_participant(self, obj):
        # Return the display name of the other participant in a private 1:1 chat
        request = self.context.get('request')
        if not request:
            return None
        user = request.user
        try:
            if not obj.is_private:
                return None
            participants = list(obj.participants.all())
            # If there are not exactly 2 participants, return room name
            if len(participants) != 2:
                return obj.name or None
            other = participants[0] if participants[1].id == user.id else participants[1]
            return getattr(other, 'full_name', None) or getattr(other, 'phone_number', None) or getattr(other, 'username', None)
        except Exception:
            return None

    def create(self, validated_data):
        # participants are provided via 'participants_ids' which map to 'participants' by source
        participants = validated_data.pop('participants', [])
        is_private = validated_data.get('is_private', True)

        # If this is a private 1:1 chat and exactly two participants were provided,
        # prefer the model helper which attempts to find an existing chat.
        if is_private and isinstance(participants, (list, tuple)) and len(participants) == 2:
            try:
                user1, user2 = participants[0], participants[1]
                room, created = get_or_create_private_chat(user1, user2)
                # If additional metadata provided (like name), update it
                # If the room was just created, set a sensible display name immediately
                if created:
                    try:
                        request = self.context.get('request')
                        # Prefer to show the 'other' participant relative to the requesting user
                        if request and getattr(request, 'user', None):
                            if participants[0].id == request.user.id:
                                other = participants[1]
                            else:
                                other = participants[0]
                        else:
                            other = participants[1]
                        display = getattr(other, 'full_name', None) or getattr(other, 'phone_number', None) or getattr(other, 'username', None)
                        if display:
                            room.name = display
                            room.save(update_fields=['name'])
                    except Exception:
                        pass
                elif not created and validated_data.get('name'):
                    room.name = validated_data.get('name')
                    room.save(update_fields=['name'])
                return room
            except Exception:
                # Fall back to default creation on error
                pass

        room = ChatRoom.objects.create(**validated_data)
        if participants:
            room.participants.set(participants)
        room.save()
        return room

    def get_messages(self, obj):
        # return the last N messages for preview in the room list (chronological asc)
        try:
            qs = obj.messages.order_by('-timestamp')[:20]
            # reuse ChatMessageSerializer for consistent shape
            ser = ChatMessageSerializer(qs, many=True, context=self.context)
            data = list(ser.data)
            return list(reversed(data))
        except Exception:
            return []

    def get_last_message(self, obj):
        try:
            m = obj.messages.order_by('-timestamp').first()
            if not m:
                return ''
            return getattr(m, 'content', '')
        except Exception:
            return ''

    def update(self, instance, validated_data):
        participants = validated_data.pop('participants', None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        if participants is not None:
            instance.participants.set(participants)
        instance.save()
        return instance