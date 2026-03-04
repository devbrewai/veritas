"""Idempotency-Key support for POST endpoints.

Uses Redis to store and replay responses. If REDIS_URL is not set, idempotency is a no-op.
"""

import json
import logging
from typing import Any

from src.config import get_settings

logger = logging.getLogger(__name__)

IDEMPOTENCY_TTL = 86400  # 24 hours
_KEY_PREFIX = "idempotency"

_redis_client: Any = None


def _get_redis():
    """Lazy Redis client. Returns None if REDIS_URL not set."""
    global _redis_client
    settings = get_settings()
    if not settings.REDIS_URL:
        return None
    if _redis_client is None:
        try:
            from redis.asyncio import Redis

            _redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception as e:
            logger.warning("Redis not available for idempotency: %s", e)
            return None
    return _redis_client


async def check_idempotency(key: str, user_id: str) -> dict | None:
    """Return cached response if this idempotency key was already processed.

    Args:
        key: Idempotency-Key header value.
        user_id: Authenticated user ID (scopes the key).

    Returns:
        Cached response dict, or None if not found or Redis unavailable.
    """
    redis = _get_redis()
    if not redis:
        return None
    cache_key = f"{_KEY_PREFIX}:{user_id}:{key}"
    try:
        raw = await redis.get(cache_key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.warning("Idempotency check failed: %s", e)
        return None


async def store_idempotency(key: str, user_id: str, response: dict) -> None:
    """Store response for idempotent replay.

    Args:
        key: Idempotency-Key header value.
        user_id: Authenticated user ID.
        response: JSON-serializable response dict (e.g. from model_dump(mode="json")).
    """
    redis = _get_redis()
    if not redis:
        return
    cache_key = f"{_KEY_PREFIX}:{user_id}:{key}"
    try:
        await redis.setex(cache_key, IDEMPOTENCY_TTL, json.dumps(response))
    except Exception as e:
        logger.warning("Idempotency store failed: %s", e)
