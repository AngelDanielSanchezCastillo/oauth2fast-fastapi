# Migration Guide: oauth2fast-fastapi 0.6.0 → 0.7.0

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
