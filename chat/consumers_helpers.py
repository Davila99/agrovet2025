import logging
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

from .models import ChatRoom, ChatMessage

User = get_user_model()
logger = logging.getLogger(__name__)


def _participants_list_from_room(room):
    try:
        vals = list(room.participants.values('id', 'full_name', 'phone_number', 'profile_picture'))
        out = []
        for u in vals:
            out.append({
                'id': u.get('id'),
                'full_name': u.get('full_name'),
                'username': (u.get('full_name') or u.get('phone_number') or ''),
                'profile_picture': u.get('profile_picture'),
            })
        return out
    except Exception:
        return []


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
        participants = _participants_list_from_room(room)
        return {'id': str(room.id), 'name': room.name or '', 'participants': participants, 'messages': msgs}
    except Exception:
        return None


@database_sync_to_async
def _get_room_participants(room_id):
    try:
        room = ChatRoom.objects.filter(id=room_id).first()
        if not room:
            return []
        return _participants_list_from_room(room)
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
            participants = _participants_list_from_room(r)
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
