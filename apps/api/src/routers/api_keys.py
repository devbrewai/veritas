"""API key management: create, list, revoke."""

import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies.auth import get_current_user_id
from src.models.api_key import ApiKey
from src.schemas.api_key import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyListItem,
    ApiKeyListResponse,
)

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


def generate_api_key() -> tuple[str, str, str]:
    """Generate a new API key. Returns (full_key, prefix, hash)."""
    raw = secrets.token_hex(24)
    full_key = f"vrt_sk_{raw}"
    prefix = f"vrt_sk_{raw[:8]}"
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, prefix, key_hash


@router.post(
    "",
    response_model=ApiKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an API key",
    description="Generate a new API key for programmatic access. The full key is only shown once in this response.",
)
async def create_api_key(
    body: ApiKeyCreateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> ApiKeyCreateResponse:
    full_key, prefix, key_hash = generate_api_key()
    api_key = ApiKey(
        user_id=user_id,
        name=body.name,
        key_prefix=prefix,
        key_hash=key_hash,
        rate_limit_per_minute=10,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return ApiKeyCreateResponse(
        api_key=full_key,
        prefix=prefix,
        name=api_key.name,
        id=api_key.id,
    )


@router.get(
    "",
    response_model=ApiKeyListResponse,
    summary="List API keys",
    description="List all API keys for the current user. Full keys are never shown again.",
)
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> ApiKeyListResponse:
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.user_id == user_id, ApiKey.revoked_at.is_(None))
        .order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    return ApiKeyListResponse(
        api_keys=[
            ApiKeyListItem(
                id=k.id,
                name=k.name,
                prefix=k.key_prefix,
                rate_limit_per_minute=k.rate_limit_per_minute,
                created_at=k.created_at,
                last_used_at=k.last_used_at,
            )
            for k in keys
        ]
    )


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke an API key",
    description="Revoke an API key. Immediate and irreversible.",
)
async def revoke_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> None:
    from uuid import UUID

    try:
        uid = UUID(key_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid key ID")
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == uid, ApiKey.user_id == user_id)
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    from datetime import datetime, timezone

    api_key.revoked_at = datetime.now(timezone.utc)
    await db.commit()
    return None
