"""FastAPI dependencies for Better Auth JWT validation.

These dependencies extract and validate JWT tokens from the Authorization
header, making the current user's ID available to protected endpoints.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.services.auth.tokens import TokenValidationError, token_service

# Security scheme for Swagger UI - auto_error=False allows custom error handling
security = HTTPBearer(auto_error=False)


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
