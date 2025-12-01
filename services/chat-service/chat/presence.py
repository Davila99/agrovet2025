"""
Redis-backed presence helpers with safe in-process fallback.
"""
from typing import Optional
import logging
import os

logger = logging.getLogger(__name__)

# In-process fallback registry
_LOCAL_ONLINE = set()

# Try to import async and sync redis clients
_redis_async = None
_redis_sync = None

try:
    import redis.asyncio as _redis_async
except Exception:
    _redis_async = None

try:
    import redis as _redis_sync
except Exception:
    _redis_sync = None


def _derive_redis_url() -> Optional[str]:
    """Derive Redis URL from environment or settings."""
    return os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')


def _get_sync_client():
    """Return a sync redis client or None."""
    if _redis_sync is None:
        return None
    try:
        url = _derive_redis_url()
        return _redis_sync.from_url(url, decode_responses=True)
    except Exception:
        logger.exception('failed creating sync redis client')
        return None


def _get_async_client():
    """Return an async redis client or None."""
    if _redis_async is None:
        return None
    try:
        url = _derive_redis_url()
        return _redis_async.from_url(url, decode_responses=True)
    except Exception:
        logger.exception('failed creating async redis client')
        return None


# Async helpers
async def mark_online(user_id: int) -> bool:
    try:
        rc = _get_async_client()
        if rc:
            await rc.sadd('chat:online_users', int(user_id))
            return True
        _LOCAL_ONLINE.add(int(user_id))
        return True
    except Exception:
        logger.exception('mark_online failed')
        try:
            _LOCAL_ONLINE.add(int(user_id))
            return True
        except Exception:
            return False


async def mark_offline(user_id: int) -> bool:
    try:
        rc = _get_async_client()
        if rc:
            await rc.srem('chat:online_users', int(user_id))
            return True
        _LOCAL_ONLINE.discard(int(user_id))
        return True
    except Exception:
        logger.exception('mark_offline failed')
        try:
            _LOCAL_ONLINE.discard(int(user_id))
            return True
        except Exception:
            return False


async def is_online(user_id: int) -> bool:
    try:
        rc = _get_async_client()
        if rc:
            return await rc.sismember('chat:online_users', int(user_id))
        return int(user_id) in _LOCAL_ONLINE
    except Exception:
        logger.exception('is_online failed')
        return int(user_id) in _LOCAL_ONLINE


# Sync helpers
def sync_mark_online(user_id: int) -> bool:
    try:
        client = _get_sync_client()
        if client:
            client.sadd('chat:online_users', int(user_id))
            return True
        _LOCAL_ONLINE.add(int(user_id))
        return True
    except Exception:
        logger.exception('sync_mark_online failed')
        try:
            _LOCAL_ONLINE.add(int(user_id))
            return True
        except Exception:
            return False


def sync_mark_offline(user_id: int) -> bool:
    try:
        client = _get_sync_client()
        if client:
            client.srem('chat:online_users', int(user_id))
            return True
        _LOCAL_ONLINE.discard(int(user_id))
        return True
    except Exception:
        logger.exception('sync_mark_offline failed')
        try:
            _LOCAL_ONLINE.discard(int(user_id))
            return True
        except Exception:
            return False


def sync_is_online(user_id: int) -> bool:
    try:
        client = _get_sync_client()
        if client:
            return client.sismember('chat:online_users', int(user_id))
        return int(user_id) in _LOCAL_ONLINE
    except Exception:
        logger.exception('sync_is_online failed')
        return int(user_id) in _LOCAL_ONLINE


async def get_all_online_users() -> list:
    """Get all currently online user IDs."""
    try:
        rc = _get_async_client()
        if rc:
            members = await rc.smembers('chat:online_users')
            return [int(m) for m in members if m]
        return list(_LOCAL_ONLINE)
    except Exception:
        logger.exception('get_all_online_users failed')
        return list(_LOCAL_ONLINE)
