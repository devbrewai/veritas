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
| `POST` | `/v1/documents/upload` | Upload and process document (passport, utility bill) |
| `GET` | `/v1/documents/{id}` | Get document by ID |

### Sanctions Screening

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/v1/screening/sanctions` | Screen a name against OFAC/UN sanctions | Public |
| `POST` | `/v1/screening/sanctions/batch` | Batch screen up to 100 names | Public |
| `POST` | `/v1/screening/document/{id}` | Screen names from a processed document | 🔒 |
| `GET` | `/v1/screening/sanctions/health` | Sanctions service status | Public |

### Adverse Media & Risk Scoring

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/v1/risk/adverse-media` | Scan name for adverse media (GDELT + VADER) | Public |
| `POST` | `/v1/risk/adverse-media/document/{id}` | Scan document for adverse media | 🔒 |
| `POST` | `/v1/risk/score` | Score risk from features (LightGBM + SHAP) | Public |
| `POST` | `/v1/risk/score/screening/{id}` | Score risk for screening result | 🔒 |
| `GET` | `/v1/risk/health` | Risk service status | Public |

## Multi-Tenancy

All user data is isolated by `user_id`. When authenticated, users can only access their own:
- Documents
- Screening results
- Risk assessments

The `user_id` is extracted from the JWT token's `sub` claim.

## Features

- **Document Processing**: OCR extraction from passports (MRZ) and utility bills
- **Sanctions Screening**: OFAC + UN consolidated list with fuzzy matching
- **Adverse Media**: GDELT news search with VADER sentiment analysis
- **Risk Scoring**: LightGBM classifier with SHAP explanations
- **Multi-Tenant Isolation**: All data filtered by authenticated user

## Testing

```bash
# Run all tests (326 tests)
uv run pytest

# Run specific test
uv run pytest tests/test_file.py::test_name

# Run with coverage
uv run pytest --cov=src
```

## Database Migrations

```bash
# Apply migrations
uv run alembic upgrade head

# Create new migration
uv run alembic revision --autogenerate -m "description"
```

> **Note**: Better Auth manages its own tables (`user`, `account`, `session`, `verification`, `jwks`). These should NOT be touched by Alembic migrations.
