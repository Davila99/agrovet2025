# chat_app/serializers.py

from rest_framework import serializers
from chat.models import ChatRoom, ChatMessage
from auth_app.models import CustomUser # Asumiendo que CustomUser es tu modelo de usuario

class CustomUserSerializer(serializers.ModelSerializer):
    """Serializer básico para exponer la información del usuario."""
    class Meta:
        model = CustomUser
        # Incluye solo la información necesaria para el chat
        fields = ('id', 'username', 'full_name') 
        read_only_fields = fields

class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer para los mensajes individuales."""
    # Usamos CustomUserSerializer para serializar el remitente anidado
    sender = CustomUserSerializer(read_only=True) 

    class Meta:
        model = ChatMessage
        fields = ('id', 'sender', 'content', 'timestamp')
        read_only_fields = ('id', 'sender', 'timestamp')

class ChatRoomSerializer(serializers.ModelSerializer):
    """Serializer para la sala de chat, incluyendo la lista de participantes."""
    # Usamos CustomUserSerializer para serializar los participantes
    participants = CustomUserSerializer(many=True, read_only=True)
    # Campo para incluir el ID del usuario con el que se desea chatear al crear una sala
    target_user_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = ChatRoom
        fields = ('id', 'name', 'participants', 'last_activity', 'target_user_id')
        read_only_fields = ('id', 'name', 'participants', 'last_activity')

    def create(self, validated_data):
        """
        Lógica personalizada para crear o encontrar una sala 1-a-1.
        """
        # El usuario que inicia la petición (el solicitante)
        user = self.context['request'].user 
        target_user_id = validated_data.pop('target_user_id', None)

        if not target_user_id:
            raise serializers.ValidationError({"detail": "Se requiere 'target_user_id' para iniciar un chat 1-a-1."})

        try:
            target_user = CustomUser.objects.get(id=target_user_id)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError({"detail": "Usuario objetivo no encontrado."})

        # 1. Buscar si ya existe una sala 1-a-1 entre ellos
        # Busca una sala que tenga exactamente 2 participantes (solicitante y objetivo)
        room = ChatRoom.objects.filter(participants=user).filter(participants=target_user).annotate(
            num_participants=models.Count('participants')
        ).filter(num_participants=2).first()
        
        # 2. Si existe, la devolvemos (aunque DRF crea una nueva, devolveremos la existente)
        if room:
            # Una forma simple de forzar la devolución de la sala existente
            self.instance = room 
            return room

        # 3. Si no existe, creamos una nueva sala
        room = ChatRoom.objects.create(**validated_data)
        room.participants.set([user, target_user]) # Añadimos ambos usuarios
        return room