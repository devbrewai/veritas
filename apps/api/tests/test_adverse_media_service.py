"""Tests for adverse media scanning service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.schemas.adverse_media import SentimentCategory
from src.services.adverse_media.gdelt_client import GDELTArticle
from src.services.adverse_media.scanner import AdverseMediaService


class TestAdverseMediaService:
    """Test cases for AdverseMediaService."""

    @pytest.fixture
    def service(self) -> AdverseMediaService:
        """Create an adverse media service instance."""
        return AdverseMediaService(gdelt_timeout=5.0)

    @pytest.mark.asyncio
    async def test_scan_name_success(self, service: AdverseMediaService) -> None:
        """Test successful name scan with articles."""
        mock_articles = [
            GDELTArticle(
                title="CEO arrested for fraud",
                url="https://example.com/1",
                source="example.com",
                published_date=None,
            ),
            GDELTArticle(
                title="Company wins award",
                url="https://example.com/2",
                source="news.com",
                published_date=None,
            ),
        ]

        with patch.object(
            service._gdelt_client, "search", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = (mock_articles, ["fraud", "scam"])

            result = await service.scan_name("Test Company")

            assert result.success is True
            assert result.data is not None
            assert result.data.query_name == "Test Company"
            assert result.data.articles_found == 2
            assert result.data.negative_mentions >= 1
            assert len(result.data.articles) == 2
            assert result.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_scan_name_no_articles(self, service: AdverseMediaService) -> None:
        """Test scan with no articles found."""
        with patch.object(
            service._gdelt_client, "search", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = ([], ["fraud", "scam"])

            result = await service.scan_name("Unknown Person")

            assert result.success is True
            assert result.data is not None
            assert result.data.articles_found == 0
            assert result.data.negative_mentions == 0
            assert result.data.average_sentiment == 0.0
            assert result.data.articles == []

    @pytest.mark.asyncio
    async def test_scan_name_handles_error(self, service: AdverseMediaService) -> None:
        """Test error handling in scan_name."""
        with patch.object(
            service._gdelt_client, "search", new_callable=AsyncMock
        ) as mock_search:
            mock_search.side_effect = Exception("API Error")

            result = await service.scan_name("Test Name")

            assert result.success is False
            assert "API Error" in result.errors[0]
            assert result.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_scan_name_sentiment_analysis(
        self, service: AdverseMediaService
    ) -> None:
        """Test sentiment analysis on articles."""
        mock_articles = [
            GDELTArticle(
                title="Terrible scandal rocks company",
                url="https://example.com/1",
                source="news.com",
                published_date=None,
            ),
            GDELTArticle(
                title="Company faces fraud charges",
                url="https://example.com/2",
                source="news.com",
                published_date=None,
            ),
        ]

        with patch.object(
            service._gdelt_client, "search", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = (mock_articles, ["fraud"])

            result = await service.scan_name("Bad Company")

            assert result.success is True
            assert result.data is not None
            # Both articles should be classified as negative
            assert result.data.negative_mentions == 2
            # Average sentiment should be negative
            assert result.data.average_sentiment < 0
            # Each article should have sentiment category
            for article in result.data.articles:
                assert article.sentiment_category == SentimentCategory.NEGATIVE

    @pytest.mark.asyncio
    async def test_scan_name_returns_search_terms(
        self, service: AdverseMediaService
    ) -> None:
        """Test that search terms are included in result."""
        search_terms = ["fraud", "money laundering", "sanctions"]

        with patch.object(
            service._gdelt_client, "search", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = ([], search_terms)

            result = await service.scan_name("Test Name")

            assert result.success is True
            assert result.data is not None
            assert result.data.search_terms_used == search_terms


class TestAdverseMediaServiceDocumentScan:
    """Test cases for document scanning."""

    @pytest.fixture
    def service(self) -> AdverseMediaService:
        """Create an adverse media service instance."""
        return AdverseMediaService(gdelt_timeout=5.0)

    @pytest.mark.asyncio
    async def test_scan_document_not_found(
        self, service: AdverseMediaService
    ) -> None:
        """Test scanning non-existent document."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        document_id = uuid4()
        result = await service.scan_document(document_id, mock_db)

        assert result.success is False
        assert "not found" in result.errors[0].lower()

    @pytest.mark.asyncio
    async def test_scan_document_no_extracted_data(
        self, service: AdverseMediaService
    ) -> None:
        """Test scanning document without extracted data."""
        mock_document = MagicMock()
        mock_document.extracted_data = None

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_document
        mock_db.execute.return_value = mock_result

        document_id = uuid4()
        result = await service.scan_document(document_id, mock_db)

        assert result.success is False
        assert "no extracted data" in result.errors[0].lower()

    @pytest.mark.asyncio
    async def test_scan_document_no_name(
        self, service: AdverseMediaService
    ) -> None:
        """Test scanning document without name in extracted data."""
        mock_document = MagicMock()
        mock_document.extracted_data = {"address": "123 Main St"}

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_document
        mock_db.execute.return_value = mock_result

        document_id = uuid4()
        result = await service.scan_document(document_id, mock_db)

        assert result.success is False
        assert "no name found" in result.errors[0].lower()

    @pytest.mark.asyncio
    async def test_scan_document_with_full_name(
        self, service: AdverseMediaService
    ) -> None:
        """Test scanning document with full_name field."""
        mock_document = MagicMock()
        mock_document.id = uuid4()
        mock_document.extracted_data = {"full_name": "John Smith"}

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_document
        mock_db.execute.return_value = mock_result

        with patch.object(
            service._gdelt_client, "search", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = ([], ["fraud"])

            result = await service.scan_document(mock_document.id, mock_db)

            assert result.success is True
            mock_search.assert_called_once()
            call_args = mock_search.call_args[0]
            assert call_args[0] == "John Smith"

    @pytest.mark.asyncio
    async def test_scan_document_builds_name_from_parts(
        self, service: AdverseMediaService
    ) -> None:
        """Test scanning document with surname and given_names."""
        mock_document = MagicMock()
        mock_document.id = uuid4()
        mock_document.extracted_data = {
            "surname": "DOE",
            "given_names": "JANE MARIE",
        }

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_document
        mock_db.execute.return_value = mock_result

        with patch.object(
            service._gdelt_client, "search", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = ([], ["fraud"])

            result = await service.scan_document(mock_document.id, mock_db)

            assert result.success is True
            mock_search.assert_called_once()
            call_args = mock_search.call_args[0]
            assert call_args[0] == "JANE MARIE DOE"
