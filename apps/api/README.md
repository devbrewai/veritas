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

## Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `UPLOAD_DIR` | Directory for uploaded files | No (default: `./uploads`) |
| `DEBUG` | Enable debug mode | No (default: `false`) |
| `GOOGLE_VISION_ENABLED` | Enable Google Vision OCR fallback | No (default: `false`) |
| `GOOGLE_CLOUD_API_KEY` | Google Cloud API key | If Vision enabled |

## API Endpoints

### Health & Info

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API info |
| `GET` | `/health` | Health check |

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/documents/upload` | Upload and process document (passport, utility bill) |
| `GET` | `/v1/documents/{id}` | Get document by ID |

### Sanctions Screening

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/screening/sanctions` | Screen a name against OFAC/UN sanctions |
| `POST` | `/v1/screening/sanctions/batch` | Batch screen up to 100 names |
| `POST` | `/v1/screening/document/{id}` | Screen names from a processed document |
| `GET` | `/v1/screening/sanctions/health` | Sanctions service status |

### Adverse Media & Risk Scoring

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/risk/adverse-media` | Scan name for adverse media (GDELT + VADER) |
| `POST` | `/v1/risk/adverse-media/document/{id}` | Scan document for adverse media |
| `POST` | `/v1/risk/score` | Score risk from features (LightGBM + SHAP) |
| `POST` | `/v1/risk/score/screening/{id}` | Score risk for screening result |
| `GET` | `/v1/risk/health` | Risk service status |

## Features

- **Document Processing**: OCR extraction from passports (MRZ) and utility bills
- **Sanctions Screening**: OFAC + UN consolidated list with fuzzy matching
- **Adverse Media**: GDELT news search with VADER sentiment analysis
- **Risk Scoring**: LightGBM classifier with SHAP explanations

## Testing

```bash
# Run all tests (300+ tests)
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
