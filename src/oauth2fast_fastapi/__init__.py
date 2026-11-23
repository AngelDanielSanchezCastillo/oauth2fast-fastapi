"""
OAuth2Fast-FastAPI - Fast and secure OAuth2 authentication for FastAPI
"""

# Register the oauth Alembic chain under the "auth" lane at import time
# (mirrors the register_seeder idiom; alembic-2fast change).
from . import migrations as _migrations  # noqa: F401
from .__version__ import __version__
from .database import (
    get_db_engine,
    get_db_session,
    shutdown_database,
    startup_database,
)
from .dependencies import get_auth_session, get_current_user, get_current_verified_user
from .models.bases import AuthModel, AuthSoftDeleteModel, BasicAuthModel
from .models.refresh_token_model import RefreshToken
from .models.user_model import User
from .routers.admin_router import router as admin_router
from .routers.public_router import router as public_router
from .schemas.user_schema import UserCreate, UserRead
from .settings import settings
from .utils.token_utils import (
    create_refresh_token,
    hash_refresh_token,
    verify_token_detailed,
)

__all__ = [
    "AuthModel",
    "AuthSoftDeleteModel",
    "BasicAuthModel",
    "RefreshToken",
    "User",
    "UserCreate",
    "UserRead",
    "__version__",
    "admin_router",
    "create_refresh_token",
    "get_auth_session",
    "get_current_user",
    "get_current_verified_user",
    "get_db_engine",
    "get_db_session",
    "hash_refresh_token",
    "public_router",
    "settings",
    "shutdown_database",
    "startup_database",
    "verify_token_detailed",
]
