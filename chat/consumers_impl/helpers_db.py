"""Database helpers for chat consumers.

These functions perform synchronous DB operations wrapped with
``database_sync_to_async`` so they can be awaited from async consumers.
"""
import logging
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from chat.models import ChatRoom, ChatMessage

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
        logger.exception('_participants_list_from_room failed')
        return []


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
    try:
        room = ChatRoom.objects.filter(id=room_id).first()
        if not room:
            return None

        msgs = []
        # unread-only branch
        if only_unread_for_user is not None:
            try:
                from chat.models import ChatMessageReceipt
                qs_receipts = ChatMessageReceipt.objects.filter(user_id=only_unread_for_user, message__room=room, read=False).select_related('message').order_by('message__timestamp')
                message_ids = list(qs_receipts.values_list('message_id', flat=True))
                qs_no_receipt = ChatMessage.objects.filter(room=room).exclude(sender_id=only_unread_for_user).exclude(receipts__user_id=only_unread_for_user).order_by('timestamp')
                no_receipt_ids = list(qs_no_receipt.values_list('id', flat=True))
                combined_ids = []
                seen = set()
                for mid in (list(qs_receipts.values_list('message__id', flat=True)) + no_receipt_ids):
                    if mid not in seen:
                        seen.add(mid)
                        combined_ids.append(mid)
                if combined_ids:
                    msgs_qs = ChatMessage.objects.filter(id__in=combined_ids).order_by('timestamp')
                    for m in msgs_qs:
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
                    participants = _participants_list_from_room(room)
                    return {
                        'id': str(room.id),
                        'name': room.name or '',
                        'participants': participants,
                        'messages': msgs,
                        'unread_only': True,
                    }
            except Exception:
                logger.exception('failed fetching unread receipts')

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
                        'read_at': getattr(r, 'read_at', None).isoformat() if getattr(r, 'read_at', None) else None,
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
            # include media metadata when present for client rendering
            try:
                media_obj = getattr(m, 'media', None)
                if media_obj:
                    media_desc = getattr(media_obj, 'description', None)
                    if media_desc:
                        import json as _json
                        try:
                            parsed = _json.loads(media_desc) if isinstance(media_desc, (str, bytes)) else media_desc
                            if isinstance(parsed, list):
                                msgs[-1]['media_spectrum'] = parsed
                            elif isinstance(parsed, dict):
                                for k in ('spectrum', 'media_spectrum', 'audio_spectrum', 'bins'):
                                    if k in parsed and isinstance(parsed[k], list):
                                        msgs[-1]['media_spectrum'] = parsed[k]
                                        break
                                else:
                                    for v in parsed.values():
                                        if isinstance(v, list):
                                            msgs[-1]['media_spectrum'] = v
                                            break
                        except Exception:
                            pass
            except Exception:
                pass

        participants = _participants_list_from_room(room)
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
        return _participants_list_from_room(room)
    except Exception:
        logger.exception('_get_room_participants_failed')
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
                # include media metadata for list responses
                try:
                    media_obj = getattr(m, 'media', None)
                    if media_obj:
                        media_desc = getattr(media_obj, 'description', None)
                        if media_desc:
                            import json as _json
                            try:
                                parsed = _json.loads(media_desc) if isinstance(media_desc, (str, bytes)) else media_desc
                                if isinstance(parsed, list):
                                    msgs[-1]['media_spectrum'] = parsed
                                elif isinstance(parsed, dict):
                                    for k in ('spectrum', 'media_spectrum', 'audio_spectrum', 'bins'):
                                        if k in parsed and isinstance(parsed[k], list):
                                            msgs[-1]['media_spectrum'] = parsed[k]
                                            break
                                    else:
                                        for v in parsed.values():
                                            if isinstance(v, list):
                                                msgs[-1]['media_spectrum'] = v
                                                break
                            except Exception:
                                pass
                except Exception:
                    pass
            participants = _participants_list_from_room(r)
            payload.append({'id': str(r.id), 'name': r.name or '', 'participants': participants, 'messages': msgs})
        return payload
    except Exception:
        logger.exception('_get_rooms_for_user failed')
        return []


