# Veritas API

FastAPI backend for the Veritas KYC/AML automation platform.

## Quick Start

```bash
# Install dependencies
uv sync --all-extras

# Run development server
uv run uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs at `/docs`.

## Prerequisites

- Python 3.12+
- PostgreSQL (configure via `DATABASE_URL`)
- Tesseract OCR (`brew install tesseract` on macOS)
- Google Cloud Vision API key (optional, for improved OCR accuracy)
- Better Auth server running (for JWT validation)

## Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `BETTER_AUTH_URL` | Better Auth server URL for JWKS | Yes (default: `http://localhost:3000`) |
| `UPLOAD_DIR` | Directory for uploaded files | No (default: `./uploads`) |
| `DOCUMENT_RETENTION_DAYS` | Days until documents expire (GDPR retention) | No (default: `30`) |
| `RATE_LIMIT_UPLOADS_PER_MINUTE` | Max document uploads per user per minute | No (default: `60`) |
| `WEB_CONCURRENCY` | Uvicorn worker processes (Docker/production) | No (default: `4` in Docker) |
| `DEBUG` | Enable debug mode | No (default: `false`) |
| `GOOGLE_VISION_ENABLED` | Enable Google Vision OCR fallback | No (default: `false`) |
| `GOOGLE_CLOUD_API_KEY` | Google Cloud API key | If Vision enabled |

## Authentication

The API uses JWT tokens issued by Better Auth (running in the Next.js app). Protected endpoints require a valid Bearer token in the Authorization header:

```bash
curl -H "Authorization: Bearer <jwt_token>" http://localhost:8000/v1/documents/upload
```

JWT tokens are validated using JWKS fetched from the Better Auth server at `{BETTER_AUTH_URL}/api/auth/jwks`.

## API Endpoints

### Health & Info (Public)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API info |
| `GET` | `/health` | Health check |

### Documents (Protected 🔒)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/documents/upload` | Upload document (returns **202 Accepted**; OCR runs in background) |
| `GET` | `/v1/documents/{id}/status` | Poll processing status until `completed` or `failed` |
| `GET` | `/v1/documents/{id}` | Get document by ID (includes `status` field) |

**Async upload flow:** Upload returns 202 with `document_id`, `status_url`, and `estimated_completion_seconds`. Poll `GET /v1/documents/{id}/status` (or `GET /v1/documents/{id}`) until `status` is `completed` or `failed`. Rate limit and concurrency are configurable via `RATE_LIMIT_UPLOADS_PER_MINUTE` (default 60) and `WEB_CONCURRENCY` (default 4 in Docker).

### KYC (Protected 🔒)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/kyc/process` | End-to-end KYC: upload + OCR + sanctions + adverse media + risk |
| `GET` | `/v1/kyc/{customer_id}` | Get aggregated KYC result for a customer |
| `POST` | `/v1/kyc/batch` | Get KYC results for multiple customers (max 10) |

### Sanctions Screening (Protected 🔒)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/screening/sanctions` | Screen a name against OFAC/UN sanctions |
| `POST` | `/v1/screening/sanctions/batch` | Batch screen up to 100 names |
| `POST` | `/v1/screening/document/{id}` | Screen names from a processed document |
| `GET` | `/v1/screening/sanctions/health` | Sanctions service status |

### Adverse Media & Risk Scoring (Protected 🔒)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/risk/adverse-media` | Scan name for adverse media (GDELT + VADER) |
| `POST` | `/v1/risk/adverse-media/document/{id}` | Scan document for adverse media |
| `POST` | `/v1/risk/score` | Score risk from features (LightGBM + SHAP) |
| `POST` | `/v1/risk/score/screening/{id}` | Score risk for screening result |
| `GET` | `/v1/risk/health` | Risk service status |

### Users & GDPR (Protected 🔒)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/v1/users/me/stats` | User statistics (documents, screenings, risk averages) |
| `GET` | `/v1/users/me/export` | Export all user data as JSON (GDPR data export) |
| `DELETE` | `/v1/users/me` | Delete all user data and files (right to be forgotten) |

## Multi-Tenancy

All user data is isolated by `user_id`. When authenticated, users can only access their own:
- Documents
- Screening results
- Risk assessments
- Audit logs

The `user_id` is extracted from the JWT token's `sub` claim.

## Features

- **Document Processing**: Async upload (202), background OCR for passports (MRZ), utility bills, business docs; PDF and HEIC/HEIF support; quality checks; poll `GET /v1/documents/{id}/status` for completion
- **End-to-End KYC**: Single endpoint chains OCR → sanctions → adverse media → risk scoring
- **Sanctions Screening**: OFAC + UN consolidated list with fuzzy matching
- **Adverse Media**: GDELT news search with VADER sentiment analysis
- **Risk Scoring**: LightGBM classifier with SHAP explanations
- **Audit Logging**: Immutable audit log for compliance (screening, risk, document actions)
- **GDPR**: Document retention (`expires_at` + cleanup script), data export (`GET /v1/users/me/export`), right to be forgotten (`DELETE /v1/users/me`)
- **Multi-Tenant Isolation**: All data filtered by authenticated user

## Testing

```bash
# Run all tests
uv run pytest

# Run specific test
uv run pytest tests/test_file.py::test_name

# Run with coverage
uv run pytest --cov=src
```

## Document retention (GDPR)

Documents have an `expires_at` timestamp (default: upload + `DOCUMENT_RETENTION_DAYS`). To delete expired documents and their files, run the cleanup script (e.g. daily via cron):

```bash
# From apps/api — ensure migrations are applied first
uv run alembic upgrade head
uv run python -m src.scripts.cleanup_expired_documents
```

If the script reports a missing `expires_at` column, run `uv run alembic upgrade head` then try again. Configure retention length with `DOCUMENT_RETENTION_DAYS` (default 30).

## Database Migrations

```bash
# Apply migrations
uv run alembic upgrade head

# Create new migration
uv run alembic revision --autogenerate -m "description"
```

> **Note**: Better Auth manages its own tables (`user`, `account`, `session`, `verification`, `jwks`). These should NOT be touched by Alembic migrations.
