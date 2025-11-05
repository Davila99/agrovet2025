"""Clean Channels consumers for chat and presence.

Provides ChatConsumer and PresenceConsumer plus small DB helpers.
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
import asyncio

from .models import ChatRoom, ChatMessage

User = get_user_model()
logger = logging.getLogger(__name__)

# Presence helpers: prefer Redis-backed shared presence; fallback to local set
from .presence import mark_online, mark_offline, is_online  # async helpers


@database_sync_to_async
def _get_room_participant_ids(room_id):
    try:
        r = ChatRoom.objects.filter(id=room_id).first()
        if not r:
            return []
        return list(r.participants.values_list('id', flat=True))
    except Exception:
        logger.exception('_get_room_participant_ids failed')
        return []


@database_sync_to_async
def _get_room_messages(room_id, limit=200, only_unread_for_user=None):
    """Fetch messages for a room.

    By default returns the most recent `limit` messages (so the client sees
    the latest history). If `only_unread_for_user` is provided (user id), the
    helper will attempt to return only the unread messages for that user in
    the room (ordered chronologically). If there are no unread receipts, it
    falls back to returning the most recent `limit` messages.
    """
    try:
        room = ChatRoom.objects.filter(id=room_id).first()
        if not room:
            return None

        msgs = []
        # If asked to return only unread messages for a user, attempt that.
        if only_unread_for_user is not None:
            try:
                from .models import ChatMessageReceipt
                # receipts for this user and room where read=False
                qs_receipts = ChatMessageReceipt.objects.filter(user_id=only_unread_for_user, message__room=room, read=False).select_related('message').order_by('message__timestamp')
                message_ids = list(qs_receipts.values_list('message_id', flat=True))
                # Additionally, include messages in the room that have no receipt
                # for this user yet (older messages created before receipts existed
                # or in case of missing receipts). Exclude messages sent by the user.
                qs_no_receipt = ChatMessage.objects.filter(room=room).exclude(sender_id=only_unread_for_user).exclude(receipts__user_id=only_unread_for_user).order_by('timestamp')
                no_receipt_ids = list(qs_no_receipt.values_list('id', flat=True))
                # Merge and preserve chronological order
                combined_ids = []
                seen = set()
                for mid in (list(qs_receipts.values_list('message__id', flat=True)) + no_receipt_ids):
                    if mid not in seen:
                        seen.add(mid)
                        combined_ids.append(mid)
                if combined_ids:
                    msgs_qs = ChatMessage.objects.filter(id__in=combined_ids).order_by('timestamp')
                    for m in msgs_qs:
                        # include receipts persisted for this message so clients
                        # know which recipients already delivered/read it
                        receipts_out = []
                        try:
                            for r in getattr(m, 'receipts', m.receipts.all()):
                                receipts_out.append({
                                    'user_id': getattr(r.user, 'id', None),
                                    'delivered': bool(r.delivered),
                                    'delivered_at': r.delivered_at.isoformat() if getattr(r, 'delivered_at', None) else None,
                                    'read': bool(r.read),
                                    'read_at': r.read_at.isoformat() if getattr(r, 'read_at', None) else None,
                                })
                        except Exception:
                            receipts_out = []

                        msgs.append({
                            'id': m.id,
                            'sender_id': getattr(m.sender, 'id', None),
                            'content': m.content,
                            'timestamp': m.timestamp.isoformat() if getattr(m, 'timestamp', None) else None,
                            'delivered': bool(getattr(m, 'delivered', False)),
                            'delivered_at': getattr(m, 'delivered_at', None).isoformat() if getattr(m, 'delivered_at', None) else None,
                            'read': bool(getattr(m, 'read', False)),
                            'read_at': getattr(m, 'read_at', None).isoformat() if getattr(m, 'read_at', None) else None,
                            'receipts': receipts_out,
                        })
                    participants = list(room.participants.values('id', 'full_name', 'username', 'profile_picture'))
                    return {
                        'id': str(room.id),
                        'name': room.name or '',
                        'participants': participants,
                        'messages': msgs,
                        'unread_only': True,
                    }
            except Exception:
                logger.exception('failed fetching unread receipts')

        # Fallback: return the most recent `limit` messages (chronological)
        qs = list(room.messages.order_by('-timestamp')[:limit])
        qs.reverse()
        for m in qs:
            receipts_out = []
            try:
                for r in getattr(m, 'receipts', m.receipts.all()):
                    receipts_out.append({
                        'user_id': getattr(r.user, 'id', None),
                        'delivered': bool(r.delivered),
                        'delivered_at': r.delivered_at.isoformat() if getattr(r, 'delivered_at', None) else None,
                        'read': bool(r.read),
                        'read_at': r.read_at.isoformat() if getattr(r, 'read_at', None) else None,
                    })
            except Exception:
                receipts_out = []

            msgs.append({
                'id': m.id,
                'sender_id': getattr(m.sender, 'id', None),
                'content': m.content,
                'timestamp': m.timestamp.isoformat() if getattr(m, 'timestamp', None) else None,
                'delivered': bool(getattr(m, 'delivered', False)),
                'delivered_at': getattr(m, 'delivered_at', None).isoformat() if getattr(m, 'delivered_at', None) else None,
                'read': bool(getattr(m, 'read', False)),
                'read_at': getattr(m, 'read_at', None).isoformat() if getattr(m, 'read_at', None) else None,
                'receipts': receipts_out,
            })

        participants = list(room.participants.values('id', 'full_name', 'username', 'profile_picture'))
        return {
            'id': str(room.id),
            'name': room.name or '',
            'participants': participants,
            'messages': msgs,
            'unread_only': False,
        }
    except Exception:
        logger.exception('_get_room_messages failed')
        return None


@database_sync_to_async
def _get_room_participants(room_id):
    try:
        room = ChatRoom.objects.filter(id=room_id).first()
        if not room:
            return []
        return list(room.participants.values('id', 'full_name', 'username', 'profile_picture'))
    except Exception:
        logger.exception('_get_room_participants failed')
        return []


@database_sync_to_async
def _get_rooms_for_user(user_id):
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return []
        rooms = ChatRoom.objects.filter(participants=user).order_by('-last_activity')
        payload = []
        for r in rooms:
            msgs = []
            for m in list(r.messages.order_by('timestamp')[:50]):
                # include receipts for each preview message so client can show ticks
                receipts_out = []
                try:
                    for rr in getattr(m, 'receipts', m.receipts.all()):
                        receipts_out.append({
                            'user_id': getattr(rr.user, 'id', None),
                            'delivered': bool(rr.delivered),
                            'delivered_at': rr.delivered_at.isoformat() if getattr(rr, 'delivered_at', None) else None,
                            'read': bool(rr.read),
                            'read_at': rr.read_at.isoformat() if getattr(rr, 'read_at', None) else None,
                        })
                except Exception:
                    receipts_out = []
                msgs.append({'id': m.id, 'sender_id': getattr(m.sender, 'id', None), 'content': m.content, 'timestamp': m.timestamp.isoformat() if getattr(m, 'timestamp', None) else None, 'receipts': receipts_out})
            participants = list(r.participants.values('id', 'full_name', 'username', 'profile_picture'))
            payload.append({'id': str(r.id), 'name': r.name or '', 'participants': participants, 'messages': msgs})
        return payload
    except Exception:
        logger.exception('_get_rooms_for_user failed')
        return []


@database_sync_to_async
def _get_undelivered_messages_for_user(user_id):
    """Return undelivered messages for rooms where the given user participates.

    This helper assumes ChatMessage has a boolean `delivered` field to track
    whether the message has been delivered to participants. For private 1:1
    chats this is sufficient. If you have group chats, consider a per-user
    delivered/seen table instead.
    """
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return []
        # messages in rooms where user participates, sent by someone else and not delivered
        # Return list of undelivered receipts (per-user) with message payload so
        # PresenceConsumer can send only messages that were not yet delivered to
        # this specific user.
        from .models import ChatMessageReceipt
        qs = ChatMessageReceipt.objects.filter(user=user, delivered=False).select_related('message__sender', 'message__room').order_by('message__timestamp')
        out = []
        for r in qs:
            m = r.message
            out.append({
                'receipt_id': r.id,
                'message_id': m.id,
                'room_id': str(m.room.id),
                'sender_id': getattr(m.sender, 'id', None),
                'username': getattr(m.sender, 'full_name', None) or getattr(m.sender, 'username', str(getattr(m.sender, 'id', ''))),
                'message': m.content,
                'content': m.content,
                'timestamp': m.timestamp.isoformat() if getattr(m, 'timestamp', None) else None,
            })
        return out
    except Exception:
        logger.exception('_get_undelivered_messages_for_user failed')
        return []


@database_sync_to_async
def _mark_messages_delivered(message_ids):
    try:
        if not message_ids:
            return 0
        # For backward compatibility we still mark ChatMessage.delivered True
        # when all recipients have receipts delivered, but callers here will
        # typically mark receipts instead. We implement a convenience updater.
        updated = 0
        try:
            qs = ChatMessage.objects.filter(id__in=message_ids)
            updated = qs.update(delivered=True)
        except Exception:
            pass
        return updated
    except Exception:
        logger.exception('_mark_messages_delivered failed')
        return 0


@database_sync_to_async
def _get_message_receipts(message_id):
    try:
        from .models import ChatMessageReceipt
        rs = ChatMessageReceipt.objects.filter(message_id=message_id).select_related('user')
        out = []
        for r in rs:
            out.append({
                'user_id': getattr(r.user, 'id', None),
                'delivered': r.delivered,
                'delivered_at': r.delivered_at.isoformat() if getattr(r, 'delivered_at', None) else None,
                'read': r.read,
                'read_at': r.read_at.isoformat() if getattr(r, 'read_at', None) else None,
            })
        return out
    except Exception:
        logger.exception('_get_message_receipts failed')
        return []


@database_sync_to_async
def _mark_receipt_delivered(receipt_id):
    try:
        from django.utils import timezone
        from .models import ChatMessageReceipt, ChatMessage
        r = ChatMessageReceipt.objects.filter(id=receipt_id).first()
        if not r:
            return {'ok': False}
        if not r.delivered:
            now = timezone.now()
            r.delivered = True
            r.delivered_at = now
            r.save(update_fields=['delivered', 'delivered_at'])
            # If all receipts for this message are delivered, update aggregate on ChatMessage
            try:
                still_undelivered = ChatMessageReceipt.objects.filter(message_id=r.message_id, delivered=False).exists()
                if not still_undelivered:
                    ChatMessage.objects.filter(id=r.message_id, delivered=False).update(delivered=True, delivered_at=now)
            except Exception:
                logger.exception('failed updating ChatMessage delivered flag')
        # return useful info for callers so they can include timestamps in events
        try:
            msg = ChatMessage.objects.filter(id=r.message_id).first()
            return {
                'ok': True,
                'receipt_id': r.id,
                'message_id': r.message_id,
                'delivered_at': r.delivered_at.isoformat() if getattr(r, 'delivered_at', None) else None,
                'message_delivered': bool(getattr(msg, 'delivered', False)),
                'message_delivered_at': getattr(msg, 'delivered_at', None).isoformat() if getattr(msg, 'delivered_at', None) else None,
            }
        except Exception:
            return {'ok': True, 'receipt_id': r.id, 'message_id': r.message_id}
    except Exception:
        logger.exception('_mark_receipt_delivered failed')
        return {'ok': False}


@database_sync_to_async
def _mark_receipts_read_for_user(room_id, user_id):
    try:
        from django.utils import timezone
        from .models import ChatMessageReceipt
        rs = ChatMessageReceipt.objects.filter(message__room_id=room_id, user_id=user_id, read=False)
        updated = rs.update(read=True, read_at=timezone.now())
        return updated
    except Exception:
        logger.exception('_mark_receipts_read_for_user failed')
        return 0


@database_sync_to_async
def _mark_receipts_read_and_get_message_ids(room_id, user_id):
    """Mark receipts read for a user in a room and return the affected message ids.

    Returns a list of message ids whose receipts were updated to read=True.
    """
    try:
        from django.utils import timezone
        from .models import ChatMessageReceipt, ChatMessage
        now = timezone.now()
        qs = ChatMessageReceipt.objects.filter(message__room_id=room_id, user_id=user_id, read=False)
        message_ids = list(qs.values_list('message_id', flat=True))
        if message_ids:
            qs.update(read=True, read_at=now)
            # If for any message all receipts are now read, mark aggregate on ChatMessage
            try:
                uniq_ids = set(message_ids)
                for mid in uniq_ids:
                    still_unread = ChatMessageReceipt.objects.filter(message_id=mid, read=False).exists()
                    if not still_unread:
                        ChatMessage.objects.filter(id=mid, read=False).update(read=True, read_at=now)
            except Exception:
                logger.exception('failed updating ChatMessage read flags')
        return message_ids
    except Exception:
        logger.exception('_mark_receipts_read_and_get_message_ids failed')
        return []


@database_sync_to_async
def _get_messages_read_info(message_ids):
    try:
        from .models import ChatMessage
        out = {}
        if not message_ids:
            return out
        qs = ChatMessage.objects.filter(id__in=message_ids)
        for m in qs:
            out[str(m.id)] = {
                'read': bool(getattr(m, 'read', False)),
                'read_at': getattr(m, 'read_at', None).isoformat() if getattr(m, 'read_at', None) else None,
            }
        return out
    except Exception:
        logger.exception('_get_messages_read_info failed')
        return {}


@database_sync_to_async
def save_message(user_id, room_id, message):
    try:
        room = ChatRoom.objects.get(id=room_id)
    except ChatRoom.DoesNotExist:
        logger.warning('save_message: room does not exist: %s', room_id)
        return None
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.warning('save_message: user does not exist: %s', user_id)
        return None

    content = None
    media_obj = None
    try:
        if isinstance(message, str):
            import json as _json
            parsed = _json.loads(message)
        else:
            parsed = message
        content = parsed.get('content') if isinstance(parsed, dict) else str(parsed)
        media_id = parsed.get('media_id') if isinstance(parsed, dict) else None
        if media_id:
            try:
                from media.models import Media
                media_obj = Media.objects.get(id=media_id)
            except Exception:
                media_obj = None
    except Exception:
        content = str(message)

    m = ChatMessage.objects.create(room=room, sender=user, content=content or '', media=media_obj)
    try:
        logger.info('Saved ChatMessage id=%s room=%s sender=%s', m.id, room.id, user.id)
    except Exception:
        pass
    from django.utils import timezone
    room.last_activity = timezone.now()
    room.save(update_fields=['last_activity'])
    # Create per-user receipts for all participants except the sender
    try:
        from .models import ChatMessageReceipt
        participant_ids = list(room.participants.values_list('id', flat=True))
        for pid in participant_ids:
            if int(pid) == int(getattr(user, 'id', -1)):
                continue
            try:
                ChatMessageReceipt.objects.create(message=m, user_id=pid, delivered=False, read=False)
            except Exception:
                # ignore duplicates or race conditions
                pass
    except Exception:
        logger.exception('failed to create message receipts')
    return m


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope.get('url_route', {}).get('kwargs', {}).get('room_id')
        self.room_group_name = f'chat_{self.room_id}'

        user = self.scope.get('user')
        try:
            hdrs = dict((k.decode(), v.decode()) for k, v in self.scope.get('headers', []))
        except Exception:
            hdrs = {}

        logger.info('WS connect room=%s user=%r channel=%s headers_preview=%s', self.room_id, user, self.channel_name, {k: (v[:64] + '...' if len(v) > 64 else v) for k, v in hdrs.items()})

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        if getattr(user, 'is_authenticated', False):
            await self.channel_layer.group_add(f'user_{getattr(user, "id")}', self.channel_name)

        await self.accept()

        try:
            # Prefer to send only the unread messages for this user to avoid
            # loading the entire history. If there are no unread messages, the
            # helper will fall back to sending the latest `limit` messages.
            uid = getattr(self.scope.get('user'), 'id', None)
            recent = await _get_room_messages(self.room_id, limit=100, only_unread_for_user=uid)
            if recent is not None:
                await self.send(text_data=json.dumps({'type': 'init_room', 'room': recent}))
        except Exception:
            logger.exception('failed to send init_room')

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        except Exception:
            logger.exception('group_discard failed')

        user = self.scope.get('user')
        if getattr(user, 'is_authenticated', False):
            try:
                await self.channel_layer.group_discard(f'user_{getattr(user, "id")}', self.channel_name)
            except Exception:
                logger.exception('group_discard user failed')
                # Notify other participants that this user has gone offline
                try:
                    rooms = await _get_rooms_for_user(getattr(user, 'id'))
                    for r in (rooms or []):
                        parts = r.get('participants') or []
                        for p in parts:
                            try:
                                pid = int(p.get('id')) if p.get('id') is not None else None
                                if pid is None or pid == int(getattr(user, 'id')):
                                    continue
                                await self.channel_layer.group_send(f'user_{pid}', {
                                    'type': 'presence.offline',
                                    'user_id': int(getattr(user, 'id')),
                                    'room_id': r.get('id')
                                })
                            except Exception:
                                logger.exception('failed sending presence.offline to participant')
                except Exception:
                    logger.exception('failed broadcasting presence.offline')

    async def receive(self, text_data=None, bytes_data=None):
        try:
            payload = json.loads(text_data) if text_data else {}
        except Exception:
            payload = {}

        user = self.scope.get('user')
        if not getattr(user, 'is_authenticated', False):
            logger.warning('anonymous send ignored')
            return

        # Support control messages from client: mark_read
        try:
            if isinstance(payload, dict) and payload.get('type') == 'mark_read':
                # mark all receipts in this room for this user as read
                try:
                    # mark receipts as read and obtain which message ids were affected
                    message_ids = await _mark_receipts_read_and_get_message_ids(self.room_id, getattr(user, 'id'))
                    updated = len(message_ids) if isinstance(message_ids, (list, tuple)) else 0
                    # obtain read_at timestamps for affected messages (if any)
                    read_info = await _get_messages_read_info(message_ids)
                    # notify other participants that this user read messages in room
                    payload = {
                        'type': 'chat.read',
                        'room_id': str(self.room_id),
                        'user_id': getattr(user, 'id'),
                        'updated': updated,
                        'message_ids': message_ids,
                        'read_info': read_info,
                    }
                    await self.channel_layer.group_send(self.room_group_name, payload)
                    # Also notify participants directly via their per-user groups so
                    # clients that are not currently subscribed to the room still
                    # receive the read notifications.
                    try:
                        participant_ids = await _get_room_participant_ids(self.room_id)
                        for pid in (participant_ids or []):
                            try:
                                await self.channel_layer.group_send(f'user_{pid}', payload)
                            except Exception:
                                logger.exception('failed sending chat.read to user group %s', pid)
                    except Exception:
                        logger.exception('failed fetching participants to broadcast chat.read')
                except Exception:
                    logger.exception('failed to mark receipts read')
                return
        except Exception:
            logger.exception('mark_read handling failed')

        try:
            saved = await save_message(getattr(user, 'id'), self.room_id, payload)
        except Exception:
            logger.exception('save_message failed')
            saved = None

        out = {
            'type': 'chat.message',
            'message': payload.get('content') if isinstance(payload, dict) else str(payload),
            'content': payload.get('content') if isinstance(payload, dict) else str(payload),
            'username': getattr(user, 'full_name', str(user)),
            'sender_id': getattr(user, 'id', None),
        }
        if isinstance(payload, dict) and 'client_msg_id' in payload:
            out['client_msg_id'] = payload.get('client_msg_id')
        if saved:
            out['message_id'] = saved.id
            out['id'] = saved.id
            out['room_id'] = str(self.room_id)
            try:
                out['participants'] = await _get_room_participants(self.room_id)
            except Exception:
                out['participants'] = []
            try:
                # include per-user receipt summary for the message
                out['receipts'] = await _get_message_receipts(saved.id)
                out['delivered'] = bool(getattr(saved, 'delivered', False))
                out['delivered_at'] = getattr(saved, 'delivered_at', None).isoformat() if getattr(saved, 'delivered_at', None) else None
                out['read'] = bool(getattr(saved, 'read', False))
                out['read_at'] = getattr(saved, 'read_at', None).isoformat() if getattr(saved, 'read_at', None) else None
            except Exception:
                out['receipts'] = []

        try:
            await self.channel_layer.group_send(self.room_group_name, out)
        except Exception:
            logger.exception('group_send failed')

        try:
            participant_ids = await _get_room_participant_ids(self.room_id)
            for pid in participant_ids:
                try:
                    await self.channel_layer.group_send(f'user_{pid}', dict(out, from_me=(int(pid) == int(getattr(user, 'id', -1)))) )
                except Exception:
                    logger.exception('notify user_group failed')
                    continue
        except Exception:
            logger.exception('per-user notify failed')

        # If this is a private 1:1 chat and all recipients (excluding sender)
        # are currently online in this process, mark the message as delivered
        # immediately to avoid re-sending it later on reconnect. This uses the
        # in-memory ONLINE_USERS registry (see note above).
        try:
            if saved:
                sender_id = int(getattr(user, 'id', -1))
                recipients = [int(x) for x in (await _get_room_participant_ids(self.room_id)) if int(x) != sender_id]
                if recipients:
                    # If all recipients are online (consult shared presence store)
                    try:
                        # query presence for each recipient concurrently
                        statuses = await asyncio.gather(*(is_online(r) for r in recipients))
                        all_online = all(statuses)
                        if all_online:
                            try:
                                # mark all receipts for this message delivered
                                from .models import ChatMessageReceipt
                                rs = ChatMessageReceipt.objects.filter(message_id=saved.id, user_id__in=recipients)
                                from django.utils import timezone
                                now = timezone.now()
                                rs.update(delivered=True, delivered_at=now)
                                logger.info('Marked receipts for message %s delivered immediately (all recipients online)', saved.id)
                            except Exception:
                                logger.exception('failed marking receipts delivered')
                    except Exception:
                        logger.exception('failed to mark message delivered based on presence store')
        except Exception:
            logger.exception('failed to mark message delivered based on ONLINE_USERS')

    async def chat_message(self, event):
        try:
            await self.send(text_data=json.dumps(event))
        except Exception:
            logger.exception('send failed')

    async def chat_read(self, event):
        # Forward read notifications to clients (they can update UI accordingly)
        try:
            await self.send(text_data=json.dumps(dict(event, type='chat.read')))
        except Exception:
            logger.exception('send read notification failed')

    async def chat_delivery(self, event):
        # Forward delivery notifications to clients so senders can update ticks
        try:
            await self.send(text_data=json.dumps(dict(event, type='chat.delivery')))
        except Exception:
            logger.exception('send delivery notification failed')


class PresenceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        logger.info('Presence connect attempt user=%r channel=%s', user, self.channel_name)
        if not getattr(user, 'is_authenticated', False):
            await self.close()
            return

        await self.channel_layer.group_add(f'user_{getattr(user, "id")}', self.channel_name)
        await self.accept()

        # mark user as online (shared store if configured)
        try:
            await mark_online(int(getattr(user, 'id')))
            logger.debug('Presence: user %s marked online (shared/local)', getattr(user, 'id'))
        except Exception:
            logger.exception('failed to mark user online')

        try:
            rooms = await _get_rooms_for_user(getattr(user, 'id'))
            if rooms:
                # Annotate participants with current online state (check presence)
                try:
                    for r in rooms:
                        parts = r.get('participants') or []
                        annotated = []
                        for p in parts:
                            pid = int(p.get('id')) if p.get('id') is not None else None
                            if pid is None:
                                annotated.append(p)
                                continue
                            try:
                                online_flag = await is_online(pid)
                            except Exception:
                                online_flag = False
                            p['online'] = bool(online_flag)
                            annotated.append(p)
                        r['participants'] = annotated
                except Exception:
                    logger.exception('failed annotating participants online state')
                await self.send(text_data=json.dumps({'type': 'init_rooms', 'rooms': rooms}))
        except Exception:
            logger.exception('failed to send init_rooms on presence connect')

        # After sending the room list, deliver any undelivered messages stored
        # while the user was offline. We fetch undelivered messages, send them
        # as `chat.message` events and then mark them delivered in the DB so
        # they aren't re-sent on subsequent reconnects.
        try:
            undelivered = await _get_undelivered_messages_for_user(getattr(user, 'id'))
            if undelivered:
                logger.info('Delivering %d undelivered messages to user=%s', len(undelivered), getattr(user, 'id'))
                delivered_receipts = []
                for item in undelivered:
                    try:
                        # item contains receipt_id and message_id
                        event = {
                            'type': 'chat.message',
                            'message': item.get('message'),
                            'content': item.get('content'),
                            'message_id': item.get('message_id'),
                            'id': item.get('message_id'),
                            'room_id': item.get('room_id'),
                            'sender_id': item.get('sender_id'),
                            'username': item.get('username'),
                            'timestamp': item.get('timestamp'),
                        }
                        await self.send(text_data=json.dumps(event))
                        delivered_receipts.append({ 'receipt_id': item.get('receipt_id'), 'message_id': item.get('message_id'), 'sender_id': item.get('sender_id') })
                    except Exception:
                        logger.exception('failed to send undelivered message to user')
                # mark receipts delivered
                try:
                    # call _mark_receipt_delivered for each receipt id
                    results = []
                    for info in delivered_receipts:
                        try:
                            rid = int(info.get('receipt_id'))
                            res = await _mark_receipt_delivered(rid)
                            results.append(res)
                            if isinstance(res, dict) and res.get('ok'):
                                # notify the original sender that this recipient has
                                # now received the message (so UI can show delivered ticks)
                                try:
                                    sender = info.get('sender_id')
                                    await self.channel_layer.group_send(f'user_{sender}', {
                                        'type': 'chat.delivery',
                                        'message_id': info.get('message_id'),
                                        'receipt_id': rid,
                                        'user_id': getattr(user, 'id'),
                                        'delivered_at': res.get('delivered_at'),
                                        'message_delivered': res.get('message_delivered'),
                                        'message_delivered_at': res.get('message_delivered_at'),
                                    })
                                except Exception:
                                    logger.exception('failed to notify sender about delivery')
                        except Exception:
                            logger.exception('failed marking receipt delivered')
                    logger.info('Marked %d receipts delivered for user=%s', sum(1 for r in results if r), getattr(user, 'id'))
                except Exception:
                    logger.exception('failed to mark undelivered receipts as delivered')
        except Exception:
            logger.exception('fetching undelivered messages failed')

        # Notify other participants that this user is now online (send to their user_<id> groups)
        try:
            # rooms contains rooms for this user
            for r in (rooms or []):
                parts = r.get('participants') or []
                for p in parts:
                    try:
                        pid = int(p.get('id')) if p.get('id') is not None else None
                        if pid is None or pid == int(getattr(user, 'id')):
                            continue
                        await self.channel_layer.group_send(f'user_{pid}', {
                            'type': 'presence.online',
                            'user_id': int(getattr(user, 'id')),
                            'room_id': r.get('id')
                        })
                    except Exception:
                        logger.exception('failed sending presence.online to participant')
        except Exception:
            logger.exception('failed to broadcast presence.online')

    async def disconnect(self, close_code):
        try:
            user = self.scope.get('user')
            if getattr(user, 'is_authenticated', False):
                await self.channel_layer.group_discard(f'user_{getattr(user, "id")}', self.channel_name)
        except Exception:
            logger.exception('presence group_discard failed')
        try:
            await mark_offline(int(getattr(self.scope.get('user'), 'id', -1)))
            logger.debug('Presence: user %s removed from shared/local registry', getattr(self.scope.get('user'), 'id', None))
        except Exception:
            logger.exception('failed to remove user from presence store')

    async def chat_message(self, event):
        try:
            await self.send(text_data=json.dumps(event))
        except Exception:
            logger.exception('presence send failed')
