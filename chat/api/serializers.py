from rest_framework import serializers
from chat.models import ChatRoom, ChatMessage
from django.contrib.auth import get_user_model

User = get_user_model()


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    media_url = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = ('id', 'room', 'sender', 'sender_username', 'content', 'media', 'media_url', 'timestamp')
        read_only_fields = ('id', 'sender', 'sender_username', 'timestamp')


class ChatRoomSerializer(serializers.ModelSerializer):
    participants_usernames = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = ('id', 'name', 'participants', 'participants_usernames', 'is_private', 'created_at', 'last_activity')
        read_only_fields = ('id', 'created_at', 'last_activity')

    def get_participants_usernames(self, obj):
        return [u.username for u in obj.participants.all()]

    def get_media_url(self, obj):
        if obj.media:
            return obj.media.url
        return None
from rest_framework import serializers
from django.contrib.auth import get_user_model
from ..models import ChatRoom, ChatMessage

User = get_user_model()

# --- 1. Serializador de Usuario Base ---
class SenderSerializer(serializers.ModelSerializer):
    """ Serializa la información básica del usuario (remitente) para el chat. """
    class Meta:
        model = User
        # Se asume que el modelo de usuario tiene 'id' y 'username'
        fields = ['id', 'username']
        read_only_fields = fields


# --- 2. Serializador de Mensajes (Lectura y Escritura) ---
class ChatMessageSerializer(serializers.ModelSerializer):
    """
    Serializador principal para los mensajes.
    - Se usa para la lectura de mensajes (GET).
    - Se usa para el envío de mensajes (POST), donde 'sender' se ignora y se asigna en la vista.
    """
    # Muestra la información completa del remitente, en lugar de solo el ID
    sender = SenderSerializer(read_only=True)
    
    # Para el campo 'room' en el POST, aceptamos el ID de la sala. 
    # El ViewSet verifica si el usuario es participante.
    room = serializers.PrimaryKeyRelatedField(
        queryset=ChatRoom.objects.all(),
        label="ID de la Sala"
    )

    class Meta:
        model = ChatMessage
        fields = ['id', 'room', 'sender', 'content', 'timestamp']
        # timestamp debe ser de solo lectura. El ViewSet asigna 'sender'.
        read_only_fields = ['timestamp', 'sender']


# --- 3. Serializador de Sala de Chat (Lectura) ---
class ChatRoomSerializer(serializers.ModelSerializer):
    """
    Serializador para listar las salas de chat de un usuario.
    Muestra los IDs de los participantes y la fecha de creación.
    """
    # Utiliza el serializador de usuario para mostrar los detalles de los participantes
    participants = SenderSerializer(many=True, read_only=True)
    
    # Campo opcional para mostrar un resumen de la última actividad (último mensaje)
    last_message = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ChatRoom
        fields = ['id', 'participants', 'created_at', 'last_message']
        read_only_fields = fields

    def get_last_message(self, obj):
        """ Obtiene el contenido del último mensaje de esta sala. """
        try:
            last_msg = obj.messages.latest('timestamp')
            # Devolvemos un objeto simple con el contenido y la hora del último mensaje
            return {
                'content': last_msg.content,
                'timestamp': last_msg.timestamp
            }
        except ChatMessage.DoesNotExist:
            return None