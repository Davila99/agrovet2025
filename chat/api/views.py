from rest_framework import viewsets, status, serializers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
import logging
from rest_framework.decorators import action
from django.db import DatabaseError, IntegrityError, DataError

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
        # Log incoming payload at debug level (avoid noisy prints)
        logger.debug('[ChatRoomViewSet] raw_body=%s', getattr(request, 'body', None))
        logger.debug('[ChatRoomViewSet] request.data=%s', getattr(request, 'data', None))
        # Create serializer and validate explicitly
        serializer = self.get_serializer(data=request.data)
        is_valid = serializer.is_valid()
        logger.debug('[ChatRoomViewSet] is_valid=%s errors=%s', is_valid, getattr(serializer, 'errors', None))

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
        logger = logging.getLogger(__name__)
        logger.debug('[ChatRoomViewSet] validated_data keys=%s participants=%s', list(serializer.validated_data.keys()), participants)

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
        # Log incoming raw body and request data at debug level
        logger.debug('[ChatMessageViewSet] raw_body=%s', getattr(request, 'body', None))
        logger.debug('[ChatMessageViewSet] request.data=%s', getattr(request, 'data', None))

        # Use request.data directly now that the DB has been migrated to utf8mb4
        # so emojis / 4-byte unicode characters are supported. The previous
        # sanitizer that stripped 4-byte chars has been removed.
        serializer = self.get_serializer(data=request.data)
        try:
            is_valid = serializer.is_valid()
        except Exception:
            logger.exception('serializer.is_valid() raised exception')
            return Response({'detail': 'Serializer validation error (see server logs).'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not is_valid:
            logger.warning('[ChatMessageViewSet] serializer errors: %s', serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            out = self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            # prefer returning the explicit payload built in perform_create
            return Response(out or serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except (DataError, DatabaseError, IntegrityError) as e:
            # Likely a DB encoding/constraint issue (e.g. attempting to store
            # a 4-byte emoji on a MySQL column that uses 'utf8' instead of
            # 'utf8mb4'). Return a helpful 400 so the client can retry
            # or remove problematic characters.
            logger.exception('Database error creating ChatMessage (possible encoding/charset issue)')
            return Response({'detail': 'Error saving message to database. Possible unsupported characters (emoji) due to DB charset. Consider migrating to utf8mb4.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception('ChatMessage create/perform_create failed')
            return Response({'detail': 'Error creating chat message (see server logs).'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
                'text': saved.content or '',
                'message': saved.content or '',
                'content': saved.content or '',
                'username': getattr(saved.sender, 'full_name', str(saved.sender)),
                'sender_id': getattr(saved.sender, 'id', None),
                'media_id': getattr(getattr(saved, 'media', None), 'id', None),
                'media_url': getattr(getattr(saved, 'media', None), 'url', None),
                # If Media.description stores JSON-encoded spectrum or metadata, surface it
                'media_spectrum': None,
                'message_id': saved.id,
                'id': saved.id,
                'client_msg_id': getattr(self.request, 'data', {}).get('client_msg_id', None),
                'room_id': str(saved.room_id),
                'timestamp': saved.timestamp.isoformat() if getattr(saved, 'timestamp', None) else None,
                'receipts': receipts,
            }

            try:
                media_obj = getattr(saved, 'media', None)
                # Re-fetch media from DB to avoid stale/related-object timing issues
                try:
                    if media_obj is not None:
                        from media.models import Media as _MediaModel
                        media_obj = _MediaModel.objects.filter(id=getattr(media_obj, 'id', None)).first() or media_obj
                except Exception:
                    pass
                if media_obj:
                    desc = getattr(media_obj, 'description', None)
                    try:
                        logging.getLogger(__name__).debug('Media description for media_id=%s repr: %s', getattr(media_obj, 'id', None), (repr(desc)[:200] + ('...' if desc and len(str(desc)) > 200 else '')) )
                    except Exception:
                        pass
                    if desc:
                        import json as _json
                        try:
                            parsed = _json.loads(desc) if isinstance(desc, (str, bytes)) else desc
                            # parsed may be a plain list of bins or a dict containing the spectrum
                            if isinstance(parsed, list):
                                out['media_spectrum'] = parsed
                            elif isinstance(parsed, dict):
                                # common keys to check
                                for k in ('spectrum', 'media_spectrum', 'audio_spectrum', 'bins'):
                                    if k in parsed and isinstance(parsed[k], list):
                                        out['media_spectrum'] = parsed[k]
                                        break
                                else:
                                    # last resort: try to find first list value
                                    found = None
                                    for v in parsed.values():
                                        if isinstance(v, list):
                                            found = v
                                            break
                                    out['media_spectrum'] = found
                            else:
                                out['media_spectrum'] = None
                        except Exception:
                            out['media_spectrum'] = None
                try:
                    if out.get('media_id') is not None:
                        logging.getLogger(__name__).info('HTTP create broadcast payload media debug: media_id=%s media_url=%s media_spectrum=%s', out.get('media_id'), out.get('media_url'), (out.get('media_spectrum') and ('len=%d' % len(out.get('media_spectrum'))) or None))
                except Exception:
                    logging.getLogger(__name__).exception('failed to log media debug info')
            except Exception:
                pass

            # Send to room group and per-user groups so clients update in real-time
            try:
                channel_layer = get_channel_layer()
                # Log the HTTP-created outbound payload for traceability
                logging.getLogger(__name__).info('[HTTP_BCAST] chat.message -> room=%s out=%s', saved.room_id, out)
                # Use the same room group naming as ChatConsumer ('chat_<room_id>')
                async_to_sync(channel_layer.group_send)(f'chat_{saved.room_id}', out)
                logging.getLogger(__name__).info('[HTTP_BCAST_DONE] chat.message group_send completed for room=%s', saved.room_id)
                for pid in participant_ids:
                    async_to_sync(channel_layer.group_send)(f'user_{pid}', dict(out, from_me=(int(pid) == int(sender_id))))
                    logging.getLogger(__name__).info('[HTTP_BCAST_DONE] chat.message per-user group_send completed for user=%s room=%s', pid, saved.room_id)

                # Fallback: send an explicit per-user direct event that maps to
                # consumer.chat_message_direct to ensure delivery even if the
                # room group delivery is missed for some consumers.
                try:
                    direct_payload = {
                        'type': 'chat_message_direct',
                        'message_id': saved.id,
                        'id': saved.id,
                        'sender_id': getattr(saved.sender, 'id', None),
                        'text': saved.content or '',
                        'message': saved.content or '',
                        'room_id': str(saved.room_id),
                        'client_msg_id': getattr(self.request, 'data', {}).get('client_msg_id', None),
                    }
                    logging.getLogger(__name__).info('[HTTP_BCAST] chat_message_direct -> room=%s payload=%s', saved.room_id, direct_payload)
                    for pid in participant_ids:
                        async_to_sync(channel_layer.group_send)(f'user_{pid}', direct_payload)
                except Exception:
                    logging.getLogger(__name__).exception('failed broadcasting direct per-user chat_message_direct')
                # Additionally, broadcast a message_update containing the per-user receipts
                try:
                    # ensure receipts is JSON-serializable (already built above)
                    update_payload = {
                        'type': 'message.update',
                        'message_id': saved.id,
                        'receipts': receipts,
                        'room_id': str(saved.room_id),
                        'room': str(saved.room_id),
                        # include client_msg_id so clients that optimistically
                        # created a local message can match incoming updates
                        # (handles the race where an update arrives before
                        # the full message_new payload).
                        'client_msg_id': getattr(self.request, 'data', {}).get('client_msg_id', None),
                        # include minimal text so the client can display a
                        # lightweight representation if the full message
                        # payload hasn't arrived yet.
                        'text': saved.content or '',
                    }
                    logging.getLogger(__name__).info('[HTTP_BCAST] message.update -> room=%s payload=%s', saved.room_id, update_payload)
                    async_to_sync(channel_layer.group_send)(f'chat_{saved.room_id}', update_payload)
                except Exception:
                    logging.getLogger(__name__).exception('failed broadcasting initial message_update')
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
            # Return the sanitized outgoing payload so the HTTP response can
            # include the created message and receipts for immediate client
            # reconciliation of optimistic messages.
            try:
                return out
            except Exception:
                # fallback to serializer.data if out is not available
                return serializer.data
        except Exception:
            logging.getLogger(__name__).exception('post-create receipt/broadcast failed')

    # Acción personalizada: obtener los últimos N mensajes de una sala
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

        # Prefetch receipts to avoid N+1 queries and ensure the serializer
        # can include per-message receipts so the client sees persisted ticks
        # after reloads.
        try:
            messages_qs = ChatMessage.objects.filter(room=room).order_by('-timestamp').prefetch_related('receipts')[:limit]
            # los devolvemos en orden cronológico ascendente
            messages = reversed(list(messages_qs))
            serializer = ChatMessageSerializer(messages, many=True, context={'request': request})
            return Response(serializer.data)
        except Exception:
            logging.getLogger(__name__).exception('failed fetching last_messages')
            return Response({'detail': 'Error al obtener mensajes.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

