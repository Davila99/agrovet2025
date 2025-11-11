from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import logging

logger = logging.getLogger(__name__)

try:
    # redis.exceptions may not be available if redis isn't installed
    import redis
    RedisConnectionError = redis.exceptions.ConnectionError
except Exception:
    RedisConnectionError = ConnectionError  # fallback


def safe_group_send_sync(group_name: str, payload: dict, persist_retry: bool = True) -> bool:
    """Attempt to send `payload` to `group_name` via the channel layer.

    If the channel layer (Redis) is unavailable, log the error and optionally
    persist a BroadcastRetry record for later retry. Returns True if send
    succeeded, False otherwise.
    """
    channel_layer = get_channel_layer()
    if channel_layer is None:
        logger.warning('No channel_layer configured; cannot broadcast to %s', group_name)
        return False

    try:
        async_to_sync(channel_layer.group_send)(group_name, payload)
        return True
    except Exception as e:
        # Prefer logging the specific Redis connection error when present.
        if isinstance(e, RedisConnectionError) or isinstance(e, ConnectionRefusedError):
            logger.exception('Channel layer connection error while broadcasting to %s', group_name)
        else:
            logger.exception('Unexpected error broadcasting to %s', group_name)

        if persist_retry:
            try:
                # Import here to avoid circular imports at module load time
                from chat.models import BroadcastRetry
                BroadcastRetry.objects.create(group_name=group_name, payload=payload, last_error=str(e)[:200])
                logger.info('Persisted BroadcastRetry for group=%s', group_name)
            except Exception:
                logger.exception('Failed to persist BroadcastRetry for group=%s', group_name)
        return False
