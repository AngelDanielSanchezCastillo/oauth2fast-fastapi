"""
Tests for the optional Redis cache of refresh tokens.

The database remains the source of truth. These tests prove that the cache is
used when available, is a no-op when unavailable, and that any cache error
falls back to the database.
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlmodel import delete

from oauth2fast_fastapi.models.refresh_token_model import RefreshToken
from oauth2fast_fastapi.utils import refresh_cache
from oauth2fast_fastapi.utils.refresh_token_service import (
    create_refresh_token_record,
    validate_refresh_token,
)


class FakeRedis:
    """Minimal async Redis surface used by the cache module."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.deleted: list[str] = []

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self.store[key] = value
        return True

    async def delete(self, key: str) -> int:
        self.deleted.append(key)
        return 1 if self.store.pop(key, None) is not None else 0


async def test_cache_roundtrip_and_invalidate(auth_session, verified_user):
    """Cache stores a record and invalidation removes it."""
    fake = FakeRedis()
    refresh_cache.set_redis_client_factory(lambda: fake)
    try:
        _raw, record = await create_refresh_token_record(
            auth_session, user_id=verified_user.id, family_id=uuid4()
        )
        await auth_session.commit()

        await refresh_cache.set_cached(record)
        cached = await refresh_cache.get_cached(record.token_hash)
        assert cached is not None
        assert cached["user_id"] == verified_user.id

        await refresh_cache.invalidate(record.token_hash)
        assert await refresh_cache.get_cached(record.token_hash) is None
        assert fake.deleted
    finally:
        refresh_cache.reset_redis_client_factory()


async def test_validation_uses_cache_when_row_is_gone(auth_session, verified_user):
    """A cache hit validates without touching the database row."""
    fake = FakeRedis()
    refresh_cache.set_redis_client_factory(lambda: fake)
    try:
        raw, record = await create_refresh_token_record(
            auth_session, user_id=verified_user.id, family_id=uuid4()
        )
        await auth_session.commit()
        await refresh_cache.set_cached(record)

        # Remove the row: only the cache can answer now.
        await auth_session.exec(
            delete(RefreshToken).where(RefreshToken.id == record.id)
        )
        await auth_session.commit()

        validated, reason = await validate_refresh_token(auth_session, raw)
        assert reason is None
        assert validated is not None
        assert validated.id == record.id
    finally:
        refresh_cache.reset_redis_client_factory()


async def test_cache_failure_falls_back_to_database(auth_session, verified_user):
    """A broken cache never breaks validation."""

    def broken_factory():
        raise RuntimeError("redis down")

    refresh_cache.set_redis_client_factory(broken_factory)
    try:
        raw, record = await create_refresh_token_record(
            auth_session, user_id=verified_user.id, family_id=uuid4()
        )
        await auth_session.commit()

        validated, reason = await validate_refresh_token(auth_session, raw)
        assert reason is None
        assert validated is not None
        assert validated.id == record.id
    finally:
        refresh_cache.reset_redis_client_factory()


async def test_cached_revocation_reports_revoked(auth_session, verified_user):
    """A cached revoked state rejects the token and revokes the family."""
    fake = FakeRedis()
    refresh_cache.set_redis_client_factory(lambda: fake)
    try:
        raw, record = await create_refresh_token_record(
            auth_session, user_id=verified_user.id, family_id=uuid4()
        )
        await auth_session.commit()

        record.revoked_at = datetime.now(UTC)
        await refresh_cache.set_cached(record)

        validated, reason = await validate_refresh_token(auth_session, raw)
        assert validated is None
        assert reason == "revoked"
    finally:
        refresh_cache.reset_redis_client_factory()
