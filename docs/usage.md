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

# Database Configuration
AUTH_DB__USERNAME=postgres
AUTH_DB__PASSWORD=yourpassword
AUTH_DB__HOSTNAME=localhost
AUTH_DB__NAME=myapp_db
AUTH_DB__PORT=5432

# Mail Server Configuration
AUTH_MAIL_SERVER__USERNAME=noreply@yourapp.com
AUTH_MAIL_SERVER__PASSWORD=your-smtp-password
AUTH_MAIL_SERVER__SERVER=smtp.gmail.com
AUTH_MAIL_SERVER__PORT=587
AUTH_MAIL_SERVER__FROM_DIRECTION=noreply@yourapp.com
AUTH_MAIL_SERVER__FROM_NAME=Your App
AUTH_MAIL_SERVER__STARTTLS=true
AUTH_MAIL_SERVER__SSL_TLS=false

# Application Settings
PROJECT_NAME=My App
FRONTEND_URL=https://yourapp.com
AUTH_URL_PREFIX=auth
```

### 2. Basic FastAPI Integration

```python
from fastapi import FastAPI, Depends
from oauth2fast_fastapi import router, engine, get_current_user, User
from sqlmodel import SQLModel

app = FastAPI()

# Include authentication router
app.include_router(router, prefix="/auth", tags=["Authentication"])

@app.on_event("startup")
async def startup():
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

@app.get("/protected")
async def protected_route(current_user: User = Depends(get_current_user)):
    return {"message": f"Hello {current_user.email}!"}
```

### 3. User Registration Flow

**Register a new user:**
```bash
POST /auth/users/register
{
  "email": "user@example.com",
  "password": "SecurePassword123",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Verify email:**
```bash
POST /auth/users/verify-email
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

### Custom User Model

Extend the base User model with custom fields:

```python
from oauth2fast_fastapi.models.user_model import User
from sqlmodel import Field

class CustomUser(User, table=True):
    __tablename__ = "custom_users"
    
    phone_number: str | None = Field(default=None)
    company: str | None = Field(default=None)
```

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

### Database Settings
- `AUTH_DB__USERNAME`: Database username
- `AUTH_DB__PASSWORD`: Database password
- `AUTH_DB__HOSTNAME`: Database host
- `AUTH_DB__NAME`: Database name
- `AUTH_DB__PORT`: Database port (default: 5432)

### Mail Settings
- `AUTH_MAIL_SERVER__USERNAME`: SMTP username
- `AUTH_MAIL_SERVER__PASSWORD`: SMTP password
- `AUTH_MAIL_SERVER__SERVER`: SMTP server
- `AUTH_MAIL_SERVER__PORT`: SMTP port
- `AUTH_MAIL_SERVER__FROM_DIRECTION`: From email address
- `AUTH_MAIL_SERVER__FROM_NAME`: From name
- `AUTH_MAIL_SERVER__STARTTLS`: Use STARTTLS (default: false)
- `AUTH_MAIL_SERVER__SSL_TLS`: Use SSL/TLS (default: true)

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
3. Check email templates in `mail/templates/`

### Database Connection Issues

Ensure your database URL is correct and the database exists:
```bash
AUTH_DB__USERNAME=postgres
AUTH_DB__PASSWORD=password
AUTH_DB__HOSTNAME=localhost
AUTH_DB__NAME=mydb
AUTH_DB__PORT=5432
```
