# Veritas

**KYC/AML Automation & Risk Scoring Platform**

Veritas automates customer onboarding verification for cross-border payments companies by processing KYC documents, screening against sanctions/adverse media, and assigning risk tiers in seconds instead of days.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Veritas                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────────────┐  │
│  │   Next.js    │      │  Better Auth │      │    FastAPI API       │  │
│  │   Frontend   │─────▶│  (JWT+JWKS)  │─────▶│    (Backend)         │  │
│  │  :3000       │      │              │      │    :8000             │  │
│  └──────────────┘      └──────────────┘      └──────────────────────┘  │
│                                                        │                │
│                                                        ▼                │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                        PostgreSQL                                 │  │
│  │  • Better Auth tables (user, session, jwks)                      │  │
│  │  • Application tables (documents, screening_results)              │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Quick start

```bash
# Clone and setup
git clone <repo-url>
cd veritas

# Start PostgreSQL (Docker)
make db-up

# Setup API
make api-setup
make api-migrate

# Setup Web
make web-setup

# Run both services
make dev
```

## Project Structure

```
veritas/
├── apps/
│   ├── api/          # FastAPI backend (Python)
│   └── web/          # Next.js frontend (TypeScript)
├── docs/
│   └── veritas-prd.md
├── packages/         # Shared utilities (future)
├── Makefile          # Development commands
└── docker-compose.yml
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Web (Next.js) | 3000 | Frontend + Better Auth |
| API (FastAPI) | 8000 | Backend API |
| PostgreSQL | 5432 | Database |

## Features

- **Document Processing**: OCR extraction from passports (MRZ) and utility bills
- **Sanctions Screening**: OFAC + UN consolidated list with fuzzy matching
- **Adverse Media**: GDELT news search with VADER sentiment analysis
- **Risk Scoring**: LightGBM classifier with SHAP explanations
- **Multi-Tenant**: Complete data isolation by user

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 16, React 19, Tailwind CSS, shadcn/ui |
| Auth | Better Auth (JWT + JWKS) |
| Backend | FastAPI, Python 3.12 |
| Database | PostgreSQL (Neon for production) |
| OCR | Tesseract, Google Vision (optional) |
| ML | LightGBM, SHAP |

## Development Commands

All commands are available via `make`:

```bash
# Database
make db-up          # Start PostgreSQL in Docker
make db-down        # Stop PostgreSQL
make db-reset       # Reset database (destroy + recreate)

# API (FastAPI)
make api-setup      # Install Python dependencies
make api-dev        # Run API dev server
make api-test       # Run all tests
make api-migrate    # Run database migrations

# Web (Next.js)
make web-setup      # Install Node dependencies
make web-dev        # Run web dev server
make web-build      # Build for production

# Combined
make dev            # Run both API and Web servers
make setup          # Setup entire project
make test           # Run all tests
```

## Environment Variables

### API (`apps/api/.env`)

```bash
DATABASE_URL=postgres://postgres:postgres@localhost:5432/veritas
BETTER_AUTH_URL=http://localhost:3000
UPLOAD_DIR=./uploads
DEBUG=true
```

### Web (`apps/web/.env.local`)

```bash
DATABASE_URL=postgres://postgres:postgres@localhost:5432/veritas
BETTER_AUTH_URL=http://localhost:3000
BETTER_AUTH_SECRET=your-secret-key-min-32-chars
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## API Documentation

When the API is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

```bash
# Run all API tests (326 tests)
make api-test

# Run specific test file
cd apps/api && uv run pytest tests/test_documents.py -v

# Run with coverage
cd apps/api && uv run pytest --cov=src
```

## Deployment

| Service | Platform | Notes |
|---------|----------|-------|
| Database | Neon | Serverless PostgreSQL |
| Backend | Render | Python web service |
| Frontend | Vercel | Next.js hosting |

## Documentation

- [API README](apps/api/README.md) - Backend setup and endpoints
- [Web README](apps/web/README.md) - Frontend setup and auth
- [PRD](docs/veritas-prd.md) - Product requirements

## License

Private - All rights reserved
