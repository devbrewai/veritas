"""Risk scoring service orchestrator.

Provides high-level risk scoring functionality combining
the ML model with business logic for risk tier assignment.
"""

import logging
import time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.document import Document
from src.models.screening_result import ScreeningResult
from src.schemas.risk import (
    Recommendation,
    RiskFeatureContribution,
    RiskScoringData,
    RiskScoringResult,
    RiskTier,
)
from src.services.risk.features import RiskFeatures, get_country_risk
from src.services.risk.model import risk_model

logger = logging.getLogger(__name__)


class RiskScoringService:
    """Service for risk scoring with ML model.

    Orchestrates risk scoring using the trained LightGBM model
    and provides SHAP-based explanations.
    """

    def __init__(self) -> None:
        """Initialize the service (model loaded via initialize())."""
        self._initialized = False

    def initialize(self) -> None:
        """Initialize by loading the risk model."""
        if risk_model.load():
            self._initialized = True
            logger.info("Risk scoring service initialized")
        else:
            logger.warning("Risk scoring service failed to initialize - model not found")

    @property
    def is_ready(self) -> bool:
        """Check if service is ready for scoring."""
        return self._initialized and risk_model.is_loaded

    @property
    def model_version(self) -> str | None:
        """Return model version if loaded."""
        return risk_model.version if risk_model.is_loaded else None

    def score(self, features: RiskFeatures) -> RiskScoringResult:
        """Score risk based on input features.

        Args:
            features: Input features for scoring.

        Returns:
            RiskScoringResult with score, tier, and explanations.
        """
        start_time = time.time()

        if not self.is_ready:
            return RiskScoringResult(
                success=False,
                errors=["Risk model not loaded"],
                processing_time_ms=0,
            )

        try:
            # Get prediction with SHAP explanations
            risk_score, risk_class, contributions = risk_model.predict(features)

            # Map class to tier
            tier_map = {0: RiskTier.LOW, 1: RiskTier.MEDIUM, 2: RiskTier.HIGH}
            risk_tier = tier_map[risk_class]

            # Derive recommendation from score
            if risk_score < 0.3:
                recommendation = Recommendation.APPROVE
            elif risk_score < 0.7:
                recommendation = Recommendation.REVIEW
            else:
                recommendation = Recommendation.REJECT

            # Build feature contributions
            feature_contribs = [
                RiskFeatureContribution(
                    feature=name,
                    value=value,
                    contribution=shap_val,
                    direction="increases_risk" if shap_val > 0 else "decreases_risk",
                )
                for name, value, shap_val in contributions[:5]
            ]

            # Top risk factors (features with positive SHAP values)
            top_risk_factors = [
                self._format_risk_factor(name, value, shap_val)
                for name, value, shap_val in contributions
                if shap_val > 0
            ][:3]

            processing_time_ms = (time.time() - start_time) * 1000

            return RiskScoringResult(
                success=True,
                data=RiskScoringData(
                    risk_score=risk_score,
                    risk_tier=risk_tier,
                    recommendation=recommendation,
                    feature_contributions=feature_contribs,
                    top_risk_factors=top_risk_factors,
                    input_features=features.to_dict(),
                ),
                processing_time_ms=processing_time_ms,
                model_version=risk_model.version,
            )

        except Exception as e:
            logger.exception(f"Error scoring risk: {e}")
            return RiskScoringResult(
                success=False,
                errors=[str(e)],
                processing_time_ms=(time.time() - start_time) * 1000,
            )

    def _format_risk_factor(
        self,
        name: str,
        value: float,
        shap_val: float,
    ) -> str:
        """Format a risk factor for display.

        Args:
            name: Feature name.
            value: Feature value.
            shap_val: SHAP contribution.

        Returns:
            Human-readable risk factor string.
        """
        factor_labels = {
            "document_quality": f"Document quality: {value:.0%}",
            "sanctions_score": f"Sanctions score: {value:.2f}",
            "sanctions_match": "Sanctions match found" if value > 0.5 else "No sanctions match",
            "adverse_media_count": f"Adverse media: {int(value)} mentions",
            "adverse_media_sentiment": f"Media sentiment: {value:.2f}",
            "country_risk": f"Country risk: {value:.0%}",
            "document_age_days": f"Document age: {int(value)} days",
        }
        return factor_labels.get(name, f"{name}: {value:.2f}")

    async def score_screening_result(
        self,
        screening_result_id: UUID,
        db: AsyncSession,
    ) -> RiskScoringResult:
        """Score risk for an existing screening result.

        Extracts features from the screening result and associated
        document, then updates the screening result with risk assessment.

        Args:
            screening_result_id: UUID of the screening result.
            db: Database session.

        Returns:
            RiskScoringResult with assessment.
        """
        start_time = time.time()

        if not self.is_ready:
            return RiskScoringResult(
                success=False,
                errors=["Risk model not loaded"],
                processing_time_ms=(time.time() - start_time) * 1000,
            )

        # Get screening result
        result = await db.execute(
            select(ScreeningResult).where(ScreeningResult.id == screening_result_id)
        )
        screening = result.scalar_one_or_none()

        if not screening:
            return RiskScoringResult(
                success=False,
                errors=[f"Screening result not found: {screening_result_id}"],
                processing_time_ms=(time.time() - start_time) * 1000,
            )

        # Get associated document for OCR confidence
        document = None
        if screening.document_id:
            doc_result = await db.execute(
                select(Document).where(Document.id == screening.document_id)
            )
            document = doc_result.scalar_one_or_none()

        # Extract features from screening result
        features = self._extract_features(screening, document)

        # Score
        score_result = self.score(features)

        # Update screening result if successful
        if score_result.success and score_result.data:
            screening.risk_score = score_result.data.risk_score
            screening.risk_tier = score_result.data.risk_tier.value
            screening.risk_reasons = {
                "contributions": [
                    c.model_dump() for c in score_result.data.feature_contributions
                ],
                "top_factors": score_result.data.top_risk_factors,
                "model_version": score_result.model_version,
            }
            screening.recommendation = score_result.data.recommendation.value
            await db.flush()
            logger.info(
                f"Updated screening result {screening.id} with risk: "
                f"{score_result.data.risk_tier.value} ({score_result.data.risk_score:.2f})"
            )

        return score_result

    def _extract_features(
        self,
        screening: ScreeningResult,
        document: Document | None,
    ) -> RiskFeatures:
        """Extract risk features from screening result and document.

        Args:
            screening: The screening result.
            document: Associated document (optional).

        Returns:
            RiskFeatures for scoring.
        """
        # Document quality from OCR confidence
        doc_quality = document.ocr_confidence if document and document.ocr_confidence else 0.5

        # Sanctions features
        sanctions_score = screening.sanctions_score or 0.0
        sanctions_match = 1 if screening.sanctions_match else 0

        # Adverse media features
        adverse_count = screening.adverse_media_count or 0
        adverse_sentiment = 0.0
        if screening.adverse_media_summary:
            adverse_sentiment = screening.adverse_media_summary.get("average_sentiment", 0.0)

        # Country risk from document nationality
        country_risk = 0.5  # Default
        if document and document.extracted_data:
            nationality = document.extracted_data.get("nationality")
            if nationality:
                country_risk = get_country_risk(nationality)

        # Document age (not easily available, default to 0)
        doc_age_days = 0

        return RiskFeatures(
            document_quality=doc_quality,
            sanctions_score=sanctions_score,
            sanctions_match=sanctions_match,
            adverse_media_count=adverse_count,
            adverse_media_sentiment=adverse_sentiment,
            country_risk=country_risk,
            document_age_days=doc_age_days,
        )


# Global service instance
risk_scoring_service = RiskScoringService()
