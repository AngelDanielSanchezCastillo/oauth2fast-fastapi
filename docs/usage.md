# OAuth2Fast-FastAPI Usage Guide

## Installation

```bash
pip install oauth2fast-fastapi
```

## Quick Start

### 1. Environment Configuration

Create a `.env` file in your project root:

```bash
# Required JWT Configuration
SECRET_KEY=your-super-secret-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Application Settings
PROJECT_NAME=My App
FRONTEND_URL=https://yourapp.com
AUTH_URL_PREFIX=auth

# Database Configuration (using pgsqlasync2fast-fastapi)
# Connection name: "auth" (set as default)
DB_DEFAULT_CONNECTION=auth
DB_CONNECTIONS__AUTH__USERNAME=postgres
DB_CONNECTIONS__AUTH__PASSWORD=yourpassword
DB_CONNECTIONS__AUTH__HOST=localhost
DB_CONNECTIONS__AUTH__DATABASE=myapp_db
DB_CONNECTIONS__AUTH__PORT=5432

# Mail Server Configuration (using mailing2fast-fastapi)
# SMTP Account name: "auth" (set as default)
MAIL_DEFAULT_ACCOUNT=auth
MAIL_SMTP_ACCOUNTS__AUTH__HOST=smtp.gmail.com
MAIL_SMTP_ACCOUNTS__AUTH__PORT=587
MAIL_SMTP_ACCOUNTS__AUTH__USERNAME=noreply@yourapp.com
MAIL_SMTP_ACCOUNTS__AUTH__PASSWORD=your-smtp-password
MAIL_SMTP_ACCOUNTS__AUTH__FROM_EMAIL=noreply@yourapp.com
MAIL_SMTP_ACCOUNTS__AUTH__FROM_NAME=Your App
MAIL_SMTP_ACCOUNTS__AUTH__SECURITY=starttls
```

### 2. Basic FastAPI Integration

```python
from fastapi import FastAPI, Depends
from oauth2fast_fastapi import (
    router,
    startup_database,
    shutdown_database,
    get_current_user,
    User,
    AuthModel,
)
from sqlmodel import SQLModel

app = FastAPI()

# Include authentication router
app.include_router(router, prefix="/auth", tags=["Authentication"])

@app.on_event("startup")
async def startup():
    # Initialize database connections
    await startup_database()
    
    # Create database tables
    from pgsqlasync2fast_fastapi import get_db_engine
    engine = get_db_engine("auth")
    async with engine.begin() as conn:
        # Create auth tables (User, etc.)
        await conn.run_sync(AuthModel.metadata.create_all)

@app.on_event("shutdown")
async def shutdown():
    # Close database connections
    await shutdown_database()

@app.get("/protected")
async def protected_route(current_user: User = Depends(get_current_user)):
    return {"message": f"Hello {current_user.email}!"}
```

### 3. User Registration Flow

**Register a new user:**
```bash
POST /auth/users/
{
  "email": "user@example.com",
  "password": "SecurePassword123",
  "name": "John Doe"
}
```

**Verify email:**
```bash
POST /auth/confirm-email
{
  "token": "verification-token-from-email"
}
```

### 4. Login and Token Generation

```bash
POST /auth/token
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=SecurePassword123
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 5. Using Protected Endpoints

```python
from fastapi import Depends
from oauth2fast_fastapi import get_current_user, get_current_verified_user, User

# Requires authentication only
@app.get("/profile")
async def get_profile(user: User = Depends(get_current_user)):
    return {"email": user.email, "verified": user.is_verified}

# Requires authentication AND email verification
@app.get("/premium-feature")
async def premium_feature(user: User = Depends(get_current_verified_user)):
    return {"message": "Access granted to verified users only"}
```

## Advanced Usage

### Manual Database Session

```python
from oauth2fast_fastapi import get_auth_session
from sqlalchemy.ext.asyncio import AsyncSession

@app.get("/users")
async def list_users(session: AsyncSession = Depends(get_auth_session)):
    # Use session for custom queries
    pass
```

## Configuration Reference

All configuration is done via environment variables with nested delimiter `__`.

### JWT Settings
- `SECRET_KEY` (required): Secret key for JWT signing
- `ALGORITHM` (default: "HS256"): JWT algorithm
- `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 60): Token expiration time

