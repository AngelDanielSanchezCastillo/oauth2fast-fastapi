import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from jose import ExpiredSignatureError, JWTError, jwt

from ..settings import settings


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Dictionary containing the data to encode in the token
        expires_delta: Optional custom expiration time delta

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm,
    )
    return encoded_jwt


def verify_token_detailed(token: str) -> tuple[dict | None, str | None]:
    """
    Verify and decode a JWT token, preserving the failure reason.

    Args:
        token: JWT token string to verify

    Returns:
        A ``(payload, reason)`` tuple. ``payload`` is the decoded claims when
        the token is valid, otherwise ``None``. ``reason`` is ``None`` for a
        valid token, or one of:

        - ``"malformed"`` — not a three-part JWT string.
        - ``"expired"`` — signature valid but ``exp`` is in the past.
        - ``"invalid"`` — bad signature or any other decoding failure.
    """
    # Structural check first: a JWT always has three dot-separated segments.
    if not token or token.count(".") != 2:
        return None, "malformed"

    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm],
        )
        return payload, None
    except ExpiredSignatureError:
        return None, "expired"
    except JWTError:
        return None, "invalid"


def verify_token(token: str) -> dict | None:
    """
    Verify and decode a JWT token.

    Backward-compatible wrapper: returns the payload when valid and ``None``
    otherwise, discarding the failure reason.

    Args:
        token: JWT token string to verify

    Returns:
        Decoded token payload if valid, None otherwise
    """
    payload, _reason = verify_token_detailed(token)
    return payload


def create_refresh_token() -> str:
    """
    Create a high-entropy opaque refresh token.

    Returns:
        URL-safe random string, never stored in plaintext.
    """
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    """
    Hash a refresh token for storage and lookup.

    Args:
        token: Raw refresh token.

    Returns:
        SHA-256 hex digest (64 characters).
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
