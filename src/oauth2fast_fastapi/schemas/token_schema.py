from sqlmodel import SQLModel


class Token(SQLModel):
    """OAuth2 token response schema"""

    access_token: str
    token_type: str = "bearer"


class TokenData(SQLModel):
    """Data extracted from JWT token"""

    email: str | None = None
