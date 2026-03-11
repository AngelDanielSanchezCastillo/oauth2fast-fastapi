from sqlmodel import Field

from .bases import AuthModel


# Database model for User
# This model represents a user registered in the database
class User(AuthModel, table=True):
    __tablename__ = "users"

    name: str = Field(index=True)
    email: str = Field(index=True, unique=True)
    password: str = Field()
    is_verified: bool = Field(default=False)
