# Migration Guide: oauth2fast-fastapi

---

## Migration Guide: 0.7.3 → 0.8.0 (UUID v7 + Soft Delete)

### Breaking Changes

#### 1. Python 3.14+ Required

The minimum Python version is now 3.14. This enables native `uuid.uuid7()` from the standard library.

#### 2. Primary Keys: BigInteger → UUID v7

All primary keys have migrated from `BigInteger` (auto-increment integers) to `UUID v7` (time-ordered UUIDs):

- `users.id`: `int` → `UUID`
- `oauth__refresh_tokens.id`: `int` → `UUID`
- `oauth__refresh_tokens.user_id`: `int` → `UUID`

**Impact**:
- All `id` fields in API responses are now UUID strings (e.g., `"01a2074b-02b7-77f7-a889-d0d50996d41c"`)
- Foreign keys referencing `users.id` must use UUID type
- Database migration required for existing data (uses `gen_random_uuid()` for backfill)

#### 3. Soft Delete Support

Both `User` and `RefreshToken` models now inherit from `AuthSoftDeleteModel`, which includes:

- `deleted_at: datetime | None` — Timestamp when the record was soft-deleted
- `deleted_by: UUID | None` — ID of the user who deleted the record

**Impact**:
- Models have two new optional fields
- API responses include `deleted_at` and `deleted_by` fields
- Soft-delete functions are available via `tools2fast_fastapi`:
  - `soft_delete(session, model_cls, id, deleted_by)`
  - `restore(session, model_cls, id, restored_by)`
  - `active_only(query)` — Filter for non-deleted records
  - `deleted_only(query)` — Filter for deleted records

#### 4. Dependencies Updated

- `tools2fast-fastapi>=0.4.0` (UUID mixins + soft-delete functions)
- `pgsqlasync2fast-fastapi>=0.6.0` (migration helpers)

### Migration Path

For existing databases, run the Alembic migration `a1b2c3d4e5f6_uuid_soft_delete`:

```bash
alembic upgrade head
```

This migration:
1. Adds UUID columns (`id_uuid`, `user_id_uuid`)
2. Backfills with `gen_random_uuid()` (UUIDv4) for existing rows
3. Adds soft-delete columns (`deleted_at`, `deleted_by`)
4. Swaps old integer columns with new UUID columns
5. Recreates primary keys, foreign keys, and indexes

**Note**: Existing data uses UUIDv4 for backward compatibility. New records use UUIDv7 (time-ordered).

### Code Changes

#### Before (0.7.3)

```python
from oauth2fast_fastapi import User

user = User(
    name="John Doe",
    email="john@example.com",
    password="hashed",
)
print(user.id)  # 123 (int)
```

#### After (0.8.0)

```python
from oauth2fast_fastapi import User

user = User(
    name="John Doe",
    email="john@example.com",
    password="hashed",
)
print(user.id)  # 01a2074b-02b7-77f7-a889-d0d50996d41c (UUID)
print(user.deleted_at)  # None (active)
print(user.deleted_by)  # None

# Soft-delete a user
from tools2fast_fastapi import soft_delete
await soft_delete(session, User, user.id, deleted_by=admin_id)

# Restore a deleted user
from tools2fast_fastapi import restore
await restore(session, User, user.id, restored_by=admin_id)

# Query only active users
from sqlmodel import select
from tools2fast_fastapi import active_only
stmt = active_only(select(User))
result = await session.exec(stmt)
```

---

## Migration Guide: 0.6.0 → 0.7.0

## Breaking Change: Router Split

The single `router` has been replaced with two separate routers:

- **`public_router`**: Public endpoints that don't require admin privileges
- **`admin_router`**: Admin endpoints for user management

### Before (0.6.0)

```python
from oauth2fast_fastapi import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
```

### After (0.7.0)

```python
from oauth2fast_fastapi import public_router, admin_router
from fastapi import FastAPI

app = FastAPI()
app.include_router(public_router)  # /auth/token, /auth/users/ (POST), etc.
app.include_router(admin_router)   # /auth/users/ (GET), /auth/users/by-email/{email}
```

### Injecting RBAC on admin endpoints

The `admin_router` does NOT include RBAC. You must inject it when mounting:

```python
from oauth2fast_fastapi import admin_router
from permissions2fast_fastapi import has_role
from fastapi import Depends

app.include_router(admin_router, dependencies=[Depends(has_role("admin"))])
```

### Endpoint Distribution

| Endpoint | Router | Method | Auth Required |
|---|---|---|---|
| `/auth/token` | `public_router` | POST | No |
| `/auth/token/refresh` | `public_router` | POST | No (cookie or body) |
| `/auth/logout` | `public_router` | POST | No (cookie or body) |
| `/auth/logout/all` | `public_router` | POST | Yes (access token) |
| `/auth/users/` | `public_router` | POST | No (registration) |
| `/auth/users/` | `admin_router` | GET | Yes (inject RBAC) |
| `/auth/users/by-email/{email}` | `admin_router` | GET | Yes (inject RBAC) |
| `/auth/confirm-email` | `public_router` | POST | No |
| `/auth/resend-verification` | `public_router` | POST | No |

### Bootstrap Flow

1. Create admin user:
   ```bash
   python -m oauth2fast_fastapi.scripts.create_admin \
       --email admin@example.com \
       --password 'StrongPassword123'
   ```

2. Assign admin role:
   ```bash
   python -m permissions2fast_fastapi.scripts.assign_role \
       --email admin@example.com \
       --role admin
   ```

## Changelog

- **BREAKING**: Removed `router` export. Use `public_router` + `admin_router` instead.
- **ADDED**: `public_router` for public auth endpoints.
- **ADDED**: `admin_router` for admin user management endpoints.
- **ADDED**: `scripts/create_admin.py` for bootstrap CLI.
- **CHANGED**: Bumped version to 0.7.0 (MINOR under 0.x allows breaking changes).
