import json
from hashlib import blake2b

from flask import current_app


def _common(key):
    """Retrieve the cache object; hash the key."""
    return (
        list(current_app.extensions["cache"].values())[0],
        blake2b(json.dumps(key).encode()).hexdigest(),
    )


def get(key):
    cache, hash = _common(key)
    result = cache.get(hash)
    if result:
        current_app.logger.info(f"Cache hit for {repr(key)}")
    return result


def set(key, value):
    cache, hash = _common(key)
    cache.set(hash, value)
