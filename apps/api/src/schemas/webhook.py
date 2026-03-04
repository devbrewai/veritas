"""Pydantic schemas for webhook registration and list."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator


# Event names used when notifying webhooks
WEBHOOK_EVENT_DOCUMENT_PROCESSED = "document.processed"
WEBHOOK_EVENT_KYC_COMPLETE = "kyc.complete"
WEBHOOK_EVENTS = (WEBHOOK_EVENT_DOCUMENT_PROCESSED, WEBHOOK_EVENT_KYC_COMPLETE)


class WebhookCreateRequest(BaseModel):
    """Request body for creating a webhook."""

    url: HttpUrl = Field(..., description="Endpoint URL to receive POST requests")
    events: list[str] = Field(
        ...,
        min_length=1,
        max_length=32,
        description="Event types to subscribe to (e.g. document.processed, kyc.complete)",
    )

    @field_validator("events")
    @classmethod
    def events_must_be_allowed(cls, v: list[str]) -> list[str]:
        invalid = [e for e in v if e not in WEBHOOK_EVENTS]
        if invalid:
            raise ValueError(f"Invalid event(s): {invalid}. Allowed: {list(WEBHOOK_EVENTS)}")
        return v


class WebhookCreateResponse(BaseModel):
    """Response when creating a webhook. Secret is only shown once."""

    id: UUID = Field(..., description="Webhook ID")
    url: str = Field(..., description="Registered URL")
    events: list[str] = Field(..., description="Subscribed events")
    secret: str = Field(..., description="Secret for HMAC signature (store securely; only shown once)")
    created_at: datetime = Field(..., description="Creation time")


class WebhookListItem(BaseModel):
    """Single webhook in list (no secret)."""

    id: UUID
    url: str
    events: list[str]
    active: bool
    created_at: datetime


class WebhookListResponse(BaseModel):
    """Response for listing webhooks."""

    webhooks: list[WebhookListItem]
