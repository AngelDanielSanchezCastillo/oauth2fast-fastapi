from collections.abc import Sequence

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from tools2fast_fastapi import APIResponse

from ..dependencies import get_auth_session
from ..mail import send_verification_email
from ..models.user_model import User
from ..schemas.user_schema import UserCreate, UserRead
from ..schemas.response_schemas import (
    UserCreatedResponse,
    UserListResponse,
    UserSingleResponse,
    UserErrorResponse,
    UserResponse,
)
from ..schemas.verification_schema import (
    EmailVerificationRequest,
    ResendVerificationRequest,
)
from ..schemas.response_schemas import (
    EmailVerificationSuccessResponse,
    EmailVerificationErrorResponse,
    ResendVerificationSuccessResponse,
    ResendVerificationErrorResponse,
    VerificationResponseModel,
)
from ..settings import settings
from ..utils.password_utils import hash_password
from ..utils.verification_utils import (
    create_verification_token,
    verify_verification_token,
)

router = APIRouter()


@router.post(
    "/users/",
    response_model=UserCreatedResponse,
    responses={
        400: {"model": UserErrorResponse, "description": "Email already exists"},
    },
)
async def create_auth_user(
    user_data: UserCreate, session: AsyncSession = Depends(get_auth_session)
) -> JSONResponse | UserCreatedResponse:
    """
    Create a new user with hashed password and send verification email.

    Args:
        user_data: User creation data with email, password, and name
        session: Database session

    Returns:
        UserCreatedResponse with created user data

    Raises:
        JSONResponse: If email already exists (400)
    """
    # Hash the password before storing
    hashed_password = hash_password(user_data.password)

    # Create user with hashed password
    user = User(
        email=user_data.email,
        name=user_data.name,
        password=hashed_password,
    )
    session.add(user)
    try:
        await session.commit()
        await session.refresh(user)

        # Generate verification token and send email
        verification_token = create_verification_token(user.email)
        verification_url = (
            f"{settings.frontend_url}verify-email?token={verification_token}"
        )

        # Send verification email (non-blocking, errors are logged)
        try:
            await send_verification_email(user.email, verification_url)
        except Exception as e:
            # Log error but don't fail user creation
            print(f"Warning: Failed to send verification email: {e}")

        return UserCreatedResponse(
            user=UserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                is_verified=user.is_verified,
                created_at=str(user.created_at) if user.created_at else None,
                updated_at=str(user.updated_at) if user.updated_at else None,
            )
        )
    except IntegrityError:
        await session.rollback()
        error_resp, http_status = APIResponse.fail(
            message="El email ya existe",
            status_code=400,
        )
        return JSONResponse(status_code=http_status, content=error_resp.model_dump())


@router.get(
    "/users/",
    response_model=UserListResponse,
)
async def read_auth_users(
    session: AsyncSession = Depends(get_auth_session),
) -> UserListResponse:
    """
    Get all users (for testing purposes).

    Args:
        session: Database session

    Returns:
        UserListResponse with list of all users
    """
    result = await session.exec(select(User))
    users = result.all()

    user_responses = [
        UserResponse(
            id=u.id,
            email=u.email,
            name=u.name,
            is_verified=u.is_verified,
            created_at=str(u.created_at) if u.created_at else None,
            updated_at=str(u.updated_at) if u.updated_at else None,
        )
        for u in users
    ]

    return UserListResponse(
        users=user_responses,
        count=len(user_responses),
    )


@router.get(
    "/users/by-email/{email}",
    response_model=UserSingleResponse,
    responses={
        404: {"model": UserErrorResponse, "description": "User not found"},
    },
)
async def read_user_by_email(
    email: str,
    session: AsyncSession = Depends(get_auth_session),
) -> JSONResponse | UserSingleResponse:
    """
    Read a user by email.

    Args:
        email: User email
        session: Database session

    Returns:
        UserSingleResponse with user data

    Raises:
        JSONResponse: If user not found (404)
    """
    # Find user by email
    result = await session.exec(select(User).where(User.email == email))
    user = result.one_or_none()

    if not user:
        error_resp, http_status = APIResponse.fail(
            message="Usuario no encontrado",
            status_code=404,
        )
        return JSONResponse(status_code=http_status, content=error_resp.model_dump())

    return UserSingleResponse(
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            is_verified=user.is_verified,
            created_at=str(user.created_at) if user.created_at else None,
            updated_at=str(user.updated_at) if user.updated_at else None,
        )
    )


