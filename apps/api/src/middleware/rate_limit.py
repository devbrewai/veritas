"""Rate limiting middleware for upload endpoints."""

import logging

from cachetools import TTLCache
from fastapi import Depends, Request

from src.config import get_settings
from src.dependencies.auth import DEFAULT_JWT_RATE_LIMIT, get_authenticated_user
from src.exceptions import VeritasError
from src.schemas.errors import ErrorCode

logger = logging.getLogger(__name__)
settings = get_settings()


class RateLimiter:
    """In-memory rate limiter using TTLCache.

    Tracks request counts per user with automatic expiration.
    """

    def __init__(self, max_requests: int, window_seconds: int = 60):
        """Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed per window.
            window_seconds: Time window in seconds (default: 60).
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # TTLCache automatically expires entries after window_seconds
        self._cache: TTLCache[str, int] = TTLCache(
            maxsize=10000,  # Max users to track
            ttl=window_seconds,
        )

    def check(self, key: str, limit: int) -> bool:
        """Check if key is within rate limit.

        Args:
            key: Rate limit bucket key (e.g. user_id:auth_key_id).
            limit: Max requests per window for this key.

        Returns:
            True if request is allowed, False if rate limited.
        """
        bucket_key = f"{key}:{limit}"
        current_count = self._cache.get(bucket_key, 0)

        if current_count >= limit:
            logger.warning("Rate limit exceeded for key %s (limit %s)", key, limit)
            return False

        self._cache[bucket_key] = current_count + 1
        return True

    def get_remaining(self, key: str, limit: int) -> int:
        """Get remaining requests for key."""
        bucket_key = f"{key}:{limit}"
        current_count = self._cache.get(bucket_key, 0)
        return max(0, limit - current_count)

    def reset(self, key: str, limit: int) -> None:
        """Reset rate limit for a key (for testing)."""
        bucket_key = f"{key}:{limit}"
        if bucket_key in self._cache:
            del self._cache[bucket_key]


# Global rate limiter (limit is per-request from request.state.rate_limit)
upload_rate_limiter = RateLimiter(
    max_requests=settings.RATE_LIMIT_UPLOADS_PER_MINUTE,
    window_seconds=60,
)


async def check_rate_limit(
    request: Request,
    user_id: str = Depends(get_authenticated_user),
) -> str:
    """Check rate limit using request.state.rate_limit (set by get_authenticated_user)."""
    rate_limit = getattr(request.state, "rate_limit", DEFAULT_JWT_RATE_LIMIT)
    auth_key_id = getattr(request.state, "auth_key_id", "session")
    key = f"{user_id}:{auth_key_id}"

    if not upload_rate_limiter.check(key, rate_limit):
        remaining = upload_rate_limiter.get_remaining(key, rate_limit)
        raise VeritasError(
            status_code=429,
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message=f"Rate limit exceeded ({rate_limit}/minute). Try again shortly.",
            details={"retry_after_seconds": 60, "limit": f"{rate_limit}/minute"},
        )
    return user_id
