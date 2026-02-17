from sqlmodel import SQLModel


class EmailVerificationRequest(SQLModel):
    """Request schema for email verification"""

    token: str


class ResendVerificationRequest(SQLModel):
    """Request schema for resending verification email"""

    email: str


class VerificationResponse(SQLModel):
    """Response schema for verification operations"""

    message: str
    success: bool = True
