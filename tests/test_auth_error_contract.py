"""
Integration tests for the auth error contract (0.6.0).

The protected dependency must return:

- 401 with ``error.type = TokenMissing`` and ``WWW-Authenticate: Bearer`` when
  no credentials are sent.
- 401 with ``error.type = TokenExpired`` and
  ``WWW-Authenticate: Bearer error="expired_token"`` for expired tokens.
- 401 with ``error.type = TokenInvalid`` (``error="invalid_token"``) for
  malformed/bad-signature tokens and for tokens whose user no longer exists.
- 200 for a valid token (backward compatibility).

These tests require PostgreSQL; run them with the same env as
``test_integration.py``.
"""

from datetime import timedelta

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from pgsqlasync2fast_fastapi import get_manager
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession
from tools2fast_fastapi import install_auth_error_handler

from oauth2fast_fastapi import (
    AuthModel,
    User,
    admin_router,
    get_current_user,
    public_router,
    shutdown_database,
    startup_database,
)
from oauth2fast_fastapi.utils.token_utils import create_access_token


@pytest.fixture(scope="module")
def app():
    """Create a FastAPI app with the auth routers and a protected route."""
    test_app = FastAPI()
    install_auth_error_handler(test_app)
    test_app.include_router(public_router, tags=["Authentication"])
    test_app.include_router(admin_router, tags=["Authentication Admin"])

    @test_app.get("/protected")
    async def protected_route(
        current_user: User = Depends(get_current_user),
    ) -> dict[str, str]:
        return {"message": f"Hello {current_user.email}!"}

    return test_app


@pytest.fixture
async def setup_database():
    """Create the auth tables and drop them afterwards."""
    await startup_database()
    manager = get_manager()
    engine = manager.get_engine("auth")

    async with engine.begin() as conn:
        await conn.run_sync(AuthModel.metadata.create_all)

    yield

    async with engine.begin() as conn:
        for table in reversed(AuthModel.metadata.sorted_tables):
            await conn.execute(text(f"DROP TABLE IF EXISTS {table.name} CASCADE"))

    await shutdown_database()


@pytest.fixture
async def client(app, setup_database):
    """Async test client bound to the app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _create_verified_user(client: AsyncClient, email: str) -> None:
    """Register a user and mark the email as verified directly in the DB."""
    response = await client.post(
        "/auth/users/",
        json={"email": email, "password": "SecurePassword123", "name": "User"},
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


async def test_missing_token_returns_token_missing(client: AsyncClient):
    """RED: no credentials → 401 TokenMissing with a Bearer challenge."""
    response = await client.get("/protected")

    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["type"] == "TokenMissing"
    assert response.headers.get("www-authenticate") == "Bearer"


async def test_expired_token_returns_token_expired(client: AsyncClient):
    """RED: expired token → 401 TokenExpired + expired_token challenge."""
    token = create_access_token(
        {"sub": "expired@example.com"},
        expires_delta=timedelta(seconds=-5),
    )

    response = await client.get(
        "/protected", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["type"] == "TokenExpired"
    assert response.headers.get("www-authenticate") == 'Bearer error="expired_token"'


async def test_malformed_token_returns_token_invalid(client: AsyncClient):
    """RED: malformed token → 401 TokenInvalid + invalid_token challenge."""
    response = await client.get(
        "/protected", headers={"Authorization": "Bearer not-a-jwt"}
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["type"] == "TokenInvalid"
    assert response.headers.get("www-authenticate") == 'Bearer error="invalid_token"'


async def test_unknown_user_returns_token_invalid(client: AsyncClient):
    """RED: valid token for a deleted user → 401 TokenInvalid (no enumeration)."""
    token = create_access_token({"sub": "ghost@example.com"})

    response = await client.get(
        "/protected", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["type"] == "TokenInvalid"
    assert response.headers.get("www-authenticate") == 'Bearer error="invalid_token"'


async def test_valid_token_still_works(client: AsyncClient):
    """RED: a valid token keeps working (backward compatibility)."""
    await _create_verified_user(client, "valid@example.com")
    token = create_access_token({"sub": "valid@example.com"})

    response = await client.get(
        "/protected", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert "valid@example.com" in response.json()["message"]
