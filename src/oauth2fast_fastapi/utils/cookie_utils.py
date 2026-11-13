"""Refresh token cookie helpers.

The refresh token travels in an httpOnly cookie scoped to the auth prefix
(``/auth`` by default). That path covers both ``/auth/token/refresh`` and
``/auth/logout`` while keeping the token out of every non-auth route.

``Secure`` defaults to ``True`` and can be disabled explicitly with
``REFRESH_COOKIE_SECURE=false`` for plain-HTTP dev/staging environments.
"""

from fastapi import Response

from ..settings import settings

REFRESH_COOKIE_NAME = "metal_erp_refresh_token"


def refresh_cookie_path() -> str:
    """Cookie path derived from ``AUTH_URL_PREFIX`` (e.g. ``/auth``)."""
    prefix = settings.auth_url_prefix.get_secret_value()
    if not prefix.startswith("/"):
        prefix = f"/{prefix}"
    return prefix.rstrip("/") or "/"


def set_refresh_cookie(response: Response, raw_token: str) -> None:
    """Attach the refresh cookie to the outgoing response."""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_token,
        max_age=settings.refresh_token_expire_minutes * 60,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite=settings.refresh_cookie_samesite,  # type: ignore[arg-type]
        path=refresh_cookie_path(),
    )


def clear_refresh_cookie(response: Response) -> None:
    """Remove the refresh cookie from the client."""
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=refresh_cookie_path(),
    )
