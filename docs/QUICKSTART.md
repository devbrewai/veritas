# Veritas Quickstart

Get from zero to your first KYC result in 5 minutes.

## 1. Get your API key

Sign up at [veritas.devbrew.ai](https://veritas.devbrew.ai), then generate an API key from the dashboard under Settings > API Keys.

## 2. Install the SDK

```bash
pip install veritas-sdk
# or use the API directly with curl/httpx
```

## 3. Option A — Sync (one call, result in under 15s)

```python
from veritas_sdk import VeritasClient

client = VeritasClient(api_key="vrt_sk_your_key_here")

kyc = client.kyc.process(
    file="passport.jpg",
    document_type="passport",
    customer_id="cust_123",
)
print(kyc.risk_assessment.tier)             # "Low"
print(kyc.risk_assessment.recommendation)  # "Approve"
print(kyc.total_processing_time_ms)        # e.g. 4230
```

## 4. Option B — Async (upload, poll status, then get results)

```python
import time
from veritas_sdk import VeritasClient

client = VeritasClient(api_key="vrt_sk_your_key_here")

result = client.documents.upload(
    file="passport.jpg",
    document_type="passport",
    customer_id="cust_123",
)
print(result.document_id, result.status_url)  # poll until completed

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

## 5. (Optional) Set up webhooks

Instead of polling, receive results via webhook:

```python
client.webhooks.create(
    url="https://your-app.com/webhooks/veritas",
    events=["kyc.complete", "risk.flagged"],
)
```

## Using curl instead

```bash
# Sync: one call, full KYC result
curl -X POST https://veritas-api.onrender.com/v1/kyc/process \
  -H "X-API-Key: vrt_sk_your_key_here" \
  -F "customer_id=cust_123" \
  -F "document_type=passport" \
  -F "file=@passport.jpg"

# Async: upload, then poll status, then get results
curl -X POST https://veritas-api.onrender.com/v1/documents/upload \
  -H "X-API-Key: vrt_sk_your_key_here" \
  -F "customer_id=cust_123" -F "document_type=passport" -F "file=@passport.jpg"
# Response includes document_id and status_url — poll GET status_url until status=completed
curl https://veritas-api.onrender.com/v1/kyc/cust_123 -H "X-API-Key: vrt_sk_your_key_here"
```

## 6. (Optional) MCP Server for AI agents

Let AI agents call Veritas directly:

```bash
pip install -e packages/veritas-mcp
export VERITAS_API_KEY="vrt_sk_your_key_here"
veritas-mcp
```

For Claude Desktop, add to your config:

```json
{
  "mcpServers": {
    "veritas": {
      "command": "python",
      "args": ["-m", "veritas_mcp"],
      "env": {
        "VERITAS_API_URL": "https://veritas-api.onrender.com/v1",
        "VERITAS_API_KEY": "vrt_sk_your_key_here"
      }
    }
  }
}
```

Tools available: `verify_identity`, `run_kyc_process`, `get_document_status`, `get_kyc_results`, `check_sanctions`, `get_statistics`.

---

That's it. Full API reference: [docs/API.md](./API.md) (includes API keys, webhooks, and MCP setup).
