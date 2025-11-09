"""WebSocket-related helpers for consumers.

Contains logic moved out of the consumers to keep the classes small.
"""
import json
import logging
import asyncio
from channels.db import database_sync_to_async

from .helpers import (
    save_message,
    _get_room_participants,
    _get_room_participant_ids,
    _get_message_receipts,
    _mark_receipt_delivered,
    _get_room_participant_ids as _get_participant_ids,
    is_online,
)

logger = logging.getLogger(__name__)


async def handle_received_message(consumer, payload):
    """Process an incoming message payload on behalf of a consumer.

    This function encapsulates the previous inlined logic: save the
    message, build the outgoing payload, broadcast to the room and to
    per-user groups, and attempt lightweight delivered marking.
    """
    user = consumer.scope.get('user')
    try:
        saved = await save_message(getattr(user, 'id'), consumer.room_id, payload)
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
        out['room_id'] = str(consumer.room_id)
        try:
            out['participants'] = await _get_room_participants(consumer.room_id)
        except Exception:
            out['participants'] = []
        try:
            out['receipts'] = await _get_message_receipts(saved.id)
            out['delivered'] = bool(getattr(saved, 'delivered', False))
            out['delivered_at'] = getattr(saved, 'delivered_at', None).isoformat() if getattr(saved, 'delivered_at', None) else None
            out['read'] = bool(getattr(saved, 'read', False))
            out['read_at'] = getattr(saved, 'read_at', None).isoformat() if getattr(saved, 'read_at', None) else None
        except Exception:
            out['receipts'] = []
        # Include media metadata when present so websocket clients can render attachments
        try:
            media_obj = getattr(saved, 'media', None)
            if media_obj:
                out['media_id'] = getattr(getattr(saved, 'media', None), 'id', None)
                out['media_url'] = getattr(getattr(saved, 'media', None), 'url', None)
                # If the Media record contains a description that encodes spectrum
                # data (JSON), try to include it for richer client rendering.
                try:
                    desc = getattr(media_obj, 'description', None)
                    if desc:
                        import json as _json
                        try:
                            parsed = _json.loads(desc) if isinstance(desc, (str, bytes)) else desc
                            if isinstance(parsed, list):
                                out['media_spectrum'] = parsed
                            elif isinstance(parsed, dict):
                                for k in ('spectrum', 'media_spectrum', 'audio_spectrum', 'bins'):
                                    if k in parsed and isinstance(parsed[k], list):
                                        out['media_spectrum'] = parsed[k]
                                        break
                                else:
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
                        logger.debug('WS saved media description preview media_id=%s repr=%s', getattr(media_obj, 'id', None), (repr(desc)[:200] + ('...' if desc and len(str(desc)) > 200 else '')) )
                    except Exception:
                        pass
                except Exception:
                    out['media_spectrum'] = None
        except Exception:
            pass

    try:
        await consumer.channel_layer.group_send(consumer.room_group_name, out)
    except Exception:
        logger.exception('group_send failed')
    else:
        try:
            # Log broadcast payload for messages with media to help debug missing spectrum
            if out.get('media_id') is not None:
                logger.info('Broadcasting chat.message with media: %s', {k: out.get(k) for k in ('message_id', 'media_id', 'media_url', 'media_spectrum')})
        except Exception:
            logger.exception('failed logging broadcast payload')
    # Defensive: if we didn't find media_spectrum yet, try re-reading the Media record
    try:
        if out.get('media_id') is not None and not out.get('media_spectrum'):
            media_id = out.get('media_id')
            async def _fetch_desc(mid):
                try:
                    from media.models import Media as _Media
                    m = _Media.objects.filter(id=mid).first()
                    return getattr(m, 'description', None) if m else None
                except Exception:
                    return None

            desc = await database_sync_to_async(_fetch_desc)(media_id)
            if desc:
                try:
                    import json as _json
                    parsed = _json.loads(desc) if isinstance(desc, (str, bytes)) else desc
                    if isinstance(parsed, list):
                        out['media_spectrum'] = parsed
                    elif isinstance(parsed, dict):
                        for k in ('spectrum', 'media_spectrum', 'audio_spectrum', 'bins'):
                            if k in parsed and isinstance(parsed[k], list):
                                out['media_spectrum'] = parsed[k]
                                break
                        else:
                            for v in parsed.values():
                                if isinstance(v, list):
                                    out['media_spectrum'] = v
                                    break
                    if out.get('media_spectrum'):
                        try:
                            logger.info('Recovered media_spectrum from DB for media_id=%s len=%s', media_id, len(out.get('media_spectrum') or []))
                        except Exception:
                            pass
                except Exception:
                    logger.exception('failed parsing media.description during broadcast recovery')
            # re-send updated out to group so late-spectrum is delivered
            try:
                if out.get('media_spectrum'):
                    await consumer.channel_layer.group_send(consumer.room_group_name, out)
            except Exception:
                logger.exception('group_send failed on recovered payload')
    except Exception:
        logger.exception('failed defensive media_spectrum recovery')

    try:
        participant_ids = await _get_participant_ids(consumer.room_id)
        for pid in participant_ids:
            try:
                await consumer.channel_layer.group_send(f'user_{pid}', dict(out, from_me=(int(pid) == int(getattr(user, 'id', -1)))) )
            except Exception:
                logger.exception('notify user_group failed')
                continue
    except Exception:
        logger.exception('per-user notify failed')

    try:
        if saved:
            sender_id = int(getattr(user, 'id', -1))
            recipients = [int(x) for x in (await _get_participant_ids(consumer.room_id)) if int(x) != sender_id]
            if recipients:
                try:
                    statuses = await asyncio.gather(*(is_online(r) for r in recipients))
                    all_online = all(statuses)
                    if all_online:
                        try:
                            logger.info('Marked receipts delivered immediately (no-op)')
                        except Exception:
                            logger.exception('failed marking receipts delivered')
                except Exception:
                    logger.exception('failed to mark message delivered based on presence store')
    except Exception:
        logger.exception('failed to mark message delivered based on ONLINE_USERS')
    # After broadcasting the message we can proactively mark per-user receipts
    # delivered for recipients who are currently online and broadcast a delivered event.
    try:
        if saved:
            try:
                # fetch current receipts with ids
                receipts = await _get_message_receipts(saved.id)
            except Exception:
                receipts = []

            # determine online recipients and mark their receipts delivered
            try:
                participant_ids = await _get_participant_ids(consumer.room_id)
            except Exception:
                participant_ids = []

            for ridx, rpe in enumerate(receipts):
                try:
                    uid = rpe.get('user_id')
                    receipt_id = rpe.get('receipt_id')
                    if uid is None or receipt_id is None:
                        continue
                    online = False
                    try:
                        online = await is_online(int(uid))
                    except Exception:
                        online = False
                    if online and not rpe.get('delivered'):
                        try:
                            # mark this specific receipt delivered
                            res = await _mark_receipt_delivered(receipt_id)
                            logger.info('Marked receipt delivered via WS helper: %s', res)
                        except Exception:
                            logger.exception('failed marking individual receipt delivered')
                except Exception:
                    logger.exception('iterating receipts failed')

            # after updating DB, fetch receipts again and broadcast a chat.message.delivered event
            try:
                updated_receipts = await _get_message_receipts(saved.id)
                delivery_out = {
                    'type': 'chat.message.delivered',
                    'message_id': saved.id,
                    'receipts': updated_receipts,
                    'room_id': str(consumer.room_id),
                }
                try:
                    await consumer.channel_layer.group_send(consumer.room_group_name, delivery_out)
                except Exception:
                    logger.exception('failed broadcasting chat.message.delivered to room')
                # also notify individual sender and participants user groups
                try:
                        for pid in participant_ids:
                            try:
                                await consumer.channel_layer.group_send(f'user_{pid}', dict(delivery_out, from_me=(int(pid) == int(getattr(user, 'id', -1)))) )
                            except Exception:
                                logger.exception('failed to notify user about delivery')
                        # Broadcast a simplified delivery event name for clients that expect it
                        try:
                            await consumer.channel_layer.group_send(consumer.room_group_name, {
                                'type': 'message_delivered',
                                'message_id': saved.id,
                                'receipts': updated_receipts,
                                'room_id': str(consumer.room_id),
                            })
                        except Exception:
                            logger.exception('failed broadcasting message_delivered')
                        # yield to event loop briefly when doing multiple sends
                        try:
                            await asyncio.sleep(0)
                        except Exception:
                            pass
                except Exception:
                    logger.exception('failed per-user notify for delivery event')
            except Exception:
                logger.exception('failed fetching updated receipts for delivery broadcast')
    except Exception:
        logger.exception('post-send delivery marking failed')
