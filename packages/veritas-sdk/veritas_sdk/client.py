"""Veritas API HTTP client."""

from __future__ import annotations

from typing import Any

import httpx

from veritas_sdk.errors import VeritasAPIError

DEFAULT_BASE_URL = "https://veritas-api.onrender.com/v1"


class VeritasClient:
    """Veritas KYC/AML API client.

    Args:
        api_key: Your Veritas API key (starts with vrt_sk_).
        base_url: API base URL including /v1 (default: production).
        timeout: Request timeout in seconds (default: 30).
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = 30,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def _request(
        self,
        method: str,
        path: str,
        extra_headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send an authenticated request and return JSON or raise VeritasAPIError."""
        path = path if path.startswith("/") else f"/{path}"
        url = f"{self._base_url}{path}"
        headers = {"X-API-Key": self._api_key}
        if extra_headers:
            headers.update(extra_headers)
        kwargs.setdefault("timeout", self._timeout)

        response = httpx.request(method, url, headers=headers, **kwargs)

        if response.status_code >= 400:
            request_id = response.headers.get("X-Request-Id")
            try:
                body = response.json()
                error = body.get("error", {})
                if isinstance(error, dict):
                    request_id = body.get("request_id") or request_id
            except Exception:
                error = {"code": "UNKNOWN", "message": response.text or "Request failed"}
            raise VeritasAPIError(response.status_code, error, request_id=request_id)

        if response.status_code == 204:
            return {}
        return response.json()
