"""Rate limiting middleware for upload endpoints."""

import logging
from uuid import UUID

from cachetools import TTLCache
from fastapi import Depends, HTTPException, status

from src.config import get_settings
from src.dependencies.auth import get_current_user_id

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

    def check(self, user_id: UUID) -> bool:
        """Check if user is within rate limit.

        Args:
            user_id: User's UUID.

        Returns:
            True if request is allowed, False if rate limited.
        """
        key = str(user_id)
        current_count = self._cache.get(key, 0)

        if current_count >= self.max_requests:
            logger.warning(f"Rate limit exceeded for user {user_id}")
            return False

        # Increment count
        self._cache[key] = current_count + 1
        return True

    def get_remaining(self, user_id: UUID) -> int:
        """Get remaining requests for user.

        Args:
            user_id: User's UUID.

        Returns:
            Number of remaining requests in current window.
        """
        key = str(user_id)
        current_count = self._cache.get(key, 0)
        return max(0, self.max_requests - current_count)

    def reset(self, user_id: UUID) -> None:
        """Reset rate limit for a user (for testing).

        Args:
            user_id: User's UUID.
        """
        key = str(user_id)
        if key in self._cache:
            del self._cache[key]


# Global rate limiter for document uploads
upload_rate_limiter = RateLimiter(
    max_requests=settings.RATE_LIMIT_UPLOADS_PER_MINUTE,
    window_seconds=60,
)


async def check_rate_limit(
    user_id: UUID = Depends(get_current_user_id),
) -> UUID:
    """FastAPI dependency to check rate limit.

    Args:
        user_id: Current authenticated user's ID.

    Returns:
        user_id if within rate limit.

    Raises:
        HTTPException: 429 Too Many Requests if rate limited.
    """
    if not upload_rate_limiter.check(user_id):
        remaining = upload_rate_limiter.get_remaining(user_id)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {settings.RATE_LIMIT_UPLOADS_PER_MINUTE} uploads per minute.",
            headers={
                "Retry-After": "60",
                "X-RateLimit-Limit": str(settings.RATE_LIMIT_UPLOADS_PER_MINUTE),
                "X-RateLimit-Remaining": str(remaining),
            },
        )
    return user_id
