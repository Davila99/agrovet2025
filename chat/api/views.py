from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.db.models import Q

# CORRECCIÓN DE IMPORTACIÓN: Usamos '..' para importar desde el directorio padre (chat)
from ..models import ChatRoom, ChatMessage
from .serializers import ChatMessageSerializer, ChatRoomSerializer # Asumiendo que existen

class ChatMessageViewSet(viewsets.ViewSet):
    """
    Gestiona el listado de salas, mensajes dentro de una sala y el envío de nuevos mensajes.
    El listado general (messages/) muestra las salas a las que pertenece el usuario.
    """
    permission_classes = [permissions.IsAuthenticated]

    # --- Acciones Generales (Mapeadas por el router de urls.py) ---

    def list(self, request):
        """
        [GET /api/chat/messages/]
        Devuelve todas las salas de chat en las que el usuario es un participante.
        """
        user = request.user
        
        # Filtra las salas donde el usuario está en la lista de participantes
        queryset = ChatRoom.objects.filter(participants=user).order_by('-created_at')
        
        # Usamos el serializador de sala de chat
        serializer = ChatRoomSerializer(queryset, many=True, context={'request': request})
        
        return Response(serializer.data)


    # --- Acciones Personalizadas ---
    
    @action(detail=False, methods=['get'])
    def room_messages(self, request):
        """
        [GET /api/chat/messages/room_messages/?room_id=X]
        Devuelve los mensajes para una sala específica.
        """
        room_id = request.query_params.get('room_id')
        if not room_id:
            return Response(
                {"detail": "Debe proporcionar el parámetro 'room_id'."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 1. Verificar si la sala existe y si el usuario pertenece a ella
        try:
            room = ChatRoom.objects.get(pk=room_id, participants=request.user)
        except ChatRoom.DoesNotExist:
            raise PermissionDenied("La sala no existe o no eres un participante.")

        # 2. Obtener los mensajes y serializarlos
        messages = ChatMessage.objects.filter(room=room).order_by('timestamp')
        serializer = ChatMessageSerializer(messages, many=True, context={'request': request})
        
        return Response(serializer.data)


    @action(detail=False, methods=['post'])
    def send(self, request):
        """
        [POST /api/chat/messages/send/]
        Crea un nuevo mensaje en una sala específica.
        """
        serializer = ChatMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        room_id = serializer.validated_data.get('room').id
        content = serializer.validated_data.get('content')
        
        # 1. Verificar si la sala existe y si el usuario pertenece a ella
        try:
            room = ChatRoom.objects.get(pk=room_id, participants=request.user)
        except ChatRoom.DoesNotExist:
            raise PermissionDenied("La sala no existe o no eres un participante.")
        
        # 2. Crear y guardar el mensaje
        message = ChatMessage.objects.create(
            room=room,
            sender=request.user,
            content=content
        )
        
        return Response(
            ChatMessageSerializer(message).data, 
            status=status.HTTP_201_CREATED
        )
