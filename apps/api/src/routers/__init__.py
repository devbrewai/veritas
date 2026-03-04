from src.routers.api_keys import router as api_keys_router
from src.routers.documents import router as documents_router
from src.routers.health import router as health_router
from src.routers.kyc import router as kyc_router
from src.routers.risk import router as risk_router
from src.routers.screening import router as screening_router
from src.routers.users import router as users_router
from src.routers.webhooks import router as webhooks_router

__all__ = [
    "api_keys_router",
    "documents_router",
    "health_router",
    "kyc_router",
    "risk_router",
    "screening_router",
    "users_router",
    "webhooks_router",
]
