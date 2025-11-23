"""
Redis configuration and utilities for microservices.
Uses namespaced keys to avoid conflicts.
"""
import os
import redis
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Redis client with namespace support.
    """
    
    def __init__(self, namespace: str = "default", db: int = 0):
        """
        Initialize Redis client with namespace.
        
        Args:
            namespace: Namespace prefix for all keys (e.g., "auth", "chat")
            db: Redis database number
        """
        self.namespace = namespace
        redis_url = os.getenv('REDIS_URL', f'redis://127.0.0.1:6379/{db}')
        
        try:
            self.client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.client.ping()
            logger.info(f"Redis client initialized: namespace={namespace}, url={redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None
    
    def _key(self, key: str) -> str:
        """Add namespace prefix to key."""
        return f"{self.namespace}:{key}"
    
    def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        if not self.client:
            return None
        return self.client.get(self._key(key))
    
    def set(self, key: str, value: str, ex: Optional[int] = None):
        """Set key-value with optional expiration in seconds."""
        if not self.client:
            return False
        return self.client.set(self._key(key), value, ex=ex)
    
    def delete(self, key: str):
        """Delete key."""
        if not self.client:
            return False
        return self.client.delete(self._key(key))
    
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self.client:
            return False
        return self.client.exists(self._key(key)) > 0
    
    def expire(self, key: str, time: int):
        """Set expiration time for key."""
        if not self.client:
            return False
        return self.client.expire(self._key(key), time)
    
    def incr(self, key: str, amount: int = 1):
        """Increment key value."""
        if not self.client:
            return None
        return self.client.incr(self._key(key), amount)
    
    def decr(self, key: str, amount: int = 1):
        """Decrement key value."""
        if not self.client:
            return None
        return self.client.decr(self._key(key), amount)


# Factory function for service-specific Redis clients
def get_redis_client(service_name: str, db: int = 0) -> RedisClient:
    """
    Get a Redis client for a specific service.
    
    Args:
        service_name: Name of the service (e.g., "auth", "chat", "marketplace")
        db: Redis database number (0 for cache, 1 for sessions, etc.)
    
    Returns:
        RedisClient instance
    """
    return RedisClient(namespace=service_name, db=db)

