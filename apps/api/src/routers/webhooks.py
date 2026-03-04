"""Webhook registration: create, list, delete."""

import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies.auth import get_authenticated_user
from src.models.webhook import WebhookConfig
from src.schemas.webhook import (
    WebhookCreateRequest,
    WebhookCreateResponse,
    WebhookListItem,
    WebhookListResponse,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _generate_secret() -> str:
    """Generate a random webhook secret (32 bytes hex)."""
    return secrets.token_hex(32)


@router.post(
    "",
    response_model=WebhookCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a webhook",
    description="Create a webhook endpoint. The secret is returned only once; use it to verify X-Veritas-Signature.",
)
async def create_webhook(
    body: WebhookCreateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_authenticated_user),
) -> WebhookCreateResponse:
    secret = _generate_secret()
    config = WebhookConfig(
        user_id=user_id,
        url=str(body.url),
        secret=secret,
        events=body.events,
        active=True,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return WebhookCreateResponse(
        id=config.id,
        url=config.url,
        events=config.events,
        secret=secret,
        created_at=config.created_at,
    )


@router.get(
    "",
    response_model=WebhookListResponse,
    summary="List webhooks",
    description="List all webhooks for the current user. Secrets are never returned.",
)
async def list_webhooks(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_authenticated_user),
) -> WebhookListResponse:
    result = await db.execute(
        select(WebhookConfig)
        .where(WebhookConfig.user_id == user_id)
        .order_by(WebhookConfig.created_at.desc())
    )
    configs = result.scalars().all()
    return WebhookListResponse(
        webhooks=[
            WebhookListItem(
                id=c.id,
                url=c.url,
                events=c.events,
                active=c.active,
                created_at=c.created_at,
            )
            for c in configs
        ]
    )


@router.delete(
    "/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a webhook",
    description="Permanently delete a webhook. Delivery will stop immediately.",
)
async def delete_webhook(
    webhook_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_authenticated_user),
) -> None:
    from uuid import UUID

    try:
        uid = UUID(webhook_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid webhook ID")
    result = await db.execute(
        select(WebhookConfig).where(
            WebhookConfig.id == uid,
            WebhookConfig.user_id == user_id,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await db.delete(config)
    await db.commit()
    return None
