from functools import partial

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pgsqlasync2fast_fastapi import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from .models.user_model import User
from .schemas.token_schema import TokenData
from .settings import settings
from .utils.token_utils import verify_token


# Dependency de Database para usar en endpoints
# Uses the "auth" connection from pgsqlasync2fast-fastapi
get_auth_session = partial(get_db_session, connection_name="auth")


# Dependency de Auth Base
oauth2_dependency = OAuth2PasswordBearer(
    tokenUrl=f"{settings.auth_url_prefix.get_secret_value()}/token"
)


async def get_current_user(
    token: str = Depends(oauth2_dependency),
    session: AsyncSession = Depends(get_auth_session),
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.

    Args:
        token: JWT token from Authorization header
        session: Database session

    Returns:
        Authenticated User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Verify and decode token
    payload = verify_token(token)
    if payload is None:
        raise credentials_exception

    # Extract email from token
    email: str | None = payload.get("sub")
    if email is None:
        raise credentials_exception

    token_data = TokenData(email=email)

    # Get user from database
    result = await session.execute(select(User).where(User.email == token_data.email))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user


async def get_current_verified_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to get the current authenticated and verified user.

    Args:
        current_user: Current authenticated user

    Returns:
        Verified User object

    Raises:
        HTTPException: If user is not verified
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified",
        )
    return current_user
