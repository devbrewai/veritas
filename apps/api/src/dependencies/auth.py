"""FastAPI dependencies for Better Auth JWT and API key authentication.

Supports dual auth: X-API-Key (programmatic) or Authorization Bearer (dashboard).
"""

import hashlib
from datetime import datetime, timezone

from fastapi import Depends, Request, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.exceptions import VeritasError
from src.models.api_key import ApiKey
from src.schemas.errors import ErrorCode
from src.services.auth.tokens import TokenValidationError, token_service

# Security schemes for Swagger/OpenAPI (scheme_name ensures both show in /docs)
security = HTTPBearer(auto_error=False, scheme_name="BearerAuth")
api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    scheme_name="ApiKeyAuth",
)

# Default rate limit for JWT (dashboard) users
DEFAULT_JWT_RATE_LIMIT = 60


async def get_authenticated_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_key: str | None = Depends(api_key_header),
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """Authenticate via X-API-Key or Bearer JWT. Set request.state.user_id and request.state.rate_limit.

    API key takes priority. Used for documents, kyc, screening, risk, users (not api_keys).
    """
    # Try API key first
    if api_key and api_key.strip():
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        result = await db.execute(
            select(ApiKey).where(
                ApiKey.key_hash == key_hash,
                ApiKey.revoked_at.is_(None),
            )
        )
        row = result.scalar_one_or_none()
        if row:
            row.last_used_at = datetime.now(timezone.utc)
            await db.commit()
            request.state.user_id = row.user_id
            request.state.rate_limit = row.rate_limit_per_minute
            request.state.auth_key_id = str(row.id)
            return row.user_id
        raise VeritasError(
            status_code=401,
            code=ErrorCode.INVALID_API_KEY,
            message="Invalid or revoked API key.",
        )

    # Fall back to Bearer JWT
    if credentials:
        try:
            user_id = token_service.get_user_id(credentials.credentials)
            request.state.user_id = user_id
            request.state.rate_limit = DEFAULT_JWT_RATE_LIMIT
            if not hasattr(request.state, "auth_key_id"):
                request.state.auth_key_id = "session"
            return user_id
        except TokenValidationError:
            raise VeritasError(
                status_code=401,
                code=ErrorCode.AUTHENTICATION_REQUIRED,
                message="Invalid or expired token.",
            )

    raise VeritasError(
        status_code=401,
        code=ErrorCode.AUTHENTICATION_REQUIRED,
        message="Provide an X-API-Key header or Authorization: Bearer <token>.",
    )


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """Extract and validate user ID from Better Auth JWT.

    This dependency:
    1. Extracts the Bearer token from the Authorization header
    2. Validates the JWT signature using JWKS from Better Auth
    3. Extracts the user ID from the token's 'sub' claim

    Args:
        credentials: Bearer token from Authorization header.

    Returns:
        User ID string from the validated token.

    Raises:
        HTTPException: 401 if not authenticated or token is invalid.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = token_service.get_user_id(credentials.credentials)
        return user_id
    except TokenValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
