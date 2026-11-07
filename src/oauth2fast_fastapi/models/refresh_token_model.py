from datetime import datetime
from uuid import UUID

from sqlmodel import Field

from .bases import AuthModel


class RefreshToken(AuthModel, table=True):
    """Persisted refresh token (PostgreSQL is the source of truth).

    The raw token is never stored: only its SHA-256 hash. ``family_id`` groups
    every refresh token produced by one login session; replaying a rotated
    token revokes the whole family.
    """

    __tablename__ = "oauth__refresh_tokens"

    user_id: int = Field(foreign_key="users.id", index=True)
    token_hash: str = Field(index=True, unique=True, max_length=64)
    family_id: UUID = Field(index=True)
    device_info: str | None = Field(default=None, max_length=512)
    expires_at: datetime = Field(index=True)
    revoked_at: datetime | None = Field(default=None)
