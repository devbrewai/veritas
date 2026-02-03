"""
Sanctions screening service.

Orchestrates sanctions screening operations including loading the screener,
performing name screening, and managing screening results.
"""

import logging
import pickle
import sys
import time
from datetime import datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.models.document import Document
from src.models.screening_result import ScreeningResult
from src.schemas.sanctions import (
    SanctionsDecision,
    SanctionsMatchData,
    SanctionsScreeningData,
    SanctionsScreeningResult,
    SanctionsServiceStatus,
)
from src.services.sanctions.matcher import (
    SanctionsMatcher,
    SanctionsQuery,
)
from src.services.sanctions.text_utils import normalize_text

logger = logging.getLogger(__name__)
settings = get_settings()


def _setup_pickle_compatibility():
    """
    Set up module aliases for loading Sentinel pickle files.

    The pickle was created with packages.compliance.* module structure,
    so we need to create aliases to our new module paths.
    """
    import src.services.sanctions.text_utils as text_utils
    import src.services.sanctions.matcher as matcher

    class FakeModule:
        pass

    # Create the packages.compliance module structure
    packages = FakeModule()
    packages.compliance = FakeModule()
    packages.compliance.sanctions = text_utils
    packages.compliance.sanctions_api = matcher

    sys.modules["packages"] = packages
    sys.modules["packages.compliance"] = packages.compliance
    sys.modules["packages.compliance.sanctions"] = packages.compliance.sanctions
    sys.modules["packages.compliance.sanctions_api"] = packages.compliance.sanctions_api


