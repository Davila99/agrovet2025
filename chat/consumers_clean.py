"""Clean consumers used as a temporary safe import.

This module provides a compact ChatConsumer and PresenceConsumer with
module-level DB helpers. It's intended as a drop-in replacement so the
server can import a correct module while we restore `consumers.py`.
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

from .models import ChatRoom, ChatMessage

User = get_user_model()
logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'

        user = self.scope.get('user')
        logger.info(f"WS connect room={self.room_id} user={repr(user)} channel={self.channel_name}")

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        if getattr(user, 'is_authenticated', False):
            user_group = f'user_{getattr(user, "id", "anonymous")} '
            await self.channel_layer.group_add(user_group.strip(), self.channel_name)

        await self.accept()
        # Send recent room messages as init payload so client can populate history
        try:
            recent = await _get_room_messages(self.room_id)
            if recent is not None:
                # send a single-room init payload
                await self.send(text_data=json.dumps({ 'type': 'init_room', 'room': recent }))
        except Exception:
            logger.exception('failed to send init_room payload')

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        except Exception:
            logger.exception('group_discard failed')

    async def receive(self, text_data=None, bytes_data=None):
        try:
            payload = json.loads(text_data) if text_data else {}
        except Exception:
            payload = {}

        user = self.scope.get('user')
        if not getattr(user, 'is_authenticated', False):
            logger.warning('anonymous send ignored')
            return

        try:
            saved = await save_message(getattr(user, 'id'), self.room_id, payload)
        except Exception:
            logger.exception('save_message failed')
            saved = None

        # Build outgoing event with explicit metadata expected by frontend
        out = {
            'type': 'chat_message',
            'message': payload.get('content') if isinstance(payload, dict) else str(payload),
            'content': payload.get('content') if isinstance(payload, dict) else str(payload),
            'username': getattr(user, 'full_name', str(user)),
            'sender_id': getattr(user, 'id', None),
        }
        if 'client_msg_id' in payload:
            out['client_msg_id'] = payload.get('client_msg_id')
        if saved:
            out['message_id'] = saved.id
            out['id'] = saved.id
            out['room_id'] = str(self.room_id)
            # attach participants so clients can compute display names
            try:
                out['participants'] = await _get_room_participants(self.room_id)
            except Exception:
                out['participants'] = []
            # ensure room name is included
            try:
                room_obj = ChatRoom.objects.filter(id=self.room_id).values('id', 'name').first()
                out['room'] = {'id': str(self.room_id), 'name': room_obj.get('name') if room_obj else ''}
            except Exception:
                out['room'] = {'id': str(self.room_id), 'name': ''}
            # include a compact sender object and room metadata so clients can render titles
            try:
                out['sender'] = {'id': saved.sender.id, 'full_name': getattr(saved.sender, 'full_name', str(saved.sender)), 'username': getattr(saved.sender, 'username', None)}
            except Exception:
                out['sender'] = {'id': getattr(saved, 'sender_id', None)}
            try:
                room = ChatRoom.objects.filter(id=self.room_id).values('id', 'name').first()
                out['room'] = {'id': str(self.room_id), 'name': room.get('name') if room else ''}
            except Exception:
                out['room'] = {'id': str(self.room_id), 'name': ''}

        try:
            # broadcast to room group (active connections in room)
            await self.channel_layer.group_send(self.room_group_name, out)
        except Exception:
            logger.exception('group_send failed')

        try:
            # also notify per-user groups (so offline presence socket can receive after reconnect)
            participant_ids = await _get_room_participant_ids(self.room_id)
            sender_id = getattr(saved, 'sender_id', None) if saved else None
            for pid in participant_ids:
                try:
                    # send same event to each user group; clients listening on presence socket
                    user_group = f'user_{pid}'
                    # also add a simple flag indicating whether the recipient is the sender
                    per_user_out = dict(out)
                    per_user_out['from_me'] = (int(pid) == int(getattr(user, 'id', -1)))
                    # include participants and room for presence consumers as well
                    try:
                        per_user_out['participants'] = per_user_out.get('participants') or await _get_room_participants(self.room_id)
                    except Exception:
                        per_user_out['participants'] = per_user_out.get('participants') or []
                    try:
                        per_user_out['room'] = per_user_out.get('room') or {'id': str(self.room_id), 'name': ChatRoom.objects.filter(id=self.room_id).values_list('name', flat=True).first() or ''}
                    except Exception:
                        per_user_out['room'] = per_user_out.get('room') or {'id': str(self.room_id), 'name': ''}
                    await self.channel_layer.group_send(user_group, per_user_out)
                except Exception:
                    # continue notifying others even if one fails
                    logger.exception('notify user_group failed')
                    continue
        except Exception:
            logger.exception('per-user notify failed')

    async def chat_message(self, event):
        try:
            await self.send(text_data=json.dumps(event))
        except Exception:
            logger.exception('send failed')


class PresenceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not getattr(user, 'is_authenticated', False):
            await self.close()
            return
        user_group = f'user_{getattr(user, "id", "anonymous")}'
        await self.channel_layer.group_add(user_group, self.channel_name)
        await self.accept()
        # On presence connect, send full rooms payload so client can sync missed messages
        try:
            rooms = await _get_rooms_for_user(getattr(user, 'id'))
            if rooms:
                await self.send(text_data=json.dumps({'type':'init_rooms', 'rooms': rooms}))
        except Exception:
            logger.exception('failed to send init_rooms on presence connect')

    async def disconnect(self, close_code):
        try:
            user = self.scope.get('user')
            if getattr(user, 'is_authenticated', False):
                user_group = f'user_{getattr(user, "id", "anonymous")} '
                await self.channel_layer.group_discard(user_group.strip(), self.channel_name)
        except Exception:
            logger.exception('presence group_discard failed')

    async def chat_message(self, event):
        try:
            # normalize event for presence consumers: ensure sender/room fields exist
            evt = dict(event)
            # older code may use message_id/room_id fields; keep them
            await self.send(text_data=json.dumps(evt))
        except Exception:
            logger.exception('presence send failed')


@database_sync_to_async
def _get_room_participant_ids(room_id):
    try:
        r = ChatRoom.objects.filter(id=room_id).first()
        if not r:
            return []
        return list(r.participants.values_list('id', flat=True))
    except Exception:
        return []


@database_sync_to_async
def _get_room_messages(room_id, limit=100):
    try:
        room = ChatRoom.objects.filter(id=room_id).first()
        if not room:
            return None
        qs = room.messages.order_by('timestamp')[:limit]
        msgs = []
        for m in qs:
            msgs.append({
                'id': m.id,
                'sender_id': getattr(m.sender, 'id', None),
                'content': m.content,
                'timestamp': m.timestamp.isoformat() if getattr(m, 'timestamp', None) else None,
                'media_id': getattr(m.media, 'id', None) if getattr(m, 'media', None) else None,
            })
        participants = list(room.participants.values('id', 'full_name', 'username', 'profile_picture'))
        return { 'id': str(room.id), 'name': room.name or '', 'participants': participants, 'messages': msgs }
    except Exception:
        return None


@database_sync_to_async
def _get_room_participants(room_id):
    try:
        room = ChatRoom.objects.filter(id=room_id).first()
        if not room:
            return []
        return list(room.participants.values('id', 'full_name', 'username', 'profile_picture'))
    except Exception:
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
            msgs = list(r.messages.order_by('timestamp').values('id', 'sender_id', 'content', 'timestamp')[:50])
            participants = list(r.participants.values('id', 'full_name', 'username', 'profile_picture'))
            payload.append({'id': str(r.id), 'name': r.name or '', 'participants': participants, 'messages': msgs})
        return payload
    except Exception:
        return []


@database_sync_to_async
def save_message(user_id, room_id, message):
    try:
        room = ChatRoom.objects.get(id=room_id)
    except ChatRoom.DoesNotExist:
        return None
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
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
        logger.info(f"Saved ChatMessage id={m.id} room={room.id} sender={user.id}")
    except Exception:
        pass
    from django.utils import timezone
    room.last_activity = timezone.now()
    room.save(update_fields=['last_activity'])
    return m
