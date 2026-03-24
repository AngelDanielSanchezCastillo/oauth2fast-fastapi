from sqlmodel import SQLModel

from tools2fast_fastapi import TimestampMixin


class UserBase(SQLModel):
    email: str
    name: str


class UserCreate(UserBase):
    password: str


class UserRead(UserBase, TimestampMixin):
    id: int
    is_verified: bool
