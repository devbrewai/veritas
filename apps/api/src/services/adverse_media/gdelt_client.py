"""GDELT API async client for news article search.

GDELT (Global Database of Events, Language, and Tone) provides a
comprehensive news database that can be searched for adverse media
mentions related to KYC/AML screening.
"""

import logging
from dataclasses import dataclass
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

# GDELT DOC 2.0 API endpoint
GDELT_API_BASE = "https://api.gdeltproject.org/api/v2/doc/doc"

# Default search terms for adverse media
DEFAULT_SEARCH_TERMS = [
    "fraud",
    "scam",
    "money laundering",
    "sanctions",
    "corruption",
    "criminal",
    "indicted",
    "arrested",
]


@dataclass
class GDELTArticle:
    """Article result from GDELT search."""

    title: str
    url: str
    source: str | None
    published_date: datetime | None


class GDELTClient:
    """Async client for GDELT DOC 2.0 API.

    Searches for adverse media mentions using the GDELT news database.
    Free tier allows 250 queries per day.
    """

    def __init__(
        self,
        timeout: float = 10.0,
        search_terms: list[str] | None = None,
    ) -> None:
        """Initialize the GDELT client.

        Args:
            timeout: Request timeout in seconds.
            search_terms: Custom search terms for adverse media.
                         Defaults to fraud, scam, money laundering, etc.
        """
        self.timeout = timeout
        self._search_terms = search_terms or DEFAULT_SEARCH_TERMS

    @property
    def search_terms(self) -> list[str]:
        """Return the configured search terms."""
        return self._search_terms.copy()

    def _build_query(self, name: str) -> str:
        """Build the GDELT search query.

        Args:
            name: The name to search for.

        Returns:
            Query string in GDELT format.
        """
        # Quote the name for exact phrase matching
        # Add OR-joined adverse media terms
        terms_query = " OR ".join(self._search_terms)
        return f'"{name}" ({terms_query})'

    def _parse_article(self, article_data: dict) -> GDELTArticle:
        """Parse a single article from GDELT response.

        Args:
            article_data: Raw article data from API.

        Returns:
            Parsed GDELTArticle instance.
        """
        published_date = None
        if date_str := article_data.get("seendate"):
            try:
                # GDELT date format: YYYYMMDDTHHMMSSZ
                published_date = datetime.strptime(date_str[:15], "%Y%m%dT%H%M%S")
            except ValueError:
                logger.debug(f"Could not parse date: {date_str}")

        return GDELTArticle(
            title=article_data.get("title", ""),
            url=article_data.get("url", ""),
            source=article_data.get("domain"),
            published_date=published_date,
        )

    async def search(
        self,
        name: str,
        max_results: int = 10,
    ) -> tuple[list[GDELTArticle], list[str]]:
        """Search GDELT for adverse media mentions.

        Args:
            name: The name to search for (person or company).
            max_results: Maximum number of articles to return.

        Returns:
            Tuple of (articles, search_terms_used).
        """
        query = self._build_query(name)

        params = {
            "query": query,
            "mode": "artlist",
            "maxrecords": str(max_results),
            "format": "json",
            "sort": "datedesc",  # Most recent first
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(GDELT_API_BASE, params=params)
                response.raise_for_status()

                # Handle empty response (no results)
                if not response.content:
                    return [], self._search_terms

                data = response.json()

            except httpx.TimeoutException:
                logger.warning(f"GDELT API timeout for query: {name}")
                return [], self._search_terms

            except httpx.HTTPStatusError as e:
                logger.warning(f"GDELT API HTTP error: {e.response.status_code}")
                return [], self._search_terms

            except httpx.RequestError as e:
                logger.warning(f"GDELT API request error: {e}")
                return [], self._search_terms

            except Exception as e:
                logger.warning(f"GDELT API unexpected error: {e}")
                return [], self._search_terms

        # Parse articles from response
        articles = []
        raw_articles = data.get("articles", [])

        for raw_article in raw_articles:
            try:
                article = self._parse_article(raw_article)
                if article.title:  # Skip articles without titles
                    articles.append(article)
            except Exception as e:
                logger.debug(f"Error parsing article: {e}")
                continue

        return articles, self._search_terms

    async def health_check(self) -> bool:
        """Check if GDELT API is reachable.

        Returns:
            True if API is accessible, False otherwise.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Simple query to check connectivity
                response = await client.get(
                    GDELT_API_BASE,
                    params={"query": "test", "mode": "artlist", "maxrecords": "1"},
                )
                return response.status_code == 200
        except Exception:
            return False
