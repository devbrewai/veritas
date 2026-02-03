"""JWKS fetcher for Better Auth token validation.

This service fetches the JSON Web Key Set from Better Auth and caches
it for efficient JWT validation without network calls on every request.
"""

import logging
from typing import Any

from cachetools import TTLCache
from jwt import PyJWKClient

from src.config import get_settings

logger = logging.getLogger(__name__)


class JWKSService:
    """Service to fetch and cache JWKS from Better Auth."""

    def __init__(self, jwks_url: str | None = None, cache_ttl: int | None = None):
        """Initialize the JWKS service.

        Args:
            jwks_url: URL to fetch JWKS from. Defaults to BETTER_AUTH_URL/api/auth/jwks.
            cache_ttl: Time-to-live for JWKS cache in seconds. Defaults to settings.
        """
        settings = get_settings()
        self._jwks_url = jwks_url or f"{settings.BETTER_AUTH_URL}/api/auth/jwks"
        self._cache_ttl = cache_ttl or settings.JWKS_CACHE_TTL
        self._client: PyJWKClient | None = None
        self._cache: TTLCache[str, Any] = TTLCache(maxsize=10, ttl=self._cache_ttl)

    @property
    def jwks_url(self) -> str:
        """Get the JWKS URL."""
        return self._jwks_url

    def _get_client(self) -> PyJWKClient:
        """Get or create the PyJWKClient.

        Returns:
            PyJWKClient instance for fetching signing keys.
        """
        if self._client is None:
            self._client = PyJWKClient(
                self._jwks_url,
                cache_jwk_set=True,
                lifespan=self._cache_ttl,
            )
        return self._client

    def get_signing_key(self, token: str) -> Any:
        """Get the signing key for a JWT token.

        Extracts the key ID (kid) from the token header and fetches
        the corresponding public key from the JWKS.

        Args:
            token: JWT token string.

        Returns:
            PyJWK signing key for token verification.

        Raises:
            jwt.exceptions.PyJWKClientError: If key cannot be fetched.
        """
        client = self._get_client()
        return client.get_signing_key_from_jwt(token)

    def clear_cache(self) -> None:
        """Clear the JWKS cache.

        Useful for testing or when keys are rotated.
        """
        self._cache.clear()
        self._client = None
        logger.info("JWKS cache cleared")


# Singleton instance
jwks_service = JWKSService()
