"""
oauth2fast_fastapi.migrations - package-owned Alembic chain (alembic-2fast).

The ``auth`` lane starts with the oauth chain: an empty auth database must
receive ``users`` (and nothing else) before the permissions2fast /
tenant2fast chains run (FK-proven order, design D6 of the Metal ERP change
``alembic-2fast``).

Registration mirrors the ``register_seeder`` idiom: importing this module
(which the top-level ``oauth2fast_fastapi/__init__.py`` does) registers the
chain spec under the ``"auth"`` lane. The chain directory
``migrations/oauth/`` ships inside the wheel via
``[tool.setuptools.package-data] migrations/**/*.py`` and is resolved from
the INSTALLED release via alembic-native ``pkg:path`` resource strings.
"""

from oauth2fast_fastapi.models.bases import metadata
from pgsqlasync2fast_fastapi import ChainSpec, register_chain

#: Tables this chain owns (design D9 ownership filter): exactly ``users``.
OAUTH_OWNED_TABLES = frozenset({"users"})

oauth_chain = ChainSpec(
    package="oauth2fast_fastapi",
    script_path="migrations/oauth",
    version_table="alembic_version_oauth",
    target_metadata=metadata,
    owned_tables=OAUTH_OWNED_TABLES,
)

register_chain("auth", oauth_chain)

__all__ = ["OAUTH_OWNED_TABLES", "oauth_chain"]