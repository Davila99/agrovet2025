"""Public helpers API for chat consumers.

This module re-exports specific helper functions from smaller
implementation modules so other code can `from .helpers import ...`
without knowing about the split.
"""

from .helpers_db import (
    _participants_list_from_room,
    _get_room_participant_ids,
    _get_room_messages,
    _get_room_participants,
    _get_rooms_for_user,
    _get_undelivered_messages_for_user,
    _mark_messages_delivered,
    _get_message_receipts,
    _mark_receipt_delivered,
    _mark_receipts_read_for_user,
    _mark_receipts_read_and_get_message_ids,
    _get_messages_read_info,
    save_message,
)

from .helpers_presence import (
    is_online,
    mark_online,
    mark_offline,
)

import logging
logger = logging.getLogger(__name__)

__all__ = [
    '_participants_list_from_room',
    '_get_room_participant_ids',
    '_get_room_messages',
    '_get_room_participants',
    '_get_rooms_for_user',
    '_get_undelivered_messages_for_user',
    '_mark_messages_delivered',
    '_get_message_receipts',
    '_mark_receipt_delivered',
    '_mark_receipts_read_for_user',
    '_mark_receipts_read_and_get_message_ids',
    '_get_messages_read_info',
    'save_message',
    'is_online',
    'mark_online',
    'mark_offline',
]

# Presence helpers: attempt to use Django cache if available, otherwise
# fall back to an in-process set. These provide minimal presence storage
# used by the PresenceConsumer and delivery heuristics. In production a
# shared store (Redis) is recommended, but this keeps behavior stable
# and avoids ImportError when the functions are imported.
try:
    from django.core.cache import cache
except Exception:
    cache = None

_INMEM_ONLINE = set()
_INMEM_LOCK = None
try:
    import asyncio
    _INMEM_LOCK = asyncio.Lock()
except Exception:
    _INMEM_LOCK = None


async def is_online(user_id):
    try:
        if user_id is None:
            return False
        if cache is not None:
            key = f"chat:online:{user_id}"
            return bool(cache.get(key))
        # fallback to in-memory
        if _INMEM_LOCK is not None:
            async with _INMEM_LOCK:
                return int(user_id) in _INMEM_ONLINE
        return int(user_id) in _INMEM_ONLINE
    except Exception:
        logger.exception('is_online failed')
        return False


async def mark_online(user_id):
    try:
        if user_id is None:
            return False
        if cache is not None:
            key = f"chat:online:{user_id}"
            # set a truthy value with a small TTL to avoid stale entries
            cache.set(key, True, timeout=3600)
            return True
        if _INMEM_LOCK is not None:
            async with _INMEM_LOCK:
                _INMEM_ONLINE.add(int(user_id))
                return True
        _INMEM_ONLINE.add(int(user_id))
        return True
    except Exception:
        logger.exception('mark_online failed')
        return False


async def mark_offline(user_id):
    try:
        if user_id is None:
            return False
        if cache is not None:
            key = f"chat:online:{user_id}"
            try:
                cache.delete(key)
            except Exception:
                cache.set(key, False, timeout=1)
            return True
        if _INMEM_LOCK is not None:
            async with _INMEM_LOCK:
                _INMEM_ONLINE.discard(int(user_id))
                return True
        _INMEM_ONLINE.discard(int(user_id))
        return True
    except Exception:
        logger.exception('mark_offline failed')
        return False
