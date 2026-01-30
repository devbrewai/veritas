from src.routers.documents import router as documents_router
from src.routers.health import router as health_router
from src.routers.screening import router as screening_router

__all__ = ["documents_router", "health_router", "screening_router"]
