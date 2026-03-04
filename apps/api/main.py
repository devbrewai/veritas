"""Veritas API - KYC/AML Automation Platform.

FastAPI application entry point with document processing,
OCR extraction, and risk scoring endpoints.
"""

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import get_settings
from src.exceptions import VeritasError
from src.schemas.errors import ErrorCode, ErrorDetail, ErrorResponse
from src.database import engine
from src.models import Base
from src.routers import (
    documents_router,
    health_router,
    kyc_router,
    risk_router,
    screening_router,
    users_router,
)
from src.services.adverse_media import adverse_media_service
from src.services.risk.scorer import risk_scoring_service
from src.services.sanctions import sanctions_screening_service

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan events for startup and shutdown."""
    # Startup: create tables if they don't exist (dev only)
    # In production, use Alembic migrations
    if settings.DEBUG:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # Initialize services
    sanctions_screening_service.initialize()
    adverse_media_service.initialize()
    risk_scoring_service.initialize()

    yield

    # Shutdown: dispose of database connections
    await engine.dispose()


app = FastAPI(
    title="Veritas KYC/AML API",
    description=(
        "Automate KYC document processing, sanctions screening, "
        "and risk assessment. One API call replaces your entire "
        "KYC pipeline. Under 15 seconds end-to-end."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={"name": "DevBrew", "url": "https://devbrew.ai"},
)

# CORS middleware - restrict origins for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Set X-Request-Id on request state and on response for tracing."""
    request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response


def _get_request_id(request: Request) -> str:
    """Get request_id from state (set by middleware)."""
    return getattr(request.state, "request_id", str(uuid.uuid4()))


@app.exception_handler(VeritasError)
async def veritas_error_handler(request: Request, exc: VeritasError) -> JSONResponse:
    """Return standardized error JSON for VeritasError."""
    request_id = _get_request_id(request)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=ErrorDetail(
                code=exc.code,
                message=exc.message,
                details=exc.details,
            ),
            request_id=request_id,
        ).model_dump(),
        headers={"X-Request-Id": request_id},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Convert HTTPException to standardized ErrorResponse shape."""
    request_id = _get_request_id(request)
    detail = exc.detail
    if isinstance(detail, dict):
        message = detail.get("message", str(detail))
        details = detail
    else:
        message = str(detail) if detail else "Request failed"
        details = None
    code = _http_status_to_code(exc.status_code)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=ErrorDetail(code=code, message=message, details=details),
            request_id=request_id,
        ).model_dump(),
        headers={"X-Request-Id": request_id},
    )


def _http_status_to_code(status_code: int) -> str:
    """Map HTTP status code to ErrorCode constant."""
    if status_code == 401:
        return ErrorCode.AUTHENTICATION_REQUIRED
    if status_code == 404:
        return ErrorCode.NOT_FOUND
    if status_code == 429:
        return ErrorCode.RATE_LIMIT_EXCEEDED
    if status_code == 413:
        return ErrorCode.DOCUMENT_TOO_LARGE
    if 400 <= status_code < 500:
        return ErrorCode.VALIDATION_ERROR
    return "INTERNAL_ERROR"


# Include routers
app.include_router(health_router)
app.include_router(documents_router, prefix=settings.API_V1_PREFIX)
app.include_router(kyc_router, prefix=settings.API_V1_PREFIX)
app.include_router(screening_router, prefix=settings.API_V1_PREFIX)
app.include_router(risk_router, prefix=settings.API_V1_PREFIX)
app.include_router(users_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root() -> dict:
    """Root endpoint with API information."""
    return {
        "name": "Veritas KYC/AML API",
        "description": "KYC/AML Automation Platform",
        "version": "1.0.0",
        "docs": "/docs",
    }
