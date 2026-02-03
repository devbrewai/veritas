"""KYC aggregation endpoints."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies.auth import get_current_user_id
from src.models.document import Document
from src.models.screening_result import ScreeningResult
from src.schemas.kyc import (
    KYCAdverseMediaResult,
    KYCBatchRequest,
    KYCBatchResponse,
    KYCDocumentSummary,
    KYCResult,
    KYCRiskResult,
    KYCSanctionsResult,
    KYCStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kyc", tags=["kyc"])


def _determine_overall_status(
    sanctions_result: KYCSanctionsResult | None,
    risk_result: KYCRiskResult | None,
) -> KYCStatus:
    """Determine overall KYC status based on screening and risk results.

    Args:
        sanctions_result: Sanctions screening result if available.
        risk_result: Risk assessment result if available.

    Returns:
        Overall KYC status.
    """
    # If we have a risk recommendation, use that
    if risk_result:
        if risk_result.recommendation == "Reject":
            return KYCStatus.REJECTED
        elif risk_result.recommendation == "Review":
            return KYCStatus.REVIEW
        elif risk_result.recommendation == "Approve":
            return KYCStatus.APPROVED

    # Fall back to sanctions decision
    if sanctions_result:
        if sanctions_result.decision == "match":
            return KYCStatus.REJECTED
        elif sanctions_result.decision == "review":
            return KYCStatus.REVIEW
        elif sanctions_result.decision == "no_match":
            return KYCStatus.APPROVED

    # No screening done yet
    return KYCStatus.PENDING


async def _get_kyc_result(
    customer_id: str,
    user_id: str,
    db: AsyncSession,
) -> KYCResult:
    """Build KYC result for a single customer.

    Args:
        customer_id: Customer identifier.
        user_id: Authenticated user's ID.
        db: Database session.

    Returns:
        Aggregated KYC result.
    """
    # Get all documents for this customer
    docs_result = await db.execute(
        select(Document).where(
            Document.customer_id == customer_id,
            Document.user_id == user_id,
        ).order_by(Document.uploaded_at.desc())
    )
    documents = docs_result.scalars().all()

    # Build document summaries
    doc_summaries = [
        KYCDocumentSummary(
            document_id=doc.id,
            document_type=doc.document_type,
            processed=doc.processed,
            ocr_confidence=doc.ocr_confidence,
            extracted_data=doc.extracted_data,
            created_at=doc.uploaded_at,
        )
        for doc in documents
    ]

    # Get screening results for this customer
    screening_result = await db.execute(
        select(ScreeningResult).where(
            ScreeningResult.customer_id == customer_id,
            ScreeningResult.user_id == user_id,
        ).order_by(ScreeningResult.screened_at.desc())
    )
    screenings = screening_result.scalars().all()

    # Build sanctions result from most recent screening
    sanctions_result = None
    adverse_media_result = None
    risk_result = None

    if screenings:
        latest = screenings[0]

        # Sanctions screening
        sanctions_result = KYCSanctionsResult(
            screening_id=latest.id,
            decision=latest.sanctions_decision,
            top_match_score=latest.sanctions_score,
            matched_name=latest.sanctions_details.get("top_match", {}).get("name")
            if latest.sanctions_details
            else None,
            screened_at=latest.screened_at,
        )

        # Adverse media
        if latest.adverse_media_count is not None:
            sentiment_category = None
            avg_sentiment = None

            if latest.adverse_media_summary:
                avg_sentiment = latest.adverse_media_summary.get("average_sentiment")
                sentiment_category = latest.adverse_media_summary.get(
                    "sentiment_category"
                )

            adverse_media_result = KYCAdverseMediaResult(
                article_count=latest.adverse_media_count,
                average_sentiment=avg_sentiment,
                sentiment_category=sentiment_category,
            )

        # Risk assessment
        if latest.risk_score is not None and latest.risk_tier:
            top_factors = []
            if latest.risk_reasons:
                top_factors = latest.risk_reasons.get("top_risk_factors", [])

            risk_result = KYCRiskResult(
                risk_score=latest.risk_score,
                risk_tier=latest.risk_tier,
                recommendation=latest.recommendation or "Review",
                top_risk_factors=top_factors,
            )

    # Determine overall status
    overall_status = _determine_overall_status(sanctions_result, risk_result)

    # Build final result with timestamps
    now = datetime.utcnow()
    created_at = documents[0].uploaded_at if documents else now
    updated_at = screenings[0].screened_at if screenings else created_at

    return KYCResult(
        customer_id=customer_id,
        documents=doc_summaries,
        sanctions_screening=sanctions_result,
        adverse_media=adverse_media_result,
        risk_assessment=risk_result,
        overall_status=overall_status,
        created_at=created_at,
        updated_at=updated_at,
    )


@router.get("/{customer_id}", response_model=KYCResult)
async def get_kyc_result(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> KYCResult:
    """Get aggregated KYC results for a customer.

    Returns document summaries, sanctions screening results,
    adverse media findings, and risk assessment for the specified customer.

    - **customer_id**: Customer identifier
    """
    return await _get_kyc_result(customer_id, user_id, db)


@router.post("/batch", response_model=KYCBatchResponse)
async def batch_kyc_results(
    request: KYCBatchRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> KYCBatchResponse:
    """Get KYC results for multiple customers in batch.

    Maximum 10 customers per request.

    - **customer_ids**: List of customer identifiers (max 10)
    """
    if len(request.customer_ids) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 customers per batch request",
        )

    results = []
    for customer_id in request.customer_ids:
        result = await _get_kyc_result(customer_id, user_id, db)
        results.append(result)

    # Count statuses
    total_approved = sum(1 for r in results if r.overall_status == KYCStatus.APPROVED)
    total_review = sum(1 for r in results if r.overall_status == KYCStatus.REVIEW)
    total_rejected = sum(1 for r in results if r.overall_status == KYCStatus.REJECTED)
    total_pending = sum(1 for r in results if r.overall_status == KYCStatus.PENDING)

    return KYCBatchResponse(
        results=results,
        total_processed=len(results),
        total_approved=total_approved,
        total_review=total_review,
        total_rejected=total_rejected,
        total_pending=total_pending,
    )
