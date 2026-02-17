from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..dependencies import get_auth_session
from ..models.user_model import User
from ..schemas.token_schema import Token
from ..settings import settings
from ..utils.password_utils import verify_password
from ..utils.token_utils import create_access_token
from .users_router import router as users_router

# Ensure prefix starts with "/"
prefix = settings.auth_url_prefix.get_secret_value()
if not prefix.startswith("/"):
    prefix = f"/{prefix}"

router = APIRouter(
    prefix=prefix,
    tags=[prefix.strip("/").capitalize()],
)

# Include users router
router.include_router(users_router)


@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_auth_session),
) -> Token:
    """
    OAuth2 compatible token login endpoint.

    Args:
        form_data: OAuth2 form with username (email) and password
        session: Database session

    Returns:
        Token with access_token and token_type

    Raises:
        HTTPException: If credentials are invalid
    """
    # Get user by email (username in OAuth2 form)
    result = await session.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    # Verify user exists and password is correct
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token = create_access_token(data={"sub": user.email})

    return Token(access_token=access_token, token_type="bearer")
