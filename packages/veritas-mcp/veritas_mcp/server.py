"""Veritas MCP Server.

Exposes Veritas KYC/AML endpoints as MCP tools that AI agents can call.

Run:
    uvx veritas-mcp
    python -m veritas_mcp
    veritas-mcp          (after pip install)

Environment variables:
    VERITAS_API_URL  — API base URL including /v1 (default: https://veritas-api.onrender.com/v1)
    VERITAS_API_KEY  — Your Veritas API key (starts with vrt_sk_)
"""

from __future__ import annotations

import base64
import os

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("veritas")

VERITAS_API_URL = os.getenv("VERITAS_API_URL", "https://veritas-api.onrender.com/v1")
VERITAS_API_KEY = os.getenv("VERITAS_API_KEY", "")


def _headers() -> dict[str, str]:
    return {"X-API-Key": VERITAS_API_KEY}


def _error_response(response: httpx.Response) -> dict:
    """Build a structured error dict from a failed HTTP response."""
    try:
        body = response.json()
    except Exception:
        body = response.text
    return {"error": True, "status_code": response.status_code, "detail": body}


@mcp.tool()
async def verify_identity(
    document_base64: str,
    document_type: str,
    customer_id: str,
) -> dict:
    """Upload a KYC document for async processing. Returns document_id and status_url.

    Poll get_document_status until completed, then use get_kyc_results(customer_id).
    For immediate full result in one call, use run_kyc_process instead.

    Args:
        document_base64: Base64-encoded document image (JPG, PNG, PDF).
        document_type: One of 'passport', 'utility_bill', 'business_reg', 'drivers_license'.
        customer_id: Unique customer identifier.
    """
    file_bytes = base64.b64decode(document_base64)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{VERITAS_API_URL}/documents/upload",
            headers=_headers(),
            files={"file": ("document", file_bytes)},
            data={"customer_id": customer_id, "document_type": document_type},
        )
    if response.status_code >= 400:
        return _error_response(response)
    return response.json()


@mcp.tool()
async def run_kyc_process(
    document_base64: str,
    document_type: str,
    customer_id: str,
) -> dict:
    """Run full KYC in one call: OCR extraction, sanctions screening, adverse media, risk assessment.

    Returns complete KYC result. Completes in under 15 seconds.
    Use when you need the result immediately without polling.

    Args:
        document_base64: Base64-encoded document image (JPG, PNG, PDF).
        document_type: One of 'passport', 'utility_bill', 'business_reg', 'drivers_license'.
        customer_id: Unique customer identifier.
    """
    file_bytes = base64.b64decode(document_base64)
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"{VERITAS_API_URL}/kyc/process",
            headers=_headers(),
            files={"file": ("document", file_bytes)},
            data={"customer_id": customer_id, "document_type": document_type},
        )
    if response.status_code >= 400:
        return _error_response(response)
    return response.json()


@mcp.tool()
async def get_document_status(document_id: str) -> dict:
    """Get processing status for an uploaded document (processing, completed, failed).

    Use after verify_identity to know when to call get_kyc_results.

    Args:
        document_id: The document ID returned by verify_identity.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{VERITAS_API_URL}/documents/{document_id}/status",
            headers=_headers(),
        )
    if response.status_code >= 400:
        return _error_response(response)
    return response.json()


@mcp.tool()
async def get_kyc_results(customer_id: str) -> dict:
    """Retrieve complete KYC results for a customer.

    Includes document extraction, sanctions screening, adverse media, and risk assessment.

    Args:
        customer_id: The customer identifier used during document upload.

    Returns:
        Full KYC results with extracted data, screening results, risk tier, and recommendation.
    """
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{VERITAS_API_URL}/kyc/{customer_id}",
            headers=_headers(),
        )
    if response.status_code >= 400:
        return _error_response(response)
    return response.json()


@mcp.tool()
async def check_sanctions(full_name: str, nationality: str = "") -> dict:
    """Screen a name against OFAC, EU, and UN sanctions lists.

    Args:
        full_name: The full name to screen.
        nationality: Optional ISO country code to narrow matching.

    Returns:
        Sanctions screening result with match status, confidence, and matched entity details.
    """
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{VERITAS_API_URL}/screening/sanctions",
            headers=_headers(),
            json={"full_name": full_name, "nationality": nationality},
        )
    if response.status_code >= 400:
        return _error_response(response)
    return response.json()


@mcp.tool()
async def get_statistics() -> dict:
    """Get usage statistics for the authenticated account.

    Returns total documents processed, customers screened, average processing time,
    risk distribution, and estimated cost savings.
    """
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{VERITAS_API_URL}/users/me/stats",
            headers=_headers(),
        )
    if response.status_code >= 400:
        return _error_response(response)
    return response.json()


def main() -> None:
    """Entry point for the Veritas MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
