"""Tests for KYCAPI."""

import tempfile
from pathlib import Path

import respx

from veritas_sdk.client import DEFAULT_BASE_URL, VeritasClient
from veritas_sdk.models import KYCBatchResult, KYCResult


@respx.mock
def test_kyc_process_returns_kyc_result(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{DEFAULT_BASE_URL}/kyc/process").mock(
        return_value=respx.MockResponse(
            200,
            json={
                "customer_id": "cust_1",
                "document_id": "doc_abc",
                "document_processed": True,
                "processing_time_ms": 4200,
                "documents": [],
                "risk_assessment": {
                    "risk_score": 0.15,
                    "risk_tier": "Low",
                    "recommendation": "Approve",
                    "top_risk_factors": [],
                },
                "overall_status": "approved",
                "errors": [],
            },
        )
    )
    client = VeritasClient(api_key="vrt_sk_test")
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        f.write(b"image")
        path = Path(f.name)
    try:
        result = client.kyc.process(path, "passport", "cust_1")
        assert isinstance(result, KYCResult)
        assert result.customer_id == "cust_1"
        assert result.document_id == "doc_abc"
        assert result.processing_time_ms == 4200
        assert result.risk_assessment is not None
        assert result.risk_assessment.risk_tier == "Low"
    finally:
        path.unlink(missing_ok=True)


@respx.mock
def test_kyc_get_returns_kyc_result(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(f"{DEFAULT_BASE_URL}/kyc/cust_123").mock(
        return_value=respx.MockResponse(
            200,
            json={
                "customer_id": "cust_123",
                "documents": [{"document_id": "d1", "document_type": "passport"}],
                "sanctions_screening": {"decision": "no_match"},
                "adverse_media": None,
                "risk_assessment": {
                    "risk_score": 0.2,
                    "risk_tier": "Low",
                    "recommendation": "Approve",
                    "top_risk_factors": [],
                },
                "overall_status": "approved",
                "created_at": "2026-01-01T00:00:00",
                "updated_at": "2026-01-01T00:00:01",
            },
        )
    )
    client = VeritasClient(api_key="vrt_sk_test")
    result = client.kyc.get("cust_123")
    assert isinstance(result, KYCResult)
    assert result.customer_id == "cust_123"
    assert len(result.documents) == 1
    assert result.risk_assessment is not None
    assert result.risk_assessment.recommendation == "Approve"


@respx.mock
def test_kyc_batch_returns_kyc_batch_result(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{DEFAULT_BASE_URL}/kyc/batch").mock(
        return_value=respx.MockResponse(
            200,
            json={
                "results": [
                    {"customer_id": "c1", "documents": [], "overall_status": "approved", "risk_assessment": None},
                    {"customer_id": "c2", "documents": [], "overall_status": "rejected", "risk_assessment": None},
                ],
                "total_processed": 2,
                "total_approved": 1,
                "total_review": 0,
                "total_rejected": 1,
                "total_pending": 0,
            },
        )
    )
    client = VeritasClient(api_key="vrt_sk_test")
    result = client.kyc.batch(["c1", "c2"])
    assert isinstance(result, KYCBatchResult)
    assert len(result.results) == 2
    assert result.results[0].customer_id == "c1"
    assert result.results[1].customer_id == "c2"
    assert result.total_processed == 2
    assert result.total_approved == 1
    assert result.total_rejected == 1


@respx.mock
def test_kyc_batch_sends_customer_ids_in_body(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{DEFAULT_BASE_URL}/kyc/batch").mock(
        return_value=respx.MockResponse(
            200,
            json={
                "results": [],
                "total_processed": 0,
                "total_approved": 0,
                "total_review": 0,
                "total_rejected": 0,
                "total_pending": 0,
            },
        )
    )
    client = VeritasClient(api_key="vrt_sk_test")
    client.kyc.batch(["cust_a", "cust_b"])
    request = respx_mock.calls.last.request
    import json
    body = json.loads(request.content)
    assert body["customer_ids"] == ["cust_a", "cust_b"]
