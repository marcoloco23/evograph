"""Redis cache service for API response caching."""

from __future__ import annotations

import json
import logging
from typing import Any

import redis

from evograph.settings import settings

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis | None:
    """Get or create a Redis client. Returns None if Redis is unavailable."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    try:
        _redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
        )
        _redis_client.ping()
        logger.info("Redis connected at %s", settings.redis_url)
        return _redis_client
    except Exception:
        logger.warning("Redis unavailable at %s — caching disabled", settings.redis_url)
        _redis_client = None
        return None


def cache_get(key: str) -> Any | None:
    """Get a cached value by key. Returns None on miss or error."""
    client = get_redis()
    if client is None:
        return None
    try:
        val = client.get(key)
        if val is not None:
            return json.loads(val)
    except Exception:
        logger.debug("Cache get error for key=%s", key, exc_info=True)
    return None


def cache_set(key: str, value: Any, ttl: int = 300) -> None:
    """Set a cached value with TTL in seconds."""
    client = get_redis()
    if client is None:
        return
    try:
        client.setex(key, ttl, json.dumps(value))
    except Exception:
        logger.debug("Cache set error for key=%s", key, exc_info=True)


def cache_delete(key: str) -> None:
    """Delete a cached value."""
    client = get_redis()
    if client is None:
        return
    try:
        client.delete(key)
    except Exception:
        logger.debug("Cache delete error for key=%s", key, exc_info=True)


def cache_invalidate_pattern(pattern: str) -> None:
    """Delete all keys matching a pattern."""
    client = get_redis()
    if client is None:
        return
    try:
        keys = client.keys(pattern)
        if keys:
            client.delete(*keys)
    except Exception:
        logger.debug("Cache invalidate error for pattern=%s", pattern, exc_info=True)


def close_redis() -> None:
    """Close the Redis connection."""
    global _redis_client
    if _redis_client is not None:
        try:
            _redis_client.close()
        except Exception:
            pass
        _redis_client = None
