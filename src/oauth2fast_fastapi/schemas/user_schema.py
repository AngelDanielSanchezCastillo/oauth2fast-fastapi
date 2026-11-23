from sqlmodel import SQLModel

from tools2fast_fastapi import TimestampMixin, UUIDIdMixin, SoftDeleteMixin


class UserBase(SQLModel):
    email: str
    name: str


class UserCreate(UserBase):
    password: str


class UserRead(UserBase, UUIDIdMixin, TimestampMixin, SoftDeleteMixin):
    is_verified: bool
