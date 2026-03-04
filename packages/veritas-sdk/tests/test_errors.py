"""Tests for VeritasAPIError."""

import pytest

from veritas_sdk.errors import VeritasAPIError


def test_veritas_api_error_attributes() -> None:
    error = VeritasAPIError(
        401,
        {"code": "INVALID_API_KEY", "message": "Invalid or revoked API key."},
        request_id="req_123",
    )
    assert error.status_code == 401
    assert error.code == "INVALID_API_KEY"
    assert error.message == "Invalid or revoked API key."
    assert error.details is None
    assert error.request_id == "req_123"
    assert "INVALID_API_KEY" in str(error)
    assert "Invalid or revoked" in str(error)


def test_veritas_api_error_with_details() -> None:
    error = VeritasAPIError(
        429,
        {
            "code": "RATE_LIMIT_EXCEEDED",
            "message": "Rate limit exceeded.",
            "details": {"retry_after_seconds": 30},
        },
    )
    assert error.code == "RATE_LIMIT_EXCEEDED"
    assert error.details == {"retry_after_seconds": 30}


def test_veritas_api_error_minimal_dict() -> None:
    error = VeritasAPIError(500, {})
    assert error.code == "UNKNOWN"
    assert error.message == "Unknown error"
    assert error.details is None
    assert error.request_id is None
