"""Clean consumers used as a temporary safe import.

This module provides a compact ChatConsumer and PresenceConsumer with
module-level DB helpers. It's intended as a drop-in replacement so the
server can import a correct module while we restore `consumers.py`.
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model

from .consumers_helpers import (
    _get_room_messages,
    _get_room_participants,
    _get_room_participant_ids,
    _get_rooms_for_user,
    save_message,
)

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
                await self.send(text_data=json.dumps({'type': 'init_room', 'room': recent}))
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
                # keep minimal room info; helper functions provide messages/participants
                out['room'] = {'id': str(self.room_id), 'name': ''}
            except Exception:
                out['room'] = {'id': str(self.room_id), 'name': ''}
            # include a compact sender object and room metadata so clients can render titles
            try:
                out['sender'] = {
                    'id': saved.sender.id,
                    'full_name': getattr(saved.sender, 'full_name', str(saved.sender)),
                    'username': getattr(saved.sender, 'username', None),
                }
            except Exception:
                out['sender'] = {'id': getattr(saved, 'sender_id', None)}

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
                    user_group = f'user_{pid}'
                    per_user_out = dict(out)
                    per_user_out['from_me'] = (int(pid) == int(getattr(user, 'id', -1)))
                    try:
                        per_user_out['participants'] = per_user_out.get('participants') or await _get_room_participants(self.room_id)
                    except Exception:
                        per_user_out['participants'] = per_user_out.get('participants') or []
                    try:
                        per_user_out['room'] = per_user_out.get('room') or {'id': str(self.room_id), 'name': ''}
                    except Exception:
                        per_user_out['room'] = per_user_out.get('room') or {'id': str(self.room_id), 'name': ''}
                    await self.channel_layer.group_send(user_group, per_user_out)
                except Exception:
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
                await self.send(text_data=json.dumps({'type': 'init_rooms', 'rooms': rooms}))
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


# helpers moved to chat.consumers_helpers for modularity and testability
