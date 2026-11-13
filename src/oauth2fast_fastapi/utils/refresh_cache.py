"""Optional Redis cache for refresh tokens.

PostgreSQL is always the source of truth. This module only accelerates the
validation path and is a no-op when ``REDIS_URL`` is unset. Every Redis error
is swallowed so the caller falls back to the database.

A client factory can be injected for tests
(:func:`set_redis_client_factory`).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from ..models.refresh_token_model import RefreshToken
from ..settings import settings

_client_factory: Callable[[], Any] | None = None
_client: Any = None


def set_redis_client_factory(factory: Callable[[], Any] | None) -> None:
    """Override how the Redis client is built (tests)."""
    global _client_factory
    _client_factory = factory


def reset_redis_client_factory() -> None:
    """Remove any injected factory and the cached client."""
    global _client_factory, _client
    _client_factory = None
    _client = None


def _get_client() -> Any | None:
    """Return a Redis client, or ``None`` when unavailable."""
    global _client
    if _client_factory is not None:
        try:
            return _client_factory()
        except Exception:  # noqa: BLE001
            return None

    if not settings.redis_url:
        return None

    if _client is not None:
        return _client

    try:
        import redis.asyncio as redis

        _client = redis.from_url(settings.redis_url, decode_responses=True)
        return _client
    except Exception:  # noqa: BLE001
        return None


def _key(token_hash: str) -> str:
    return f"oauth:refresh:{token_hash}"


def _serialize(record: RefreshToken) -> dict[str, Any]:
    return {
        "id": record.id,
        "user_id": record.user_id,
        "token_hash": record.token_hash,
        "family_id": str(record.family_id),
        "device_info": record.device_info,
        "expires_at": record.expires_at.isoformat(),
        "revoked_at": record.revoked_at.isoformat() if record.revoked_at else None,
    }


async def get_cached(token_hash: str) -> dict[str, Any] | None:
    """Return the cached record state, or ``None`` on miss/error."""
    client = _get_client()
    if client is None:
        return None
    try:
        raw = await client.get(_key(token_hash))
        return json.loads(raw) if raw else None
    except Exception:  # noqa: BLE001
        return None


async def set_cached(record: RefreshToken) -> None:
    """Cache a record until it expires. Best effort."""
    client = _get_client()
    if client is None or record.expires_at is None:
        return
    try:
        remaining = int((record.expires_at - datetime.now(UTC)).total_seconds())
        await client.set(
            _key(record.token_hash),
            json.dumps(_serialize(record)),
            ex=max(remaining, 1),
        )
    except Exception:  # noqa: BLE001
        return


async def invalidate(token_hash: str) -> None:
    """Drop a record from the cache. Best effort."""
    client = _get_client()
    if client is None:
        return
    try:
        await client.delete(_key(token_hash))
    except Exception:  # noqa: BLE001
        return