@database_sync_to_async
def _get_undelivered_messages_for_user(user_id):
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return []
        from chat.models import ChatMessageReceipt
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
        from chat.models import ChatMessageReceipt
        rs = ChatMessageReceipt.objects.filter(message_id=message_id).select_related('user')
        out = []
        for r in rs:
            out.append({
                'receipt_id': r.id,
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
        from chat.models import ChatMessageReceipt, ChatMessage
        r = ChatMessageReceipt.objects.filter(id=receipt_id).first()
        if not r:
            return {'ok': False}
        if not r.delivered:
            now = timezone.now()
            r.delivered = True
            r.delivered_at = now
            r.save(update_fields=['delivered', 'delivered_at'])
            try:
                logger.info('Marked receipt delivered id=%s message_id=%s user_id=%s', r.id, r.message_id, getattr(r.user, 'id', None))
            except Exception:
                pass
        try:
            # If no remaining undelivered receipts exist for this message, mark the ChatMessage delivered
            msg = ChatMessage.objects.filter(id=r.message_id).first()
            if msg is not None:
                remaining = ChatMessageReceipt.objects.filter(message_id=msg.id, delivered=False).exists()
                if not remaining and not msg.delivered:
                    msg.delivered = True
                    msg.delivered_at = r.delivered_at or timezone.now()
                    msg.save(update_fields=['delivered', 'delivered_at'])
            return {
                'ok': True,
                'receipt_id': r.id,
                'message_id': r.message_id,
                'delivered_at': r.delivered_at.isoformat() if getattr(r, 'delivered_at', None) else None,
                'message_delivered': bool(getattr(msg, 'delivered', False)) if msg is not None else False,
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
        from chat.models import ChatMessageReceipt
        rs = ChatMessageReceipt.objects.filter(message__room_id=room_id, user_id=user_id, read=False)
        updated = rs.update(read=True, read_at=timezone.now())
        return updated
    except Exception:
        logger.exception('_mark_receipts_read_for_user failed')
        return 0


@database_sync_to_async
def _mark_receipts_read_and_get_message_ids(room_id, user_id):
    try:
        from django.utils import timezone
        from chat.models import ChatMessageReceipt, ChatMessage
        now = timezone.now()
        qs = ChatMessageReceipt.objects.filter(message__room_id=room_id, user_id=user_id, read=False)
        message_ids = list(qs.values_list('message_id', flat=True))
        if message_ids:
            qs.update(read=True, read_at=now)
            try:
                logger.info('Marked %s receipts read in room=%s for user=%s', len(message_ids), room_id, user_id)
            except Exception:
                pass
            try:
                uniq_ids = set(message_ids)
                for mid in uniq_ids:
                    still_unread = ChatMessageReceipt.objects.filter(message_id=mid, read=False).exists()
                    if not still_unread:
                        # mark the aggregate ChatMessage as read and seen
                        ChatMessage.objects.filter(id=mid).update(read=True, seen=True, read_at=now)
            except Exception:
                logger.exception('failed updating ChatMessage read flags')
        return message_ids
    except Exception:
        logger.exception('_mark_receipts_read_and_get_message_ids failed')
        return []


@database_sync_to_async
def _get_messages_read_info(message_ids):
    try:
        from chat.models import ChatMessage
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
                try:
                    # log description preview
                    d = getattr(media_obj, 'description', None)
                    logger.debug('save_message fetched media id=%s desc_preview=%s len=%s', media_id, (repr(d)[:200] + ('...' if d and len(str(d)) > 200 else '')), len(str(d) if d is not None else ''))
                except Exception:
                    pass
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
        from chat.models import ChatMessageReceipt
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