@router.post(
    "/confirm-email",
    response_model=EmailVerificationSuccessResponse,
    responses={
        400: {"model": EmailVerificationErrorResponse, "description": "Invalid token"},
        404: {"model": EmailVerificationErrorResponse, "description": "User not found"},
    },
)
async def confirm_email(
    request: EmailVerificationRequest,
    session: AsyncSession = Depends(get_auth_session),
) -> JSONResponse | EmailVerificationSuccessResponse:
    """
    Confirm user email with verification token.

    Args:
        request: Verification request with token
        session: Database session

    Returns:
        EmailVerificationSuccessResponse on success

    Raises:
        JSONResponse: If token is invalid (400) or user not found (404)
    """
    # Verify token and extract email
    email = verify_verification_token(request.token)
    if not email:
        error_resp, http_status = APIResponse.fail(
            message="Token de verificación inválido o expirado",
            status_code=400,
        )
        return JSONResponse(status_code=http_status, content=error_resp.model_dump())

    # Find user by email
    result = await session.exec(select(User).where(User.email == email))
    user = result.one_or_none()

    if not user:
        error_resp, http_status = APIResponse.fail(
            message="Usuario no encontrado",
            status_code=404,
        )
        return JSONResponse(status_code=http_status, content=error_resp.model_dump())

    # Check if already verified
    if user.is_verified:
        return EmailVerificationSuccessResponse(
            message="El email ya ha sido verificado previamente",
            data=VerificationResponseModel(
                message="El email ya ha sido verificado previamente",
                success=True,
            ),
        )

    # Mark user as verified
    user.is_verified = True
    session.add(user)
    await session.commit()

    return EmailVerificationSuccessResponse(
        message="Email verificado exitosamente",
        data=VerificationResponseModel(
            message="Email verificado exitosamente",
            success=True,
        ),
    )


@router.post(
    "/resend-verification",
    response_model=ResendVerificationSuccessResponse,
    responses={
        400: {"model": ResendVerificationErrorResponse, "description": "Already verified"},
        404: {"model": ResendVerificationErrorResponse, "description": "User not found"},
    },
)
async def resend_verification(
    request: ResendVerificationRequest,
    session: AsyncSession = Depends(get_auth_session),
) -> JSONResponse | ResendVerificationSuccessResponse:
    """
    Resend verification email to user.

    Args:
        request: Resend request with email
        session: Database session

    Returns:
        ResendVerificationSuccessResponse on success

    Raises:
        JSONResponse: If user not found (404) or already verified (400)
    """
    # Find user by email
    result = await session.exec(select(User).where(User.email == request.email))
    user = result.one_or_none()

    if not user:
        error_resp, http_status = APIResponse.fail(
            message="Usuario no encontrado",
            status_code=404,
        )
        return JSONResponse(status_code=http_status, content=error_resp.model_dump())

    # Check if already verified
    if user.is_verified:
        error_resp, http_status = APIResponse.fail(
            message="El email ya está verificado",
            status_code=400,
        )
        return JSONResponse(status_code=http_status, content=error_resp.model_dump())

    # Generate new verification token and send email
    verification_token = create_verification_token(user.email)
    verification_url = f"{settings.frontend_url}verify-email?token={verification_token}"

    await send_verification_email(user.email, verification_url)

    return ResendVerificationSuccessResponse(
        message="Email de verificación enviado exitosamente",
        data=VerificationResponseModel(
            message="Email de verificación enviado exitosamente",
            success=True,
        ),
    )
