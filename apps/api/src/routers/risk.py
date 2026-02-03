"""Risk scoring and adverse media API endpoints.

Provides endpoints for adverse media scanning and ML-based risk scoring
with SHAP explanations.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies.auth import get_current_user_id
from src.schemas.adverse_media import (
    AdverseMediaRequest,
    AdverseMediaResponse,
    AdverseMediaResult,
)
from src.schemas.risk import (
    RiskScoringRequest,
    RiskScoringResponse,
    RiskScoringResult,
    RiskServiceStatus,
)
from src.services.adverse_media import adverse_media_service
from src.services.risk import RiskFeatures
from src.services.risk.scorer import risk_scoring_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/risk", tags=["Risk"])


# Endpoints
@router.get("/health", response_model=RiskServiceStatus)
async def health_check() -> RiskServiceStatus:
    """Check health of risk scoring services.

    Returns status of adverse media service (GDELT + sentiment)
    and risk scoring model (LightGBM).
    """
    return RiskServiceStatus(
        status="healthy" if risk_scoring_service.is_ready else "degraded",
        model_loaded=risk_scoring_service.is_ready,
        model_version=risk_scoring_service.model_version,
        adverse_media_available=adverse_media_service.is_ready,
    )


@router.post("/adverse-media", response_model=AdverseMediaResponse)
async def scan_adverse_media(
    request: AdverseMediaRequest,
) -> AdverseMediaResponse:
    """Scan for adverse media mentions of a name.

    Searches GDELT for news articles mentioning the name in conjunction
    with adverse keywords (fraud, sanctions, money laundering, etc.),
    then analyzes sentiment of each article using VADER.

    Returns:
        - article_count: Number of adverse media articles found
        - articles: List of articles with title, source, sentiment
        - average_sentiment: Overall sentiment score (-1 to 1)
        - sentiment_category: Negative, Neutral, or Positive
    """
    if not adverse_media_service.is_ready:
        result = AdverseMediaResult(
            success=False,
            errors=["Adverse media service not initialized"],
        )
        return AdverseMediaResponse(result=result)

    try:
        result = await adverse_media_service.scan_name(
            name=request.name,
            max_results=request.max_results,
        )
        return AdverseMediaResponse(result=result)
    except Exception as e:
        logger.exception(f"Error scanning adverse media: {e}")
        result = AdverseMediaResult(
            success=False,
            errors=[str(e)],
        )
        return AdverseMediaResponse(result=result)


@router.post("/adverse-media/document/{document_id}", response_model=AdverseMediaResponse)
async def scan_document_adverse_media(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> AdverseMediaResponse:
    """Scan for adverse media based on document extracted data.

    Extracts the name from the document's OCR data and performs
    an adverse media scan.

    Args:
        document_id: UUID of the document to scan
        user_id: Current authenticated user's ID

    Returns:
        Adverse media scan results
    """
    if not adverse_media_service.is_ready:
        result = AdverseMediaResult(
            success=False,
            errors=["Adverse media service not initialized"],
        )
        return AdverseMediaResponse(result=result)

    try:
        result = await adverse_media_service.scan_document(
            document_id=document_id,
            db=db,
            user_id=user_id,
        )
        return AdverseMediaResponse(result=result)
    except Exception as e:
        logger.exception(f"Error scanning document adverse media: {e}")
        result = AdverseMediaResult(
            success=False,
            errors=[str(e)],
        )
        return AdverseMediaResponse(result=result)


@router.post("/score", response_model=RiskScoringResponse)
async def score_risk(request: RiskScoringRequest) -> RiskScoringResponse:
    """Score risk from provided features.

    Takes risk features as input and returns a risk score with
    SHAP-based explanations.

    Features:
        - document_quality: OCR confidence (0-1)
        - sanctions_score: Sanctions match confidence (0-1)
        - sanctions_match: Binary sanctions hit (0 or 1)
        - adverse_media_count: Number of adverse articles
        - adverse_media_sentiment: Average sentiment (-1 to 1)
        - country_risk: Country risk score (0-1)
        - document_age_days: Days since document issued

    Returns:
        - risk_score: Calibrated probability (0-1)
        - risk_tier: Low, Medium, or High
        - recommendation: Approve, Review, or Reject
        - feature_contributions: SHAP-based feature importance
        - top_risk_factors: Human-readable risk factors
    """
    if not risk_scoring_service.is_ready:
        result = RiskScoringResult(
            success=False,
            errors=["Risk scoring service not initialized"],
        )
        return RiskScoringResponse(result=result)

    try:
        # Convert bool to int for sanctions_match
        sanctions_match_int = 1 if request.sanctions_match else 0

        features = RiskFeatures(
            document_quality=request.document_quality,
            sanctions_score=request.sanctions_score,
            sanctions_match=sanctions_match_int,
            adverse_media_count=request.adverse_media_count,
            adverse_media_sentiment=request.adverse_media_sentiment,
            country_risk=request.country_risk,
            document_age_days=request.document_age_days,
        )

        result = risk_scoring_service.score(features)
        return RiskScoringResponse(result=result)
    except Exception as e:
        logger.exception(f"Error scoring risk: {e}")
        result = RiskScoringResult(
            success=False,
            errors=[str(e)],
        )
        return RiskScoringResponse(result=result)


@router.post("/score/screening/{screening_id}", response_model=RiskScoringResponse)
async def score_screening_result(
    screening_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> RiskScoringResponse:
    """Score risk for an existing screening result.

    Extracts features from the screening result and associated document,
    computes risk score, and updates the screening result with the
    risk assessment.

    Args:
        screening_id: UUID of the screening result to score
        user_id: Current authenticated user's ID

    Returns:
        Risk scoring result with SHAP explanations
    """
    if not risk_scoring_service.is_ready:
        result = RiskScoringResult(
            success=False,
            errors=["Risk scoring service not initialized"],
        )
        return RiskScoringResponse(result=result)

    try:
        result = await risk_scoring_service.score_screening_result(
            screening_result_id=screening_id,
            db=db,
            user_id=user_id,
        )
        return RiskScoringResponse(result=result)
    except Exception as e:
        logger.exception(f"Error scoring screening result: {e}")
        result = RiskScoringResult(
            success=False,
            errors=[str(e)],
        )
        return RiskScoringResponse(result=result)
