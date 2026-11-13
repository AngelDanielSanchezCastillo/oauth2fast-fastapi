from functools import partial

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from pgsqlasync2fast_fastapi import get_db_session
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from tools2fast_fastapi import AuthError

from .models.user_model import User
from .schemas.token_schema import TokenData
from .settings import settings
from .utils.token_utils import verify_token_detailed

# Dependency de Database para usar en endpoints
# Uses the "auth" connection from pgsqlasync2fast-fastapi
get_auth_session = partial(get_db_session, connection_name="auth")


# Dependency de Auth Base
# ``auto_error=False`` lets the dependency emit the project envelope for a
# missing token instead of FastAPI's default ``{"detail": ...}`` body.
oauth2_dependency = OAuth2PasswordBearer(
    tokenUrl=f"{settings.auth_url_prefix.get_secret_value()}/token",
    auto_error=False,
)


async def get_current_user(
    token: str | None = Depends(oauth2_dependency),
    session: AsyncSession = Depends(get_auth_session),
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.

    Args:
        token: JWT token from Authorization header (None when missing)
        session: Database session

    Returns:
        Authenticated User object, or a ready-to-return ``JSONResponse`` with
        the standardized auth error envelope when authentication fails.

    Raises:
        JSONResponse: 401 with ``error.type`` in
            ``TokenMissing`` / ``TokenExpired`` / ``TokenInvalid``.
    """
    if token is None:
        raise AuthError(
            error_code="TokenMissing",
            message="Credenciales no proporcionadas",
        )

    payload, reason = verify_token_detailed(token)

    if reason == "expired":
        raise AuthError(
            error_code="TokenExpired",
            message="Token expirado",
            www_authenticate='Bearer error="expired_token"',
        )

    if reason is not None or payload is None:
        raise AuthError(
            error_code="TokenInvalid",
            message="Token inválido",
            www_authenticate='Bearer error="invalid_token"',
        )

    # Extract email from token
    email: str | None = payload.get("sub")
    if email is None:
        raise AuthError(
            error_code="TokenInvalid",
            message="Token inválido",
            www_authenticate='Bearer error="invalid_token"',
        )

    token_data = TokenData(email=email)

    # Get user from database
    result = await session.exec(select(User).where(User.email == token_data.email))
    user = result.one_or_none()

    if user is None:
        # Do not leak whether the subject exists: same contract as a bad token.
        raise AuthError(
            error_code="TokenInvalid",
            message="Token inválido",
            www_authenticate='Bearer error="invalid_token"',
        )

    return user


async def get_current_verified_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to get the current authenticated and verified user.

    Args:
        current_user: Current authenticated user

    Returns:
        Verified User object, or a ready-to-return ``JSONResponse`` when the
        email is not verified.
    """
    if not current_user.is_verified:
        raise AuthError(
            error_code="EmailNotVerified",
            message="Email no verificado",
            status_code=403,
        )
    return current_user
