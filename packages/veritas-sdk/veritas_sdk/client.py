"""Veritas API HTTP client."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from veritas_sdk.errors import VeritasAPIError
from veritas_sdk.models import (
    DocumentStatusResult,
    KYCBatchResult,
    KYCResult,
    UploadResult,
    document_status_result_from_dict,
    kyc_batch_result_from_dict,
    kyc_result_from_dict,
    upload_result_from_dict,
)

DEFAULT_BASE_URL = "https://veritas-api.onrender.com/v1"


class DocumentsAPI:
    """Document upload and status endpoints."""

    def __init__(self, client: VeritasClient) -> None:
        self._client = client

    def upload(
        self,
        file: str | Path,
        document_type: str,
        customer_id: str,
        idempotency_key: str | None = None,
    ) -> UploadResult:
        """Upload a document for async KYC processing. Poll status() until completed."""
        file_path = Path(file)
        headers: dict[str, str] = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        with open(file_path, "rb") as f:
            response = self._client._request(
                "POST",
                "/documents/upload",
                files={"file": (file_path.name, f)},
                data={"customer_id": customer_id, "document_type": document_type},
                extra_headers=headers if headers else None,
            )
        return upload_result_from_dict(response)

    def status(self, document_id: str) -> DocumentStatusResult:
        """Get processing status for an uploaded document."""
        response = self._client._request(
            "GET",
            f"/documents/{document_id}/status",
        )
        return document_status_result_from_dict(response)


class KYCAPI:
    """KYC process, get, and batch endpoints."""

    def __init__(self, client: VeritasClient) -> None:
        self._client = client

    def process(
        self,
        file: str | Path,
        document_type: str,
        customer_id: str,
    ) -> KYCResult:
        """Single-call KYC: upload and get full result (OCR + sanctions + adverse media + risk). Under 15s."""
        file_path = Path(file)
        with open(file_path, "rb") as f:
            response = self._client._request(
                "POST",
                "/kyc/process",
                files={"file": (file_path.name, f)},
                data={"customer_id": customer_id, "document_type": document_type},
            )
        return kyc_result_from_dict(response)

    def get(self, customer_id: str) -> KYCResult:
        """Get KYC results for a customer (after async upload is completed)."""
        response = self._client._request("GET", f"/kyc/{customer_id}")
        return kyc_result_from_dict(response)

    def batch(self, customer_ids: list[str]) -> KYCBatchResult:
        """Get KYC results for multiple customers (max 10 per request)."""
        response = self._client._request(
            "POST",
            "/kyc/batch",
            json={"customer_ids": customer_ids},
        )
        return kyc_batch_result_from_dict(response)


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
        self.documents = DocumentsAPI(self)
        self.kyc = KYCAPI(self)

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
