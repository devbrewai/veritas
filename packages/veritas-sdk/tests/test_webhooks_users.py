"""Tests for WebhooksAPI and UsersAPI."""

import respx

from veritas_sdk.client import DEFAULT_BASE_URL, VeritasClient


@respx.mock
def test_webhooks_create_returns_dict(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(f"{DEFAULT_BASE_URL}/webhooks").mock(
        return_value=respx.MockResponse(
            201,
            json={
                "id": "wh_123",
                "url": "https://example.com/webhook",
                "events": ["kyc.complete"],
                "secret": "whsec_abc",
                "created_at": "2026-01-01T00:00:00",
            },
        )
    )
    client = VeritasClient(api_key="vrt_sk_test")
    result = client.webhooks.create("https://example.com/webhook", ["kyc.complete"])
    assert result["id"] == "wh_123"
    assert result["url"] == "https://example.com/webhook"
    assert result["secret"] == "whsec_abc"
    assert "kyc.complete" in result["events"]


@respx.mock
def test_webhooks_list_returns_webhooks_dict(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(f"{DEFAULT_BASE_URL}/webhooks").mock(
        return_value=respx.MockResponse(
            200,
            json={
                "webhooks": [
                    {"id": "wh_1", "url": "https://a.com", "events": ["document.processed"], "active": True, "created_at": "2026-01-01T00:00:00"},
                ]
            },
        )
    )
    client = VeritasClient(api_key="vrt_sk_test")
    result = client.webhooks.list()
    assert "webhooks" in result
    assert len(result["webhooks"]) == 1
    assert result["webhooks"][0]["url"] == "https://a.com"


@respx.mock
def test_webhooks_delete_calls_delete_endpoint(respx_mock: respx.MockRouter) -> None:
    respx_mock.delete(f"{DEFAULT_BASE_URL}/webhooks/wh_456").mock(
        return_value=respx.MockResponse(204)
    )
    client = VeritasClient(api_key="vrt_sk_test")
    client.webhooks.delete("wh_456")
    assert respx_mock.calls.last.request.url.path == "/v1/webhooks/wh_456"


@respx.mock
def test_users_export_returns_dict(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(f"{DEFAULT_BASE_URL}/users/me/export").mock(
        return_value=respx.MockResponse(
            200,
            json={"documents": [], "screenings": [], "audit_logs": []},
        )
    )
    client = VeritasClient(api_key="vrt_sk_test")
    result = client.users.export()
    assert "documents" in result
    assert result["documents"] == []


@respx.mock
def test_users_delete_me_calls_delete_endpoint(respx_mock: respx.MockRouter) -> None:
    respx_mock.delete(f"{DEFAULT_BASE_URL}/users/me").mock(
        return_value=respx.MockResponse(204)
    )
    client = VeritasClient(api_key="vrt_sk_test")
    result = client.users.delete_me()
    assert result == {}
    assert respx_mock.calls.last.request.method == "DELETE"
