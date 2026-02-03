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

### Frontend (apps/web)

```bash
cd apps/web

# Install dependencies
bun install

# Run development server
bun dev

# Build for production (REQUIRED before commits)
bun run build

# Lint
bun lint
```

### Using Makefile (Recommended)

```bash
# From project root
make setup        # Setup entire project
make dev          # Run both API and Web servers
make api-test     # Run API tests
make web-build    # Build web app
```

## Testing Requirements

**IMPORTANT: Always test before committing changes.**

### API Changes
```bash
cd apps/api && uv run pytest
```

### Frontend Changes
```bash
cd apps/web && bun run build
```

**Rule:** For any frontend-related changes (components, pages, lib files, config), you MUST run `bun run build` successfully before committing. TypeScript errors caught during build must be fixed before the commit.

## Tech Stack

**Backend:** Python 3.12, FastAPI, PostgreSQL
**Document Processing:** Tesseract OCR, pytesseract, OpenCV, Pillow
**MRZ Parsing:** mrz library for passport Machine Readable Zone
**ML/Risk Scoring:** LightGBM, SHAP
**Auth:** Better Auth (Next.js) + JWT validation (FastAPI via JWKS)
**Frontend:** Next.js 16, React 19, Tailwind CSS, shadcn/ui

## Architecture Notes

- **Multi-tenant design:** All database queries filter by `user_id` extracted from JWT
- **Auth flow:** Better Auth (Next.js) issues JWT → FastAPI validates via JWKS
- **Document processing:** Currently synchronous (async processing in Day 6)
- **OCR pipeline:** preprocess → detect MRZ region → extract text → parse MRZ
- **Passport parser:** Uses TD3 format (2 lines × 44 characters)

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