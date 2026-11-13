from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from tools2fast_fastapi import APIResponse, AuthError, BaseSuccessResponse

from ..dependencies import get_auth_session, get_current_user
from ..models.user_model import User
from ..schemas.response_schemas import TokenErrorResponse, TokenSuccessResponse
from ..schemas.token_schema import RefreshTokenRequest
from ..settings import settings
from ..utils.cookie_utils import (
    REFRESH_COOKIE_NAME,
    clear_refresh_cookie,
    set_refresh_cookie,
)
from ..utils.password_utils import verify_password
from ..utils.refresh_token_service import (
    create_refresh_token_record,
    revoke_all_for_user,
    revoke_refresh_token,
    rotate_refresh_token,
    validate_refresh_token,
)
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


def _access_expires_in() -> int:
    """Access token lifetime in seconds (OAuth2 ``expires_in``)."""
    return settings.access_token_expire_minutes * 60


@router.post(
    "/token",
    response_model=TokenSuccessResponse,
    responses={
        401: {"model": TokenErrorResponse, "description": "Invalid credentials"},
        403: {"model": TokenErrorResponse, "description": "Email not verified"},
    },
)
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_auth_session),
) -> JSONResponse | TokenSuccessResponse:
    """
    OAuth2 compatible token login endpoint.

    Args:
        request: Incoming request (used for the device user-agent).
        response: Outgoing response (used to attach the refresh cookie).
        form_data: OAuth2 form with username (email) and password
        session: Database session

    Returns:
        TokenSuccessResponse with access_token, refresh_token and expires_in

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

    # Verificación de email: SIEMPRE exigida (incondicional desde 0.4.6).
    # enforce_email_verification ya no activa la verificación; solo controla
    # si se aplica la indulgencia de verification_grace_days (int o None).
    if not user.is_verified:
        # Sin indulgencia (flag False o grace_days None): bloqueo inmediato
        if (
            not settings.enforce_email_verification
            or settings.verification_grace_days is None
        ):
            error_resp, http_status = APIResponse.fail(
                message="Email no verificado. Verifica tu email antes de iniciar sesión.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
            return JSONResponse(
                status_code=http_status,
                content=error_resp.model_dump(),
            )

        # Con periodo de gracia: se bloquea solo si la cuenta excede los días permitidos
        if _days_since_creation(user.created_at) > settings.verification_grace_days:
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

    # Create access token and a new refresh family (one per login session).
    access_token = create_access_token(data={"sub": user.email})
    raw_refresh, _record = await create_refresh_token_record(
        session,
        user_id=user.id,
        family_id=uuid4(),
        device_info=request.headers.get("user-agent"),
    )
    await session.commit()

    set_refresh_cookie(response, raw_refresh)

    return TokenSuccessResponse(
        token={
            "access_token": access_token,
            "token_type": "bearer",
            "refresh_token": raw_refresh,
            "expires_in": _access_expires_in(),
        }
    )


@router.post(
    "/token/refresh",
    response_model=TokenSuccessResponse,
    responses={
        401: {"model": TokenErrorResponse, "description": "Invalid refresh token"},
    },
)
async def refresh_token(
    request: Request,
    response: Response,
    body: RefreshTokenRequest | None = Body(default=None),
    session: AsyncSession = Depends(get_auth_session),
) -> TokenSuccessResponse:
    """
    Rotate the refresh token and issue a new access token.

    The refresh token is read from the httpOnly cookie first; non-browser
    clients may send it in the JSON body instead.

    Raises:
        AuthError: 401 ``TokenMissing`` / ``TokenExpired`` / ``TokenInvalid``.
    """
    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_token and body is not None:
        raw_token = body.refresh_token

    record, reason = await validate_refresh_token(session, raw_token or "")

    if reason == "missing":
        raise AuthError(
            error_code="TokenMissing",
            message="Refresh token requerido",
        )
    if reason == "expired":
        raise AuthError(
            error_code="TokenExpired",
            message="Refresh token expirado",
            www_authenticate='Bearer error="expired_token"',
        )
    if reason in ("invalid", "revoked"):
        # On reuse the service already revoked the whole family: persist it.
        if reason == "revoked":
            await session.commit()
        raise AuthError(
            error_code="TokenInvalid",
            message="Refresh token inválido",
            www_authenticate='Bearer error="invalid_token"',
        )

    assert record is not None  # validated above

    user = await session.get(User, record.user_id)
    if user is None:
        raise AuthError(
            error_code="TokenInvalid",
            message="Refresh token inválido",
            www_authenticate='Bearer error="invalid_token"',
        )

    new_raw_refresh, _new_record = await rotate_refresh_token(
        session,
        record,
        device_info=request.headers.get("user-agent"),
    )
    await session.commit()

    access_token = create_access_token(data={"sub": user.email})
    set_refresh_cookie(response, new_raw_refresh)

    return TokenSuccessResponse(
        token={
            "access_token": access_token,
            "token_type": "bearer",
            "refresh_token": new_raw_refresh,
            "expires_in": _access_expires_in(),
        }
    )


@router.post("/logout", response_model=BaseSuccessResponse)
async def logout(
    request: Request,
    response: Response,
    body: RefreshTokenRequest | None = Body(default=None),
    session: AsyncSession = Depends(get_auth_session),
) -> BaseSuccessResponse:
    """
    Revoke the current device's refresh token and clear the cookie.

    Idempotent: an already invalid token still results in a clean logout.
    """
    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_token and body is not None:
        raw_token = body.refresh_token

    if raw_token:
        record, _reason = await validate_refresh_token(session, raw_token)
        if record is not None:
            await revoke_refresh_token(session, record)
        await session.commit()

    clear_refresh_cookie(response)
    return BaseSuccessResponse(message="Sesión cerrada")


@router.post("/logout/all", response_model=BaseSuccessResponse)
async def logout_all(
    response: Response,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_auth_session),
) -> BaseSuccessResponse:
    """
    Revoke every refresh token of the authenticated user (all devices).

    Raises:
        AuthError: 401 when the access token is missing/invalid/expired.
    """
    await revoke_all_for_user(session, current_user.id)
    await session.commit()

    clear_refresh_cookie(response)
    return BaseSuccessResponse(message="Se cerraron todas las sesiones")
