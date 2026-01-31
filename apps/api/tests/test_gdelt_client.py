"""Tests for GDELT API client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.adverse_media.gdelt_client import (
    GDELTArticle,
    GDELTClient,
    DEFAULT_SEARCH_TERMS,
)


class TestGDELTClient:
    """Test cases for GDELTClient."""

    @pytest.fixture
    def client(self) -> GDELTClient:
        """Create a GDELT client instance."""
        return GDELTClient(timeout=5.0)

    def test_default_search_terms(self, client: GDELTClient) -> None:
        """Test that default search terms are configured."""
        terms = client.search_terms
        assert "fraud" in terms
        assert "money laundering" in terms
        assert "sanctions" in terms

    def test_custom_search_terms(self) -> None:
        """Test custom search terms configuration."""
        custom_terms = ["terrorism", "bribery"]
        client = GDELTClient(search_terms=custom_terms)
        assert client.search_terms == custom_terms

    def test_build_query(self, client: GDELTClient) -> None:
        """Test query building."""
        query = client._build_query("John Smith")
        assert '"John Smith"' in query
        assert "fraud" in query
        assert "money laundering" in query

    def test_parse_article_complete(self, client: GDELTClient) -> None:
        """Test parsing a complete article."""
        raw = {
            "title": "CEO Arrested for Fraud",
            "url": "https://example.com/article",
            "domain": "example.com",
            "seendate": "20260115T120000Z",
        }
        article = client._parse_article(raw)

        assert article.title == "CEO Arrested for Fraud"
        assert article.url == "https://example.com/article"
        assert article.source == "example.com"
        assert article.published_date is not None
        assert article.published_date.year == 2026

    def test_parse_article_missing_fields(self, client: GDELTClient) -> None:
        """Test parsing article with missing fields."""
        raw = {"title": "Some Article"}
        article = client._parse_article(raw)

        assert article.title == "Some Article"
        assert article.url == ""
        assert article.source is None
        assert article.published_date is None

    def test_parse_article_invalid_date(self, client: GDELTClient) -> None:
        """Test parsing article with invalid date."""
        raw = {
            "title": "Article",
            "seendate": "invalid-date",
        }
        article = client._parse_article(raw)

        assert article.title == "Article"
        assert article.published_date is None

    @pytest.mark.asyncio
    async def test_search_returns_search_terms(self, client: GDELTClient) -> None:
        """Test that search returns the search terms used."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"articles": []}'
        mock_response.json.return_value = {"articles": []}
        mock_response.raise_for_status.return_value = None

        with patch(
            "src.services.adverse_media.gdelt_client.httpx.AsyncClient"
        ) as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance

            articles, terms = await client.search("Test Name")

            assert terms == DEFAULT_SEARCH_TERMS
            assert articles == []

    @pytest.mark.asyncio
    async def test_search_parses_articles(self, client: GDELTClient) -> None:
        """Test that search parses articles correctly."""
        mock_data = {
            "articles": [
                {
                    "title": "Article 1",
                    "url": "https://example.com/1",
                    "domain": "example.com",
                },
                {
                    "title": "Article 2",
                    "url": "https://example.com/2",
                    "domain": "news.com",
                },
            ]
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"articles": [...]}'
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status.return_value = None

        with patch(
            "src.services.adverse_media.gdelt_client.httpx.AsyncClient"
        ) as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance

            articles, terms = await client.search("Test Name", max_results=10)

            assert len(articles) == 2
            assert articles[0].title == "Article 1"
            assert articles[1].source == "news.com"

    @pytest.mark.asyncio
    async def test_search_handles_empty_response(self, client: GDELTClient) -> None:
        """Test handling of empty API response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b""  # Empty response
        mock_response.raise_for_status.return_value = None

        with patch(
            "src.services.adverse_media.gdelt_client.httpx.AsyncClient"
        ) as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance

            articles, terms = await client.search("Rare Name")

            assert articles == []
            assert terms == DEFAULT_SEARCH_TERMS

    @pytest.mark.asyncio
    async def test_search_handles_timeout(self, client: GDELTClient) -> None:
        """Test handling of API timeout."""
        import httpx

        with patch(
            "src.services.adverse_media.gdelt_client.httpx.AsyncClient"
        ) as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = httpx.TimeoutException("Timeout")
            mock_client.return_value.__aenter__.return_value = mock_instance

            articles, terms = await client.search("Test Name")

            assert articles == []
            assert terms == DEFAULT_SEARCH_TERMS

    @pytest.mark.asyncio
    async def test_search_handles_http_error(self, client: GDELTClient) -> None:
        """Test handling of HTTP errors."""
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch(
            "src.services.adverse_media.gdelt_client.httpx.AsyncClient"
        ) as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = httpx.HTTPStatusError(
                "Server Error",
                request=MagicMock(),
                response=mock_response,
            )
            mock_client.return_value.__aenter__.return_value = mock_instance

            articles, terms = await client.search("Test Name")

            assert articles == []
            assert terms == DEFAULT_SEARCH_TERMS

    @pytest.mark.asyncio
    async def test_search_skips_articles_without_title(
        self, client: GDELTClient
    ) -> None:
        """Test that articles without titles are skipped."""
        mock_data = {
            "articles": [
                {"title": "Valid Article", "url": "https://example.com/1"},
                {"title": "", "url": "https://example.com/2"},  # Empty title
                {"url": "https://example.com/3"},  # No title
            ]
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"articles": [...]}'
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status.return_value = None

        with patch(
            "src.services.adverse_media.gdelt_client.httpx.AsyncClient"
        ) as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance

            articles, _ = await client.search("Test Name")

            assert len(articles) == 1
            assert articles[0].title == "Valid Article"


class TestGDELTClientIntegration:
    """Integration tests for GDELT client (requires network access)."""

    @pytest.fixture
    def client(self) -> GDELTClient:
        """Create a GDELT client instance."""
        return GDELTClient(timeout=10.0)

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Integration test - requires network access")
    async def test_real_api_search(self, client: GDELTClient) -> None:
        """Test actual API search (skipped by default)."""
        articles, terms = await client.search("Bank of America", max_results=5)

        # Should return search terms regardless of results
        assert len(terms) > 0

        # May or may not find articles depending on recent news
        assert isinstance(articles, list)

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Integration test - requires network access")
    async def test_real_health_check(self, client: GDELTClient) -> None:
        """Test actual API health check (skipped by default)."""
        is_healthy = await client.health_check()
        assert isinstance(is_healthy, bool)
