"""Sanctions screening and risk assessment endpoints."""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.schemas.sanctions import (
    SanctionsBatchRequest,
    SanctionsBatchResponse,
    SanctionsScreeningResult,
    SanctionsScreenRequest,
    SanctionsScreenResponse,
    SanctionsServiceStatus,
)
from src.services.sanctions import sanctions_screening_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/screening", tags=["screening"])


@router.post("/sanctions", response_model=SanctionsScreenResponse)
async def screen_name(
    request: SanctionsScreenRequest,
) -> SanctionsScreenResponse:
    """
    Screen a single name against sanctions lists.

    Returns the top matches with confidence scores and a decision
    (match, review, or no_match).

    - **name**: The name to screen (required)
    - **aliases**: Optional list of name variations
    - **nationality**: Optional country code to filter results
    - **top_k**: Number of top matches to return (1-10, default: 3)
    """
    if not sanctions_screening_service.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sanctions screening service not available",
        )

    result = await sanctions_screening_service.screen_name(
        name=request.name,
        aliases=request.aliases,
        nationality=request.nationality,
        top_k=request.top_k,
    )

    return SanctionsScreenResponse(
        result=result,
        screened_at=datetime.utcnow(),
        api_version="1.0.0",
    )


@router.post("/sanctions/batch", response_model=SanctionsBatchResponse)
async def screen_names_batch(
    request: SanctionsBatchRequest,
) -> SanctionsBatchResponse:
    """
    Screen multiple names against sanctions lists in batch.

    Maximum 100 names per request.

    - **queries**: List of screening requests (max 100)
    """
    if not sanctions_screening_service.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sanctions screening service not available",
        )

    queries = [
        {
            "name": q.name,
            "aliases": q.aliases,
            "nationality": q.nationality,
        }
        for q in request.queries
    ]

    results = await sanctions_screening_service.screen_batch(queries)

    total_matches = sum(
        1
        for r in results
        if r.success and r.data and r.data.decision.value == "match"
    )
    total_reviews = sum(
        1
        for r in results
        if r.success and r.data and r.data.decision.value == "review"
    )
    total_time = sum(r.processing_time_ms for r in results)

    return SanctionsBatchResponse(
        results=results,
        total_screened=len(results),
        total_matches=total_matches,
        total_reviews=total_reviews,
        total_processing_time_ms=total_time,
        screened_at=datetime.utcnow(),
    )


@router.post("/document/{document_id}", response_model=SanctionsScreenResponse)
async def screen_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> SanctionsScreenResponse:
    """
    Screen names extracted from a processed document.

    Extracts full_name and nationality from the document's extracted_data
    and performs sanctions screening. Stores result in screening_results table.

    - **document_id**: UUID of the processed document
    """
    if not sanctions_screening_service.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sanctions screening service not available",
        )

    result = await sanctions_screening_service.screen_document(
        document_id=document_id,
        db=db,
    )

    if not result.success and "not found" in str(result.errors):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )

    return SanctionsScreenResponse(
        result=result,
        screened_at=datetime.utcnow(),
        api_version="1.0.0",
    )


@router.get("/sanctions/health", response_model=SanctionsServiceStatus)
async def get_sanctions_health() -> SanctionsServiceStatus:
    """
    Get sanctions screening service health status.

    Returns whether the screener is loaded, record count, and version info.
    """
    return sanctions_screening_service.get_status()
