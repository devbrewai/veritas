"""Veritas KYC/AML API Python SDK.

Usage:
    from veritas_sdk import VeritasClient

    client = VeritasClient(api_key="vrt_sk_...")
    kyc = client.kyc.process(file="passport.jpg", document_type="passport", customer_id="cust_123")
    print(kyc.risk_assessment.tier)
"""

from veritas_sdk.client import DEFAULT_BASE_URL, DocumentsAPI, KYCAPI, UsersAPI, VeritasClient, WebhooksAPI
from veritas_sdk.errors import VeritasAPIError
from veritas_sdk.models import (
    DocumentStatusResult,
    KYCBatchResult,
    KYCResult,
    RiskAssessment,
    UploadResult,
)

__all__ = [
    "DEFAULT_BASE_URL",
    "DocumentStatusResult",
    "DocumentsAPI",
    "KYCAPI",
    "KYCBatchResult",
    "KYCResult",
    "RiskAssessment",
    "UploadResult",
    "VeritasAPIError",
    "VeritasClient",
    "WebhooksAPI",
    "UsersAPI",
    "__version__",
]
__version__ = "0.1.0"
