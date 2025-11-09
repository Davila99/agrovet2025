"""PresenceConsumer implementation (kept concise).

Handles online presence, initial room list and undelivered messages.
"""
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

from .helpers import _get_rooms_for_user, _get_undelivered_messages_for_user, _get_room_participant_ids
from .helpers import _mark_receipt_delivered
from .helpers_presence import is_online, mark_online, mark_offline

logger = logging.getLogger(__name__)


class PresenceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        logger.info('Presence connect attempt user=%r channel=%s', user, self.channel_name)
        if not getattr(user, 'is_authenticated', False):
            await self.close()
            return

        await self.channel_layer.group_add(f'user_{getattr(user, "id")}', self.channel_name)
        await self.accept()

        try:
            await mark_online(int(getattr(user, 'id')))
        except Exception:
            logger.exception('failed to mark user online')

        try:
            rooms = await _get_rooms_for_user(getattr(user, 'id'))
            if rooms:
                # annotate participants with online flag
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
                await self.send(text_data=json.dumps({'type': 'init_rooms', 'rooms': rooms}))
        except Exception:
            logger.exception('failed to send init_rooms on presence connect')

        try:
            undelivered = await _get_undelivered_messages_for_user(getattr(user, 'id'))
            if undelivered:
                delivered_receipts = []
                for item in undelivered:
                    try:
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
                # mark receipts delivered and notify senders
                results = []
                for info in delivered_receipts:
                    try:
                        rid = int(info.get('receipt_id'))
                        res = await _mark_receipt_delivered(rid)
                        results.append(res)
                        if isinstance(res, dict) and res.get('ok'):
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
        except Exception:
            logger.exception('fetching undelivered messages failed')

        try:
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
        except Exception:
            logger.exception('failed to remove user from presence store')

    async def chat_message(self, event):
        try:
            await self.send(text_data=json.dumps(event))
        except Exception:
            logger.exception('presence send failed')
