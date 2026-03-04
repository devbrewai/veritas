"""Tests for response model dataclasses and from_dict helpers."""

import uuid

import pytest

from veritas_sdk.models import (
    DocumentStatusResult,
    KYCBatchResult,
    KYCResult,
    RiskAssessment,
    UploadResult,
    document_status_result_from_dict,
    kyc_batch_result_from_dict,
    kyc_result_from_dict,
    upload_result_from_dict,
)


def test_upload_result_from_dict() -> None:
    data = {
        "document_id": str(uuid.uuid4()),
        "status": "processing",
        "message": "Poll status_url for completion.",
        "status_url": "/v1/documents/abc/status",
        "estimated_completion_seconds": 8,
    }
    result = upload_result_from_dict(data)
    assert result.document_id == data["document_id"]
    assert result.status == "processing"
    assert result.message == data["message"]
    assert result.status_url == data["status_url"]
    assert result.estimated_completion_seconds == 8


def test_upload_result_from_dict_uuid_object() -> None:
    doc_id = uuid.uuid4()
    data = {
        "document_id": doc_id,
        "status": "processing",
        "message": "OK",
        "status_url": "/v1/documents/x/status",
        "estimated_completion_seconds": None,
    }
    result = upload_result_from_dict(data)
    assert result.document_id == str(doc_id)


def test_document_status_result_from_dict() -> None:
    data = {
        "document_id": "doc_123",
        "status": "completed",
        "message": None,
        "estimated_completion_seconds": None,
    }
    result = document_status_result_from_dict(data)
    assert result.document_id == "doc_123"
    assert result.status == "completed"
    assert result.message is None
    assert result.estimated_completion_seconds is None


def test_kyc_result_from_dict_minimal() -> None:
    data = {
        "customer_id": "cust_1",
        "documents": [],
        "sanctions_screening": None,
        "adverse_media": None,
        "risk_assessment": None,
        "overall_status": "pending",
    }
    result = kyc_result_from_dict(data)
    assert result.customer_id == "cust_1"
    assert result.documents == []
    assert result.risk_assessment is None
    assert result.overall_status == "pending"


def test_kyc_result_from_dict_with_risk() -> None:
    data = {
        "customer_id": "cust_2",
        "documents": [{"document_id": "d1", "document_type": "passport"}],
        "sanctions_screening": {"decision": "no_match"},
        "adverse_media": {"article_count": 0},
        "risk_assessment": {
            "risk_score": 0.15,
            "risk_tier": "Low",
            "recommendation": "Approve",
            "top_risk_factors": [],
        },
        "overall_status": "approved",
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:01",
    }
    result = kyc_result_from_dict(data)
    assert result.customer_id == "cust_2"
    assert len(result.documents) == 1
    assert result.risk_assessment is not None
    assert result.risk_assessment.risk_score == 0.15
    assert result.risk_assessment.risk_tier == "Low"
    assert result.risk_assessment.recommendation == "Approve"
    assert result.overall_status == "approved"
    assert result.created_at == "2026-01-01T00:00:00"


def test_kyc_result_from_dict_process_response() -> None:
    data = {
        "customer_id": "cust_3",
        "document_id": str(uuid.uuid4()),
        "document_processed": True,
        "processing_time_ms": 4200,
        "documents": [],
        "risk_assessment": {"risk_score": 0.2, "risk_tier": "Low", "recommendation": "Approve", "top_risk_factors": []},
        "overall_status": "approved",
        "errors": [],
    }
    result = kyc_result_from_dict(data)
    assert result.document_id == data["document_id"]
    assert result.document_processed is True
    assert result.processing_time_ms == 4200
    assert result.errors == []


def test_kyc_batch_result_from_dict() -> None:
    data = {
        "results": [
            {"customer_id": "c1", "documents": [], "overall_status": "approved", "risk_assessment": None},
            {"customer_id": "c2", "documents": [], "overall_status": "rejected", "risk_assessment": None},
        ],
        "total_processed": 2,
        "total_approved": 1,
        "total_review": 0,
        "total_rejected": 1,
        "total_pending": 0,
    }
    result = kyc_batch_result_from_dict(data)
    assert len(result.results) == 2
    assert result.results[0].customer_id == "c1"
    assert result.results[1].customer_id == "c2"
    assert result.total_processed == 2
    assert result.total_approved == 1
    assert result.total_rejected == 1
