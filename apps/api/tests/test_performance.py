"""Performance tests for PRD acceptance criteria.

Validates timing targets:
- Sanctions screening: <3 seconds per name
- Adverse media scan: <5 seconds (mocked GDELT)
- Risk scoring: <500ms per score
- End-to-end pipeline: <15 seconds total
"""

import time
from unittest.mock import AsyncMock, patch

import pytest

from src.services.adverse_media.scanner import AdverseMediaService
from src.services.risk.features import RiskFeatures
from src.services.risk.scorer import RiskScoringService
from src.services.sanctions.screener import SanctionsScreeningService


class TestSanctionsPerformance:
    """PRD: Sanctions screening returns results in <3 seconds."""

    @pytest.fixture
    def service(self):
        svc = SanctionsScreeningService()
        svc.initialize()
        if not svc.is_loaded:
            pytest.skip("Sanctions screener pickle not available")
        return svc

    @pytest.mark.asyncio
    async def test_single_name_under_3_seconds(self, service):
        """Each name screens in <3 seconds (PRD target)."""
        names = [
            "Vladimir Putin",
            "John Smith",
            "BANCO NACIONAL DE CUBA",
            "Kim Jong Un",
            "Jane Doe",
            "Ali Hassan",
            "Maria Rodriguez",
        ]
        for name in names:
            start = time.perf_counter()
            result = await service.screen_name(name)
            elapsed_ms = (time.perf_counter() - start) * 1000

            assert result.success, f"Screening failed for '{name}'"
            assert elapsed_ms < 3000, (
                f"Sanctions screening '{name}' took {elapsed_ms:.0f}ms (PRD limit: 3000ms)"
            )

    @pytest.mark.asyncio
    async def test_batch_10_names_under_10_seconds(self, service):
        """Batch of 10 names completes in <10 seconds."""
        queries = [{"name": f"Test Person {i}"} for i in range(10)]

        start = time.perf_counter()
        results = await service.screen_batch(queries)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert len(results) == 10
        assert all(r.success for r in results)
        assert elapsed_ms < 10000, (
            f"Batch of 10 took {elapsed_ms:.0f}ms (limit: 10000ms)"
        )


class TestAdverseMediaPerformance:
    """PRD: Adverse media search completes in <5 seconds."""

    @pytest.mark.asyncio
    async def test_scan_name_under_5_seconds_with_mock(self):
        """Adverse media scan completes in <5 seconds (mocked GDELT)."""
        service = AdverseMediaService(gdelt_timeout=5.0)
        service.initialize()

        mock_articles = [
            type("Article", (), {
                "title": f"Article about Test Person {i}",
                "url": f"https://example.com/{i}",
                "source": "example.com",
                "published_date": None,
            })()
            for i in range(5)
        ]

        with patch.object(
            service._gdelt_client,
            "search",
            new_callable=AsyncMock,
            return_value=(mock_articles, ["fraud", "scam"]),
        ):
            start = time.perf_counter()
            result = await service.scan_name("Test Person", max_results=10)
            elapsed_ms = (time.perf_counter() - start) * 1000

        assert result.success
        assert result.data is not None
        assert result.data.articles_found == 5
        assert elapsed_ms < 5000, (
            f"Adverse media scan took {elapsed_ms:.0f}ms (PRD limit: 5000ms)"
        )

    @pytest.mark.asyncio
    async def test_gdelt_timeout_respects_5_second_limit(self):
        """GDELT client timeout defaults to 5 seconds."""
        service = AdverseMediaService()
        assert service._gdelt_client.timeout == 5.0


