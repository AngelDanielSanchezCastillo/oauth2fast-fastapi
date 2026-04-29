"""
Response schemas for oauth2fast API endpoints.

These schemas provide unified API response format with success/error patterns.
"""

from typing import Literal
from pydantic import BaseModel

from tools2fast_fastapi import ErrorDetail


# ============ Token/Auth Responses ============

class TokenResponse(BaseModel):
    """Response for token data."""
    access_token: str
    token_type: str = "bearer"


class TokenSuccessResponse(BaseModel):
    """Successful token response."""
    success: Literal[True] = True
    message: str = "Éxito"
    token: TokenResponse


class TokenErrorResponse(BaseModel):
    """Error response for token operations."""
    success: Literal[False] = False
    error_type: Literal["controlled"] = "controlled"
    message: str
    error: ErrorDetail | None = None


class TokenUnexpectedErrorResponse(BaseModel):
    """Unexpected error response for token operations."""
    success: Literal[False] = False
    error_type: Literal["unexpected"] = "unexpected"
    message: str = "Ha ocurrido un error"
    error: ErrorDetail | None = None


# ============ User Responses ============

class UserResponse(BaseModel):
    """Response for user data."""
    id: int
    email: str
    name: str
    is_verified: bool
    created_at: str | None = None
    updated_at: str | None = None


class UserCreatedResponse(BaseModel):
    """Successful user creation response."""
    success: Literal[True] = True
    message: str = "Usuario creado exitosamente"
    user: UserResponse


class UserListResponse(BaseModel):
    """Successful user list response."""
    success: Literal[True] = True
    message: str = "Éxito"
    users: list[UserResponse]
    count: int


class UserSingleResponse(BaseModel):
    """Successful single user response."""
    success: Literal[True] = True
    message: str = "Éxito"
    user: UserResponse


class UserErrorResponse(BaseModel):
    """Error response for user operations."""
    success: Literal[False] = False
    error_type: Literal["controlled"] = "controlled"
    message: str
    error: ErrorDetail | None = None


class UserUnexpectedErrorResponse(BaseModel):
    """Unexpected error response for user operations."""
    success: Literal[False] = False
    error_type: Literal["unexpected"] = "unexpected"
    message: str = "Ha ocurrido un error"
    error: ErrorDetail | None = None


# ============ Verification Responses ============

class VerificationResponseModel(BaseModel):
    """Response for verification operations."""
    message: str
    success: bool = True


class EmailVerificationSuccessResponse(BaseModel):
    """Successful email verification response."""
    success: Literal[True] = True
    message: str
    data: VerificationResponseModel | None = None


class EmailVerificationErrorResponse(BaseModel):
    """Error response for email verification."""
    success: Literal[False] = False
    error_type: Literal["controlled"] = "controlled"
    message: str
    error: ErrorDetail | None = None


class EmailVerificationUnexpectedErrorResponse(BaseModel):
    """Unexpected error response for email verification."""
    success: Literal[False] = False
    error_type: Literal["unexpected"] = "unexpected"
    message: str = "Ha ocurrido un error"
    error: ErrorDetail | None = None


class ResendVerificationSuccessResponse(BaseModel):
    """Successful resend verification response."""
    success: Literal[True] = True
    message: str
    data: VerificationResponseModel | None = None


class ResendVerificationErrorResponse(BaseModel):
    """Error response for resend verification."""
    success: Literal[False] = False
    error_type: Literal["controlled"] = "controlled"
    message: str
    error: ErrorDetail | None = None


class ResendVerificationUnexpectedErrorResponse(BaseModel):
    """Unexpected error response for resend verification."""
    success: Literal[False] = False
    error_type: Literal["unexpected"] = "unexpected"
    message: str = "Ha ocurrido un error"
    error: ErrorDetail | None = None
