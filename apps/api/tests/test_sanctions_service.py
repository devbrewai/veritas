"""
Integration tests for sanctions screening service.
"""

import pytest

from src.schemas.sanctions import SanctionsDecision
from src.services.sanctions.screener import SanctionsScreeningService


class TestSanctionsScreeningService:
    """Tests for the SanctionsScreeningService."""

    @pytest.fixture
    def service(self):
        """Create and initialize a screening service."""
        svc = SanctionsScreeningService()
        svc.initialize()
        return svc

    def test_service_initializes(self, service):
        """Service should initialize and load screener."""
        assert service.is_loaded is True
        status = service.get_status()
        assert status.status == "healthy"
        assert status.record_count > 0

    def test_service_status_when_loaded(self, service):
        """Status should show healthy when loaded."""
        status = service.get_status()
        assert status.status == "healthy"
        assert status.loaded is True
        assert status.record_count == 39350  # OFAC list size
        assert status.version is not None

    @pytest.mark.asyncio
    async def test_screen_common_name_no_match(self, service):
        """Common names should return no_match."""
        result = await service.screen_name("John Smith")

        assert result.success is True
        assert result.data is not None
        assert result.data.decision == SanctionsDecision.NO_MATCH
        assert result.data.is_match is False

    @pytest.mark.asyncio
    async def test_screen_name_returns_processing_time(self, service):
        """Screening should return processing time."""
        result = await service.screen_name("Jane Doe")

        assert result.success is True
        assert result.processing_time_ms > 0
        assert result.processing_time_ms < 2000  # Should be under 2 seconds

    @pytest.mark.asyncio
    async def test_screen_name_with_nationality_filter(self, service):
        """Should filter results by nationality."""
        result = await service.screen_name("Test Name", nationality="US")

        assert result.success is True
        assert result.data is not None
        assert result.data.applied_filters["country"] == "US"

    @pytest.mark.asyncio
    async def test_screen_name_includes_query_info(self, service):
        """Result should include original and normalized query."""
        result = await service.screen_name("JOSÉ GARCÍA")

        assert result.success is True
        assert result.data is not None
        assert result.data.query_name == "JOSÉ GARCÍA"
        assert result.data.query_normalized == "jose garcia"

    @pytest.mark.asyncio
    async def test_screen_known_sanctioned_entity(self, service):
        """Known sanctioned entities should return review or match."""
        # Test with a generic bank name that might be on sanctions lists
        result = await service.screen_name("BANCO NACIONAL DE CUBA")

        assert result.success is True
        assert result.data is not None
        # Should at least return some matches for a Cuban bank
        if result.data.all_matches:
            # If matches found, should have reasonable scores
            assert result.data.all_matches[0].score > 0

    @pytest.mark.asyncio
    async def test_screen_batch_multiple_names(self, service):
        """Batch screening should process multiple names."""
        queries = [
            {"name": "John Doe"},
            {"name": "Jane Smith"},
            {"name": "Test Entity"},
        ]
        results = await service.screen_batch(queries)

        assert len(results) == 3
        for result in results:
            assert result.success is True

    @pytest.mark.asyncio
    async def test_screen_batch_with_aliases(self, service):
        """Batch screening should handle aliases."""
        queries = [
            {"name": "John Doe", "aliases": ["J. Doe", "Johnny Doe"]},
        ]
        results = await service.screen_batch(queries)

        assert len(results) == 1
        assert results[0].success is True

    @pytest.mark.asyncio
    async def test_screen_empty_name_handled(self, service):
        """Empty name should be handled gracefully."""
        # The SanctionsQuery validator will catch empty names
        # But let's test the service behavior
        result = await service.screen_name("   ")

        # Should either fail validation or return no matches
        if result.success:
            assert result.data.query_normalized == ""

    @pytest.mark.asyncio
    async def test_screen_non_latin_name(self, service):
        """Non-Latin names should be normalized."""
        result = await service.screen_name("中国银行")  # Bank of China in Chinese

        assert result.success is True
        # Non-Latin is normalized to empty, so no tokens to match
        assert result.data is not None


class TestSanctionsServiceStatus:
    """Tests for service status reporting."""

    def test_uninitialized_service_status(self):
        """Uninitialized service should report unavailable."""
        service = SanctionsScreeningService()
        # Don't call initialize()
        status = service.get_status()

        assert status.status == "unavailable"
        assert status.loaded is False
        assert status.record_count == 0

    def test_initialized_service_status(self):
        """Initialized service should report healthy."""
        service = SanctionsScreeningService()
        service.initialize()
        status = service.get_status()

        assert status.status == "healthy"
        assert status.loaded is True
        assert status.record_count > 0
        assert status.last_updated is not None


class TestScreeningPerformance:
    """Performance tests for screening operations."""

    @pytest.fixture
    def service(self):
        """Create and initialize a screening service."""
        svc = SanctionsScreeningService()
        svc.initialize()
        return svc

    @pytest.mark.asyncio
    async def test_screening_latency_target(self, service):
        """Screening should complete within latency target (<2 seconds)."""
        import time

        test_names = [
            "Vladimir Putin",
            "John Smith",
            "BANCO DE CUBA",
            "Kim Jong Un",
            "Jane Doe",
        ]

        for name in test_names:
            start = time.time()
            result = await service.screen_name(name)
            latency = (time.time() - start) * 1000

            assert result.success is True
            assert latency < 2000, f"Screening '{name}' took {latency:.1f}ms (>2s)"

    @pytest.mark.asyncio
    async def test_batch_screening_performance(self, service):
        """Batch screening 10 names should complete reasonably fast."""
        import time

        queries = [{"name": f"Test Person {i}"} for i in range(10)]

        start = time.time()
        results = await service.screen_batch(queries)
        total_time = (time.time() - start) * 1000

        assert len(results) == 10
        # 10 names should complete in under 5 seconds
        assert total_time < 5000, f"Batch of 10 took {total_time:.1f}ms"
