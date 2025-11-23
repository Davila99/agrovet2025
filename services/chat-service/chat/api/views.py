"""
API views for Chat service.
"""
from rest_framework import viewsets, status, serializers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
import logging
from rest_framework.decorators import action
from django.db import DatabaseError, IntegrityError, DataError
from django.utils import timezone
import sys
import os

from chat.models import ChatRoom, ChatMessage, get_or_create_private_chat, ChatMessageReceipt
from chat.api.serializers import ChatRoomSerializer, ChatMessageSerializer
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from chat.presence import sync_is_online

# Add common to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.http_clients.auth_client import get_auth_client
from common.http_clients.media_client import get_media_client
from common.events.kafka_producer import get_producer

logger = logging.getLogger(__name__)


def get_user_from_token(request):
    """Obtener usuario desde token."""
    token = request.META.get('HTTP_AUTHORIZATION', '').replace('Token ', '').replace('Bearer ', '')
    if not token:
        return None
    auth_client = get_auth_client()
    return auth_client.verify_token(token)


class ChatRoomViewSet(viewsets.ModelViewSet):
    queryset = ChatRoom.objects.all().order_by('-last_activity')
    serializer_class = ChatRoomSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """Crear sala de chat."""
        user = get_user_from_token(request)
        if not user:
            return Response({'detail': 'No autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Si es sala privada con 2 participantes, usar get_or_create_private_chat
        data = request.data or {}
        is_private = data.get('is_private', True)
        participants_ids = data.get('participants_ids') or data.get('participants', [])
        
        if is_private and participants_ids and len(participants_ids) == 2:
            try:
                room, created = get_or_create_private_chat(participants_ids[0], participants_ids[1])
                serializer = self.get_serializer(room, context={'request': request})
                return Response(serializer.data, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)
            except ValueError as e:
                return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        # Crear sala normal
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        
        # Publicar evento
        try:
            producer = get_producer()
            producer.publish('chat.events', 'chat.room.created', {
                'room_id': serializer.instance.id,
                'participants_ids': serializer.instance.participants_ids,
            })
        except Exception as e:
            logger.error(f"Failed to publish chat.room.created event: {e}")
        
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def get_queryset(self):
        """Filtrar salas del usuario autenticado."""
        user = get_user_from_token(self.request)
        if not user:
            return ChatRoom.objects.none()
        
        user_id = user.get('id')
        # Filtrar salas donde el usuario es participante
        return ChatRoom.objects.filter(participants_ids__contains=[user_id])

    def perform_create(self, serializer):
        """Asignar participantes."""
        participants_ids = serializer.validated_data.get('participants_ids', [])
        room = serializer.save()
        room.participants_ids = participants_ids
        room.save()

    @action(detail=False, methods=['post'], url_path='get_or_create_private')
    def get_or_create_private(self, request):
        """API helper para crear sala privada."""
        user = get_user_from_token(request)
        if not user:
            return Response({'detail': 'No autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
        
        participants = request.data.get('participants_ids') or request.data.get('participants')
        if not participants or not isinstance(participants, (list, tuple)) or len(participants) != 2:
            return Response({'detail': 'Se requieren exactamente 2 participantes.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user1_id, user2_id = int(participants[0]), int(participants[1])
            room, created = get_or_create_private_chat(user1_id, user2_id)
            serializer = self.get_serializer(room, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception('get_or_create_private failed')
            return Response({'detail': 'Error al obtener/crear sala privada.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChatMessageViewSet(viewsets.ModelViewSet):
    queryset = ChatMessage.objects.all().order_by('timestamp')
    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """Crear mensaje."""
        user = get_user_from_token(request)
        if not user:
            return Response({'detail': 'No autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            out = self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(out or serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except (DataError, DatabaseError, IntegrityError) as e:
            logger.exception('Database error creating ChatMessage')
            return Response({'detail': 'Error saving message to database.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception('ChatMessage create failed')
            return Response({'detail': 'Error creating chat message.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_queryset(self):
        """Filtrar mensajes por sala."""
        qs = self.queryset
        room_id = self.request.query_params.get('room')
        if room_id:
            qs = qs.filter(room_id=room_id)
        return qs

    def perform_create(self, serializer):
        """Crear mensaje con sender y receipts."""

            try:
                import requests
                media_service_url = os.getenv('MEDIA_SERVICE_URL', 'http://localhost:8001')
                response = requests.post(
                    f"{media_service_url}/api/media/",
                    json={
                        'url': media_url_from_client,
                        'name': self.request.data.get('media_name'),
                        'description': self.request.data.get('description'),
                    },
                    timeout=10
                )
                if response.status_code == 201:
                    media_data = response.json()
                    media_id = media_data.get('id')
            except Exception as e:
                logger.error(f"Failed to create media in Media Service: {e}")

        # Crear mensaje
        saved = serializer.save(sender_id=user_id, media_id=media_id)
        
        # Crear receipts para participantes excepto sender
        try:
            room = saved.room
            participant_ids = room.participants_ids or []
            recipients = [pid for pid in participant_ids if pid != user_id]
            
            for recipient_id in recipients:
                ChatMessageReceipt.objects.get_or_create(
                    message=saved,
                    user_id=recipient_id,
                    defaults={'delivered': False, 'read': False}
                )
        except Exception:
            logger.exception('Failed creating receipts')

        # Broadcast vía Channel Layer
        try:
            channel_layer = get_channel_layer()
            out = {
                'type': 'chat.message',
                'message_id': saved.id,
                'sender_id': user_id,
                'text': saved.content or '',
                'content': saved.content or '',
                'room_id': str(saved.room_id),
                'media_id': saved.media_id,
                'timestamp': saved.timestamp.isoformat() if saved.timestamp else None,
                'client_msg_id': self.request.data.get('client_msg_id'),
            }
            
            async_to_sync(channel_layer.group_send)(f'chat_{saved.room_id}', out)
            
            # Marcar receipts como entregados para usuarios online
            online_recips = [r for r in recipients if sync_is_online(r)]
            if online_recips:
                now = timezone.now()
                ChatMessageReceipt.objects.filter(
                    message=saved,
                    user_id__in=online_recips
                ).update(delivered=True, delivered_at=now)
            
            # Publicar evento Kafka
            try:
                producer = get_producer()
                producer.publish('chat.events', 'chat.message.sent', {
                    'message_id': saved.id,
                    'room_id': saved.room_id,
                    'sender_id': user_id,
                })
            except Exception as e:
                logger.error(f"Failed to publish chat.message.sent event: {e}")
            
            return out
        except Exception:
            logger.exception('Failed broadcasting message')
            return serializer.data

    @action(detail=False, methods=['get'])
    def last_messages(self, request):
        """Obtener últimos N mensajes de una sala."""
        user = get_user_from_token(request)
        if not user:
            return Response({'detail': 'No autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
        
        room_id = request.query_params.get('room')
        limit = int(request.query_params.get('limit', 50))
        
        if not room_id or room_id in ('null', 'undefined'):
            return Response({'detail': "Se requiere 'room' query param válido."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            room_pk = int(room_id)
            room = ChatRoom.objects.get(pk=room_pk)
            user_id = user.get('id')
            
            # Verificar que el usuario es participante
            if user_id not in (room.participants_ids or []):
                return Response({'detail': 'No eres participante de esta sala.'}, status=status.HTTP_403_FORBIDDEN)
            
            messages_qs = ChatMessage.objects.filter(room=room).order_by('-timestamp').prefetch_related('receipts')[:limit]
            messages = reversed(list(messages_qs))
            serializer = ChatMessageSerializer(messages, many=True, context={'request': request})
            return Response(serializer.data)
        except ChatRoom.DoesNotExist:
            return Response({'detail': 'Sala no existe.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            logger.exception('failed fetching last_messages')
            return Response({'detail': 'Error al obtener mensajes.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='mark_read')
    def mark_read(self, request):
        """Marcar mensajes como leídos."""
        user = get_user_from_token(request)
        if not user:
            return Response({'detail': 'No autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
        
        user_id = user.get('id')
        room_id = request.data.get('room') or request.data.get('room_id')
        
        if not room_id or str(room_id).lower() in ('null', 'undefined'):
            return Response({'detail': "Invalid 'room' parameter."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            room_pk = int(room_id)
            room = ChatRoom.objects.get(pk=room_pk)
            
            # Verificar que el usuario es participante
            if user_id not in (room.participants_ids or []):
                return Response({'detail': 'No eres participante de esta sala.'}, status=status.HTTP_403_FORBIDDEN)
            
            # Marcar receipts como leídos
            now = timezone.now()
            receipts_qs = ChatMessageReceipt.objects.filter(
                message__room_id=room_pk,
                user_id=user_id,
                read=False
            )
            message_ids = list(receipts_qs.values_list('message_id', flat=True))
            
            if message_ids:
                receipts_qs.update(delivered=True, delivered_at=now, read=True, read_at=now)
                
                # Actualizar flags agregados en ChatMessage
                for mid in set(message_ids):
                    try:
                        still_unread = ChatMessageReceipt.objects.filter(message_id=mid, read=False).exists()
                        if not still_unread:
                            ChatMessage.objects.filter(id=mid).update(read=True, seen=True, read_at=now)
                    except Exception:
                        logger.exception(f'Failed updating message {mid}')
            
            return Response({'updated': message_ids}, status=status.HTTP_200_OK)
        except ChatRoom.DoesNotExist:
            return Response({'detail': 'Sala no existe.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            logger.exception('mark_read failed')
            return Response({'detail': 'Error marcando mensajes como leídos.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

