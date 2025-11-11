"""Async Chat consumer: implements a clear sent->delivered->read flow.

This module provides a single ChatConsumer (AsyncJsonWebsocketConsumer)
that creates messages, marks per-user receipts delivered when a recipient
receives the message via WebSocket, and marks messages read when a user
requests it. It also broadcasts lightweight events for clients to update
UI ticks.
"""
import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

from chat.models import ChatMessage, ChatMessageReceipt, ChatRoom

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user or not getattr(user, 'is_authenticated', False):
            await self.close()
            return

        self.user = user
        self.room_id = self.scope.get('url_route', {}).get('kwargs', {}).get('room_id')
        self.room_group_name = f'chat_{self.room_id}'

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.channel_layer.group_add(f'user_{getattr(user, "id")}', self.channel_name)

        await self.accept()
        logger.info('[CONNECT] user=%s joined room=%s channel=%s', getattr(user, 'id', None), self.room_id, self.channel_name)

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        except Exception:
            logger.exception('group_discard failed')
        try:
            await self.channel_layer.group_discard(f'user_{getattr(self.user, "id")}', self.channel_name)
        except Exception:
            logger.exception('group_discard user failed')
        logger.info('[DISCONNECT] user=%s left room=%s', getattr(self.user, 'id', None), self.room_id)

    async def receive_json(self, content, **kwargs):
        try:
            logger.debug('[RECEIVE_JSON] user=%s payload=%s', getattr(self.user, 'id', None), content)
            event_type = content.get('type')
            if event_type == 'chat_message':
                await self.create_message(content)
            # allow clients to send a temporary preview payload (contains preview_data_url)
            # without creating a persistent ChatMessage. This will rebroadcast the
            # lightweight preview to the room so other connected clients can display
            # a thumbnail immediately while the upload finishes on the sender side.
            elif event_type in ('chat.message', 'preview_message', 'preview'):
                # Only accept preview messages that include a preview_data_url or a previewUrl
                try:
                    if not (content.get('preview_data_url') or content.get('previewUrl') or content.get('preview_url')):
                        logger.debug('[RECEIVE_JSON] preview event ignored, missing preview field')
                    else:
                        # build a normalized preview payload and broadcast to room group
                        room_id = content.get('room_id') or self.room_id
                        preview_msg = {
                            'id': content.get('id') or content.get('temp_id') or f'tmp_{int(timezone.now().timestamp()*1000)}',
                            'client_msg_id': content.get('client_msg_id') or content.get('clientMsgId') or None,
                            'sender_id': getattr(self.user, 'id', None),
                            'preview_data_url': content.get('preview_data_url') or content.get('previewUrl') or content.get('preview_url'),
                            'media_type': content.get('media_type') or content.get('mediaType') or None,
                            'media_uploading': True,
                            'status': 'uploading',
                            'room': room_id,
                            'room_id': room_id,
                            'timestamp': content.get('timestamp') or timezone.now().isoformat(),
                        }
                        # Broadcast as a lightweight event; consumers will handle preview_message
                        group_name = f'chat_{room_id}'
                        await self.channel_layer.group_send(group_name, {
                            'type': 'preview_message',
                            'message': preview_msg,
                            'room_id': room_id,
                        })
                        logger.info('[PREVIEW_BCAST] rebroadcast preview to room=%s sender=%s', room_id, getattr(self.user, 'id', None))
                except Exception:
                    logger.exception('receive_json: failed handling preview event')
            elif event_type == 'mark_read':
                await self.mark_messages_read(content)
            else:
                logger.warning('[UNKNOWN_EVENT] %s', event_type)
        except Exception:
            logger.exception('receive_json handling failed')

    async def create_message(self, content):
        """Create a ChatMessage and per-user receipts, then broadcast."""
        user = self.user
        room_id = content.get('room_id') or self.room_id
        text = content.get('text', '')
        try:
            room = await database_sync_to_async(ChatRoom.objects.get)(id=room_id)
        except Exception:
            logger.exception('create_message: room lookup failed %s', room_id)
            return

        try:
            msg = await database_sync_to_async(ChatMessage.objects.create)(room=room, sender=user, content=text)
        except Exception:
            logger.exception('create_message: failed saving message')
            return

        # create receipts for each participant except sender
        try:
            participants = await database_sync_to_async(lambda: list(room.participants.all()))()
            for p in participants:
                if p.id == user.id:
                    continue
                r, created = await database_sync_to_async(ChatMessageReceipt.objects.get_or_create)(message=msg, user=p)
                if created:
                    logger.info('[RECEIPT_CREATED] msg=%s user=%s', msg.id, getattr(p, 'id', None))
        except Exception:
            logger.exception('create_message: failed creating receipts')

        logger.info('[MESSAGE_CREATED] id=%s sender=%s room=%s', msg.id, user.id, room_id)

        # Broadcast the message to the room
        try:
            # include room hint so clients can route incoming messages without guessing
            out_payload = {
                # Use underscore type to match legacy consumers that expect 'chat_message'
                'type': 'chat_message',
                'message_id': msg.id,
                'sender_id': user.id,
                'text': text,
                'room_id': room_id,
                'room': room_id,
                'client_msg_id': getattr(self.scope.get('query_string', b''), 'decode', lambda: None)(),
            }
            # Log the outgoing payload for traceability
            logger.info('[BCAST_OUT] chat.message -> room=%s payload=%s', room_id, out_payload)
            await self.channel_layer.group_send(self.room_group_name, out_payload)
            logger.info('[BCAST_DONE] chat.message group_send completed for %s', self.room_group_name)
        except Exception:
            logger.exception('create_message: failed group_send')

    async def chat_message(self, event):
        """Handler invoked when a chat.message is sent to this channel's group.

        Mark the per-user receipt delivered for the connected user and reply
        with a delivered status so the sender can show double gray ticks.
        """
        # Diagnostic log: record the full incoming group event for tracing
        try:
            logger.info('[EVENT_IN] chat.message event=%s for user=%s', event, getattr(self.user, 'id', None))
        except Exception:
            logger.exception('failed logging incoming chat.message event')

        msg_id = event.get('message_id')
        sender_id = event.get('sender_id')
        text = event.get('text') or event.get('message') or event.get('content')

        logger.debug('[DELIVER] sending msg=%s to user=%s', msg_id, getattr(self.user, 'id', None))

        # mark delivered for this connected user
        try:
            await database_sync_to_async(self._mark_delivered)(msg_id, self.user)
        except Exception:
            logger.exception('chat_message: _mark_delivered failed')

        # fetch updated receipts and broadcast a message_update so sender(s) see delivered ticks
        try:
            receipts = await database_sync_to_async(lambda: list(
                ChatMessageReceipt.objects.filter(message_id=msg_id).values('user_id', 'delivered', 'delivered_at', 'read', 'read_at')
            ))()
            # convert datetimes to ISO strings for channel layer serialization
            serial = []
            for r in receipts:
                serial.append({
                    'user_id': r.get('user_id'),
                    'delivered': bool(r.get('delivered')),
                    'delivered_at': (r.get('delivered_at').isoformat() if r.get('delivered_at') else None),
                    'read': bool(r.get('read')),
                    'read_at': (r.get('read_at').isoformat() if r.get('read_at') else None),
                })
            # include room hint so clients can apply the update to the proper room quickly
            logger.info('[BCAST] message_update msg=%s receipts=%s room=%s', msg_id, serial, self.room_id)
            update_payload = {
                'type': 'message.update',
                'message_id': msg_id,
                'receipts': serial,
                'room_id': self.room_id,
                'room': self.room_id,
            }
            logger.debug('[BCAST_OUT] message.update -> room=%s payload=%s', self.room_id, update_payload)
            await self.channel_layer.group_send(self.room_group_name, update_payload)
        except Exception:
            logger.exception('chat_message: broadcasting message_update failed')

        # send the message payload to the client including status
        try:
            logger.info('[SEND_SOCKET] about to send chat_message id=%s to user=%s', msg_id, getattr(self.user, 'id', None))
            # Build a payload re-using any media-related fields the group event carried
            out_payload = {
                'type': 'chat.message',
                'id': msg_id,
                'sender_id': sender_id,
                'text': text,
                'status': 'delivered',
                'room': self.room_id,
                'room_id': self.room_id,
            }
            # Preserve optional media/preview/client identifiers if present on the event
            try:
                for key in ('media_id', 'media_url', 'media_spectrum', 'client_msg_id', 'clientMsgId', 'message', 'content', 'preview_data_url', 'previewUrl'):
                    if key in event and event.get(key) is not None:
                        out_payload[key] = event.get(key)
            except Exception:
                logger.exception('failed merging optional media fields into outgoing payload')

            # Use a consistent dotted event type for WS messages
            await self.send_json(out_payload)
            logger.info('[SENT_SOCKET] chat_message id=%s sent to user=%s', msg_id, getattr(self.user, 'id', None))
        except Exception:
            logger.exception('chat_message: send_json failed')

    async def preview_message(self, event):
        """Handler for preview broadcasts: forwards a lightweight preview
        payload to the connected client without persisting or marking receipts.
        This is used when a sender emits a temporary preview (preview_data_url)
        while the actual file upload is in progress.
        """
        try:
            msg = event.get('message') or {}
            # send as a consistent 'chat.message' payload so JS clients handle it
            await self.send_json({
                'type': 'chat.message',
                'message': msg,
                'room': event.get('room_id') or msg.get('room') or None,
                'room_id': event.get('room_id') or msg.get('room') or None,
            })
            logger.debug('[PREVIEW_SEND] forwarded preview to user=%s msg=%s', getattr(self.user, 'id', None), msg.get('id'))
        except Exception:
            logger.exception('preview_message: send_json failed')

    def _mark_delivered(self, msg_id, user):
        try:
            receipt, _ = ChatMessageReceipt.objects.get_or_create(message_id=msg_id, user=user)
            if not receipt.delivered:
                receipt.delivered = True
                receipt.delivered_at = timezone.now()
                receipt.save(update_fields=['delivered', 'delivered_at'])
                logger.info('[RECEIPT_DELIVERED] msg=%s user=%s', msg_id, getattr(user, 'id', None))
        except Exception as e:
            logger.exception('[ERROR_DELIVERED] msg=%s user=%s: %s', msg_id, getattr(user, 'id', None), e)

    async def mark_messages_read(self, content):
        # accept either 'room' or 'room_id' from client payload
        room_id = content.get('room') or content.get('room_id') or self.room_id
        user = self.user
        logger.info('[READ_MARK] user=%s marking room=%s as read', getattr(user, 'id', None), room_id)

        try:
            # Mark all messages as read for this user in the room. We no longer
            # require receipts to be 'delivered' before marking them read because
            # a client that opens the chat and reads messages should cause the
            # sender to see blue ticks even if the delivered flag was not
            # previously updated (e.g., due to connection timing).
            message_ids = await database_sync_to_async(self._mark_all_read)(room_id, user)
        except Exception:
            logger.exception('mark_messages_read: _mark_all_read failed')
            message_ids = []

        # Log in the requested format so it's easy to grep in logs
        try:
            updated_count = len(message_ids) if message_ids else 0
            logger.info('[WS] Mark read for user=%s room=%s updated=%s', getattr(user, 'id', None), room_id, updated_count)
        except Exception:
            logger.exception('mark_messages_read: failed logging WS Mark read')

        # notify the room that this user read messages and broadcast updated receipts per message
        try:
            await self.channel_layer.group_send(self.room_group_name, {
                'type': 'messages.read.broadcast',
                'user_id': getattr(user, 'id', None),
                'room_id': room_id,
            })
        except Exception:
            logger.exception('mark_messages_read: group_send failed')

        # For each affected message, broadcast an updated receipts payload
        try:
            for mid in message_ids or []:
                receipts = await database_sync_to_async(lambda: list(
                    ChatMessageReceipt.objects.filter(message_id=mid).values('user_id', 'delivered', 'delivered_at', 'read', 'read_at')
                ))()
                serial = []
                for r in receipts:
                    serial.append({
                        'user_id': r.get('user_id'),
                        'delivered': bool(r.get('delivered')),
                        'delivered_at': (r.get('delivered_at').isoformat() if r.get('delivered_at') else None),
                        'read': bool(r.get('read')),
                        'read_at': (r.get('read_at').isoformat() if r.get('read_at') else None),
                    })
                logger.info('[BCAST] message_update(read) msg=%s receipts=%s room=%s', mid, serial, room_id)
                # Include room hint so clients can route the update without
                # falling back to active room. Also include 'room' for older
                # compatibility.
                await self.channel_layer.group_send(self.room_group_name, {
                    'type': 'message.update',
                    'message_id': mid,
                    'receipts': serial,
                    'room_id': room_id,
                    'room': room_id,
                })
        except Exception:
            logger.exception('mark_messages_read: broadcasting message_update failed')

    def _mark_all_read(self, room_id, user):
        try:
            # We look for receipts that are not yet read for this user in the room.
            # Previously we only marked messages read if they were already marked
            # delivered; this could leave messages unmarked when delivery flags
            # weren't set. Here we mark delivered/read together so the sender
            # receives the read update reliably.
            # First, determine which message ids have unread receipts for this user
            receipts_qs = ChatMessageReceipt.objects.filter(message__room_id=room_id, user=user, read=False)
            message_ids = list(receipts_qs.values_list('message_id', flat=True))
            if not message_ids:
                logger.debug('[NO_UNREAD] user=%s room=%s', getattr(user, 'id', None), room_id)
                return []

            now = timezone.now()
            # Set delivered/read flags and timestamps for those receipts
            ChatMessageReceipt.objects.filter(message__room_id=room_id, user=user, read=False).update(
                delivered=True, delivered_at=now, read=True, read_at=now
            )
            logger.info('[MARK_READ] user=%s room=%s count=%s', getattr(user, 'id', None), room_id, len(message_ids))

            # Update aggregate ChatMessage.read/seen when all receipts are read
            try:
                filtered_message_ids = []
                for mid in set(message_ids):
                    try:
                        msg_obj = ChatMessage.objects.filter(id=mid).first()
                        if msg_obj and getattr(msg_obj, 'sender_id', None) == getattr(user, 'id', None):
                            # skip marking this message's aggregated flags
                            continue
                        filtered_message_ids.append(mid)
                    except Exception:
                        # if any unexpected error, be conservative and include the id
                        filtered_message_ids.append(mid)

                for mid in filtered_message_ids:
                    still_unread = ChatMessageReceipt.objects.filter(message_id=mid, read=False).exists()
                    if not still_unread:
                        # only update aggregated ChatMessage flags for messages not
                        # authored by the marking user
                        try:
                            ChatMessage.objects.filter(id=mid).update(read=True, seen=True, read_at=now)
                        except Exception:
                            logger.exception('failed updating ChatMessage aggregated flags for id=%s', mid)
            except Exception:
                logger.exception('failed updating aggregate ChatMessage read flags')
                return message_ids

            # Return affected message ids when successful
            return message_ids
        except Exception:
            logger.exception(' _mark_all_read failed')
            return []

    async def messages_read_broadcast(self, event):
        logger.debug('[BROADCAST_READ] user=%s room=%s', event.get('user_id'), event.get('room_id'))
        try:
            # Do not send a status_update to the user who originated the read
            # action. Sending it to the originator is noisy and can cause the
            # client to interpret its own read as a remote action.
            origin_user = event.get('user_id')
            if origin_user is not None and str(origin_user) == str(getattr(self.user, 'id', None)):
                logger.debug('[BROADCAST_READ] skipping status_update to originator user=%s', origin_user)
                return

            await self.send_json({
                'type': 'status_update',
                'status': 'read',
                'user_id': event.get('user_id'),
                'room_id': event.get('room_id'),
            })
        except Exception:
            logger.exception('messages_read_broadcast: send_json failed')

    async def message_update(self, event):
        """Broadcast when receipts for a message change (delivered/read)."""
        # Diagnostic log for incoming update events
        try:
            logger.info('[EVENT_IN] message.update event=%s for user=%s', event, getattr(self.user, 'id', None))
        except Exception:
            logger.exception('failed logging incoming message.update event')

        # Include room hints at top-level and inside the message object so
        # JS clients can route the update reliably regardless of payload
        # shape variations from different producers.
        try:
            await self.send_json({
                'type': 'message_update',
                'message': {
                    'id': event.get('message_id'),
                    'receipts': event.get('receipts'),
                    'room_id': event.get('room_id') or event.get('room'),
                },
                'room_id': event.get('room_id') or event.get('room'),
                'room': event.get('room') or event.get('room_id'),
            })
        except Exception:
            logger.exception('message_update: send_json failed')

    # Compatibility handlers for events emitted elsewhere in the codebase
    async def chat_message_read(self, event):
        try:
            await self.send_json(dict(event, type='chat.message.read'))
        except Exception:
            logger.exception('chat_message_read: send_json failed')

    async def chat_message_delivered(self, event):
        try:
            await self.send_json(dict(event, type='chat.message.delivered'))
        except Exception:
            logger.exception('chat_message_delivered: send_json failed')

    async def chat_read(self, event):
        try:
            await self.send_json(dict(event, type='chat.read'))
        except Exception:
            logger.exception('chat_read: send_json failed')

    async def chat_delivery(self, event):
        try:
            await self.send_json(dict(event, type='chat.delivery'))
        except Exception:
            logger.exception('chat_delivery: send_json failed')

    async def message_delivered(self, event):
        try:
            # forward as-is but include a friendly type for JS listeners
            await self.send_json(dict(event, type='message_delivered'))
        except Exception:
            logger.exception('send message_delivered failed')

    async def chat_message_direct(self, event):
        """Fallback handler for direct per-user broadcasts from HTTP create path.

        This is used as a redundancy: if the room group delivery is missed for
        some reason, the server will also send a per-user event of this type to
        the `user_<id>` group so connected consumers still receive the message.
        """
        try:
            logger.info('[EVENT_IN] chat_message_direct event=%s for user=%s', event, getattr(self.user, 'id', None))
        except Exception:
            logger.exception('failed logging incoming chat_message_direct event')

        try:
            # Normalize payload keys similar to chat_message handler
            msg_id = event.get('message_id') or event.get('id')
            sender_id = event.get('sender_id')
            text = event.get('text') or event.get('message') or event.get('content')

            out = {
                'type': 'chat.message',
                'id': msg_id,
                'sender_id': sender_id,
                'text': text,
                'status': 'delivered',
                'room': event.get('room_id') or event.get('room'),
                'room_id': event.get('room_id') or event.get('room'),
            }
            try:
                for key in ('media_id', 'media_url', 'media_spectrum', 'client_msg_id', 'clientMsgId', 'message', 'content', 'preview_data_url', 'previewUrl'):
                    if key in event and event.get(key) is not None:
                        out[key] = event.get(key)
            except Exception:
                logger.exception('chat_message_direct: failed merging optional media fields')

            # Send the enriched payload
            await self.send_json(out)
        except Exception:
            logger.exception('chat_message_direct: send_json failed')

    async def message_seen(self, event):
        try:
            await self.send_json(dict(event, type='message_seen'))
        except Exception:
            logger.exception('send message_seen failed')

