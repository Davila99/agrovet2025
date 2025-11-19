from django.core.cache import cache
from django.conf import settings
import json

def get_or_set_cache(key, func, timeout=None, version=None):
    """Retrieve value from cache or set it by calling func().

    func may be a callable or a literal value.
    """
    if timeout is None:
        timeout = getattr(settings, 'DEFAULT_CACHE_TIMEOUT', 300)
    val = cache.get(key, version=version)
    if val is not None:
        try:
            return json.loads(val)
        except Exception:
            return val

    # compute value
    value = func() if callable(func) else func
    try:
        store = json.dumps(value)
    except Exception:
        store = value
    cache.set(key, store, timeout=timeout, version=version)
    return value

def invalidate_cache(key, version=None):
    try:
        cache.delete(key, version=version)
        return True
    except Exception:
        return False
