"""Redis-backed presence helpers with safe in-process fallback.

Provides async and sync helpers to mark users online/offline and check
presence. If `redis` (redis-py) with asyncio support is available it will
use Redis set `agrovet:online_users`. Otherwise it falls back to an
in-memory set (suitable for development/single-process).

This module is defensive: it will not crash if Redis isn't reachable and
will silently fall back to local registry.
"""
from typing import Optional
import logging
logger = logging.getLogger(__name__)

# In-process fallback registry
_LOCAL_ONLINE = set()

# Try to import async and sync redis clients. If they are missing we'll
# operate on the local fallback set.
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

from django.conf import settings

def _derive_redis_url() -> Optional[str]:
    # Try to find a host/url from CHANNEL_LAYERS if available, else use env
    try:
        cl = getattr(settings, 'CHANNEL_LAYERS', None)
        if cl and isinstance(cl, dict):
            default = cl.get('default') or {}
            cfg = default.get('CONFIG') or {}
            hosts = cfg.get('hosts') or cfg.get('host')
            if hosts:
                # hosts may be list like [('127.0.0.1', 6379)] or ['redis://...']
                if isinstance(hosts, (list, tuple)) and len(hosts) > 0:
                    h = hosts[0]
                    if isinstance(h, (list, tuple)) and len(h) >= 2:
                        host, port = h[0], h[1]
                        return f'redis://{host}:{port}/0'
                    if isinstance(h, str) and h.startswith('redis'):
                        return h
                if isinstance(hosts, str):
                    return hosts
    except Exception:
        logger.debug('derive_redis_url failed', exc_info=True)
    # lastly try DJANGO_REDIS_URL or REDIS_URL in settings
    return getattr(settings, 'REDIS_URL', None) or getattr(settings, 'DJANGO_REDIS_URL', None)


def _get_sync_client():
    """Return a sync redis client or None."""
    if _redis_sync is None:
        return None
    try:
        url = _derive_redis_url() or 'redis://127.0.0.1:6379/0'
        return _redis_sync.from_url(url, decode_responses=True)
    except Exception:
        logger.exception('failed creating sync redis client')
        return None


def _get_async_client():
    """Return an async redis client or None."""
    if _redis_async is None:
        return None
    try:
        url = _derive_redis_url() or 'redis://127.0.0.1:6379/0'
        return _redis_async.from_url(url, decode_responses=True)
    except Exception:
        logger.exception('failed creating async redis client')
        return None


# Async helpers
async def mark_online(user_id: int) -> bool:
    try:
        rc = _get_async_client()
        if rc:
            await rc.sadd('agrovet:online_users', int(user_id))
            return True
        # fallback
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
            await rc.srem('agrovet:online_users', int(user_id))
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
            return await rc.sismember('agrovet:online_users', int(user_id))
        return int(user_id) in _LOCAL_ONLINE
    except Exception:
        logger.exception('is_online failed')
        return int(user_id) in _LOCAL_ONLINE


# Sync helpers (for views and other sync code)
def sync_mark_online(user_id: int) -> bool:
    try:
        client = _get_sync_client()
        if client:
            client.sadd('agrovet:online_users', int(user_id))
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
            client.srem('agrovet:online_users', int(user_id))
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
            return client.sismember('agrovet:online_users', int(user_id))
        return int(user_id) in _LOCAL_ONLINE
    except Exception:
        logger.exception('sync_is_online failed')
        return int(user_id) in _LOCAL_ONLINE
