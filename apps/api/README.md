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

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API info |
| `GET` | `/health` | Health check |
| `POST` | `/v1/documents/upload` | Upload and process document |
| `GET` | `/v1/documents/{id}` | Get document by ID |

## Testing

```bash
# Run all tests
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
