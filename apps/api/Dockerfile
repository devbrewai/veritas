# =============================================================================
# Stage 1: Builder
# =============================================================================
FROM python:3.12-slim AS builder

# Install build-time system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:0.6 /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install production dependencies only (exact versions from lockfile)
RUN uv sync --frozen --no-dev --no-editable

# Copy application source
COPY main.py alembic.ini ./
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY models/ ./models/

# =============================================================================
# Stage 2: Runtime
# =============================================================================
FROM python:3.12-slim AS runtime

LABEL maintainer="DevBrew"
LABEL description="Veritas API - KYC/AML Automation Platform"

# Install runtime-only system dependencies
#   tesseract-ocr + eng: OCR engine for document processing
#   poppler-utils: pdf2image requires pdftoppm
#   libgl1 + libglib2.0-0: OpenCV runtime dependencies
#   libpq5: asyncpg PostgreSQL client library
#   curl: health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 veritas && \
    useradd --uid 1000 --gid veritas --shell /bin/bash --create-home veritas

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application from builder
COPY --from=builder /app/main.py /app/alembic.ini ./
COPY --from=builder /app/src/ ./src/
COPY --from=builder /app/alembic/ ./alembic/
COPY --from=builder /app/models/ ./models/

# Create writable uploads directory
RUN mkdir -p /app/uploads && chown -R veritas:veritas /app

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Python production settings
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Application defaults (overridden by Render env vars)
ENV UPLOAD_DIR=/app/uploads \
    SANCTIONS_PICKLE_PATH=/app/models/sanctions_screener.pkl \
    DEBUG=false

# Switch to non-root user
USER veritas

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Run migrations then start server
# Using exec so uvicorn replaces the shell as PID 1 (proper signal handling)
CMD ["sh", "-c", "python -m alembic upgrade head && exec python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-1} --log-level info --access-log --proxy-headers --forwarded-allow-ips='*'"]
