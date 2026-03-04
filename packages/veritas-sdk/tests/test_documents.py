"""Tests for DocumentsAPI."""

import tempfile
from pathlib import Path

import respx

from veritas_sdk.client import DEFAULT_BASE_URL, VeritasClient
from veritas_sdk.models import DocumentStatusResult, UploadResult


@respx.mock
def test_documents_upload_returns_upload_result(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{DEFAULT_BASE_URL}/documents/upload").mock(
        return_value=respx.MockResponse(
            202,
            json={
                "document_id": "doc_abc",
                "status": "processing",
                "message": "Poll for status.",
                "status_url": "/v1/documents/doc_abc/status",
                "estimated_completion_seconds": 8,
            },
        )
    )
    client = VeritasClient(api_key="vrt_sk_test")
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        f.write(b"fake image")
        path = Path(f.name)
    try:
        result = client.documents.upload(
            file=path,
            document_type="passport",
            customer_id="cust_123",
        )
        assert isinstance(result, UploadResult)
        assert result.document_id == "doc_abc"
        assert result.status == "processing"
        assert result.status_url == "/v1/documents/doc_abc/status"
        assert result.estimated_completion_seconds == 8
    finally:
        path.unlink(missing_ok=True)


@respx.mock
def test_documents_upload_sends_idempotency_key(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{DEFAULT_BASE_URL}/documents/upload").mock(
        return_value=respx.MockResponse(
            202,
            json={
                "document_id": "doc_xyz",
                "status": "processing",
                "message": "OK",
                "status_url": "/v1/documents/doc_xyz/status",
                "estimated_completion_seconds": 5,
            },
        )
    )
    client = VeritasClient(api_key="vrt_sk_test")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"pdf")
        path = Path(f.name)
    try:
        client.documents.upload(
            file=path,
            document_type="passport",
            customer_id="cust_1",
            idempotency_key="key_123",
        )
        request = respx_mock.calls.last.request
        assert request.headers.get("Idempotency-Key") == "key_123"
    finally:
        path.unlink(missing_ok=True)


@respx.mock
def test_documents_status_returns_document_status_result(
    respx_mock: respx.MockRouter,
) -> None:
    respx_mock.get(f"{DEFAULT_BASE_URL}/documents/doc_123/status").mock(
        return_value=respx.MockResponse(
            200,
            json={
                "document_id": "doc_123",
                "status": "completed",
                "message": None,
                "estimated_completion_seconds": None,
            },
        )
    )
    client = VeritasClient(api_key="vrt_sk_test")
    result = client.documents.status("doc_123")
    assert isinstance(result, DocumentStatusResult)
    assert result.document_id == "doc_123"
    assert result.status == "completed"
