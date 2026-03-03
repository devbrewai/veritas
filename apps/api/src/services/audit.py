"""Audit logging service for compliance tracking.

Provides a fire-and-forget helper that records every screening decision,
risk assessment, and document operation into the immutable audit_logs table.
Failures are caught and logged — they never break the calling request.
"""

import logging
from enum import Enum

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    """Standardised action names for audit log entries."""

    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_VIEWED = "document_viewed"
    SANCTIONS_SCREENED = "sanctions_screened"
    SANCTIONS_BATCH_SCREENED = "sanctions_batch_screened"
    SANCTIONS_DOCUMENT_SCREENED = "sanctions_document_screened"
    ADVERSE_MEDIA_SCANNED = "adverse_media_scanned"
    ADVERSE_MEDIA_DOCUMENT_SCANNED = "adverse_media_document_scanned"
    RISK_SCORED = "risk_scored"
    RISK_SCREENING_SCORED = "risk_screening_scored"
    KYC_PROCESSED = "kyc_processed"
    KYC_VIEWED = "kyc_viewed"
    KYC_BATCH_VIEWED = "kyc_batch_viewed"


def get_client_ip(request: Request) -> str | None:
    """Extract client IP from the request, preferring X-Forwarded-For."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


async def log_audit_event(
    db: AsyncSession,
    *,
    user_id: str,
    action: AuditAction,
    resource_type: str,
    resource_id: str | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> None:
    """Persist an audit log entry. Never raises — logs errors internally."""
    try:
        entry = AuditLog(
            user_id=user_id,
            action=action.value,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
        )
        db.add(entry)
        await db.flush()
    except Exception:
        logger.exception("Failed to write audit log entry")
