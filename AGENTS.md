# AGENTS.md

This file provides guidance to coding agents (Codex, Gemini, and similar tools) when working with code in this repository.

Use this as persistent project operating guidance. Keep instructions explicit, scoped, and actionable.

## Project Overview

Veritas is a KYC/AML automation platform for cross-border payments companies. It automates document extraction (OCR), sanctions screening, adverse media scanning, and ML-based risk scoring.

## Repository Structure

```text
veritas/
|- apps/
|  |- api/                    # Python FastAPI backend
|  |  |- main.py              # FastAPI application entry point
|  |  |- alembic/             # Database migrations
|  |  |- src/
|  |  |  |- config.py         # Settings from environment
|  |  |  |- database.py       # Async SQLAlchemy setup
|  |  |  |- models/           # SQLAlchemy models
|  |  |  |- schemas/          # Pydantic request/response schemas
|  |  |  |- routers/          # API endpoints
|  |  |  `- services/         # Business logic
|  |  |     |- ocr/           # OCR pipeline (preprocessor, detector, extractor)
|  |  |     `- parsers/       # Document parsers (passport MRZ)
|  |  `- tests/               # Pytest tests
|  `- web/                    # Next.js frontend
|- packages/
|  `- shared/                 # Shared utilities
`- docs/
   `- veritas-prd.md          # Product requirements document
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

# Build for production (required before frontend commits)
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

Always validate relevant changes before committing.

### API Changes

```bash
cd apps/api && uv run pytest
```

### Frontend Changes

```bash
cd apps/web && bun run build
```

Rule: for any frontend-related changes (components, pages, lib files, config), `bun run build` must pass before commit.

## Tech Stack

- Backend: Python 3.12, FastAPI, PostgreSQL
- Document Processing: Tesseract OCR, pytesseract, OpenCV, Pillow
- MRZ Parsing: mrz library for passport Machine Readable Zone
- ML/Risk Scoring: LightGBM, SHAP
- Auth: Better Auth (Next.js) + JWT validation (FastAPI via JWKS)
- Frontend: Next.js 16, React 19, Tailwind CSS, shadcn/ui

## Architecture Notes

- Multi-tenant design: all database queries filter by `user_id` extracted from JWT.
- Auth flow: Better Auth (Next.js) issues JWT, FastAPI validates via JWKS.
- Document processing: currently synchronous (async processing planned later).
- OCR pipeline: preprocess -> detect MRZ region -> extract text -> parse MRZ.
- Passport parser: uses TD3 format (2 lines x 44 characters).

## API Endpoints

- `GET /` - API info
- `GET /health` - Health check
- `POST /v1/documents/upload` - Upload and process document
- `GET /v1/documents/{document_id}` - Get document by ID

## Environment Variables

Copy `.env.example` to `.env` and configure:

- `DATABASE_URL` - PostgreSQL connection string
- `UPLOAD_DIR` - Directory for uploaded files
- `DEBUG` - Enable debug mode (creates tables on startup)

## Git Conventions

Follow Angular commit conventions:

```text
<type>(<scope>): <subject>

- Bullet point descriptions
- Use proper capitalization
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Rules:

- Do not include "Co-Authored-By" or AI-generated attribution comments.
- Use bullet points in the commit body to describe changes.
- Keep commits atomic: one logical change per commit.
- Commit methodically: stage and commit related changes together.

## Agent Operating Guidelines

- Read the nearest applicable instruction files before editing.
- Prefer small, scoped changes and verify the impacted area.
- Include concrete validation commands in execution plans.
- Do not stage unrelated files in the same commit.
- Record assumptions and blockers explicitly in final notes.
- Escalate privileges only when required for task completion.

## Instruction Precedence

When instructions conflict, apply them in this order:

1. Platform, system, and developer instructions.
2. The closest applicable `AGENTS.md` to the working directory.
3. Task-specific user request and constraints.

For discovery behavior, tools like Codex resolve `AGENTS.md` by walking up from the current working directory, so nested agent files can override root guidance for subprojects.
