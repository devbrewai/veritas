"""Adverse media scanning service.

Orchestrates GDELT search and sentiment analysis to identify
adverse media mentions for KYC/AML screening.
"""

import logging
import time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.document import Document
from src.models.screening_result import ScreeningResult
from src.schemas.adverse_media import (
    AdverseMediaArticle,
    AdverseMediaData,
    AdverseMediaResult,
)
from src.services.adverse_media.gdelt_client import GDELTClient
from src.services.adverse_media.sentiment import SentimentAnalyzer

logger = logging.getLogger(__name__)


class AdverseMediaService:
    """Service for adverse media scanning.

    Combines GDELT news search with VADER sentiment analysis
    to identify and classify negative media mentions.
    """

    def __init__(
        self,
        gdelt_timeout: float = 10.0,
        gdelt_search_terms: list[str] | None = None,
    ) -> None:
        """Initialize the adverse media service.

        Args:
            gdelt_timeout: Timeout for GDELT API requests.
            gdelt_search_terms: Custom search terms for GDELT.
        """
        self._gdelt_client = GDELTClient(
            timeout=gdelt_timeout,
            search_terms=gdelt_search_terms,
        )
        self._sentiment_analyzer = SentimentAnalyzer()
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the service (mark as ready)."""
        self._initialized = True
        logger.info("Adverse media service initialized")

    @property
    def is_ready(self) -> bool:
        """Check if service is ready."""
        return self._initialized

    async def check_gdelt_health(self) -> bool:
        """Check if GDELT API is accessible.

        Returns:
            True if GDELT is reachable, False otherwise.
        """
        return await self._gdelt_client.health_check()

    async def scan_name(
        self,
        name: str,
        max_results: int = 10,
    ) -> AdverseMediaResult:
        """Scan a name for adverse media mentions.

        Args:
            name: The name to search for (person or company).
            max_results: Maximum number of articles to return.

        Returns:
            AdverseMediaResult with articles and sentiment analysis.
        """
        start_time = time.time()

        try:
            # Search GDELT for articles
            articles, search_terms = await self._gdelt_client.search(
                name, max_results
            )

            # Analyze sentiment of each article title
            processed_articles: list[AdverseMediaArticle] = []
            negative_count = 0
            total_sentiment = 0.0

            for article in articles:
                score, category = self._sentiment_analyzer.analyze(article.title)

                if category.value == "negative":
                    negative_count += 1

                total_sentiment += score

                processed_articles.append(
                    AdverseMediaArticle(
                        title=article.title,
                        url=article.url,
                        source=article.source,
                        published_date=article.published_date,
                        sentiment_score=score,
                        sentiment_category=category,
                    )
                )

            # Calculate average sentiment
            avg_sentiment = total_sentiment / len(articles) if articles else 0.0

            processing_time_ms = (time.time() - start_time) * 1000

            return AdverseMediaResult(
                success=True,
                data=AdverseMediaData(
                    query_name=name,
                    articles_found=len(articles),
                    negative_mentions=negative_count,
                    average_sentiment=avg_sentiment,
                    articles=processed_articles,
                    search_terms_used=search_terms,
                ),
                processing_time_ms=processing_time_ms,
            )

        except Exception as e:
            logger.exception(f"Error scanning adverse media for '{name}': {e}")
            processing_time_ms = (time.time() - start_time) * 1000
            return AdverseMediaResult(
                success=False,
                errors=[str(e)],
                processing_time_ms=processing_time_ms,
            )

    async def scan_document(
        self,
        document_id: UUID,
        db: AsyncSession,
        max_results: int = 10,
        user_id: str | None = None,
    ) -> AdverseMediaResult:
        """Scan names from a processed document.

        Extracts the full name from document's extracted_data and
        performs adverse media scan. Updates associated screening
        result if one exists.

        Args:
            document_id: UUID of the document to scan.
            db: Database session.
            max_results: Maximum articles to return.
            user_id: User ID for multi-tenant filtering (optional for backward compat).

        Returns:
            AdverseMediaResult with scan findings.
        """
        start_time = time.time()

        # Get document with user_id filter if provided
        query = select(Document).where(Document.id == document_id)
        if user_id is not None:
            query = query.where(Document.user_id == user_id)
        result = await db.execute(query)
        document = result.scalar_one_or_none()

        if not document:
            return AdverseMediaResult(
                success=False,
                errors=[f"Document not found: {document_id}"],
                processing_time_ms=(time.time() - start_time) * 1000,
            )

        if not document.extracted_data:
            return AdverseMediaResult(
                success=False,
                errors=["Document has no extracted data"],
                processing_time_ms=(time.time() - start_time) * 1000,
            )

        # Extract name from document data
        extracted = document.extracted_data
        full_name = extracted.get("full_name")

        # Try to build name from parts if full_name not available
        if not full_name:
            surname = extracted.get("surname", "")
            given_names = extracted.get("given_names", "")
            full_name = f"{given_names} {surname}".strip()

        if not full_name:
            return AdverseMediaResult(
                success=False,
                errors=["No name found in document extracted data"],
                processing_time_ms=(time.time() - start_time) * 1000,
            )

        # Scan the name
        scan_result = await self.scan_name(full_name, max_results)

        # Update screening result if it exists and scan was successful
        if scan_result.success and scan_result.data:
            await self._update_screening_result(
                document_id,
                scan_result.data,
                db,
            )

        return scan_result

    async def _update_screening_result(
        self,
        document_id: UUID,
        scan_data: AdverseMediaData,
        db: AsyncSession,
    ) -> None:
        """Update existing screening result with adverse media findings.

        Args:
            document_id: Document UUID.
            scan_data: Adverse media scan results.
            db: Database session.
        """
        result = await db.execute(
            select(ScreeningResult).where(
                ScreeningResult.document_id == document_id
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.adverse_media_count = scan_data.negative_mentions
            existing.adverse_media_summary = {
                "articles_found": scan_data.articles_found,
                "negative_mentions": scan_data.negative_mentions,
                "average_sentiment": scan_data.average_sentiment,
                "search_terms": scan_data.search_terms_used,
                "top_articles": [
                    {
                        "title": a.title,
                        "url": a.url,
                        "source": a.source,
                        "sentiment": a.sentiment_score,
                        "category": a.sentiment_category.value,
                    }
                    for a in scan_data.articles[:5]  # Top 5 articles
                ],
            }
            await db.flush()
            logger.info(
                f"Updated screening result {existing.id} with adverse media: "
                f"{scan_data.negative_mentions} negative mentions"
            )


# Global service instance
adverse_media_service = AdverseMediaService()
