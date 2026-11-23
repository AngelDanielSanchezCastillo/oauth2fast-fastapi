"""
Refresh token lifecycle service.

PostgreSQL is always the source of truth. An optional Redis cache (see
``refresh_cache``) accelerates validation but never replaces the database.

Reuse detection: presenting an already-revoked token revokes every token in
its family. Rotated tokens are revoked immediately, so a replay is treated as
a compromise signal.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..models.refresh_token_model import RefreshToken
from ..settings import settings
from ..utils import refresh_cache
from ..utils.token_utils import create_refresh_token, hash_refresh_token


def _from_cache(data: dict) -> RefreshToken:
    """Rebuild a detached record from a cached payload."""
    return RefreshToken(
        id=data["id"],
        user_id=data["user_id"],
        token_hash=data["token_hash"],
        family_id=UUID(data["family_id"]),
        device_info=data.get("device_info"),
        expires_at=datetime.fromisoformat(data["expires_at"]),
        revoked_at=(
            datetime.fromisoformat(data["revoked_at"])
            if data.get("revoked_at")
            else None
        ),
    )


async def create_refresh_token_record(
    session: AsyncSession,
    *,
    user_id: UUID,
    family_id: UUID | None = None,
    device_info: str | None = None,
    expires_delta: timedelta | None = None,
) -> tuple[str, RefreshToken]:
    """Create (but do not commit) a refresh token record.

    Args:
        session: Auth database session.
        user_id: Owner of the token.
        family_id: Session family. A new UUID is generated when omitted.
        device_info: Optional user-agent for auditing.
        expires_delta: Override the configured TTL.

    Returns:
        ``(raw_token, record)``. Only the hash is persisted.
    """
    raw_token = create_refresh_token()
    delta = expires_delta or timedelta(minutes=settings.refresh_token_expire_minutes)
    record = RefreshToken(
        user_id=user_id,
        token_hash=hash_refresh_token(raw_token),
        family_id=family_id or uuid4(),
        device_info=device_info,
        expires_at=datetime.now(UTC) + delta,
    )
    session.add(record)
    return raw_token, record


async def _get_by_raw_token(
    session: AsyncSession, raw_token: str
) -> RefreshToken | None:
    """Look up a record by the hash of its raw token."""
    result = await session.exec(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(raw_token)
        )
    )
    return result.one_or_none()


async def validate_refresh_token(
    session: AsyncSession, raw_token: str
) -> tuple[RefreshToken | None, str | None]:
    """Validate a raw refresh token.

    Args:
        session: Auth database session.
        raw_token: Token presented by the client.

    Returns:
        ``(record, reason)``. ``reason`` is ``None`` when valid, otherwise one
        of ``"missing"``, ``"invalid"``, ``"expired"`` or ``"revoked"``.

        On ``"revoked"`` (reuse detection) every token in the family is
        revoked. The caller must commit.
    """
    if not raw_token:
        return None, "missing"

    token_hash = hash_refresh_token(raw_token)

    cached = await refresh_cache.get_cached(token_hash)
    if cached is not None:
        revoked_at = cached.get("revoked_at")
        if revoked_at:
            await revoke_family(session, UUID(cached["family_id"]))
            return None, "revoked"
        if datetime.fromisoformat(cached["expires_at"]) <= datetime.now(UTC):
            return None, "expired"
        return _from_cache(cached), None

    record = await _get_by_raw_token(session, raw_token)
    if record is None:
        return None, "invalid"

    if record.revoked_at is not None:
        # Reuse of a revoked token: revoke the whole family (compromise signal).
        await revoke_family(session, record.family_id)
        return None, "revoked"

    if record.expires_at <= datetime.now(UTC):
        return None, "expired"

    await refresh_cache.set_cached(record)
    return record, None


async def revoke_refresh_token(session: AsyncSession, record: RefreshToken) -> None:
    """Revoke a single refresh token (logout on the current device)."""
    persisted = await session.get(RefreshToken, record.id)
    target = persisted or record
    target.revoked_at = datetime.now(UTC)
    session.add(target)
    await refresh_cache.invalidate(target.token_hash)


async def revoke_family(session: AsyncSession, family_id: UUID) -> None:
    """Revoke every still-active token in a family."""
    result = await session.exec(
        select(RefreshToken).where(
            RefreshToken.family_id == family_id,
            RefreshToken.revoked_at.is_(None),
        )
    )
    now = datetime.now(UTC)
    for record in result.all():
        record.revoked_at = now
        session.add(record)
        await refresh_cache.invalidate(record.token_hash)


async def revoke_all_for_user(session: AsyncSession, user_id: UUID) -> None:
    """Revoke every still-active token of a user (global logout)."""
    result = await session.exec(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
    )
    now = datetime.now(UTC)
    for record in result.all():
        record.revoked_at = now
        session.add(record)
        await refresh_cache.invalidate(record.token_hash)


async def rotate_refresh_token(
    session: AsyncSession,
    old_record: RefreshToken,
    *,
    device_info: str | None = None,
) -> tuple[str, RefreshToken]:
    """Rotate a refresh token: issue a new one and revoke the old one."""
    persisted = await session.get(RefreshToken, old_record.id)
    previous = persisted or old_record

    raw_token, new_record = await create_refresh_token_record(
        session,
        user_id=previous.user_id,
        family_id=previous.family_id,
        device_info=device_info or previous.device_info,
    )
    previous.revoked_at = datetime.now(UTC)
    session.add(previous)
    await refresh_cache.invalidate(previous.token_hash)
    return raw_token, new_record
