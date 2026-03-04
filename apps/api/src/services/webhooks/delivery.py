"""Webhook delivery: HMAC-SHA256 signing and retries.

Payloads are signed with X-Veritas-Signature: t=<timestamp>,v1=<hex_sig>.
Retry delays: 0, 5, 30, 300 seconds.
"""

import hashlib
import hmac
import json
import logging
import time
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session_maker
from src.models.webhook import WebhookConfig

logger = logging.getLogger(__name__)

SIGNATURE_HEADER = "X-Veritas-Signature"
SIGNATURE_VERSION = "v1"
RETRY_DELAYS_SECONDS = [0, 5, 30, 300]
HTTP_TIMEOUT = 30.0


def sign_payload(secret: str, payload_bytes: bytes, timestamp: int) -> str:
    """Compute HMAC-SHA256 signature for payload. Returns hex digest."""
    # Signed payload: timestamp + "." + body (Stripe-style)
    signed_payload = f"{timestamp}.{payload_bytes.decode('utf-8')}"
    sig = hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return sig


def build_signature_header(secret: str, payload_bytes: bytes, timestamp: int | None = None) -> str:
    """Build X-Veritas-Signature header value: t=<timestamp>,v1=<sig>."""
    ts = timestamp or int(time.time())
    sig = sign_payload(secret, payload_bytes, ts)
    return f"t={ts},v1={sig}"


async def deliver_webhook(
    url: str,
    secret: str,
    event: str,
    payload: dict[str, Any],
) -> None:
    """POST payload to url with HMAC signature. Retries with delays [0, 5, 30, 300]."""
    body = {"event": event, "payload": payload}
    payload_bytes = json.dumps(body, sort_keys=True).encode("utf-8")
    timestamp = int(time.time())
    signature = build_signature_header(secret, payload_bytes, timestamp)
    headers = {
        "Content-Type": "application/json",
        SIGNATURE_HEADER: signature,
    }
    last_error: Exception | None = None
    for attempt, delay in enumerate(RETRY_DELAYS_SECONDS):
        if delay > 0:
            await asyncio_sleep(delay)
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                resp = await client.post(url, content=payload_bytes, headers=headers)
                if 200 <= resp.status_code < 300:
                    logger.info("Webhook delivered to %s (event=%s)", url, event)
                    return
                last_error = httpx.HTTPStatusError(
                    f"Webhook delivery failed: {resp.status_code}",
                    request=resp.request,
                    response=resp,
                )
        except Exception as e:
            last_error = e
            logger.warning(
                "Webhook delivery attempt %s to %s failed: %s",
                attempt + 1,
                url,
                e,
            )
    logger.error(
        "Webhook delivery failed after %s attempts to %s (event=%s): %s",
        len(RETRY_DELAYS_SECONDS),
        url,
        event,
        last_error,
    )


async def asyncio_sleep(seconds: float) -> None:
    """Sleep for seconds (plumbed for tests)."""
    import asyncio
    await asyncio.sleep(seconds)


async def notify_webhooks(user_id: str, event: str, payload: dict[str, Any]) -> None:
    """Find active webhooks for user and event, then deliver each in background.

    Does not block: spawns asyncio tasks for delivery. Call after document
    processing or KYC pipeline completes.
    """
    async with async_session_maker() as db:
        result = await db.execute(
            select(WebhookConfig).where(
                WebhookConfig.user_id == user_id,
                WebhookConfig.active.is_(True),
                WebhookConfig.events.contains([event]),
            )
        )
        configs = result.scalars().all()
    if not configs:
        return
    import asyncio
    for config in configs:
        asyncio.create_task(
            deliver_webhook(config.url, config.secret, event, payload),
        )
    logger.debug("Scheduled %s webhook(s) for user %s event %s", len(configs), user_id, event)
