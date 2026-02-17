from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..dependencies import get_auth_session
from ..mail import send_verification_email
from ..models.user_model import User
from ..schemas.user_schema import UserCreate, UserRead
from ..schemas.verification_schema import (
    EmailVerificationRequest,
    ResendVerificationRequest,
    VerificationResponse,
)
from ..settings import settings
from ..utils.password_utils import hash_password
from ..utils.verification_utils import (
    create_verification_token,
    verify_verification_token,
)

router = APIRouter(
    prefix=settings.auth_url_prefix.get_secret_value(),
    tags=[settings.auth_url_prefix.get_secret_value()[1:].capitalize()],
)


@router.post("/users/", response_model=UserRead)
async def create_auth_user(
    user_data: UserCreate, session: AsyncSession = Depends(get_auth_session)
) -> UserRead:
    """
    Create a new user with hashed password and send verification email.

    Args:
        user_data: User creation data with email, password, and name
        session: Database session

    Returns:
        Created user data

    Raises:
        HTTPException: If email already exists
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

        return UserRead(
            id=user.id,
            email=user.email,
            name=user.name,
            is_verified=user.is_verified,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="El email ya existe")


@router.get("/users/", response_model=list[UserRead])
async def read_auth_users(
    session: AsyncSession = Depends(get_auth_session),
) -> Sequence[UserRead]:
    """
    Get all users (for testing purposes).

    Args:
        session: Database session

    Returns:
        List of all users
    """
    result = await session.execute(select(User))
    users = result.scalars().all()

    return [
        UserRead(
            id=u.id,
            email=u.email,
            name=u.name,
            is_verified=u.is_verified,
            created_at=u.created_at,
            updated_at=u.updated_at,
        )
        for u in users
    ]


@router.get("/users/by-email/{email}", response_model=UserRead)
async def read_user_by_email(
    email: str,
    session: AsyncSession = Depends(get_auth_session),
) -> UserRead:
    """
    Read a user by email.

    Args:
        email: User email
        session: Database session

    Returns:
        User data

    Raises:
        HTTPException: If user not found
    """
    # Find user by email
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    return UserRead(
        id=user.id,
        email=user.email,
        name=user.name,
        is_verified=user.is_verified,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("/confirm-email", response_model=VerificationResponse)
async def confirm_email(
    request: EmailVerificationRequest,
    session: AsyncSession = Depends(get_auth_session),
) -> VerificationResponse:
    """
    Confirm user email with verification token.

    Args:
        request: Verification request with token
        session: Database session

    Returns:
        Verification response

    Raises:
        HTTPException: If token is invalid or user not found
    """
    # Verify token and extract email
    email = verify_verification_token(request.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de verificación inválido o expirado",
        )

    # Find user by email
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    # Check if already verified
    if user.is_verified:
        return VerificationResponse(
            message="El email ya ha sido verificado previamente",
            success=True,
        )

    # Mark user as verified
    user.is_verified = True
    session.add(user)
    await session.commit()

    return VerificationResponse(
        message="Email verificado exitosamente",
        success=True,
    )


@router.post("/resend-verification", response_model=VerificationResponse)
async def resend_verification(
    request: ResendVerificationRequest,
    session: AsyncSession = Depends(get_auth_session),
) -> VerificationResponse:
    """
    Resend verification email to user.

    Args:
        request: Resend request with email
        session: Database session

    Returns:
        Verification response

    Raises:
        HTTPException: If user not found or already verified
    """
    # Find user by email
    result = await session.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    # Check if already verified
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está verificado",
        )

    # Generate new verification token and send email
    verification_token = create_verification_token(user.email)
    verification_url = f"{settings.frontend_url}verify-email?token={verification_token}"

    await send_verification_email(user.email, verification_url)

    return VerificationResponse(
        message="Email de verificación enviado exitosamente",
        success=True,
    )
