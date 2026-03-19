"""
OAuth2Fast-FastAPI - Fast and secure OAuth2 authentication for FastAPI
"""

from .__version__ import __version__
from .database import (
    get_db_engine,
    get_db_session,
    shutdown_database,
    startup_database,
)
from .dependencies import get_auth_session, get_current_user, get_current_verified_user
from .models.bases import AuthModel, BasicAuthModel
from .models.user_model import User
from .routers.base_router import router
from .schemas.user_schema import UserCreate, UserRead
from .settings import settings

__all__ = [
    "__version__",
    # Database utilities
    "get_db_session",
    "get_db_engine",
    "startup_database",
    "shutdown_database",
    # Authentication dependencies
    "get_auth_session",
    "get_current_user",
    "get_current_verified_user",
    # Models and schemas
    "AuthModel",
    "BasicAuthModel",
    "User",
    "UserCreate",
    "UserRead",
    # Router
    "router",
    # Settings
    "settings",
]
