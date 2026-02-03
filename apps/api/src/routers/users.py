"""User-related endpoints."""

import logging
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies.auth import get_current_user_id
from src.models.document import Document
from src.models.screening_result import ScreeningResult
from src.schemas.user import UserStats

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me/stats", response_model=UserStats)
async def get_user_stats(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
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
