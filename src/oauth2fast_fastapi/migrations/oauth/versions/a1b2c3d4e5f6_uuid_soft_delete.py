"""uuid_soft_delete

Revision ID: a1b2c3d4e5f6
Revises: 45b786644a86
Create Date: 2026-11-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from pgsqlasync2fast_fastapi.migration_helpers import (
    add_soft_delete_columns_alembic,
    finalize_uuid_alembic,
    prepare_fk_uuid_alembic,
    prepare_pk_uuid_alembic,
)


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '45b786644a86'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migrate users and oauth__refresh_tokens from BigInteger to UUID.

    Also add soft-delete columns (deleted_at, deleted_by) to both tables.

    Cross-chain coordination (ODD-3 Fase 1.5):
    - ``role_users.user_id`` (permissions2fast) and ``tenant_users.user_id``
      (tenants2fast-auth) reference ``users.id``. This migration drops those
      external FKs before the PK swap (Postgres refuses otherwise) and leaves
      a persistent ``_uuid_migration_user_map`` table so the sibling chains can
      backfill their columns with the SAME UUIDs instead of losing the values.
    - The map is dropped by ``tenants2fast-auth`` after it consumes it.

    Two-phase, FK-safe (pgsqlasync2fast 0.6.2 helpers):
    - prepare PKs/FKs while the old integer columns still exist, backfilling
      child rows by joining ``users.id_uuid`` on the old integer ``user_id``;
    - finalize: drop the child FK, swap PKs, swap FKs, recreate constraints.
    """
    # --- Soft-delete columns ---------------------------------------------
    add_soft_delete_columns_alembic(op, 'users')
    add_soft_delete_columns_alembic(op, 'oauth__refresh_tokens')

    # --- Cross-chain user-id map (old int -> new UUID) --------------------
    # Ephemeral by design: created here, consumed by permissions2fast and
    # tenants2fast-auth, dropped by the latter. Not a TEMP TABLE because each
    # chain runs in a different process/connection.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS _uuid_migration_user_map (
            old_id BIGINT PRIMARY KEY,
            new_uuid UUID NOT NULL UNIQUE
        )
        """
    )

    # --- Phase 1: prepare UUID columns (old integer columns kept) ---------
    prepare_pk_uuid_alembic(op, 'users')
    op.execute(
        """
        INSERT INTO _uuid_migration_user_map (old_id, new_uuid)
        SELECT id, id_uuid FROM users
        ON CONFLICT (old_id) DO NOTHING
        """
    )
    prepare_pk_uuid_alembic(op, 'oauth__refresh_tokens')
    prepare_fk_uuid_alembic(
        op, 'oauth__refresh_tokens', 'user_id', 'users', nullable=False
    )

    # --- Drop external FKs to users before the PK swap --------------------
    # Only the known 2fast tables are touched; their chains recreate the FKs
    # as UUID after backfilling from the map. Offline-safe (no bind needed).
    for table_name in ("role_users", "tenant_users"):
        for constraint_name in (
            f"{table_name}_user_id_fkey",
            f"fk_{table_name}_user_id",
        ):
            op.execute(
                f'ALTER TABLE IF EXISTS "{table_name}" '
                f'DROP CONSTRAINT IF EXISTS "{constraint_name}"'
            )

    # --- Phase 2: finalize swap (FK-safe order) ---------------------------
    finalize_uuid_alembic(
        op,
        pk_tables=['users', 'oauth__refresh_tokens'],
        fk_relations=[('oauth__refresh_tokens', 'user_id', 'users')],
    )


def downgrade() -> None:
    """Reverse migration: UUID back to BigInteger.

    WARNING: Destructive. UUID→integer mapping uses row numbering.
    In practice, prefer a full database rebuild over downgrading.
    """
    # ═══════════════════════════════════════════════════════════════════════
    # STEP 1: Revert oauth__refresh_tokens
    # ═══════════════════════════════════════════════════════════════════════
    op.drop_index(op.f('ix_oauth__refresh_tokens_deleted_at'), table_name='oauth__refresh_tokens')
    op.drop_index(op.f('ix_oauth__refresh_tokens_user_id'), table_name='oauth__refresh_tokens')
    op.drop_index(op.f('ix_oauth__refresh_tokens_id'), table_name='oauth__refresh_tokens')
    op.drop_constraint('oauth__refresh_tokens_user_id_fkey', 'oauth__refresh_tokens', type_='foreignkey')
    op.drop_constraint('oauth__refresh_tokens_pkey', 'oauth__refresh_tokens')

    op.add_column('oauth__refresh_tokens', sa.Column('id_bigint', sa.BigInteger(), nullable=True))
    op.add_column('oauth__refresh_tokens', sa.Column('user_id_bigint', sa.BigInteger(), nullable=True))

    # Assign sequential integers
    op.execute("""
        UPDATE oauth__refresh_tokens
        SET id_bigint = sub.rn
        FROM (SELECT id, ROW_NUMBER() OVER (ORDER BY id) as rn FROM oauth__refresh_tokens) sub
        WHERE oauth__refresh_tokens.id = sub.id
    """)
    op.execute("""
        UPDATE oauth__refresh_tokens
        SET user_id_bigint = sub.rn
        FROM (SELECT id, ROW_NUMBER() OVER (ORDER BY id) as rn FROM users) sub
        WHERE oauth__refresh_tokens.user_id = sub.id
    """)

    op.alter_column('oauth__refresh_tokens', 'id_bigint', nullable=False)
    op.alter_column('oauth__refresh_tokens', 'user_id_bigint', nullable=False)

    op.drop_column('oauth__refresh_tokens', 'id')
    op.drop_column('oauth__refresh_tokens', 'user_id')
    op.drop_column('oauth__refresh_tokens', 'deleted_at')
    op.drop_column('oauth__refresh_tokens', 'deleted_by')

    op.alter_column('oauth__refresh_tokens', 'id_bigint', new_column_name='id')
    op.alter_column('oauth__refresh_tokens', 'user_id_bigint', new_column_name='user_id')

    op.create_primary_key('oauth__refresh_tokens_pkey', 'oauth__refresh_tokens', ['id'])
    op.create_foreign_key(
        'oauth__refresh_tokens_user_id_fkey',
        'oauth__refresh_tokens',
        'users',
        ['user_id'],
        ['id'],
    )
    op.create_index(op.f('ix_oauth__refresh_tokens_id'), 'oauth__refresh_tokens', ['id'], unique=False)
    op.create_index(op.f('ix_oauth__refresh_tokens_user_id'), 'oauth__refresh_tokens', ['user_id'], unique=False)

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 2: Revert users
    # ═══════════════════════════════════════════════════════════════════════
    op.drop_index(op.f('ix_users_deleted_at'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_constraint('oauth__refresh_tokens_user_id_fkey', 'oauth__refresh_tokens', type_='foreignkey')
    op.drop_constraint('users_pkey', 'users')

    op.add_column('users', sa.Column('id_bigint', sa.BigInteger(), nullable=True))

    op.execute("""
        UPDATE users
        SET id_bigint = sub.rn
        FROM (SELECT id, ROW_NUMBER() OVER (ORDER BY id) as rn FROM users) sub
        WHERE users.id = sub.id
    """)

    op.alter_column('users', 'id_bigint', nullable=False)

    op.drop_column('users', 'id')
    op.drop_column('users', 'deleted_at')
    op.drop_column('users', 'deleted_by')

    op.alter_column('users', 'id_bigint', new_column_name='id')

    op.create_primary_key('users_pkey', 'users', ['id'])
    op.create_foreign_key(
        'oauth__refresh_tokens_user_id_fkey',
        'oauth__refresh_tokens',
        'users',
        ['user_id'],
        ['id'],
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
