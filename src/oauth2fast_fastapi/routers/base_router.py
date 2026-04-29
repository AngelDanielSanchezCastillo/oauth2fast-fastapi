from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from tools2fast_fastapi import APIResponse

from ..dependencies import get_auth_session
from ..models.user_model import User
from ..schemas.response_schemas import TokenSuccessResponse, TokenErrorResponse
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


@router.post(
    "/token",
    response_model=TokenSuccessResponse,
    responses={
        401: {"model": TokenErrorResponse, "description": "Invalid credentials"},
    },
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_auth_session),
) -> JSONResponse | TokenSuccessResponse:
    """
    OAuth2 compatible token login endpoint.

    Args:
        form_data: OAuth2 form with username (email) and password
        session: Database session

    Returns:
        TokenSuccessResponse with access_token and token_type

    Raises:
        JSONResponse: If credentials are invalid (401)
    """
    # Get user by email (username in OAuth2 form)
    result = await session.exec(select(User).where(User.email == form_data.username))
    user = result.one_or_none()

    # Verify user exists and password is correct
    if not user or not verify_password(form_data.password, user.password):
        error_resp, http_status = APIResponse.fail(
            message="Incorrect email or password",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
        return JSONResponse(
            status_code=http_status,
            content=error_resp.model_dump(),
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token = create_access_token(data={"sub": user.email})

    return TokenSuccessResponse(
        token={"access_token": access_token, "token_type": "bearer"}
    )
