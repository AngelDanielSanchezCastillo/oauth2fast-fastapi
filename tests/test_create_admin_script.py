"""Tests for the create_admin bootstrap script."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from oauth2fast_fastapi.scripts.create_admin import create_admin_user


@pytest.mark.asyncio
async def test_create_admin_user_creates_verified_user():
    """create_admin_user creates a user with is_verified=True."""
    session = AsyncMock()
    # Mock the commit and refresh to be no-ops
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    user = await create_admin_user(
        session=session,
        email="admin@example.com",
        password="StrongPassword123",
        name="Admin User",
    )

    # The user should be added to the session
    session.add.assert_called_once()
    session.commit.assert_called_once()

    # Verify user properties
    assert user.email == "admin@example.com"
    assert user.name == "Admin User"
    assert user.is_verified is True
    # Password should be hashed (not the plaintext)
    assert user.password != "StrongPassword123"


@pytest.mark.asyncio
async def test_create_admin_user_with_default_name():
    """create_admin_user uses email as default name when name is None."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    user = await create_admin_user(
        session=session,
        email="admin@example.com",
        password="StrongPassword123",
        name=None,
    )

    assert user.name == "Admin"


@pytest.mark.asyncio
async def test_create_admin_user_password_is_hashed():
    """create_admin_user hashes the password before storing."""
    from oauth2fast_fastapi.utils.password_utils import verify_password

    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    user = await create_admin_user(
        session=session,
        email="admin@example.com",
        password="MySecretPass123",
        name="Admin",
    )

    # The stored password should verify against the original
    assert verify_password("MySecretPass123", user.password)
    # And NOT against a different password
    assert not verify_password("WrongPassword", user.password)
