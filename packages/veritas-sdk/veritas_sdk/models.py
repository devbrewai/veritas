"""Response models for the Veritas API.

Dataclasses aligned with API response shapes. UUIDs and dates are kept as strings
for simplicity (API returns UUID and ISO datetime strings in JSON).
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class UploadResult:
    """Response from POST /documents/upload (202 Accepted)."""

    document_id: str
    status: str
    message: str
    status_url: str
    estimated_completion_seconds: int | None


@dataclass
class DocumentStatusResult:
    """Response from GET /documents/{id}/status."""

    document_id: str
    status: str  # processing, completed, failed
    message: str | None
    estimated_completion_seconds: int | None


@dataclass
class RiskAssessment:
    """Risk assessment result within KYC response."""

    risk_score: float
    risk_tier: str  # Low, Medium, High
    recommendation: str  # Approve, Review, Reject
    top_risk_factors: list[str]


@dataclass
class KYCResult:
    """Aggregated KYC result for a customer.

    Used for both GET /kyc/{customer_id} and POST /kyc/process.
    For process(), document_id, document_processed, processing_time_ms, and errors may be set.
    """

    customer_id: str
    documents: list[dict[str, Any]]
    sanctions_screening: dict[str, Any] | None
    adverse_media: dict[str, Any] | None
    risk_assessment: RiskAssessment | None
    overall_status: str
    created_at: str | None = None
    updated_at: str | None = None
    # POST /kyc/process only
    document_id: str | None = None
    document_processed: bool | None = None
    processing_time_ms: int | None = None
    errors: list[str] | None = None
    extracted_data: dict[str, Any] | None = None
    ocr_confidence: float | None = None


@dataclass
class KYCBatchResult:
    """Response from POST /kyc/batch."""

    results: list[KYCResult]
    total_processed: int
    total_approved: int
    total_review: int
    total_rejected: int
    total_pending: int


def _parse_risk_assessment(data: dict[str, Any] | None) -> RiskAssessment | None:
    if not data:
        return None
    return RiskAssessment(
        risk_score=data.get("risk_score", 0.0),
        risk_tier=data.get("risk_tier", ""),
        recommendation=data.get("recommendation", "Review"),
        top_risk_factors=data.get("top_risk_factors") or [],
    )


def upload_result_from_dict(data: dict[str, Any]) -> UploadResult:
    """Build UploadResult from API response dict."""
    doc_id = data.get("document_id")
    if hasattr(doc_id, "hex"):
        doc_id = str(doc_id)
    return UploadResult(
        document_id=doc_id or "",
        status=data.get("status", "processing"),
        message=data.get("message", ""),
        status_url=data.get("status_url", ""),
        estimated_completion_seconds=data.get("estimated_completion_seconds"),
    )


def document_status_result_from_dict(data: dict[str, Any]) -> DocumentStatusResult:
    """Build DocumentStatusResult from API response dict."""
    doc_id = data.get("document_id")
    if hasattr(doc_id, "hex"):
        doc_id = str(doc_id)
    return DocumentStatusResult(
        document_id=doc_id or "",
        status=data.get("status", "processing"),
        message=data.get("message"),
        estimated_completion_seconds=data.get("estimated_completion_seconds"),
    )


def kyc_result_from_dict(data: dict[str, Any]) -> KYCResult:
    """Build KYCResult from API response dict (GET /kyc/{id} or POST /kyc/process)."""
    doc_id = data.get("document_id")
    if doc_id is not None and hasattr(doc_id, "hex"):
        doc_id = str(doc_id)
    return KYCResult(
        customer_id=data.get("customer_id", ""),
        documents=data.get("documents") or [],
        sanctions_screening=data.get("sanctions_screening"),
        adverse_media=data.get("adverse_media"),
        risk_assessment=_parse_risk_assessment(data.get("risk_assessment")),
        overall_status=data.get("overall_status", "pending"),
        created_at=_str_if_present(data.get("created_at")),
        updated_at=_str_if_present(data.get("updated_at")),
        document_id=doc_id,
        document_processed=data.get("document_processed"),
        processing_time_ms=data.get("processing_time_ms"),
        errors=data.get("errors"),
        extracted_data=data.get("extracted_data"),
        ocr_confidence=data.get("ocr_confidence"),
    )


def _str_if_present(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def kyc_batch_result_from_dict(data: dict[str, Any]) -> KYCBatchResult:
    """Build KYCBatchResult from API response dict."""
    results = [kyc_result_from_dict(r) for r in data.get("results") or []]
    return KYCBatchResult(
        results=results,
        total_processed=data.get("total_processed", 0),
        total_approved=data.get("total_approved", 0),
        total_review=data.get("total_review", 0),
        total_rejected=data.get("total_rejected", 0),
        total_pending=data.get("total_pending", 0),
    )
