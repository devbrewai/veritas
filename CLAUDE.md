# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Veritas is a KYC/AML automation platform for cross-border payments companies. It automates document extraction (OCR), sanctions screening, adverse media scanning, and ML-based risk scoring.

## Repository Structure

```
veritas/
├── apps/
│   ├── api/                    # Python FastAPI backend
│   │   ├── main.py             # FastAPI application entry point
│   │   ├── alembic/            # Database migrations
│   │   ├── src/
│   │   │   ├── config.py       # Settings from environment
│   │   │   ├── database.py     # Async SQLAlchemy setup
│   │   │   ├── models/         # SQLAlchemy models
│   │   │   ├── schemas/        # Pydantic request/response schemas
│   │   │   ├── routers/        # API endpoints
│   │   │   └── services/       # Business logic
│   │   │       ├── ocr/        # OCR pipeline (preprocessor, detector, extractor)
│   │   │       └── parsers/    # Document parsers (passport MRZ)
│   │   └── tests/              # Pytest tests
│   └── web/                    # Next.js 14 frontend (to be built)
├── packages/
│   └── shared/                 # Shared utilities (to be built)
└── docs/
    └── veritas-prd.md          # Product requirements document
```

## Development Commands

### Backend (apps/api)

```bash
cd apps/api

# Install dependencies (uses uv package manager)
uv sync --all-extras

# Run development server
uv run uvicorn main:app --reload --port 8000

# Run tests
uv run pytest
uv run pytest tests/test_file.py::test_name  # Single test

# Database migrations (requires PostgreSQL running)
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "description"

# Add a dependency
uv add <package>
uv add --dev <package>  # Dev dependency
```

### Frontend (apps/web) - To be implemented

```bash
cd apps/web
bun install
bun dev
```

## Tech Stack

**Backend:** Python 3.12, FastAPI, PostgreSQL, Redis
**Document Processing:** Tesseract OCR, pytesseract, OpenCV, Pillow
**MRZ Parsing:** mrz library for passport Machine Readable Zone
**ML/Risk Scoring:** LightGBM, SHAP (to be added)
**Auth:** Better Auth (to be added)
**Frontend:** Next.js 14, Tailwind CSS, Shadcn/UI (to be built)

## Architecture Notes

- Multi-tenant design: all database queries must filter by `user_id` (to be added in Day 5)
- Document processing is synchronous for Day 1 (will be async in Day 6)
- OCR pipeline: preprocess → detect MRZ region → extract text → parse MRZ
- Passport parser uses TD3 format (2 lines × 44 characters)

## Current API Endpoints

- `GET /` - API info
- `GET /health` - Health check
- `POST /v1/documents/upload` - Upload and process document
- `GET /v1/documents/{document_id}` - Get document by ID

## External Dependencies

- **Tesseract OCR**: Must be installed system-wide (`brew install tesseract` on macOS)
- **PostgreSQL**: Required for document metadata (configure via DATABASE_URL in .env)

## Environment Variables

Copy `.env.example` to `.env` and configure:
- `DATABASE_URL` - PostgreSQL connection string
- `UPLOAD_DIR` - Directory for uploaded files
- `DEBUG` - Enable debug mode (creates tables on startup)

## Frontend Patterns

- Server components by default; use `'use client'` for interactive components
- Path aliases: `@/components`, `@/data`, `@/layouts`, `@/lib`, `@/modules`
- Folders prefixed with `_` (e.g., `app/_insights`) don't create routes
- Site config centralized in `data/siteMetadata.js`

## Git Conventions

Follow Angular commit conventions:

```
<type>(<scope>): <subject>

- Bullet point descriptions
- Use proper capitalization
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Rules:**

- Do not include "Co-Authored-By" or any AI-generated attribution comments
- Use bullet points in the commit body to describe changes
- Keep commits atomic: one logical change per commit
- Commit methodically: stage and commit related changes together