### Database Settings (pgsqlasync2fast-fastapi)
- `DB_DEFAULT_CONNECTION` (default: "default"): Default database connection name
- `DB_CONNECTIONS__AUTH__USERNAME`: Database username for auth connection
- `DB_CONNECTIONS__AUTH__PASSWORD`: Database password for auth connection
- `DB_CONNECTIONS__AUTH__HOST`: Database host for auth connection
- `DB_CONNECTIONS__AUTH__DATABASE`: Database name for auth connection
- `DB_CONNECTIONS__AUTH__PORT`: Database port for auth connection (default: 5432)

### Mail Settings (mailing2fast-fastapi)
- `MAIL_DEFAULT_ACCOUNT` (default: "default"): Default SMTP account name
- `MAIL_SMTP_ACCOUNTS__AUTH__HOST`: SMTP server host for auth account
- `MAIL_SMTP_ACCOUNTS__AUTH__PORT`: SMTP server port for auth account
- `MAIL_SMTP_ACCOUNTS__AUTH__USERNAME`: SMTP username for auth account
- `MAIL_SMTP_ACCOUNTS__AUTH__PASSWORD`: SMTP password for auth account
- `MAIL_SMTP_ACCOUNTS__AUTH__FROM_EMAIL`: From email address for auth account
- `MAIL_SMTP_ACCOUNTS__AUTH__FROM_NAME`: From name for auth account
- `MAIL_SMTP_ACCOUNTS__AUTH__SECURITY`: Security protocol (none, tls, starttls)

### Application Settings
- `PROJECT_NAME`: Application name (used in emails)
- `FRONTEND_URL`: Frontend URL (for email links)
- `AUTH_URL_PREFIX`: Auth router prefix (default: "auth")

## Troubleshooting

### Missing SECRET_KEY Error

If you see an error about missing `SECRET_KEY`, make sure it's defined in your `.env` file:

```bash
SECRET_KEY=your-secret-key-here
```

Generate a secure secret key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Email Verification Not Working

1. Check your SMTP settings in `.env`
2. Verify `FRONTEND_URL` is correct
3. Ensure `MAIL_DEFAULT_ACCOUNT` is set to "auth"
4. Check that all `MAIL_SMTP_ACCOUNTS__AUTH__*` variables are configured

### Database Connection Issues

Ensure your database configuration is correct:
```bash
DB_DEFAULT_CONNECTION=auth
DB_CONNECTIONS__AUTH__USERNAME=postgres
DB_CONNECTIONS__AUTH__PASSWORD=password
DB_CONNECTIONS__AUTH__HOST=localhost
DB_CONNECTIONS__AUTH__DATABASE=mydb
DB_CONNECTIONS__AUTH__PORT=5432
```

## Migration from v0.1.x to v0.2.0

Version 0.2.0 introduces breaking changes in environment variable structure:

**Database variables changed:**
- `AUTH_DB__USERNAME` → `DB_CONNECTIONS__AUTH__USERNAME`
- `AUTH_DB__PASSWORD` → `DB_CONNECTIONS__AUTH__PASSWORD`
- `AUTH_DB__HOSTNAME` → `DB_CONNECTIONS__AUTH__HOST`
- `AUTH_DB__NAME` → `DB_CONNECTIONS__AUTH__DATABASE`
- `AUTH_DB__PORT` → `DB_CONNECTIONS__AUTH__PORT`

**Email variables changed:**
- `AUTH_MAIL_SERVER__USERNAME` → `MAIL_SMTP_ACCOUNTS__AUTH__USERNAME`
- `AUTH_MAIL_SERVER__PASSWORD` → `MAIL_SMTP_ACCOUNTS__AUTH__PASSWORD`
- `AUTH_MAIL_SERVER__SERVER` → `MAIL_SMTP_ACCOUNTS__AUTH__HOST`
- `AUTH_MAIL_SERVER__PORT` → `MAIL_SMTP_ACCOUNTS__AUTH__PORT`
- `AUTH_MAIL_SERVER__FROM_DIRECTION` → `MAIL_SMTP_ACCOUNTS__AUTH__FROM_EMAIL`
- `AUTH_MAIL_SERVER__FROM_NAME` → `MAIL_SMTP_ACCOUNTS__AUTH__FROM_NAME`
- `AUTH_MAIL_SERVER__STARTTLS` and `AUTH_MAIL_SERVER__SSL_TLS` → `MAIL_SMTP_ACCOUNTS__AUTH__SECURITY` (values: "none", "tls", "starttls")

**New required variables:**
- `DB_DEFAULT_CONNECTION=auth`
- `MAIL_DEFAULT_ACCOUNT=auth`

**Code changes:**
- `from oauth2fast_fastapi import engine` → `from oauth2fast_fastapi import get_db_engine`
- Add `startup_database()` and `shutdown_database()` to app lifecycle events
