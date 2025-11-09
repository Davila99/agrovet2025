"""Presence helpers used by PresenceConsumer and delivery heuristics.

Small, self-contained async helpers that prefer Django cache and
fall back to an in-memory set. Keep behaviour minimal and safe.
"""
import logging
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

logger = logging.getLogger(__name__)


async def is_online(user_id):
    try:
        if user_id is None:
            return False
        if cache is not None:
            key = f"chat:online:{user_id}"
            return bool(cache.get(key))
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
