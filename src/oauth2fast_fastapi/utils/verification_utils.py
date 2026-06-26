from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from ..settings import settings


def build_verification_url(token: str) -> str:
    """
    Build the full verification URL for email verification emails.

    Normalizes ``settings.frontend_url`` regardless of trailing slash, so
    callers always get a correct URL without duplicated or missing slashes.

    Args:
        token: JWT verification token string

    Returns:
        Full verification URL pointing to the frontend verify-email page
    """
    base = settings.frontend_url.rstrip("/")
    return f"{base}/verify-email?token={token}"


def create_verification_token(email: str) -> str:
    """
    Create a JWT verification token for email verification.

    Args:
        email: User's email address

    Returns:
        Encoded JWT token string valid for 24 hours
    """
    expire = datetime.now(UTC) + timedelta(hours=24)
    to_encode = {"sub": email, "exp": expire, "type": "email_verification"}

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm,
    )
    return encoded_jwt


def verify_verification_token(token: str) -> str | None:
    """
    Verify and decode an email verification token.

    Args:
        token: JWT verification token string

    Returns:
        Email address if token is valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm],
        )

        # Verify token type
        if payload.get("type") != "email_verification":
            return None

        email: str | None = payload.get("sub")
        return email
    except JWTError:
        return None
