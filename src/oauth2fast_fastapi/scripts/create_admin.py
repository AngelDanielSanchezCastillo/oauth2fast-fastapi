"""
Bootstrap script to create an admin user.

Creates a user in oauth__users with is_verified=True.
Does NOT assign roles — use permissions2fast's assign_role script for that.

Usage::

    python -m oauth2fast_fastapi.scripts.create_admin \\
        --email admin@example.com \\
        --password 'StrongPassword123' \\
        --name 'Admin User'
"""

import argparse
import asyncio
import sys

from ..database import shutdown_database, startup_database
from ..models.user_model import User
from ..utils.password_utils import hash_password


async def create_admin_user(
    session,
    *,
    email: str,
    password: str,
    name: str | None = None,
) -> User:
    """
    Create an admin user with is_verified=True.

    Args:
        session: AsyncSession for database operations.
        email: User email address.
        password: Plaintext password (will be hashed).
        name: Optional display name (defaults to "Admin").

    Returns:
        The created User instance.
    """
    hashed_password = hash_password(password)

    user = User(
        email=email,
        name=name or "Admin",
        password=hashed_password,
        is_verified=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _main_async(args: argparse.Namespace) -> None:
    """Async entry point for the CLI."""
    from sqlmodel.ext.asyncio.session import AsyncSession

    # Import here to avoid circular imports at module level
    from ..database import get_db_engine

    await startup_database()

    engine = get_db_engine("auth")
    async with AsyncSession(engine, expire_on_commit=False) as session:
        try:
            user = await create_admin_user(
                session,
                email=args.email,
                password=args.password,
                name=args.name,
            )
            print(f"Admin user created successfully:")
            print(f"  ID: {user.id}")
            print(f"  Email: {user.email}")
            print(f"  Name: {user.name}")
            print(f"  Verified: {user.is_verified}")
            print()
            print("Next step: assign admin role using:")
            print(
                f"  python -m permissions2fast_fastapi.scripts.assign_role "
                f"--email {user.email} --role admin"
            )
        except Exception as e:
            print(f"Error creating admin user: {e}", file=sys.stderr)
            sys.exit(1)

    await shutdown_database()


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Create an admin user (is_verified=True, no roles assigned).",
    )
    parser.add_argument(
        "--email",
        required=True,
        help="Email address for the admin user",
    )
    parser.add_argument(
        "--password",
        required=True,
        help="Password for the admin user",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Display name (defaults to 'Admin')",
    )
    args = parser.parse_args()

    asyncio.run(_main_async(args))


if __name__ == "__main__":
    main()
