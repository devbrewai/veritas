"""Tests for Veritas MCP server tools."""

from __future__ import annotations

import base64

import httpx
import pytest
import respx

from veritas_mcp.server import (
    VERITAS_API_URL,
    check_sanctions,
    get_document_status,
    get_kyc_results,
    get_statistics,
    run_kyc_process,
    verify_identity,
)

SAMPLE_DOC_B64 = base64.b64encode(b"fake-image-bytes").decode()


@pytest.mark.asyncio
@respx.mock
async def test_verify_identity() -> None:
    expected = {
        "document_id": "doc_abc123",
        "status": "processing",
        "status_url": "/v1/documents/doc_abc123/status",
        "estimated_completion_seconds": 8,
    }
    respx.post(f"{VERITAS_API_URL}/documents/upload").mock(
        return_value=httpx.Response(202, json=expected),
    )

    result = await verify_identity(SAMPLE_DOC_B64, "passport", "cust_123")

    assert result == expected


@pytest.mark.asyncio
@respx.mock
async def test_run_kyc_process() -> None:
    expected = {
        "customer_id": "cust_123",
        "overall_status": "approved",
        "risk_assessment": {"risk_score": 0.15, "risk_tier": "Low"},
    }
    respx.post(f"{VERITAS_API_URL}/kyc/process").mock(
        return_value=httpx.Response(200, json=expected),
    )

    result = await run_kyc_process(SAMPLE_DOC_B64, "passport", "cust_123")

    assert result == expected
    assert result["overall_status"] == "approved"


@pytest.mark.asyncio
@respx.mock
async def test_get_document_status() -> None:
    expected = {
        "document_id": "doc_abc123",
        "status": "completed",
        "estimated_completion_seconds": None,
    }
    respx.get(f"{VERITAS_API_URL}/documents/doc_abc123/status").mock(
        return_value=httpx.Response(200, json=expected),
    )

    result = await get_document_status("doc_abc123")

    assert result["status"] == "completed"


@pytest.mark.asyncio
@respx.mock
async def test_get_kyc_results() -> None:
    expected = {
        "customer_id": "cust_123",
        "documents": [],
        "overall_status": "approved",
    }
    respx.get(f"{VERITAS_API_URL}/kyc/cust_123").mock(
        return_value=httpx.Response(200, json=expected),
    )

    result = await get_kyc_results("cust_123")

    assert result["customer_id"] == "cust_123"


@pytest.mark.asyncio
@respx.mock
async def test_check_sanctions() -> None:
    expected = {
        "screening_id": "scr_abc",
        "decision": "no_match",
        "top_match_score": None,
    }
    respx.post(f"{VERITAS_API_URL}/screening/sanctions").mock(
        return_value=httpx.Response(200, json=expected),
    )

    result = await check_sanctions("John Doe", nationality="US")

    assert result["decision"] == "no_match"


@pytest.mark.asyncio
@respx.mock
async def test_get_statistics() -> None:
    expected = {
        "total_documents": 42,
        "total_customers": 15,
        "average_processing_time_ms": 4200,
    }
    respx.get(f"{VERITAS_API_URL}/users/me/stats").mock(
        return_value=httpx.Response(200, json=expected),
    )

    result = await get_statistics()

    assert result["total_documents"] == 42


@pytest.mark.asyncio
@respx.mock
async def test_tool_returns_error_on_api_failure() -> None:
    error_body = {
        "error": {"code": "INVALID_API_KEY", "message": "Invalid API key"},
        "request_id": "req_xyz",
    }
    respx.get(f"{VERITAS_API_URL}/kyc/cust_bad").mock(
        return_value=httpx.Response(401, json=error_body),
    )

    result = await get_kyc_results("cust_bad")

    assert result["error"] is True
    assert result["status_code"] == 401
    assert result["detail"]["error"]["code"] == "INVALID_API_KEY"
