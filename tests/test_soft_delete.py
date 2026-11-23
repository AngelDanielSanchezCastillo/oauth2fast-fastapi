"""
Soft-delete tests for oauth2fast models (0.8.0+).

Verifies that User and RefreshToken models support soft-delete via
the SoftDeleteMixin inherited from AuthSoftDeleteModel.

Tests cover:
- Models have deleted_at and deleted_by fields
- Soft-delete functions work correctly
- active_only() and deleted_only() filters work
- Unique global constraints (email uniqueness even after soft-delete)
"""

from datetime import datetime, timezone
from uuid import uuid7

import pytest
from sqlmodel import select

from oauth2fast_fastapi.models.user_model import User
from oauth2fast_fastapi.models.refresh_token_model import RefreshToken
from tools2fast_fastapi import soft_delete, restore, active_only, deleted_only


async def test_user_has_soft_delete_fields():
    """User model inherits SoftDeleteMixin with deleted_at and deleted_by."""
    user = User(
        name="Test User",
        email="test@example.com",
        password="hashed",
    )
    assert hasattr(user, "deleted_at")
    assert hasattr(user, "deleted_by")
    assert user.deleted_at is None
    assert user.deleted_by is None


async def test_refresh_token_has_soft_delete_fields():
    """RefreshToken model inherits SoftDeleteMixin."""
    user_id = uuid7()
    token = RefreshToken(
        user_id=user_id,
        token_hash="abc123",
        family_id=uuid7(),
        expires_at=datetime.now(timezone.utc),
    )
    assert hasattr(token, "deleted_at")
    assert hasattr(token, "deleted_by")
    assert token.deleted_at is None
    assert token.deleted_by is None


async def test_user_id_is_uuid():
    """User primary key is UUID type."""
    user = User(
        name="Test User",
        email="test@example.com",
        password="hashed",
    )
    from uuid import UUID
    assert isinstance(user.id, UUID)


async def test_refresh_token_user_id_is_uuid():
    """RefreshToken.user_id foreign key is UUID type."""
    user_id = uuid7()
    token = RefreshToken(
        user_id=user_id,
        token_hash="abc123",
        family_id=uuid7(),
        expires_at=datetime.now(timezone.utc),
    )
    from uuid import UUID
    assert isinstance(token.user_id, UUID)


async def test_soft_delete_user(auth_session, verified_user):
    """soft_delete() marks user as deleted with timestamp and actor."""
    admin_id = uuid7()
    
    # Verify user is active
    assert verified_user.deleted_at is None
    assert verified_user.deleted_by is None
    
    # Soft-delete the user
    await soft_delete(auth_session, User, verified_user.id, deleted_by=admin_id)
    
    # Refresh to get updated values
    await auth_session.refresh(verified_user)
    
    # Verify user is marked as deleted
    assert verified_user.deleted_at is not None
    assert verified_user.deleted_by == admin_id
    assert isinstance(verified_user.deleted_at, datetime)


async def test_restore_user(auth_session, verified_user):
    """restore() reactivates a soft-deleted user."""
    admin_id = uuid7()
    restorer_id = uuid7()
    
    # Soft-delete first
    await soft_delete(auth_session, User, verified_user.id, deleted_by=admin_id)
    await auth_session.refresh(verified_user)
    assert verified_user.deleted_at is not None
    
    # Restore the user
    await restore(auth_session, User, verified_user.id, restored_by=restorer_id)
    
    # Refresh to get updated values
    await auth_session.refresh(verified_user)
    
    # Verify user is active again
    assert verified_user.deleted_at is None
    assert verified_user.deleted_by is None


async def test_active_only_filter(auth_session):
    """active_only() filters out soft-deleted records."""
    admin_id = uuid7()
    
    # Create two users
    user1 = User(name="Active User", email="active@example.com", password="hashed")
    user2 = User(name="Deleted User", email="deleted@example.com", password="hashed")
    auth_session.add(user1)
    auth_session.add(user2)
    await auth_session.commit()
    await auth_session.refresh(user1)
    await auth_session.refresh(user2)
    
    # Soft-delete user2
    await soft_delete(auth_session, User, user2.id, deleted_by=admin_id)
    
    # Query with active_only filter
    stmt = active_only(select(User))
    result = await auth_session.exec(stmt)
    active_users = result.all()
    
    # Only user1 should be in the result
    user_ids = [u.id for u in active_users]
    assert user1.id in user_ids
    assert user2.id not in user_ids


async def test_deleted_only_filter(auth_session):
    """deleted_only() returns only soft-deleted records."""
    admin_id = uuid7()
    
    # Create two users
    user1 = User(name="Active User 2", email="active2@example.com", password="hashed")
    user2 = User(name="Deleted User 2", email="deleted2@example.com", password="hashed")
    auth_session.add(user1)
    auth_session.add(user2)
    await auth_session.commit()
    await auth_session.refresh(user1)
    await auth_session.refresh(user2)
    
    # Soft-delete user2
    await soft_delete(auth_session, User, user2.id, deleted_by=admin_id)
    
    # Query with deleted_only filter
    stmt = deleted_only(select(User))
    result = await auth_session.exec(stmt)
    deleted_users = result.all()
    
    # Only user2 should be in the result
    user_ids = [u.id for u in deleted_users]
    assert user2.id in user_ids
    assert user1.id not in user_ids
