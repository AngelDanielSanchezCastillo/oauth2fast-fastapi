"""
Admin authentication router.

Endpoints that require admin privileges:
- List users
- Get user by email

This router does NOT include RBAC. The consumer must inject RBAC when mounting:

    from oauth2fast_fastapi import admin_router
    from permissions2fast_fastapi import has_role
    from fastapi import Depends

    app.include_router(admin_router, dependencies=[Depends(has_role("admin"))])
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from tools2fast_fastapi import APIResponse

from ..dependencies import get_auth_session
from ..models.user_model import User
from ..schemas.response_schemas import (
    UserErrorResponse,
    UserListResponse,
    UserResponse,
    UserSingleResponse,
)

# Ensure prefix starts with "/"
from ..settings import settings

prefix = settings.auth_url_prefix.get_secret_value()
if not prefix.startswith("/"):
    prefix = f"/{prefix}"

router = APIRouter(
    prefix=prefix,
    tags=[f"{prefix.strip('/').capitalize()} Admin"],
)


@router.get(
    "/users/",
    response_model=UserListResponse,
)
async def read_auth_users(
    session: AsyncSession = Depends(get_auth_session),
) -> UserListResponse:
    """
    Get all users.

    This is an ADMIN endpoint. The consumer must inject RBAC when mounting
    the admin_router, e.g.:

        app.include_router(admin_router, dependencies=[Depends(has_role("admin"))])

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
            deleted_at=str(u.deleted_at) if u.deleted_at else None,
            deleted_by=u.deleted_by,
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

    This is an ADMIN endpoint. The consumer must inject RBAC when mounting
    the admin_router, e.g.:

        app.include_router(admin_router, dependencies=[Depends(has_role("admin"))])

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
            deleted_at=str(user.deleted_at) if user.deleted_at else None,
            deleted_by=user.deleted_by,
        )
    )
