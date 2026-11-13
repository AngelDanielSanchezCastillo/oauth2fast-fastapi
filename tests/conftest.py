"""Shared fixtures for the oauth2fast test suite.

Database-backed suites require PostgreSQL. Run them with the same
``DB_CONNECTIONS__AUTH__*`` environment used by ``test_integration.py``.
"""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
# The test client talks plain HTTP, so the Secure flag would prevent httpx from
# sending the refresh cookie. This mirrors the documented staging/dev setup.
os.environ.setdefault("REFRESH_COOKIE_SECURE", "false")

import pytest
from pgsqlasync2fast_fastapi import get_manager
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from oauth2fast_fastapi import AuthModel, User, shutdown_database, startup_database


@pytest.fixture
async def auth_engine():
    """Create the auth schema, yield the engine, then drop the tables."""
    await startup_database()
    manager = get_manager()
    engine = manager.get_engine("auth")

    async with engine.begin() as conn:
        await conn.run_sync(AuthModel.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        for table in reversed(AuthModel.metadata.sorted_tables):
            await conn.execute(text(f"DROP TABLE IF EXISTS {table.name} CASCADE"))

    await shutdown_database()


@pytest.fixture
async def auth_session(auth_engine):
    """Yield an ``AsyncSession`` bound to the auth engine."""
    async with AsyncSession(auth_engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture
async def verified_user(auth_session) -> User:
    """Persist and return a verified user."""
    user = User(
        email="refresh-owner@example.com",
        name="Refresh Owner",
        password="hashed",
        is_verified=True,
    )
    auth_session.add(user)
    await auth_session.commit()
    await auth_session.refresh(user)
    return user
