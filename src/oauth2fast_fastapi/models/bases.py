from sqlmodel import MetaData, SQLModel

from tools2fast_fastapi import IdMixin, TimestampMixin

metadata = MetaData()

class BasicModel(SQLModel):
    __abstract__ = True
    metadata = metadata

class BasicAuthModel(TimestampMixin, BasicModel):
    """Base model without predefined primary key, but with timestamps."""

    __abstract__ = True

class IdAuthModel(IdMixin, BasicModel):
    """Base model with BigInteger primary key."""
    
    __abstract__ = True

class AuthModel(TimestampMixin, IdAuthModel):
    """Default base model with BigInteger primary key and timestamps."""

    __abstract__ = True
