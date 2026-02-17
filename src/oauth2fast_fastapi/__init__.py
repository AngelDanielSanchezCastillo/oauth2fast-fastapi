"""
OAuth2Fast-FastAPI - Fast and secure OAuth2 authentication for FastAPI
"""

from .__version__ import __version__
from .database import engine
from .dependencies import get_auth_session, get_current_user, get_current_verified_user
from .models.user_model import User
from .routers.base_router import router
from .settings import settings

__all__ = [
    "__version__",
    "engine",
    "get_auth_session",
    "get_current_user",
    "get_current_verified_user",
    "User",
    "router",
    "settings",
]
