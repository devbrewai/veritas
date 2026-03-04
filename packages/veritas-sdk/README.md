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

## Configuration

- **`VERITAS_API_URL`** — Base URL for the API (e.g. `https://veritas-api.onrender.com/v1`). If set, the client uses it when no `base_url` is passed to `VeritasClient`. Use `http://localhost:8000/v1` for local development.
- You can still pass `base_url` explicitly to `VeritasClient(api_key="...", base_url="...")` to override the env var.

The SDK does not load a `.env` file; it only reads `os.environ`. To use env vars, either set them in your shell or load `.env` in your application (e.g. with `python-dotenv`). See [.env.example](.env.example) in this package for the optional variables.

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
