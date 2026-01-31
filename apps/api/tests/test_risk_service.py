"""Tests for risk scoring service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.schemas.risk import Recommendation, RiskTier
from src.services.risk.features import RiskFeatures
from src.services.risk.scorer import RiskScoringService


class TestRiskScoringService:
    """Test cases for RiskScoringService."""

    @pytest.fixture
    def service(self) -> RiskScoringService:
        """Create and initialize a risk scoring service."""
        service = RiskScoringService()
        service.initialize()
        if not service.is_ready:
            pytest.skip("Risk model not available")
        return service

    @pytest.fixture
    def low_risk_features(self) -> RiskFeatures:
        """Create low-risk feature set."""
        return RiskFeatures(
            document_quality=0.95,
            sanctions_score=0.05,
            sanctions_match=0,
            adverse_media_count=0,
            adverse_media_sentiment=0.1,
            country_risk=0.1,
            document_age_days=30,
        )

    @pytest.fixture
    def high_risk_features(self) -> RiskFeatures:
        """Create high-risk feature set."""
        return RiskFeatures(
            document_quality=0.4,
            sanctions_score=0.95,
            sanctions_match=1,
            adverse_media_count=5,
            adverse_media_sentiment=-0.8,
            country_risk=0.9,
            document_age_days=800,
        )

    @pytest.fixture
    def medium_risk_features(self) -> RiskFeatures:
        """Create medium-risk feature set."""
        return RiskFeatures(
            document_quality=0.7,
            sanctions_score=0.5,
            sanctions_match=0,
            adverse_media_count=2,
            adverse_media_sentiment=-0.3,
            country_risk=0.5,
            document_age_days=200,
        )

    def test_service_initialization(self) -> None:
        """Test that service initializes correctly."""
        service = RiskScoringService()
        assert service.is_ready is False

        service.initialize()
        # May or may not be ready depending on model availability
        assert isinstance(service.is_ready, bool)

    def test_model_version_available(self, service: RiskScoringService) -> None:
        """Test that model version is available when loaded."""
        assert service.model_version is not None
        assert service.model_version != "unknown"

    def test_score_returns_result(
        self, service: RiskScoringService, low_risk_features: RiskFeatures
    ) -> None:
        """Test that score returns a valid result."""
        result = service.score(low_risk_features)

        assert result.success is True
        assert result.data is not None
        assert not result.errors  # Empty list or None

    def test_score_low_risk(
        self, service: RiskScoringService, low_risk_features: RiskFeatures
    ) -> None:
        """Test scoring for low-risk features."""
        result = service.score(low_risk_features)

        assert result.success is True
        assert result.data is not None
        assert result.data.risk_score < 0.3
        assert result.data.risk_tier == RiskTier.LOW
        assert result.data.recommendation == Recommendation.APPROVE

    def test_score_high_risk(
        self, service: RiskScoringService, high_risk_features: RiskFeatures
    ) -> None:
        """Test scoring for high-risk features."""
        result = service.score(high_risk_features)

        assert result.success is True
        assert result.data is not None
        assert result.data.risk_score > 0.7
        assert result.data.risk_tier == RiskTier.HIGH
        assert result.data.recommendation == Recommendation.REJECT

    def test_score_medium_risk(
        self, service: RiskScoringService, medium_risk_features: RiskFeatures
    ) -> None:
        """Test scoring for medium-risk features."""
        result = service.score(medium_risk_features)

        assert result.success is True
        assert result.data is not None
        assert 0.2 <= result.data.risk_score <= 0.8

    def test_score_includes_feature_contributions(
        self, service: RiskScoringService, low_risk_features: RiskFeatures
    ) -> None:
        """Test that score includes feature contributions."""
        result = service.score(low_risk_features)

        assert result.success is True
        assert result.data is not None
        assert len(result.data.feature_contributions) > 0

        for contrib in result.data.feature_contributions:
            assert contrib.feature is not None
            assert contrib.value is not None
            assert contrib.contribution is not None
            assert contrib.direction in ["increases_risk", "decreases_risk"]

    def test_score_includes_top_risk_factors(
        self, service: RiskScoringService, high_risk_features: RiskFeatures
    ) -> None:
        """Test that high-risk score includes top risk factors."""
        result = service.score(high_risk_features)

        assert result.success is True
        assert result.data is not None
        # High risk should have some risk factors
        assert len(result.data.top_risk_factors) > 0

    def test_score_includes_input_features(
        self, service: RiskScoringService, low_risk_features: RiskFeatures
    ) -> None:
        """Test that result includes input features."""
        result = service.score(low_risk_features)

        assert result.success is True
        assert result.data is not None
        assert result.data.input_features is not None
        assert "document_quality" in result.data.input_features
        assert result.data.input_features["document_quality"] == 0.95

    def test_score_includes_processing_time(
        self, service: RiskScoringService, low_risk_features: RiskFeatures
    ) -> None:
        """Test that result includes processing time."""
        result = service.score(low_risk_features)

        assert result.processing_time_ms is not None
        assert result.processing_time_ms >= 0

    def test_score_includes_model_version(
        self, service: RiskScoringService, low_risk_features: RiskFeatures
    ) -> None:
        """Test that result includes model version."""
        result = service.score(low_risk_features)

        assert result.success is True
        assert result.model_version is not None

    def test_score_without_initialization(self) -> None:
        """Test scoring without initialization returns error."""
        service = RiskScoringService()
        features = RiskFeatures(
            document_quality=0.8,
            sanctions_score=0.2,
            sanctions_match=0,
            adverse_media_count=0,
            adverse_media_sentiment=0.0,
            country_risk=0.3,
            document_age_days=100,
        )

        result = service.score(features)

        assert result.success is False
        assert result.errors is not None
        assert "not loaded" in result.errors[0]


class TestRiskScoringServiceFormatting:
    """Test risk factor formatting."""

    @pytest.fixture
    def service(self) -> RiskScoringService:
        """Create and initialize a risk scoring service."""
        service = RiskScoringService()
        service.initialize()
        if not service.is_ready:
            pytest.skip("Risk model not available")
        return service

    def test_format_document_quality(self, service: RiskScoringService) -> None:
        """Test document quality formatting."""
        formatted = service._format_risk_factor("document_quality", 0.85, 0.1)
        assert "Document quality" in formatted
        assert "85%" in formatted

    def test_format_sanctions_score(self, service: RiskScoringService) -> None:
        """Test sanctions score formatting."""
        formatted = service._format_risk_factor("sanctions_score", 0.75, 0.2)
        assert "Sanctions score" in formatted
        assert "0.75" in formatted

    def test_format_sanctions_match_true(self, service: RiskScoringService) -> None:
        """Test sanctions match formatting when true."""
        formatted = service._format_risk_factor("sanctions_match", 1, 0.3)
        assert "Sanctions match found" in formatted

    def test_format_sanctions_match_false(self, service: RiskScoringService) -> None:
        """Test sanctions match formatting when false."""
        formatted = service._format_risk_factor("sanctions_match", 0, 0.1)
        assert "No sanctions match" in formatted

    def test_format_adverse_media_count(self, service: RiskScoringService) -> None:
        """Test adverse media count formatting."""
        formatted = service._format_risk_factor("adverse_media_count", 3, 0.2)
        assert "Adverse media" in formatted
        assert "3 mentions" in formatted

    def test_format_country_risk(self, service: RiskScoringService) -> None:
        """Test country risk formatting."""
        formatted = service._format_risk_factor("country_risk", 0.8, 0.15)
        assert "Country risk" in formatted
        assert "80%" in formatted

    def test_format_document_age(self, service: RiskScoringService) -> None:
        """Test document age formatting."""
        formatted = service._format_risk_factor("document_age_days", 365, 0.05)
        assert "Document age" in formatted
        assert "365 days" in formatted

    def test_format_unknown_feature(self, service: RiskScoringService) -> None:
        """Test unknown feature formatting."""
        formatted = service._format_risk_factor("unknown_feature", 0.5, 0.1)
        assert "unknown_feature" in formatted
        assert "0.50" in formatted


class TestRiskScoringServiceScreeningResult:
    """Test scoring from screening results."""

    @pytest.fixture
    def service(self) -> RiskScoringService:
        """Create and initialize a risk scoring service."""
        service = RiskScoringService()
        service.initialize()
        if not service.is_ready:
            pytest.skip("Risk model not available")
        return service

    @pytest.mark.asyncio
    async def test_score_screening_not_found(
        self, service: RiskScoringService
    ) -> None:
        """Test scoring when screening result not found."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.score_screening_result(uuid4(), mock_db)

        assert result.success is False
        assert result.errors is not None
        assert "not found" in result.errors[0]

    @pytest.mark.asyncio
    async def test_score_screening_without_initialization(self) -> None:
        """Test scoring screening without initialization."""
        service = RiskScoringService()
        mock_db = AsyncMock()

        result = await service.score_screening_result(uuid4(), mock_db)

        assert result.success is False
        assert result.errors is not None
        assert "not loaded" in result.errors[0]

    @pytest.mark.asyncio
    async def test_score_screening_success(
        self, service: RiskScoringService
    ) -> None:
        """Test successful screening result scoring."""
        # Create mock screening result
        mock_screening = MagicMock()
        mock_screening.id = uuid4()
        mock_screening.document_id = uuid4()
        mock_screening.sanctions_score = 0.1
        mock_screening.sanctions_match = False
        mock_screening.adverse_media_count = 0
        mock_screening.adverse_media_summary = None

        # Create mock document
        mock_document = MagicMock()
        mock_document.id = mock_screening.document_id
        mock_document.ocr_confidence = 0.95
        mock_document.extracted_data = {"nationality": "USA"}

        # Setup mock db
        mock_db = AsyncMock()
        screening_result = MagicMock()
        screening_result.scalar_one_or_none.return_value = mock_screening

        doc_result = MagicMock()
        doc_result.scalar_one_or_none.return_value = mock_document

        mock_db.execute.side_effect = [screening_result, doc_result]
        mock_db.flush = AsyncMock()

        result = await service.score_screening_result(mock_screening.id, mock_db)

        assert result.success is True
        assert result.data is not None
        # Low risk inputs should give low risk score
        assert result.data.risk_score < 0.5
        # Verify screening result was updated
        assert mock_screening.risk_score is not None
        assert mock_screening.risk_tier is not None
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_score_screening_without_document(
        self, service: RiskScoringService
    ) -> None:
        """Test scoring when document not found."""
        # Create mock screening result without document
        mock_screening = MagicMock()
        mock_screening.id = uuid4()
        mock_screening.document_id = None
        mock_screening.sanctions_score = 0.8
        mock_screening.sanctions_match = True
        mock_screening.adverse_media_count = 3
        mock_screening.adverse_media_summary = {"average_sentiment": -0.5}

        # Setup mock db
        mock_db = AsyncMock()
        screening_result = MagicMock()
        screening_result.scalar_one_or_none.return_value = mock_screening

        mock_db.execute.return_value = screening_result
        mock_db.flush = AsyncMock()

        result = await service.score_screening_result(mock_screening.id, mock_db)

        # Should still work but with default document values
        assert result.success is True
        assert result.data is not None
