"""Tests for VeritasClient._request (error handling and success)."""

import pytest
import respx

from veritas_sdk.client import VeritasClient, DEFAULT_BASE_URL
from veritas_sdk.errors import VeritasAPIError


@respx.mock
def test_request_returns_json_on_success(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(f"{DEFAULT_BASE_URL}/kyc/cust_123").mock(
        return_value=respx.MockResponse(200, json={"customer_id": "cust_123", "documents": []})
    )
    client = VeritasClient(api_key="vrt_sk_test")
    result = client._request("GET", "/kyc/cust_123")
    assert result["customer_id"] == "cust_123"
    assert result["documents"] == []


@respx.mock
def test_request_raises_veritas_api_error_on_401(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{DEFAULT_BASE_URL}/documents/upload").mock(
        return_value=respx.MockResponse(
            401,
            json={
                "error": {
                    "code": "INVALID_API_KEY",
                    "message": "Invalid or revoked API key.",
                },
                "request_id": "req_123",
            },
            headers={"X-Request-Id": "req_123"},
        )
    )
    client = VeritasClient(api_key="vrt_sk_bad")
    with pytest.raises(VeritasAPIError) as exc_info:
        client._request("POST", "/documents/upload", json={})
    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "INVALID_API_KEY"
    assert exc_info.value.request_id == "req_123"


@respx.mock
def test_request_uses_request_id_from_body_when_header_missing(
    respx_mock: respx.MockRouter,
) -> None:
    respx_mock.get(f"{DEFAULT_BASE_URL}/kyc/cust_456").mock(
        return_value=respx.MockResponse(
            404,
            json={
                "error": {"code": "CUSTOMER_NOT_FOUND", "message": "Customer not found."},
                "request_id": "req_from_body",
            },
        )
    )
    client = VeritasClient(api_key="vrt_sk_test")
    with pytest.raises(VeritasAPIError) as exc_info:
        client._request("GET", "/kyc/cust_456")
    assert exc_info.value.request_id == "req_from_body"


@respx.mock
def test_request_sends_api_key_header(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(f"{DEFAULT_BASE_URL}/users/me/stats").mock(
        return_value=respx.MockResponse(200, json={"total_documents": 0})
    )
    client = VeritasClient(api_key="vrt_sk_secret")
    client._request("GET", "/users/me/stats")
    request = respx_mock.calls.last.request
    assert request.headers.get("X-API-Key") == "vrt_sk_secret"
