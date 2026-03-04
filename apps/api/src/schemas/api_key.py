"""Pydantic schemas for API key CRUD."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ApiKeyCreateRequest(BaseModel):
    """Request body for creating an API key."""

    name: str = Field(..., min_length=1, max_length=255, description="Label for this key (e.g. Production)")


class ApiKeyCreateResponse(BaseModel):
    """Response when creating an API key. Full key is only shown once."""

    api_key: str = Field(..., description="Full API key (store securely; only shown once)")
    prefix: str = Field(..., description="Key prefix for identification in dashboard")
    name: str = Field(..., description="Key name")
    id: UUID = Field(..., description="Key ID for revoke/list")


class ApiKeyListItem(BaseModel):
    """Single API key in list (no secret)."""

    id: UUID
    name: str
    prefix: str
    rate_limit_per_minute: int
    created_at: datetime
    last_used_at: datetime | None = None


class ApiKeyListResponse(BaseModel):
    """Response for listing API keys."""

    api_keys: list[ApiKeyListItem]
