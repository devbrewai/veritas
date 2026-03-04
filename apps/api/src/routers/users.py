"""User-related endpoints."""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from src.config import get_settings
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies.auth import get_current_user_id
from src.models.audit_log import AuditLog
from src.models.document import Document
from src.models.screening_result import ScreeningResult
from src.schemas.user import (
    AuditLogExportItem,
    DocumentExportItem,
    ScreeningExportItem,
    UserDataExport,
    UserStats,
)
from src.services.audit import AuditAction, get_client_ip, log_audit_event
from src.services.retention import delete_all_user_data

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me/stats", response_model=UserStats)
async def get_user_stats(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> UserStats:
    """Get statistics for the current user.

    Returns counts of documents, screenings, and risk score averages.
    """
    # Calculate start of current month
    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)

    # Get total document count
    total_docs_result = await db.execute(
        select(func.count(Document.id)).where(Document.user_id == user_id)
    )
    total_documents = total_docs_result.scalar() or 0

    # Get documents by type
    docs_by_type_result = await db.execute(
        select(Document.document_type, func.count(Document.id))
        .where(Document.user_id == user_id)
        .group_by(Document.document_type)
    )
    documents_by_type = {
        doc_type: count for doc_type, count in docs_by_type_result.all()
    }

    # Get documents this month
    docs_this_month_result = await db.execute(
        select(func.count(Document.id)).where(
            Document.user_id == user_id,
            Document.uploaded_at >= month_start,
        )
    )
    documents_this_month = docs_this_month_result.scalar() or 0

    # Get total screening count
    total_screenings_result = await db.execute(
        select(func.count(ScreeningResult.id)).where(
            ScreeningResult.user_id == user_id
        )
    )
    total_screenings = total_screenings_result.scalar() or 0

    # Get screenings by decision
    screenings_by_decision_result = await db.execute(
        select(ScreeningResult.sanctions_decision, func.count(ScreeningResult.id))
        .where(ScreeningResult.user_id == user_id)
        .group_by(ScreeningResult.sanctions_decision)
    )
    screenings_by_decision = {
        decision: count for decision, count in screenings_by_decision_result.all()
    }

    # Get screenings this month
    screenings_this_month_result = await db.execute(
        select(func.count(ScreeningResult.id)).where(
            ScreeningResult.user_id == user_id,
            ScreeningResult.screened_at >= month_start,
        )
    )
    screenings_this_month = screenings_this_month_result.scalar() or 0

    # Calculate average risk score
    avg_risk_result = await db.execute(
        select(func.avg(ScreeningResult.risk_score)).where(
            ScreeningResult.user_id == user_id,
            ScreeningResult.risk_score.isnot(None),
        )
    )
    average_risk_score = avg_risk_result.scalar()

    # Get risk tier distribution
    risk_tier_result = await db.execute(
        select(ScreeningResult.risk_tier, func.count(ScreeningResult.id))
        .where(
            ScreeningResult.user_id == user_id,
            ScreeningResult.risk_tier.isnot(None),
        )
        .group_by(ScreeningResult.risk_tier)
    )
    risk_tier_distribution = {
        tier: count for tier, count in risk_tier_result.all()
    }

    return UserStats(
        total_documents=total_documents,
        documents_by_type=documents_by_type,
        documents_this_month=documents_this_month,
        total_screenings=total_screenings,
        screenings_by_decision=screenings_by_decision,
        screenings_this_month=screenings_this_month,
        average_risk_score=average_risk_score,
        risk_tier_distribution=risk_tier_distribution,
    )


async def _get_user_export_data(user_id: str, db: AsyncSession) -> UserDataExport:
    """Build full user data export (documents, screenings, audit_logs)."""
    docs_result = await db.execute(
        select(Document).where(Document.user_id == user_id).order_by(Document.uploaded_at)
    )
    docs = docs_result.scalars().all()
    screenings_result = await db.execute(
        select(ScreeningResult)
        .where(ScreeningResult.user_id == user_id)
        .order_by(ScreeningResult.screened_at)
    )
    screenings = screenings_result.scalars().all()
    audit_result = await db.execute(
        select(AuditLog).where(AuditLog.user_id == user_id).order_by(AuditLog.created_at)
    )
    audit_logs = audit_result.scalars().all()
    def doc_to_export(d: Document) -> DocumentExportItem:
        return DocumentExportItem(
            id=d.id,
            customer_id=d.customer_id,
            document_type=d.document_type,
            uploaded_at=d.uploaded_at,
            expires_at=d.expires_at,
            file_size_bytes=d.file_size_bytes,
            processed=d.processed,
            ocr_confidence=d.ocr_confidence,
            issue_date=d.issue_date,
        )

    def screening_to_export(s: ScreeningResult) -> ScreeningExportItem:
        return ScreeningExportItem(
            id=s.id,
            document_id=s.document_id,
            customer_id=s.customer_id,
            full_name=s.full_name,
            sanctions_decision=s.sanctions_decision,
            sanctions_score=s.sanctions_score,
            risk_score=s.risk_score,
            risk_tier=s.risk_tier,
            recommendation=s.recommendation,
            screened_at=s.screened_at,
        )

    def audit_to_export(a: AuditLog) -> AuditLogExportItem:
        return AuditLogExportItem(
            id=a.id,
            action=a.action,
            resource_type=a.resource_type,
            resource_id=a.resource_id,
            details=a.details,
            created_at=a.created_at,
        )

    return UserDataExport(
        documents=[doc_to_export(d) for d in docs],
        screening_results=[screening_to_export(s) for s in screenings],
        audit_logs=[audit_to_export(a) for a in audit_logs],
    )


@router.get(
    "/me/export",
    summary="Export user data (GDPR)",
    description="Export all user data (documents metadata, KYC results, audit) for GDPR data portability. Returns JSON download.",
)
async def get_user_export(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> Response:
    """Export all user data as JSON (GDPR data export)."""
    export_data = await _get_user_export_data(user_id, db)
    await log_audit_event(
        db,
        user_id=user_id,
        action=AuditAction.DATA_EXPORT_REQUESTED,
        resource_type="user",
        resource_id=user_id,
        details={"exported_at": export_data.exported_at},
        ip_address=get_client_ip(request),
    )
    await db.commit()
    filename = f"veritas-export-{user_id[:16]}-{datetime.utcnow().strftime('%Y%m%d')}.json"
    return Response(
        content=export_data.model_dump_json(),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete(
    "/me",
    status_code=204,
    summary="Delete account (right to be forgotten)",
    description="Delete account and all associated data. Irreversible.",
)
async def delete_me(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> None:
    """Delete all user data (right to be forgotten). Returns 204 No Content."""
    await log_audit_event(
        db,
        user_id=user_id,
        action=AuditAction.ACCOUNT_DELETED,
        resource_type="user",
        resource_id=user_id,
        details={"requested_at": datetime.utcnow().isoformat()},
        ip_address=get_client_ip(request),
    )
    await db.flush()
    await delete_all_user_data(db, user_id, settings.UPLOAD_DIR)
    await db.commit()
