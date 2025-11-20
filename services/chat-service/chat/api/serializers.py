from rest_framework import serializers
from chat.models import ChatRoom, ChatMessage, get_or_create_private_chat
import sys
import os

# Add common to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.http_clients.auth_client import get_auth_client
from common.http_clients.media_client import get_media_client


class SenderSerializer(serializers.Serializer):
    """Serializer breve para información de usuario desde Auth Service."""
    id = serializers.IntegerField()
    full_name = serializers.CharField(allow_null=True)
    phone_number = serializers.CharField(allow_null=True)
    profile_picture = serializers.CharField(allow_null=True)
    profile_picture_url = serializers.CharField(allow_null=True)


class ChatMessageSerializer(serializers.ModelSerializer):
    sender = serializers.SerializerMethodField()
    media_url = serializers.SerializerMethodField()
    receipts = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = [
            'id', 'room', 'sender', 'content', 'media_id', 'media_url',
            'timestamp', 'receipts', 'delivered', 'delivered_at', 'read', 'read_at'
        ]
        read_only_fields = ['id', 'sender', 'timestamp']

    def get_sender(self, obj):
        """Obtener información del sender desde Auth Service."""
        try:
            auth_client = get_auth_client()
            user = auth_client.get_user(obj.sender_id)
            if user:
                return {
                    'id': user.get('id'),
                    'full_name': user.get('full_name'),
                    'phone_number': user.get('phone_number'),
                    'profile_picture': user.get('profile_picture'),
                    'profile_picture_url': user.get('profile_picture'),
                }
        except Exception:
            pass
        return {'id': obj.sender_id, 'full_name': None, 'phone_number': None, 'profile_picture': None, 'profile_picture_url': None}

    def get_media_url(self, obj):
        """Obtener URL de media desde Media Service."""
        if not obj.media_id:
            return None
        try:
            media_client = get_media_client()
            media = media_client.get_media(obj.media_id)
            return media.get('url') if media else None
        except Exception:
            return None

    def get_receipts(self, obj):
        """Obtener receipts del mensaje."""
        try:
            receipts = obj.receipts.all()
            return [{
                'user_id': r.user_id,
                'delivered': bool(r.delivered),
                'delivered_at': r.delivered_at.isoformat() if r.delivered_at else None,
                'read': bool(r.read),
                'read_at': r.read_at.isoformat() if r.read_at else None,
            } for r in receipts]
        except Exception:
            return []


class ChatRoomSerializer(serializers.ModelSerializer):
    participants = serializers.SerializerMethodField()
    participants_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    messages = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = [
            'id', 'name', 'participants', 'participants_ids', 'is_private',
            'created_at', 'last_activity', 'messages', 'last_message'
        ]
        read_only_fields = ['id', 'created_at', 'last_activity', 'messages', 'last_message']

    def get_participants(self, obj):
        """Obtener información de participantes desde Auth Service."""
        if not obj.participants_ids:
            return []
        try:
            auth_client = get_auth_client()
            participants = []
            for user_id in obj.participants_ids:
                user = auth_client.get_user(user_id)
                if user:
                    participants.append({
                        'id': user.get('id'),
                        'full_name': user.get('full_name'),
                        'phone_number': user.get('phone_number'),
                        'profile_picture': user.get('profile_picture'),
                    })
            return participants
        except Exception:
            return []

    def get_messages(self, obj):
        """Obtener últimos mensajes."""
        try:
            messages = obj.messages.order_by('-timestamp')[:20]
            return ChatMessageSerializer(messages, many=True, context=self.context).data[::-1]  # Reverse para orden cronológico
        except Exception:
            return []

    def get_last_message(self, obj):
        """Obtener último mensaje."""
        try:
            msg = obj.messages.order_by('-timestamp').first()
            return msg.content if msg else ''
        except Exception:
            return ''

    def create(self, validated_data):
        """Crear sala, usando get_or_create_private_chat si es privada."""
        participants_ids = validated_data.pop('participants_ids', [])
        is_private = validated_data.get('is_private', True)
        
        if is_private and len(participants_ids) == 2:
            try:
                room, created = get_or_create_private_chat(participants_ids[0], participants_ids[1])
                return room
            except Exception:
                pass
        
        room = ChatRoom.objects.create(**validated_data)
        room.participants_ids = participants_ids
        room.save()
        return room

