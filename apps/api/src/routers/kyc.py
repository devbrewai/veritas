"""KYC aggregation endpoints."""

import logging
import time
import uuid
from datetime import datetime, date, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.database import get_db
from src.dependencies.auth import get_current_user_id
from src.middleware.rate_limit import check_rate_limit
from src.models.document import Document
from src.models.screening_result import ScreeningResult
from src.services.document_processor import (
    process_business_document,
    process_passport,
    process_utility_bill,
)
from src.services.retention import compute_expires_at
from src.schemas.kyc import (
    KYCAdverseMediaResult,
    KYCBatchRequest,
    KYCBatchResponse,
    KYCDocumentSummary,
    KYCProcessResponse,
    KYCResult,
    KYCRiskResult,
    KYCSanctionsResult,
    KYCStatus,
)

from src.services.adverse_media import adverse_media_service
from src.services.audit import AuditAction, get_client_ip, log_audit_event
from src.services.risk.scorer import risk_scoring_service
from src.services.sanctions import sanctions_screening_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kyc", tags=["kyc"])
settings = get_settings()


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

@router.post("/process", response_model=KYCProcessResponse)
async def process_kyc(
    request: Request,
    file: UploadFile = File(...),
    customer_id: str = Form(...),
    document_type: str = Form(default="passport"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(check_rate_limit),
) -> KYCProcessResponse:
    """
    Run the full KYC pipeline in a single request.

    Chains: document upload/OCR -> sanctions screening -> adverse media scan -> risk scoring. 
    Returns a unified result.

    Rate limited to 10 requests per minute per user.
    """
    pipeline_start = time.time()
    errors: list[str] = []

    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    ext = file.filename.split(".")[-1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}",
        )
    
    content = await file.read()
    file_size = len(content)

    if file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {settings.MAX_FILE_SIZE_MB}MB",
        )
    
    # Save file
    doc_id = uuid.uuid4()
    upload_dir = Path(settings.UPLOAD_DIR) / str(doc_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"original.{ext}"

    with open(file_path, "wb") as f:
        f.write(content)

    #  Step 1: OCR Extraction
    ocr_result = None
    supported_types = ["passport", "utility_bill", "business_reg"]
    if document_type == "passport":
        ocr_result = process_passport(file_path)
    elif document_type == "utility_bill":
        ocr_result = process_utility_bill(file_path)
    elif document_type == "business_reg":
        ocr_result = process_business_document(file_path)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported document type: '{document_type}'. Supported: {supported_types}",
        )
    
    extracted_data = ocr_result.get("data") if ocr_result else None
    ocr_confidence = ocr_result.get("confidence") if ocr_result else None
    doc_processed = extracted_data is not None

    if not doc_processed:
        ocr_errors = ocr_result.get("errors", []) if ocr_result else []
        errors.extend(ocr_errors)
    
    #  Persist document
    document = Document(
        id=doc_id,
        user_id=user_id,
        customer_id=customer_id,
        document_type=document_type,
        file_path=str(file_path),
        file_size_bytes=file_size,
        processed=doc_processed,
        extracted_data=extracted_data,
        ocr_confidence=ocr_confidence,
        processing_error="; ".join(errors) if errors else None,
        expires_at=compute_expires_at(settings.DOCUMENT_RETENTION_DAYS),
    )

    if doc_processed and document_type == "passport" and extracted_data:
        expiry_date_str = extracted_data.get("expiry_date")
        if expiry_date_str:
            try:
                expiry_date = date.fromisoformat(expiry_date_str)
                document.issue_date = expiry_date - timedelta(days=365 * 10)
            except (ValueError, TypeError):
                pass
    
    db.add(document)
    await db.flush()

    #  If OCR failed, return early with partial result
    if not doc_processed:
        processing_time_ms = int((time.time() - pipeline_start) * 1000)
        await log_audit_event(
            db,
            user_id=user_id,
            action=AuditAction.KYC_PROCESSED,
            resource_type="kyc",
            resource_id=str(doc_id),
            details={
                "customer_id": customer_id,
                "overall_status": "pending",
                "document_processed": False,
                "processing_time_ms": processing_time_ms,
            },
            ip_address=get_client_ip(request),
        )
        await db.commit()
        return KYCProcessResponse(
            customer_id=customer_id,
            document_id=doc_id,
            document_processed=doc_processed,
            errors=errors,
            processing_time_ms=processing_time_ms,
        )
    
    #  Step 2: Sanction Screening
    sanctions_result_schema = None
    screening_db_id = None

    if sanctions_screening_service.is_loaded:
        sanctions_result = await sanctions_screening_service.screen_document(
            document_id=doc_id,
            db=db,
            user_id=user_id,
        )
        if sanctions_result.success and sanctions_result.data:
            sanctions_result_schema = KYCSanctionsResult(
                screening_id=uuid.uuid4(),
                decision=sanctions_result.data.decision.value,
                top_match_score=sanctions_result.confidence,
                matched_name=(
                    sanctions_result.data.top_match.matched_name
                    if sanctions_result.data.top_match
                    else None
                ),
                screened_at=datetime.utcnow(),
            )
            # Find the screening result just created
            sr_query = await db.execute(
                select(ScreeningResult).where(
                    ScreeningResult.document_id == doc_id,
                    ScreeningResult.user_id == user_id,
                ).order_by(ScreeningResult.screened_at.desc())
            )
            sr = sr_query.scalar_one_or_none()
            if sr:
                screening_db_id = sr.id
                sanctions_result_schema.screening_id = sr.id
        else:
            errors.extend(sanctions_result.errors or [])
    else:
        errors.append("Sanctions screening service not available")

    # Step 3: Adverse Media Scan
    adverse_media_schema = None

    if adverse_media_service.is_ready and screening_db_id:
        adverse_result = await adverse_media_service.scan_document(
            document_id=doc_id,
            db=db,
            user_id=user_id,
        )
        if adverse_result.success and adverse_result.data:
            adverse_media_schema = KYCAdverseMediaResult(
                article_count=adverse_result.data.articles_found,
                average_sentiment=adverse_result.data.average_sentiment,
                sentiment_category=(
                    "Negative" if adverse_result.data.average_sentiment < -0.05
                    else "Positive" if adverse_result.data.average_sentiment > 0.05
                    else "Neutral"
                ) if adverse_result.data.average_sentiment is not None else None,
            )
        elif not adverse_result.success:
            errors.extend(adverse_result.errors or [])

    # Step 4: Risk Scoring
    risk_schema = None

    if risk_scoring_service.is_ready and screening_db_id:
        risk_result = await risk_scoring_service.score_screening_result(
            screening_result_id=screening_db_id,
            db=db,
            user_id=user_id,
        )
        if risk_result.success and risk_result.data:
            risk_schema = KYCRiskResult(
                risk_score=risk_result.data.risk_score,
                risk_tier=risk_result.data.risk_tier.value,
                recommendation=risk_result.data.recommendation.value,
                top_risk_factors=risk_result.data.top_risk_factors,
            )
        elif not risk_result.success:
            errors.extend(risk_result.errors or []) 

    # Determine overall status
    overall_status = _determine_overall_status(sanctions_result_schema, risk_schema)

    processing_time_ms = int((time.time() - pipeline_start) * 1000)

    await log_audit_event(
        db,
        user_id=user_id,
        action=AuditAction.KYC_PROCESSED,
        resource_type="kyc",
        resource_id=str(doc_id),
        details={
            "customer_id": customer_id,
            "overall_status": overall_status.value,
            "document_processed": True,
            "processing_time_ms": processing_time_ms,
        },
        ip_address=get_client_ip(request),
    )

    await db.commit()

    return KYCProcessResponse(
        customer_id=customer_id,
        document_id=doc_id,
        document_processed=True,
        extracted_data=extracted_data,
        ocr_confidence=ocr_confidence,
        sanctions_screening=sanctions_result_schema,
        adverse_media=adverse_media_schema,
        risk_assessment=risk_schema,
        overall_status=overall_status,
        processing_time_ms=processing_time_ms,
        errors=errors,
    )

@router.get("/{customer_id}", response_model=KYCResult)
async def get_kyc_result(
    http_request: Request,
    customer_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> KYCResult:
    """Get aggregated KYC results for a customer.

    Returns document summaries, sanctions screening results,
    adverse media findings, and risk assessment for the specified customer.

    - **customer_id**: Customer identifier
    """
    result = await _get_kyc_result(customer_id, user_id, db)

    await log_audit_event(
        db,
        user_id=user_id,
        action=AuditAction.KYC_VIEWED,
        resource_type="kyc",
        resource_id=customer_id,
        ip_address=get_client_ip(http_request),
    )

    return result


@router.post("/batch", response_model=KYCBatchResponse)
async def batch_kyc_results(
    http_request: Request,
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

    await log_audit_event(
        db,
        user_id=user_id,
        action=AuditAction.KYC_BATCH_VIEWED,
        resource_type="kyc",
        details={
            "customer_ids": request.customer_ids,
            "total_processed": len(results),
        },
        ip_address=get_client_ip(http_request),
    )

    return KYCBatchResponse(
        results=results,
        total_processed=len(results),
        total_approved=total_approved,
        total_review=total_review,
        total_rejected=total_rejected,
        total_pending=total_pending,
    )
