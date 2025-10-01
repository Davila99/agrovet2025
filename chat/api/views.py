# chat_app/views.py

from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from django.shortcuts import get_object_or_404

from chat.models import ChatRoom, ChatMessage
from .serializers import ChatRoomSerializer, ChatMessageSerializer

class ChatRoomViewSet(viewsets.ModelViewSet):
    """
    ViewSet para listar, crear y obtener detalles de las salas de chat.
    """
    serializer_class = ChatRoomSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Devuelve solo las salas de chat donde el usuario actual es un participante."""
        # Filtra las salas que incluyen al usuario de la petición
        return ChatRoom.objects.filter(participants=self.request.user).order_by('-last_activity')

    def perform_create(self, serializer):
        """Asegura que el usuario de la petición se pase al serializer para la lógica de creación."""
        # La lógica de creación/búsqueda de sala se maneja en el serializer
        serializer.save()

    # Nuevo endpoint para obtener todos los mensajes de una sala específica
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Obtiene la lista de mensajes para un ChatRoom específico (por ID)."""
        room = get_object_or_404(ChatRoom, pk=pk)
        
        # Opcional: Asegúrate de que el usuario sea parte de la sala antes de mostrar los mensajes
        if not room.participants.filter(id=request.user.id).exists():
             return Response({"detail": "No autorizado para ver esta sala de chat."}, status=403)

        # Obtenemos los mensajes ordenados
        messages = room.messages.all() 
        
        # Serializamos y devolvemos la respuesta
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)