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
from src.routers import documents_router, health_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan events for startup and shutdown."""
    # Startup: create tables if they don't exist (dev only)
    # In production, use Alembic migrations
    if settings.DEBUG:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(documents_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root() -> dict:
    """Root endpoint with API information."""
    return {
        "name": "Veritas API",
        "description": "KYC/AML Automation Platform",
        "version": "0.1.0",
        "docs": "/docs",
    }
