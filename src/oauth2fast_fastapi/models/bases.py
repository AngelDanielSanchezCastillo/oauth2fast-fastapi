from sqlmodel import MetaData, SQLModel

from tools2fast_fastapi import TimestampMixin, UUIDIdMixin, SoftDeleteMixin

metadata = MetaData()


class BasicModel(SQLModel):
    __abstract__ = True
    metadata = metadata


class BasicAuthModel(TimestampMixin, BasicModel):
    """Base model without predefined primary key, but with timestamps."""

    __abstract__ = True


class IdAuthModel(UUIDIdMixin, BasicModel):
    """Base model with UUID v7 primary key."""

    __abstract__ = True


class AuthModel(TimestampMixin, IdAuthModel):
    """Default base model with UUID primary key and timestamps."""

    __abstract__ = True


class AuthSoftDeleteModel(SoftDeleteMixin, AuthModel):
    """Base model with UUID primary key, timestamps, and soft-delete."""

    __abstract__ = True
