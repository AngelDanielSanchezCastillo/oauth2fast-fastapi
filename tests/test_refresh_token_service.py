"""
Service-level tests for refresh tokens (0.6.0).

Covers creation, validation, rotation with family tracking, reuse detection
(the whole family is revoked) and logout semantics (single device vs all).
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlmodel import select

from oauth2fast_fastapi.models.refresh_token_model import RefreshToken
from oauth2fast_fastapi.utils.refresh_token_service import (
    create_refresh_token_record,
    revoke_all_for_user,
    revoke_refresh_token,
    rotate_refresh_token,
    validate_refresh_token,
)
from oauth2fast_fastapi.utils.token_utils import hash_refresh_token


async def test_create_persists_hashed_token(auth_session, verified_user):
    """RED: the raw token is never stored; only its hash is."""
    raw, record = await create_refresh_token_record(
        auth_session,
        user_id=verified_user.id,
        family_id=uuid4(),
        device_info="pytest-agent",
    )
    await auth_session.commit()

    assert record.user_id == verified_user.id
    assert record.token_hash == hash_refresh_token(raw)
    assert record.token_hash != raw
    assert record.device_info == "pytest-agent"
    assert record.revoked_at is None
    assert record.expires_at > datetime.now(UTC)


async def test_validate_returns_record_for_valid_token(auth_session, verified_user):
    """RED: a valid refresh token validates with no reason."""
    raw, record = await create_refresh_token_record(
        auth_session,
        user_id=verified_user.id,
        family_id=uuid4(),
    )
    await auth_session.commit()

    validated, reason = await validate_refresh_token(auth_session, raw)

    assert reason is None
    assert validated is not None
    assert validated.id == record.id


async def test_validate_reports_missing_and_invalid(auth_session):
    """RED: empty tokens are ``missing``; unknown tokens are ``invalid``."""
    _, missing_reason = await validate_refresh_token(auth_session, "")
    _, invalid_reason = await validate_refresh_token(auth_session, "does-not-exist")

    assert missing_reason == "missing"
    assert invalid_reason == "invalid"


async def test_validate_reports_expired(auth_session, verified_user):
    """RED: an expired refresh token reports ``expired``."""
    raw, _record = await create_refresh_token_record(
        auth_session,
        user_id=verified_user.id,
        family_id=uuid4(),
        expires_delta=timedelta(seconds=-1),
    )
    await auth_session.commit()

    _, reason = await validate_refresh_token(auth_session, raw)

    assert reason == "expired"


async def test_rotation_keeps_family_and_revokes_old(auth_session, verified_user):
    """RED: rotation creates a new token in the same family and revokes the old."""
    family = uuid4()
    raw, record = await create_refresh_token_record(
        auth_session,
        user_id=verified_user.id,
        family_id=family,
    )
    await auth_session.commit()

    new_raw, new_record = await rotate_refresh_token(
        auth_session, record, device_info="pytest-agent"
    )
    await auth_session.commit()
    await auth_session.refresh(record)

    assert new_raw != raw
    assert new_record.family_id == family
    assert new_record.revoked_at is None
    assert record.revoked_at is not None

    validated, reason = await validate_refresh_token(auth_session, new_raw)
    assert reason is None
    assert validated is not None
    assert validated.id == new_record.id


async def test_reuse_revokes_whole_family(auth_session, verified_user):
    """RED: replaying a rotated token revokes every token in the family."""
    family = uuid4()
    raw, record = await create_refresh_token_record(
        auth_session,
        user_id=verified_user.id,
        family_id=family,
    )
    await auth_session.commit()

    new_raw, _new_record = await rotate_refresh_token(auth_session, record)
    await auth_session.commit()

    # Replay the old token: this is a reuse event.
    _, reason = await validate_refresh_token(auth_session, raw)
    assert reason == "revoked"

    # The freshly rotated token belongs to the same family and must be dead.
    validated, new_reason = await validate_refresh_token(auth_session, new_raw)
    assert validated is None
    assert new_reason == "revoked"


async def test_revoke_single_device(auth_session, verified_user):
    """RED: logout revokes only the given token, not the whole family."""
    family = uuid4()
    raw_a, record_a = await create_refresh_token_record(
        auth_session, user_id=verified_user.id, family_id=family
    )
    raw_b, _record_b = await create_refresh_token_record(
        auth_session, user_id=verified_user.id, family_id=uuid4()
    )
    await auth_session.commit()

    await revoke_refresh_token(auth_session, record_a)
    await auth_session.commit()

    _, reason_a = await validate_refresh_token(auth_session, raw_a)
    _, reason_b = await validate_refresh_token(auth_session, raw_b)

    assert reason_a == "revoked"
    assert reason_b is None


async def test_revoke_all_for_user(auth_session, verified_user):
    """RED: the global logout kills every session of the user."""
    raw_a, _ = await create_refresh_token_record(
        auth_session, user_id=verified_user.id, family_id=uuid4()
    )
    raw_b, _ = await create_refresh_token_record(
        auth_session, user_id=verified_user.id, family_id=uuid4()
    )
    await auth_session.commit()

    await revoke_all_for_user(auth_session, verified_user.id)
    await auth_session.commit()

    _, reason_a = await validate_refresh_token(auth_session, raw_a)
    _, reason_b = await validate_refresh_token(auth_session, raw_b)

    assert reason_a == "revoked"
    assert reason_b == "revoked"


async def test_records_are_persisted_in_oauth_table(auth_session, verified_user):
    """RED: rows live in the dedicated ``oauth__refresh_tokens`` table."""
    await create_refresh_token_record(
        auth_session, user_id=verified_user.id, family_id=uuid4()
    )
    await auth_session.commit()

    result = await auth_session.exec(select(RefreshToken))
    assert len(result.all()) == 1
    assert RefreshToken.__tablename__ == "oauth__refresh_tokens"
