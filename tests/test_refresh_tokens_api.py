"""
API-level tests for refresh tokens and logout (0.6.0).

Exercises the full HTTP flow: login issues access + refresh (body and httpOnly
cookie), refresh rotates, reuse revokes the family, logout revokes the current
device and global logout revokes every session.

Requires PostgreSQL (same env as ``test_integration.py``).
"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pgsqlasync2fast_fastapi import get_manager
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession
from tools2fast_fastapi import install_auth_error_handler

from oauth2fast_fastapi import admin_router, public_router

COOKIE_NAME = "metal_erp_refresh_token"
PASSWORD = "SecurePassword123"


@pytest.fixture
async def api_client(auth_engine):
    """FastAPI app with the auth routers and the auth error handler."""
    app = FastAPI()
    install_auth_error_handler(app)
    app.include_router(public_router, tags=["Authentication"])
    app.include_router(admin_router, tags=["Authentication Admin"])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def _register_verified(client: AsyncClient, email: str) -> None:
    response = await client.post(
        "/auth/users/",
        json={"email": email, "password": PASSWORD, "name": "User"},
    )
    assert response.status_code == 200, response.text

    manager = get_manager()
    engine = manager.get_engine("auth")
    async with AsyncSession(engine, expire_on_commit=False) as session:
        await session.execute(
            text("UPDATE users SET is_verified = true WHERE email = :email"),
            {"email": email},
        )
        await session.commit()


async def _login(client: AsyncClient, email: str) -> dict:
    response = await client.post(
        "/auth/token",
        data={"username": email, "password": PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_login_returns_refresh_token_and_expires_in(api_client):
    """RED: login returns refresh_token and expires_in, and sets the cookie."""
    await _register_verified(api_client, "login-refresh@example.com")

    body = await _login(api_client, "login-refresh@example.com")

    token = body["token"]
    assert token["access_token"]
    assert token["refresh_token"]
    assert isinstance(token["expires_in"], int)
    assert token["expires_in"] > 0

    cookie = api_client.cookies.get(COOKIE_NAME)
    assert cookie is not None
    assert cookie == token["refresh_token"]


async def test_login_cookie_is_httponly_with_auth_path(api_client):
    """RED: the refresh cookie is httpOnly and scoped to /auth."""
    await _register_verified(api_client, "cookie-flags@example.com")

    response = await api_client.post(
        "/auth/token",
        data={"username": "cookie-flags@example.com", "password": PASSWORD},
    )

    set_cookie = response.headers.get("set-cookie", "")
    assert COOKIE_NAME in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Path=/auth" in set_cookie
    assert "SameSite=strict" in set_cookie.lower() or "SameSite=strict" in set_cookie


async def test_refresh_with_cookie_rotates(api_client):
    """RED: refreshing via the cookie returns a new access and a rotated refresh."""
    await _register_verified(api_client, "rotate-cookie@example.com")
    first = await _login(api_client, "rotate-cookie@example.com")
    old_refresh = first["token"]["refresh_token"]

    response = await api_client.post("/auth/token/refresh")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token"]["access_token"]
    assert body["token"]["refresh_token"]
    assert body["token"]["refresh_token"] != old_refresh


async def test_refresh_with_body_supports_non_browser_clients(api_client):
    """RED: refresh accepts the token in the JSON body (CLI/desktop clients)."""
    await _register_verified(api_client, "rotate-body@example.com")
    first = await _login(api_client, "rotate-body@example.com")
    refresh = first["token"]["refresh_token"]

    # A fresh client without cookies, sending the token in the body.
    app = api_client._transport.app  # type: ignore[attr-defined]
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as bare:
        response = await bare.post(
            "/auth/token/refresh", json={"refresh_token": refresh}
        )

    assert response.status_code == 200, response.text
    assert response.json()["token"]["access_token"]


async def test_refresh_without_token_returns_token_missing(api_client):
    """RED: no cookie and no body → 401 TokenMissing."""
    response = await api_client.post("/auth/token/refresh")

    assert response.status_code == 401
    assert response.json()["error"]["type"] == "TokenMissing"


async def test_refresh_with_invalid_token_returns_token_invalid(api_client):
    """RED: unknown refresh token → 401 TokenInvalid."""
    response = await api_client.post(
        "/auth/token/refresh", json={"refresh_token": "unknown"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["type"] == "TokenInvalid"


async def test_reuse_of_rotated_token_revokes_family(api_client):
    """RED: replaying an old refresh kills the whole family."""
    await _register_verified(api_client, "reuse@example.com")
    first = await _login(api_client, "reuse@example.com")
    old_refresh = first["token"]["refresh_token"]

    app = api_client._transport.app  # type: ignore[attr-defined]
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as bare:
        rotated = await bare.post(
            "/auth/token/refresh", json={"refresh_token": old_refresh}
        )
        assert rotated.status_code == 200
        new_refresh = rotated.json()["token"]["refresh_token"]
        bare.cookies.clear()

        # Replay the old token.
        replay = await bare.post(
            "/auth/token/refresh", json={"refresh_token": old_refresh}
        )
        assert replay.status_code == 401
        assert replay.json()["error"]["type"] == "TokenInvalid"
        bare.cookies.clear()

        # The rotated token belongs to the same family: it must be dead too.
        after = await bare.post(
            "/auth/token/refresh", json={"refresh_token": new_refresh}
        )
        assert after.status_code == 401


async def test_logout_revokes_current_device_only(api_client):
    """RED: normal logout revokes the current device, not other sessions."""
    await _register_verified(api_client, "logout@example.com")

    # Session A (current client).
    first = await _login(api_client, "logout@example.com")
    current_refresh = first["token"]["refresh_token"]

    # Session B (another device): a separate client with its own cookie.
    app = api_client._transport.app  # type: ignore[attr-defined]
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as other:
        other_body = await _login(other, "logout@example.com")
        other_refresh = other_body["token"]["refresh_token"]

        logout = await api_client.post("/auth/logout")
        assert logout.status_code == 200

        # Current device is dead.
        current = await api_client.post(
            "/auth/token/refresh", json={"refresh_token": current_refresh}
        )
        assert current.status_code == 401

        # Other device still works.
        still_alive = await other.post(
            "/auth/token/refresh", json={"refresh_token": other_refresh}
        )
        assert still_alive.status_code == 200


async def test_logout_all_revokes_every_session(api_client):
    """RED: global logout revokes every refresh token of the user."""
    await _register_verified(api_client, "logout-all@example.com")
    first = await _login(api_client, "logout-all@example.com")
    access = first["token"]["access_token"]
    refresh = first["token"]["refresh_token"]

    response = await api_client.post(
        "/auth/logout/all",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert response.status_code == 200

    after = await api_client.post(
        "/auth/token/refresh", json={"refresh_token": refresh}
    )
    assert after.status_code == 401


async def test_expired_refresh_reports_token_expired(api_client):
    """RED: an expired refresh token reports TokenExpired."""
    await _register_verified(api_client, "expired-refresh@example.com")
    first = await _login(api_client, "expired-refresh@example.com")
    refresh = first["token"]["refresh_token"]

    # Expire the record directly in the DB.
    manager = get_manager()
    engine = manager.get_engine("auth")
    from oauth2fast_fastapi.utils.token_utils import hash_refresh_token

    async with AsyncSession(engine, expire_on_commit=False) as session:
        await session.execute(
            text(
                "UPDATE oauth__refresh_tokens SET expires_at = now() - interval '1 minute' "
                "WHERE token_hash = :hash"
            ),
            {"hash": hash_refresh_token(refresh)},
        )
        await session.commit()

    response = await api_client.post(
        "/auth/token/refresh", json={"refresh_token": refresh}
    )
    assert response.status_code == 401
    assert response.json()["error"]["type"] == "TokenExpired"
