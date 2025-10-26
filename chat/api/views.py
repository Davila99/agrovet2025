from rest_framework import viewsets, status, serializers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
import logging
from rest_framework.decorators import action

from chat.models import ChatRoom, ChatMessage, get_or_create_private_chat
from chat.api.serializers import ChatRoomSerializer, ChatMessageSerializer
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone
from chat.presence import sync_is_online

User = get_user_model()


class ChatRoomViewSet(viewsets.ModelViewSet):
    queryset = ChatRoom.objects.all().order_by('-last_activity')
    serializer_class = ChatRoomSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        logger = logging.getLogger(__name__)
        auth_hdr = request.META.get('HTTP_AUTHORIZATION')
        logger.info(f"ChatRoom create called. Authorization header: {auth_hdr}")
        logger.info(f"request.user={request.user!r}, is_authenticated={getattr(request.user,'is_authenticated',False)} request.auth={getattr(request,'auth',None)}")
        # Dump incoming raw body for debugging
        try:
            print(f"[ChatRoomViewSet] raw_body={request.body}")
        except Exception:
            pass
        try:
            print(f"[ChatRoomViewSet] request.data={request.data}")
        except Exception:
            pass
        # Create serializer and validate explicitly so we can print serializer state
        serializer = self.get_serializer(data=request.data)
        try:
            print(f"[ChatRoomViewSet] serializer fields={list(serializer.fields.keys())}")
        except Exception:
            pass

        is_valid = serializer.is_valid()
        try:
            print(f"[ChatRoomViewSet] is_valid={is_valid} errors={serializer.errors} validated_data={getattr(serializer, 'validated_data', None)}")
        except Exception:
            pass

        if not is_valid:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # If this is a private room request with participants provided, prefer
        # to use the atomic helper which will return an existing room instead
        # of creating duplicates. This avoids race conditions when the client
        # posts repeatedly.
        try:
            data = request.data or {}
            is_private = data.get('is_private') if 'is_private' in data else serializer.validated_data.get('is_private', True)
            participants_ids = data.get('participants_ids') or data.get('participants')
            if is_private and participants_ids and isinstance(participants_ids, (list, tuple)) and len(participants_ids) == 2:
                try:
                    u1 = User.objects.get(pk=participants_ids[0])
                    u2 = User.objects.get(pk=participants_ids[1])
                    room, created = get_or_create_private_chat(u1, u2)
                    out_ser = self.get_serializer(room, context={'request': request})
                    return Response(out_ser.data, status=status.HTTP_200_OK)
                except User.DoesNotExist:
                    return Response({'detail': 'Uno de los participantes no existe.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logging.getLogger(__name__).exception('atomic private room handling failed')

        # proceed to create via perform_create (fallback)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return self.queryset.filter(participants=user)
        return self.queryset.none()

    def perform_create(self, serializer):
        participants = serializer.validated_data.get('participants', [])
        is_private = serializer.validated_data.get('is_private', True)

        # debug print validated participants
        try:
            print(f"[ChatRoomViewSet] validated_data keys={list(serializer.validated_data.keys())}")
            print(f"[ChatRoomViewSet] participants={participants}")
        except Exception:
            pass

        if is_private:
            if not isinstance(participants, (list, tuple)) or len(participants) != 2:
                raise serializers.ValidationError("Las salas privadas deben tener exactamente 2 participantes.")

            user0, user1 = participants[0], participants[1]
            valid = False
            if (hasattr(user0, 'specialist_profile') or hasattr(user0, 'businessman_profile')) and not (hasattr(user1, 'specialist_profile') or hasattr(user1, 'businessman_profile')):
                valid = True
            if (hasattr(user1, 'specialist_profile') or hasattr(user1, 'businessman_profile')) and not (hasattr(user0, 'specialist_profile') or hasattr(user0, 'businessman_profile')):
                valid = True

            if not valid:
                raise serializers.ValidationError("Las salas privadas deben ser entre un usuario normal y un especialista o businessman.")

        # Save will be handled by serializer.create (we set participants there)
        return super().perform_create(serializer)

    @action(detail=False, methods=['post'], url_path='get_or_create_private')
    def get_or_create_private(self, request):
        """API helper to atomically get or create a private 1:1 chat between two participants.

        Expects JSON: { "participants_ids": [id1, id2] }
        Returns the chat room object (200) or 400 on validation error.
        """
        logger = logging.getLogger(__name__)
        data = request.data or {}
        try:
            logger.info(f"get_or_create_private called. user={getattr(request,'user',None)} auth={request.META.get('HTTP_AUTHORIZATION')} data={data}")
        except Exception:
            pass
        participants = data.get('participants_ids') or data.get('participants')
        if not participants or not isinstance(participants, (list, tuple)) or len(participants) != 2:
            return Response({'detail': 'Se requieren exactamente 2 participantes.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user1 = User.objects.get(pk=participants[0])
            user2 = User.objects.get(pk=participants[1])
        except User.DoesNotExist:
            return Response({'detail': 'Uno de los participantes no existe.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            room, created = get_or_create_private_chat(user1, user2)
            serializer = self.get_serializer(room, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logging.getLogger(__name__).exception('get_or_create_private failed')
            return Response({'detail': 'Error al obtener/crear sala privada.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class ChatMessageViewSet(viewsets.ModelViewSet):
    queryset = ChatMessage.objects.all().order_by('timestamp')
    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        logger = logging.getLogger(__name__)
        auth_hdr = request.META.get('HTTP_AUTHORIZATION')
        logger.info(f"ChatMessage create called. Authorization header: {auth_hdr}")
        logger.info(f"request.user={request.user!r}, is_authenticated={getattr(request.user,'is_authenticated',False)} request.auth={getattr(request,'auth',None)}")
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        qs = self.queryset
        room_id = self.request.query_params.get('room')
        if room_id:
            qs = qs.filter(room_id=room_id)
        return qs

    def perform_create(self, serializer):
        # Save message with sender context
        saved = serializer.save(sender=self.request.user)

        try:
            # Ensure per-user receipts exist for all participants except sender
            from chat.models import ChatMessageReceipt
            room = saved.room
            sender_id = getattr(self.request.user, 'id', None)
            participant_ids = list(room.participants.values_list('id', flat=True))
            recipients = [int(pid) for pid in participant_ids if int(pid) != int(sender_id)]
            # Create receipts if missing
            for pid in recipients:
                ChatMessageReceipt.objects.get_or_create(message=saved, user_id=pid, defaults={'delivered': False, 'read': False})

            # Build a minimal payload similar to the websocket path so connected
            # clients receive the new message and can update UI/receipts.
            receipts_qs = ChatMessageReceipt.objects.filter(message=saved).select_related('user')
            receipts = []
            for r in receipts_qs:
                receipts.append({
                    'receipt_id': r.id,
                    'user_id': getattr(r.user, 'id', None),
                    'delivered': bool(r.delivered),
                    'delivered_at': r.delivered_at.isoformat() if getattr(r, 'delivered_at', None) else None,
                    'read': bool(r.read),
                    'read_at': r.read_at.isoformat() if getattr(r, 'read_at', None) else None,
                })

            out = {
                'type': 'chat.message',
                'message': saved.content or '',
                'content': saved.content or '',
                'username': getattr(saved.sender, 'full_name', str(saved.sender)),
                'sender_id': getattr(saved.sender, 'id', None),
                'message_id': saved.id,
                'id': saved.id,
                'room_id': str(saved.room_id),
                'timestamp': saved.timestamp.isoformat() if getattr(saved, 'timestamp', None) else None,
                'receipts': receipts,
            }

            # Send to room group and per-user groups so clients update in real-time
            try:
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(f'room_{saved.room_id}', out)
                for pid in participant_ids:
                    async_to_sync(channel_layer.group_send)(f'user_{pid}', dict(out, from_me=(int(pid) == int(sender_id))))
                # Mark receipts delivered for recipients that are online in this process
                try:
                    # consult presence store synchronously to decide immediate deliveries
                    online_recips = [r for r in recipients if sync_is_online(r)]
                    if online_recips:
                        now = timezone.now()
                        updated_qs = ChatMessageReceipt.objects.filter(message=saved, user_id__in=online_recips)
                        updated_qs.update(delivered=True, delivered_at=now)
                        # notify sender about these deliveries so UI can show delivered ticks
                        for r in ChatMessageReceipt.objects.filter(message=saved, user_id__in=online_recips):
                            try:
                                async_to_sync(channel_layer.group_send)(f'user_{sender_id}', {
                                    'type': 'chat.delivery',
                                    'message_id': saved.id,
                                    'receipt_id': r.id,
                                    'user_id': getattr(r.user, 'id', None),
                                    'delivered_at': r.delivered_at.isoformat() if getattr(r, 'delivered_at', None) else None,
                                    'message_delivered': bool(getattr(saved, 'delivered', False)),
                                })
                            except Exception:
                                logging.getLogger(__name__).exception('failed to notify sender about immediate delivery')
                except Exception:
                    logging.getLogger(__name__).exception('failed marking immediate delivered receipts')
            except Exception:
                logging.getLogger(__name__).exception('failed to broadcast message via channel layer')
        except Exception:
            logging.getLogger(__name__).exception('post-create receipt/broadcast failed')

    # Acción personalizada: obtener los últimos N mensajes de una sala
    from rest_framework.decorators import action

    @action(detail=False, methods=['get'])
    def last_messages(self, request):
        room_id = request.query_params.get('room')
        limit = int(request.query_params.get('limit', 50))
        # sanitize common client-side string values that mean 'no value'
        if not room_id or room_id in ('null', 'undefined'):
            return Response({'detail': "Se requiere 'room' query param válido."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            room_pk = int(room_id)
        except (TypeError, ValueError):
            return Response({'detail': "'room' debe ser un id numérico válido."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            room = ChatRoom.objects.get(pk=room_pk, participants=request.user)
        except ChatRoom.DoesNotExist:
            return Response({'detail': 'Sala no existe o no eres participante.'}, status=status.HTTP_404_NOT_FOUND)

        messages = ChatMessage.objects.filter(room=room).order_by('-timestamp')[:limit]
        # los devolvemos en orden cronológico ascendente
        messages = reversed(list(messages))
        serializer = ChatMessageSerializer(messages, many=True, context={'request': request})
        return Response(serializer.data)

