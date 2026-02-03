"""JWT token validation using Better Auth JWKS.

This service validates JWT tokens issued by Better Auth by fetching
the public keys from the JWKS endpoint and verifying token signatures.
"""

import logging

import jwt
from jwt.exceptions import InvalidTokenError, PyJWKClientError

from src.config import get_settings
from src.services.auth.jwks import jwks_service

logger = logging.getLogger(__name__)


class TokenValidationError(Exception):
    """Raised when token validation fails."""

    pass


class TokenService:
    """Validate JWTs issued by Better Auth."""

    def __init__(self):
        """Initialize the token service."""
        self._settings = get_settings()

    def decode_token(self, token: str) -> dict:
        """Decode and validate a JWT from Better Auth.

        Fetches the signing key from JWKS and verifies the token signature,
        expiration, and claims.

        Args:
            token: JWT string from Authorization header.

        Returns:
            Decoded token payload as dictionary.

        Raises:
            TokenValidationError: If token is invalid, expired, or cannot be verified.
        """
        try:
            # Get signing key from JWKS
            signing_key = jwks_service.get_signing_key(token)

            # Decode and validate the token
            # Better Auth uses EdDSA by default, but also supports RS256 and ES256
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["EdDSA", "RS256", "ES256"],
                options={
                    "verify_aud": False,  # Better Auth doesn't set audience by default
                    "verify_iss": False,  # Issuer verification optional
                },
            )
            return payload

        except PyJWKClientError as e:
            logger.warning(f"Failed to fetch signing key: {e}")
            raise TokenValidationError(f"Failed to fetch signing key: {e}")

        except InvalidTokenError as e:
            logger.warning(f"Token validation failed: {e}")
            raise TokenValidationError(str(e))

    def get_user_id(self, token: str) -> str:
        """Extract user ID from token.

        Args:
            token: JWT string.

        Returns:
            User ID string from the token's 'sub' claim.

        Raises:
            TokenValidationError: If token is invalid or missing user ID.
        """
        payload = self.decode_token(token)

        user_id = payload.get("sub")
        if not user_id:
            raise TokenValidationError("Token missing user ID (sub claim)")

        return user_id

    def get_user_email(self, token: str) -> str | None:
        """Extract user email from token if present.

        Args:
            token: JWT string.

        Returns:
            User email from the token, or None if not present.

        Raises:
            TokenValidationError: If token is invalid.
        """
        payload = self.decode_token(token)
        return payload.get("email")


# Singleton instance
token_service = TokenService()
