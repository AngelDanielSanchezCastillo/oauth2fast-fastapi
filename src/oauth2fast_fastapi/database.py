"""
Database module for OAuth2Fast-FastAPI.

This module uses pgsqlasync2fast-fastapi for database connectivity.
The database connection is configured via environment variables with the prefix DB_CONNECTIONS__AUTH__
"""

# Re-export from pgsqlasync2fast-fastapi for backward compatibility
from pgsqlasync2fast_fastapi import (
    get_db_engine,
    get_db_session,
    shutdown_database,
    startup_database,
)

__all__ = [
    "get_db_session",
    "get_db_engine",
    "startup_database",
    "shutdown_database",
]

