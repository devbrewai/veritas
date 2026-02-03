"""FastAPI dependencies for request handling."""

from src.dependencies.auth import get_current_user_id

__all__ = ["get_current_user_id"]
