from sqlmodel import MetaData, SQLModel

from .mixins import IdMixin, TimestampMixin

metadata = MetaData()


class BasicAuthModel(TimestampMixin, SQLModel):
    """Base model without predefined primary key, but with timestamps."""

    __abstract__ = True
    metadata = metadata


class AuthModel(IdMixin, BasicAuthModel):
    """Default base model with BigInteger primary key and timestamps."""

    __abstract__ = True
