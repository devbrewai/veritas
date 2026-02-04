"""Veritas API - KYC/AML Automation Platform.

FastAPI application entry point with document processing,
OCR extraction, and risk scoring endpoints.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
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
    title="Veritas API",
    description="KYC/AML Automation Platform - Document extraction, sanctions screening, and risk scoring",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware - restrict origins for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        "name": "Veritas API",
        "description": "KYC/AML Automation Platform",
        "version": "0.1.0",
        "docs": "/docs",
    }
