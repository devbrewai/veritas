# Veritas Python SDK

Python client for the Veritas KYC/AML API. Use it to run KYC (document upload, sanctions screening, risk assessment) with typed results and consistent error handling.

## Installation

From the monorepo root:

```bash
uv pip install -e packages/veritas-sdk
```

Or from this directory:

```bash
uv sync
```

## Quick start

### Option A — Sync (one call, result in under 15s)

```python
from veritas_sdk import VeritasClient

client = VeritasClient(api_key="vrt_sk_your_key_here")

kyc = client.kyc.process(
    file="passport.jpg",
    document_type="passport",
    customer_id="cust_123",
)
print(kyc.risk_assessment.tier)             # "Low"
print(kyc.risk_assessment.recommendation)   # "Approve"
print(kyc.processing_time_ms)               # e.g. 4230
```

### Option B — Async (upload, poll status, then get results)

```python
import time
from veritas_sdk import VeritasClient

client = VeritasClient(api_key="vrt_sk_your_key_here")

result = client.documents.upload(
    file="passport.jpg",
    document_type="passport",
    customer_id="cust_123",
)
print(result.document_id, result.status_url)

while True:
    status = client.documents.status(result.document_id)
    if status.status == "completed":
        break
    if status.status == "failed":
        raise RuntimeError("Processing failed")
    time.sleep(1)

kyc = client.kyc.get("cust_123")
print(kyc.risk_assessment.tier)
```

### Webhooks

```python
client.webhooks.create(
    url="https://your-app.com/webhooks/veritas",
    events=["kyc.complete", "risk.flagged"],
)
```

## API reference

- [API.md](../../docs/API.md) — Full endpoint reference, auth, errors, idempotency.
- [QUICKSTART.md](../../docs/QUICKSTART.md) — Step-by-step guide and curl examples.

## Error handling

On 4xx/5xx the client raises `VeritasAPIError` with `status_code`, `code`, `message`, `details`, and `request_id`:

```python
from veritas_sdk import VeritasClient, VeritasAPIError

try:
    client.kyc.get("unknown_cust")
except VeritasAPIError as e:
    print(e.code)        # e.g. "CUSTOMER_NOT_FOUND"
    print(e.request_id)  # for support/debugging
```