class TestRiskScoringPerformance:
    """PRD: Risk scoring should be fast (part of <15s e2e target)."""

    @pytest.fixture
    def service(self):
        svc = RiskScoringService()
        svc.initialize()
        if not svc.is_ready:
            pytest.skip("Risk model not available")
        return svc

    def test_score_under_500ms(self, service):
        """Single risk score completes in <500ms."""
        profiles = [
            RiskFeatures(
                document_quality=0.95, sanctions_score=0.05,
                sanctions_match=0, adverse_media_count=0,
                adverse_media_sentiment=0.0, country_risk=0.1,
                document_age_days=30,
            ),
            RiskFeatures(
                document_quality=0.4, sanctions_score=0.85,
                sanctions_match=1, adverse_media_count=5,
                adverse_media_sentiment=-0.7, country_risk=0.8,
                document_age_days=1000,
            ),
            RiskFeatures(
                document_quality=0.7, sanctions_score=0.45,
                sanctions_match=0, adverse_media_count=2,
                adverse_media_sentiment=-0.2, country_risk=0.5,
                document_age_days=365,
            ),
        ]
        for features in profiles:
            start = time.perf_counter()
            result = service.score(features)
            elapsed_ms = (time.perf_counter() - start) * 1000

            assert result.success, f"Scoring failed: {result.errors}"
            assert elapsed_ms < 500, (
                f"Risk scoring took {elapsed_ms:.0f}ms (limit: 500ms)"
            )

    def test_batch_100_scores_under_5_seconds(self, service):
        """100 risk scores complete in <5 seconds."""
        features = RiskFeatures(
            document_quality=0.9, sanctions_score=0.1,
            sanctions_match=0, adverse_media_count=0,
            adverse_media_sentiment=0.0, country_risk=0.1,
            document_age_days=90,
        )

        start = time.perf_counter()
        results = [service.score(features) for _ in range(100)]
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert all(r.success for r in results)
        assert elapsed_ms < 5000, (
            f"100 risk scores took {elapsed_ms:.0f}ms (limit: 5000ms)"
        )


class TestEndToEndPerformance:
    """PRD: End-to-end KYC processing in <15 seconds total."""

    @pytest.mark.asyncio
    async def test_pipeline_services_combined_under_15_seconds(self):
        """Full pipeline (sanctions + adverse media + risk) under 15 seconds.

        Simulates the pipeline without OCR (OCR depends on Tesseract and
        real images). Tests the screening + adverse media + risk chain
        which is the variable-time portion of the pipeline.
        """
        sanctions_svc = SanctionsScreeningService()
        sanctions_svc.initialize()
        if not sanctions_svc.is_loaded:
            pytest.skip("Sanctions screener not available")

        risk_svc = RiskScoringService()
        risk_svc.initialize()
        if not risk_svc.is_ready:
            pytest.skip("Risk model not available")

        adverse_svc = AdverseMediaService(gdelt_timeout=5.0)
        adverse_svc.initialize()

        mock_articles = [
            type("Article", (), {
                "title": "Fraud investigation into Test Person",
                "url": "https://example.com/1",
                "source": "example.com",
                "published_date": None,
            })()
        ]

        start = time.perf_counter()

        # Step 1: Sanctions screening
        sanctions_result = await sanctions_svc.screen_name(
            "Test Person", nationality="US"
        )
        assert sanctions_result.success

        # Step 2: Adverse media (mocked GDELT)
        with patch.object(
            adverse_svc._gdelt_client,
            "search",
            new_callable=AsyncMock,
            return_value=(mock_articles, ["fraud", "scam"]),
        ):
            adverse_result = await adverse_svc.scan_name("Test Person")
        assert adverse_result.success

        # Step 3: Risk scoring
        sanctions_score = sanctions_result.confidence or 0.0
        is_match = (
            sanctions_result.data.is_match
            if sanctions_result.data
            else False
        )
        adverse_count = (
            adverse_result.data.negative_mentions
            if adverse_result.data
            else 0
        )
        adverse_sentiment = (
            adverse_result.data.average_sentiment
            if adverse_result.data
            else 0.0
        )

        features = RiskFeatures(
            document_quality=0.95,
            sanctions_score=sanctions_score,
            sanctions_match=1 if is_match else 0,
            adverse_media_count=adverse_count,
            adverse_media_sentiment=adverse_sentiment,
            country_risk=0.1,
            document_age_days=30,
        )
        risk_result = risk_svc.score(features)
        assert risk_result.success

        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 15000, (
            f"Pipeline (sanctions + adverse media + risk) took "
            f"{elapsed_ms:.0f}ms (PRD limit: 15000ms)"
        )
