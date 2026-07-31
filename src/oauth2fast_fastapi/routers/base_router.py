from datetime import datetime, timezone

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


def _days_since_creation(created_at: datetime | None) -> int:
    """
    Días transcurridos desde la creación del usuario (0 si no hay fecha).

    Si ``created_at`` es naive se asume UTC antes de restar, para evitar
    comparar zonas horarias distintas.
    """
    if created_at is None:
        return 0
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - created_at).days


@router.post(
    "/token",
    response_model=TokenSuccessResponse,
    responses={
        401: {"model": TokenErrorResponse, "description": "Invalid credentials"},
        403: {"model": TokenErrorResponse, "description": "Email not verified"},
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
        JSONResponse: If credentials are invalid (401) or email is not verified (403)
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

    # Verificación de email con periodo de gracia opcional (desactivada por defecto)
    grace_days = settings.verification_grace_days
    if settings.enforce_email_verification and not user.is_verified:
        # Sin periodo de gracia configurado: bloqueo inmediato
        if grace_days is None:
            error_resp, http_status = APIResponse.fail(
                message="Email no verificado. Verifica tu email antes de iniciar sesión.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
            return JSONResponse(
                status_code=http_status,
                content=error_resp.model_dump(),
            )

        # Con periodo de gracia: se bloquea solo si la cuenta excede los días permitidos
        if _days_since_creation(user.created_at) > grace_days:
            error_resp, http_status = APIResponse.fail(
                message=(
                    "Email no verificado. El periodo de gracia ha expirado. "
                    "Verifica tu email o solicita un nuevo enlace."
                ),
                status_code=status.HTTP_403_FORBIDDEN,
            )
            return JSONResponse(
                status_code=http_status,
                content=error_resp.model_dump(),
            )

    # Create access token
    access_token = create_access_token(data={"sub": user.email})

    return TokenSuccessResponse(
        token={"access_token": access_token, "token_type": "bearer"}
    )
