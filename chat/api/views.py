from rest_framework import viewsets, status, serializers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model

from chat.models import ChatRoom, ChatMessage
from chat.api.serializers import ChatRoomSerializer, ChatMessageSerializer

User = get_user_model()


class ChatRoomViewSet(viewsets.ModelViewSet):
    queryset = ChatRoom.objects.all().order_by('-last_activity')
    serializer_class = ChatRoomSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return self.queryset.filter(participants=user)
        return self.queryset.none()

    def perform_create(self, serializer):
        participants = serializer.validated_data.get('participants', [])
        is_private = serializer.validated_data.get('is_private', True)

        if is_private:
            if len(participants) != 2:
                raise serializers.ValidationError("Las salas privadas deben tener exactamente 2 participantes.")

            user0, user1 = participants[0], participants[1]
            valid = False
            if (hasattr(user0, 'specialist_profile') or hasattr(user0, 'businessman_profile')) and not (hasattr(user1, 'specialist_profile') or hasattr(user1, 'businessman_profile')):
                valid = True
            if (hasattr(user1, 'specialist_profile') or hasattr(user1, 'businessman_profile')) and not (hasattr(user0, 'specialist_profile') or hasattr(user0, 'businessman_profile')):
                valid = True

            if not valid:
                raise serializers.ValidationError("Las salas privadas deben ser entre un usuario normal y un especialista o businessman.")

        room = serializer.save()
        if participants:
            room.participants.set(participants)
        room.save()


class ChatMessageViewSet(viewsets.ModelViewSet):
    queryset = ChatMessage.objects.all().order_by('timestamp')
    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = self.queryset
        room_id = self.request.query_params.get('room')
        if room_id:
            qs = qs.filter(room_id=room_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

    # Acción personalizada: obtener los últimos N mensajes de una sala
    from rest_framework.decorators import action

    @action(detail=False, methods=['get'])
    def last_messages(self, request):
        room_id = request.query_params.get('room')
        limit = int(request.query_params.get('limit', 50))
        if not room_id:
            return Response({'detail': "Se requiere 'room' query param."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            room = ChatRoom.objects.get(pk=room_id, participants=request.user)
        except ChatRoom.DoesNotExist:
            return Response({'detail': 'Sala no existe o no eres participante.'}, status=status.HTTP_404_NOT_FOUND)

        messages = ChatMessage.objects.filter(room=room).order_by('-timestamp')[:limit]
        # los devolvemos en orden cronológico ascendente
        messages = reversed(list(messages))
        serializer = ChatMessageSerializer(messages, many=True, context={'request': request})
        return Response(serializer.data)

