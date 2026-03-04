# Veritas API Reference

Base URL: `https://veritas-api.onrender.com/v1`

## Authentication

All endpoints require authentication via one of:

- **API Key:** `X-API-Key: vrt_sk_...` header
- **Bearer Token:** `Authorization: Bearer <jwt_token>` header (session-based)

## Endpoints

### Upload Document (async)

`POST /v1/documents/upload`

Upload a KYC document for processing. The document is queued for background OCR, sanctions screening, adverse media, and risk scoring. Poll `status_url` or `GET /v1/documents/{document_id}/status` until `status` is `completed`, then use `GET /v1/kyc/{customer_id}` for full results. For a single synchronous call that returns the full KYC result, use `POST /v1/kyc/process` instead.

**Headers:**

- `Content-Type: multipart/form-data`
- `X-API-Key: vrt_sk_...`
- `Idempotency-Key: <unique_string>` (optional, recommended)

**Request:**

| Field           | Type   | Required | Description                                                                 |
| --------------- | ------ | -------- | --------------------------------------------------------------------------- |
| `customer_id`   | string | yes      | Unique customer identifier                                                  |
| `document_type` | string | yes      | `passport`, `utility_bill`, `business_reg`, `drivers_license`               |
| `file`          | binary | yes      | Image (JPG, PNG, HEIC) or PDF. Max 10MB                                    |

**Response (202 Accepted):**

```json
{
  "document_id": "doc_abc123",
  "status": "processing",
  "status_url": "/v1/documents/doc_abc123/status",
  "estimated_completion_seconds": 8
}
```

### Get Document Status

`GET /v1/documents/{document_id}/status`

Poll this endpoint (or the `status_url` from the upload response) to check when async processing is complete.

**Response (200 OK):**

```json
{
  "document_id": "doc_abc123",
  "status": "completed",
  "estimated_completion_seconds": null
}
```

Status values: `processing`, `completed`, `failed`.

### Process KYC (sync)

`POST /v1/kyc/process`

Single-call end-to-end KYC: upload a document and receive the full result (OCR extraction, sanctions screening, adverse media, risk assessment) in one response. Completes in under 15 seconds. Use this when you need an immediate result without polling.

**Request:** Same as upload (multipart: `customer_id`, `document_type`, `file`).

**Response (200 OK):** Same shape as `GET /v1/kyc/{customer_id}` (unified `KYCResult` with `documents`, `screening`, `risk_assessment`, `total_processing_time_ms`).

### Get KYC Results

`GET /v1/kyc/{customer_id}`

Retrieve complete KYC results including document extraction, sanctions screening, adverse media, and risk assessment. Use after async upload when document status is `completed`, or to fetch results from a previous `POST /v1/kyc/process`.

**Response (200 OK):**

```json
{
  "customer_id": "cust_123",
  "documents": [],
  "screening": {
    "sanctions_match": false,
    "sanctions_checked": ["OFAC", "EU", "UN"],
    "adverse_media": {
      "mentions_found": 0,
      "summary": "No negative mentions found"
    }
  },
  "risk_assessment": {
    "score": 0.15,
    "tier": "Low",
    "reasons": [],
    "recommendation": "Approve"
  },
  "total_processing_time_ms": 4230
}
```

### Account & GDPR

`GET /v1/users/me/export` — Export all user data (documents metadata, KYC results) for GDPR data portability. Returns a JSON or downloadable archive.

`DELETE /v1/users/me` — Right to be forgotten: delete account and associated data. Irreversible.

Document retention is configurable (e.g. `DOCUMENT_RETENTION_DAYS`); documents have an `expires_at` and a cleanup process removes expired data.

## Idempotency

For `POST` endpoints, include an `Idempotency-Key` header to safely retry requests. If a request with the same key was already processed, the original response is returned with an `X-Idempotent-Replay: true` header.

Keys are scoped per user and expire after 24 hours.

```bash
curl -X POST https://veritas-api.onrender.com/v1/documents/upload \
  -H "X-API-Key: vrt_sk_..." \
  -H "Idempotency-Key: upload_cust123_passport_20260210" \
  -F "customer_id=cust_123" \
  -F "document_type=passport" \
  -F "file=@passport.jpg"
```

## Error Responses

All errors return a consistent shape with `error` (code, message, details) and `request_id`. The response includes an `X-Request-Id` header for tracing.

### 400 — Bad Request

```json
{
  "error": {
    "code": "DOCUMENT_QUALITY_LOW",
    "message": "OCR confidence below threshold (62%). Please re-upload a clearer scan.",
    "details": { "confidence": 0.62, "threshold": 0.85 }
  },
  "request_id": "req_a1b2c3d4"
}
```

### 413 — Payload Too Large

```json
{
  "error": {
    "code": "DOCUMENT_TOO_LARGE",
    "message": "File size exceeds 10MB limit.",
    "details": { "size_bytes": 15728640, "max_bytes": 10485760 }
  },
  "request_id": "req_e5f6g7h8"
}
```

### 429 — Rate Limited

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again in 30 seconds.",
    "details": { "retry_after_seconds": 30, "limit": "10/minute" }
  },
  "request_id": "req_i9j0k1l2"
}
```

### 401 — Unauthorized

```json
{
  "error": {
    "code": "AUTHENTICATION_REQUIRED",
    "message": "Provide an X-API-Key header or Authorization: Bearer <token>.",
    "details": null
  },
  "request_id": "req_xyz"
}
```
