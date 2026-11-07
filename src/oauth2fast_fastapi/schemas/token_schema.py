from sqlmodel import SQLModel


class Token(SQLModel):
    """OAuth2 token response schema"""

    access_token: str
    token_type: str = "bearer"


class TokenData(SQLModel):
    """Data extracted from JWT token"""

    email: str | None = None


class RefreshTokenRequest(SQLModel):
    """Optional refresh token sent in the request body.

    Browser clients use the httpOnly cookie; non-browser clients (CLI,
    desktop, tests) may send the token in the JSON body instead.
    """

    refresh_token: str | None = None
