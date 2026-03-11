"""
cache.py — Lightweight Redis caching utilities for FastAPI/async backends.

Usage:
    from backend.cache import cached, delete_cache

    @cached("lead:stats:{user_id}", ttl=60)
    async def expensive_fn(user_id: str) -> dict:
        ...

    # Invalidate after a write:
    await delete_cache("lead:stats:*")
"""

import asyncio
import json
import logging
from functools import wraps
from typing import Any, Callable, Optional

import redis.asyncio as aioredis

from .config import settings

logger = logging.getLogger(__name__)

# ─── Connection pool shared across the process ────────────────────────────────
_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> Optional[aioredis.Redis]:
    """Return a shared async Redis client, or None if unavailable."""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,
            )
            await _redis_client.ping()
        except Exception as exc:   # noqa: BLE001
            logger.warning("Redis unavailable — caching disabled: %s", exc)
            _redis_client = None
    return _redis_client


async def cache_get(key: str) -> Optional[Any]:
    """Return the cached value for *key*, or None on miss/error."""
    redis = await get_redis()
    if redis is None:
        return None
    try:
        raw = await redis.get(key)
        return json.loads(raw) if raw is not None else None
    except Exception as exc:   # noqa: BLE001
        logger.debug("cache_get(%s) error: %s", key, exc)
        return None


async def cache_set(key: str, value: Any, ttl: int = 60) -> None:
    """Store *value* under *key* with the given TTL (seconds)."""
    redis = await get_redis()
    if redis is None:
        return
    try:
        await redis.setex(key, ttl, json.dumps(value, default=str))
    except Exception as exc:   # noqa: BLE001
        logger.debug("cache_set(%s) error: %s", key, exc)


async def delete_cache(pattern: str) -> None:
    """Delete all keys matching *pattern* (supports glob wildcards)."""
    redis = await get_redis()
    if redis is None:
        return
    try:
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)
    except Exception as exc:   # noqa: BLE001
        logger.debug("delete_cache(%s) error: %s", pattern, exc)


def cached(key_template: str, ttl: int = 60) -> Callable:
    """
    Async-function decorator that caches the result in Redis.

    *key_template* supports Python format-string syntax resolved against the
    function's keyword arguments, e.g.::

        @cached("lead:stats:{user_id}", ttl=60)
        async def get_stats(user_id: str): ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                cache_key = key_template.format(**kwargs)
            except KeyError:
                # Fallback: skip caching if template args don't match
                return await func(*args, **kwargs)

            cached_value = await cache_get(cache_key)
            if cached_value is not None:
                logger.debug("Cache HIT  %s", cache_key)
                return cached_value

            logger.debug("Cache MISS %s", cache_key)
            result = await func(*args, **kwargs)

            # Pydantic models → dict for JSON serialisation
            serialisable = result
            if hasattr(result, "model_dump"):
                serialisable = result.model_dump()

            await cache_set(cache_key, serialisable, ttl=ttl)
            return result

        return wrapper
    return decorator
