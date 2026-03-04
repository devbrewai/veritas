"""Tests for the document processor service (sync OCR and async runner)."""

from pathlib import Path

import pytest

from src.services.document_processor import process_document_sync


class TestProcessDocumentSync:
    """Tests for process_document_sync."""

    def test_unsupported_document_type_returns_error_dict(self) -> None:
        """Unsupported type returns dict with errors and no data."""
        result = process_document_sync(Path("/nonexistent.jpg"), "drivers_license")
        assert "data" in result
        assert result["data"] is None
        assert "errors" in result
        assert len(result["errors"]) > 0
        assert "document type" in result["errors"][0].lower() or "not supported" in result["errors"][0].lower()
        assert result.get("confidence") == 0.0

    def test_missing_file_returns_error_dict(self) -> None:
        """Missing file path returns dict with load error."""
        result = process_document_sync(Path("/nonexistent/path/image.jpg"), "passport")
        assert result["data"] is None
        assert "errors" in result
        assert len(result["errors"]) > 0
        assert result.get("ocr_provider") == "none"

    def test_returns_expected_keys(self) -> None:
        """Result dict has expected keys for downstream."""
        result = process_document_sync(Path("/nonexistent.jpg"), "passport")
        assert "data" in result
        assert "confidence" in result
        assert "errors" in result
        assert "ocr_provider" in result
