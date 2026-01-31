"""Pydantic schemas for risk scoring."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class RiskTier(str, Enum):
    """Risk tier classification."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class Recommendation(str, Enum):
    """Recommendation based on risk assessment."""

    APPROVE = "Approve"
    REVIEW = "Review"
    REJECT = "Reject"


class RiskFeatureContribution(BaseModel):
    """SHAP-based feature contribution to risk score."""

    feature: str
    value: float  # Raw feature value
    contribution: float  # SHAP value (positive = increases risk)
    direction: str  # "increases_risk" or "decreases_risk"


class RiskScoringData(BaseModel):
    """Core risk scoring result data."""

    risk_score: float = Field(ge=0.0, le=1.0)
    risk_tier: RiskTier
    recommendation: Recommendation
    feature_contributions: list[RiskFeatureContribution] = Field(default_factory=list)
    top_risk_factors: list[str] = Field(default_factory=list)
    input_features: dict[str, float] = Field(default_factory=dict)


class RiskScoringResult(BaseModel):
    """Full risk scoring result."""

    success: bool
    data: RiskScoringData | None = None
    errors: list[str] = Field(default_factory=list)
    processing_time_ms: float = 0.0
    model_version: str = "1.0.0"


class RiskScoringRequest(BaseModel):
    """Request for risk scoring with feature inputs."""

    document_quality: float = Field(
        ge=0.0, le=1.0, description="OCR confidence score"
    )
    sanctions_score: float = Field(
        ge=0.0, le=1.0, description="Sanctions match similarity score"
    )
    sanctions_match: bool = Field(
        default=False, description="Whether a sanctions match was found"
    )
    adverse_media_count: int = Field(
        ge=0, default=0, description="Number of negative media mentions"
    )
    adverse_media_sentiment: float = Field(
        ge=-1.0, le=1.0, default=0.0, description="Average sentiment score"
    )
    country_risk: float = Field(
        ge=0.0, le=1.0, default=0.5, description="Country risk score"
    )
    document_age_days: int = Field(
        ge=0, default=0, description="Days since document was issued"
    )


class RiskScoringResponse(BaseModel):
    """API response for risk scoring."""

    result: RiskScoringResult
    scored_at: datetime = Field(default_factory=datetime.utcnow)
    api_version: str = "1.0.0"


class RiskServiceStatus(BaseModel):
    """Risk scoring service health status."""

    status: str
    model_loaded: bool
    model_version: str | None = None
    adverse_media_available: bool