class SanctionsScreeningService:
    """
    Main service for sanctions screening operations.

    This service loads the pre-built screener on initialization and provides
    methods for screening names, documents, and batches of queries.
    """

    def __init__(self):
        """Initialize the service (screener loaded separately via initialize())."""
        self._matcher: SanctionsMatcher | None = None
        self._loaded: bool = False
        self._record_count: int = 0
        self._version: str = "unknown"
        self._last_updated: datetime | None = None

    def initialize(self) -> None:
        """
        Load the sanctions screener from pickle file.

        This should be called during application startup.
        """
        if not settings.SANCTIONS_ENABLED:
            logger.info("Sanctions screening is disabled")
            return

        pickle_path = Path(settings.SANCTIONS_PICKLE_PATH)
        if not pickle_path.exists():
            logger.error(f"Sanctions pickle not found at: {pickle_path}")
            return

        try:
            logger.info(f"Loading sanctions screener from: {pickle_path}")
            start_time = time.time()

            # Set up module aliases for pickle compatibility
            _setup_pickle_compatibility()

            # Load the pickle
            with open(pickle_path, "rb") as f:
                self._matcher = pickle.load(f)

            self._loaded = True
            self._record_count = len(self._matcher.sanctions_index)
            self._version = self._matcher.version
            self._last_updated = datetime.utcnow()

            load_time_ms = (time.time() - start_time) * 1000
            logger.info(
                f"Loaded sanctions screener with {self._record_count} records "
                f"in {load_time_ms:.1f}ms"
            )

        except Exception as e:
            logger.exception(f"Failed to load sanctions screener: {e}")
            self._loaded = False

    @property
    def is_loaded(self) -> bool:
        """Check if the screener is loaded and ready."""
        return self._loaded and self._matcher is not None

    def get_status(self) -> SanctionsServiceStatus:
        """Get the current service status."""
        if not settings.SANCTIONS_ENABLED:
            return SanctionsServiceStatus(
                status="unavailable",
                loaded=False,
                record_count=0,
                version="disabled",
                last_updated=None,
                cache_enabled=False,
            )

        if not self.is_loaded:
            return SanctionsServiceStatus(
                status="unavailable",
                loaded=False,
                record_count=0,
                version="not_loaded",
                last_updated=None,
                cache_enabled=False,
            )

        return SanctionsServiceStatus(
            status="healthy",
            loaded=True,
            record_count=self._record_count,
            version=self._version,
            last_updated=self._last_updated,
            cache_enabled=False,  # Redis caching not implemented yet
        )

    async def screen_name(
        self,
        name: str,
        aliases: list[str] | None = None,
        nationality: str | None = None,
        top_k: int = 3,
    ) -> SanctionsScreeningResult:
        """
        Screen a name against sanctions lists.

        Args:
            name: The name to screen
            aliases: Optional list of name aliases to also check
            nationality: Optional country code to filter results
            top_k: Number of top matches to return

        Returns:
            SanctionsScreeningResult with match details
        """
        start_time = time.time()

        if not self.is_loaded:
            return SanctionsScreeningResult(
                success=False,
                errors=["Sanctions screener not loaded"],
                processing_time_ms=0,
            )

        try:
            # Screen the primary name
            query = SanctionsQuery(
                name=name,
                country=nationality,
                top_k=top_k,
            )
            response = self._matcher.match(query)

            # If aliases provided, screen them too and merge results
            all_matches = list(response.top_matches)
            if aliases:
                for alias in aliases[:5]:  # Limit to 5 aliases
                    alias_query = SanctionsQuery(
                        name=alias,
                        country=nationality,
                        top_k=top_k,
                    )
                    alias_response = self._matcher.match(alias_query)
                    all_matches.extend(alias_response.top_matches)

            # Deduplicate and sort by score
            seen_uids = set()
            unique_matches = []
            for match in sorted(all_matches, key=lambda m: m.score, reverse=True):
                if match.uid not in seen_uids:
                    seen_uids.add(match.uid)
                    unique_matches.append(match)
                    if len(unique_matches) >= top_k:
                        break

            # Convert to Pydantic schemas
            match_data = [
                SanctionsMatchData(
                    matched_name=m.matched_name,
                    score=m.score,
                    decision=SanctionsDecision(m.decision),
                    country=m.country,
                    program=m.program,
                    source=m.source,
                    uid=m.uid,
                    similarity_details={
                        "sim_set": m.sim_set,
                        "sim_sort": m.sim_sort,
                        "sim_partial": m.sim_partial,
                    }
                    if m.sim_set is not None
                    else None,
                )
                for m in unique_matches
            ]

            # Determine overall decision
            top_match = match_data[0] if match_data else None
            if top_match and top_match.decision == SanctionsDecision.MATCH:
                overall_decision = SanctionsDecision.MATCH
                is_match = True
            elif top_match and top_match.decision == SanctionsDecision.REVIEW:
                overall_decision = SanctionsDecision.REVIEW
                is_match = False
            else:
                overall_decision = SanctionsDecision.NO_MATCH
                is_match = False

            processing_time_ms = (time.time() - start_time) * 1000

            return SanctionsScreeningResult(
                success=True,
                data=SanctionsScreeningData(
                    query_name=name,
                    query_normalized=normalize_text(name),
                    is_match=is_match,
                    decision=overall_decision,
                    top_match=top_match,
                    all_matches=match_data,
                    applied_filters={"country": nationality, "program": None},
                ),
                confidence=top_match.score if top_match else 0.0,
                processing_time_ms=processing_time_ms,
            )

        except Exception as e:
            logger.exception(f"Error screening name '{name}': {e}")
            processing_time_ms = (time.time() - start_time) * 1000
            return SanctionsScreeningResult(
                success=False,
                errors=[str(e)],
                processing_time_ms=processing_time_ms,
            )

    async def screen_document(
        self,
        document_id: UUID,
        db: AsyncSession,
        user_id: UUID | None = None,
    ) -> SanctionsScreeningResult:
        """
        Screen names extracted from a processed document.

        Extracts full_name and nationality from the document's extracted_data
        and performs sanctions screening. Stores result in screening_results table.

        Args:
            document_id: ID of the processed document
            db: Database session
            user_id: User ID for multi-tenant filtering (optional for backward compat)

        Returns:
            SanctionsScreeningResult with match details
        """
        start_time = time.time()

        # Get the document with user_id filter if provided
        query = select(Document).where(Document.id == document_id)
        if user_id is not None:
            query = query.where(Document.user_id == user_id)
        result = await db.execute(query)
        document = result.scalar_one_or_none()

        if not document:
            return SanctionsScreeningResult(
                success=False,
                errors=[f"Document not found: {document_id}"],
                processing_time_ms=(time.time() - start_time) * 1000,
            )

        if not document.extracted_data:
            return SanctionsScreeningResult(
                success=False,
                errors=["Document has no extracted data"],
                processing_time_ms=(time.time() - start_time) * 1000,
            )

        # Extract name and nationality from document data
        extracted = document.extracted_data
        full_name = extracted.get("full_name")
        if not full_name:
            # Try to build from surname and given_names (passport format)
            surname = extracted.get("surname", "")
            given_names = extracted.get("given_names", "")
            full_name = f"{given_names} {surname}".strip()

        if not full_name:
            return SanctionsScreeningResult(
                success=False,
                errors=["No name found in document extracted data"],
                processing_time_ms=(time.time() - start_time) * 1000,
            )

        nationality = extracted.get("nationality")

        # Screen the name
        screening_result = await self.screen_name(
            name=full_name,
            nationality=nationality,
        )

        # Store the result in database
        if screening_result.success and screening_result.data:
            db_result = ScreeningResult(
                document_id=document_id,
                user_id=document.user_id,  # Inherit user_id from document
                customer_id=document.customer_id,
                full_name=full_name,
                sanctions_match=screening_result.data.is_match,
                sanctions_decision=screening_result.data.decision.value,
                sanctions_score=screening_result.confidence,
                sanctions_details={
                    "top_match": screening_result.data.top_match.model_dump()
                    if screening_result.data.top_match
                    else None,
                    "all_matches": [m.model_dump() for m in screening_result.data.all_matches],
                    "lists_checked": screening_result.data.lists_checked,
                },
                processing_time_ms=int(screening_result.processing_time_ms),
            )
            db.add(db_result)
            await db.flush()

        return screening_result

    async def screen_batch(
        self,
        queries: list[dict],
    ) -> list[SanctionsScreeningResult]:
        """
        Screen multiple names in batch.

        Args:
            queries: List of dicts with 'name', optional 'aliases', 'nationality'

        Returns:
            List of SanctionsScreeningResult for each query
        """
        results = []
        for query in queries:
            result = await self.screen_name(
                name=query["name"],
                aliases=query.get("aliases"),
                nationality=query.get("nationality"),
            )
            results.append(result)
        return results


# Global service instance
sanctions_screening_service = SanctionsScreeningService()
