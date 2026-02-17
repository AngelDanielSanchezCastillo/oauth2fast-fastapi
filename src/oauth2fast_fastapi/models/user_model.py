from sqlmodel import (
    BigInteger,
    Column,
    Field,
)

from .bases import AuthModel


# Database model for User
# This model represents a user registered in the database
class User(AuthModel, table=True):
    __tablename__ = "users"

    id: int = Field(
        default=None, sa_column=Column(BigInteger, index=True, primary_key=True)
    )
    name: str = Field(index=True)
    email: str = Field(index=True, unique=True)
    password: str = Field()
    is_verified: bool = Field(default=False)
