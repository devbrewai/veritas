"""Tests for document age calculation in risk scoring."""

from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest

from src.services.risk.scorer import RiskScoringService


class TestDocumentAgeExtraction:
    """Test document age calculation from issue_date and expiry_date."""

    @pytest.fixture
    def service(self) -> RiskScoringService:
        """Create a risk scoring service."""
        return RiskScoringService()

    def test_uses_issue_date_when_available(self, service: RiskScoringService) -> None:
        """Test that issue_date is used when set on document."""
        # Document issued 2 years ago
        issue_date = date.today() - timedelta(days=730)

        document = MagicMock()
        document.issue_date = issue_date
        document.ocr_confidence = 0.9
        document.extracted_data = {}

        screening = MagicMock()
        screening.sanctions_score = 0.1
        screening.sanctions_match = False
        screening.adverse_media_count = 0
        screening.adverse_media_summary = None

        features = service._extract_features(screening, document)

        # Should be approximately 730 days (within 1 day tolerance)
        assert 729 <= features.document_age_days <= 731

    def test_fallback_to_expiry_date(self, service: RiskScoringService) -> None:
        """Test fallback calculation from expiry_date when issue_date is None."""
        # Expiry date 8 years from now
        # Implies issue date was 2 years ago (10-year validity)
        expiry_date = date.today() + timedelta(days=365 * 8)

        document = MagicMock()
        document.issue_date = None
        document.ocr_confidence = 0.9
        document.extracted_data = {"expiry_date": expiry_date.isoformat()}

        screening = MagicMock()
        screening.sanctions_score = 0.1
        screening.sanctions_match = False
        screening.adverse_media_count = 0
        screening.adverse_media_summary = None

        features = service._extract_features(screening, document)

        # Should be approximately 730 days (2 years old, within tolerance)
        assert 700 <= features.document_age_days <= 760

    def test_no_issue_date_no_expiry_defaults_to_zero(
        self, service: RiskScoringService
    ) -> None:
        """Test that age defaults to 0 when neither issue_date nor expiry_date available."""
        document = MagicMock()
        document.issue_date = None
        document.ocr_confidence = 0.9
        document.extracted_data = {}

        screening = MagicMock()
        screening.sanctions_score = 0.1
        screening.sanctions_match = False
        screening.adverse_media_count = 0
        screening.adverse_media_summary = None

        features = service._extract_features(screening, document)

        assert features.document_age_days == 0

    def test_invalid_expiry_date_defaults_to_zero(
        self, service: RiskScoringService
    ) -> None:
        """Test that invalid expiry_date string defaults to 0."""
        document = MagicMock()
        document.issue_date = None
        document.ocr_confidence = 0.9
        document.extracted_data = {"expiry_date": "invalid-date"}

        screening = MagicMock()
        screening.sanctions_score = 0.1
        screening.sanctions_match = False
        screening.adverse_media_count = 0
        screening.adverse_media_summary = None

        features = service._extract_features(screening, document)

        assert features.document_age_days == 0

    def test_old_document_high_age(self, service: RiskScoringService) -> None:
        """Test that old documents have high age values."""
        # Document issued 9 years ago (expiry in 1 year)
        expiry_date = date.today() + timedelta(days=365)

        document = MagicMock()
        document.issue_date = None
        document.ocr_confidence = 0.9
        document.extracted_data = {"expiry_date": expiry_date.isoformat()}

        screening = MagicMock()
        screening.sanctions_score = 0.1
        screening.sanctions_match = False
        screening.adverse_media_count = 0
        screening.adverse_media_summary = None

        features = service._extract_features(screening, document)

        # Should be approximately 9 years (3285 days)
        assert features.document_age_days > 3000

    def test_new_document_low_age(self, service: RiskScoringService) -> None:
        """Test that new documents have low age values."""
        # Document issued recently (expiry in ~10 years)
        expiry_date = date.today() + timedelta(days=365 * 10 - 30)

        document = MagicMock()
        document.issue_date = None
        document.ocr_confidence = 0.9
        document.extracted_data = {"expiry_date": expiry_date.isoformat()}

        screening = MagicMock()
        screening.sanctions_score = 0.1
        screening.sanctions_match = False
        screening.adverse_media_count = 0
        screening.adverse_media_summary = None

        features = service._extract_features(screening, document)

        # Should be approximately 30 days old
        assert features.document_age_days < 100

    def test_no_document_defaults_to_zero(self, service: RiskScoringService) -> None:
        """Test that missing document defaults age to 0."""
        screening = MagicMock()
        screening.sanctions_score = 0.1
        screening.sanctions_match = False
        screening.adverse_media_count = 0
        screening.adverse_media_summary = None

        features = service._extract_features(screening, None)

        assert features.document_age_days == 0

    def test_expired_document_still_calculates_age(
        self, service: RiskScoringService
    ) -> None:
        """Test that expired documents still get age calculated."""
        # Document expired 1 year ago (issued 11 years ago)
        expiry_date = date.today() - timedelta(days=365)

        document = MagicMock()
        document.issue_date = None
        document.ocr_confidence = 0.9
        document.extracted_data = {"expiry_date": expiry_date.isoformat()}

        screening = MagicMock()
        screening.sanctions_score = 0.1
        screening.sanctions_match = False
        screening.adverse_media_count = 0
        screening.adverse_media_summary = None

        features = service._extract_features(screening, document)

        # Should be approximately 11 years (4015 days)
        assert features.document_age_days > 3800
