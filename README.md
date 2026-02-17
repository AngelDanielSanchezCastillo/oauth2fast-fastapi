# oauth2fast-fastapi

🔐 Fast and secure OAuth2 authentication module for FastAPI with email verification and JWT tokens

> [!WARNING]
> **Internal Use Notice**
> 
> This package is designed and maintained by the **Solautyc Team** for internal use. While it is publicly available, it may not work as expected in all environments or use cases outside of our specific infrastructure. We do not provide support or guarantees for external usage, and we are not responsible for any issues that may arise from using this package in other contexts.
> 
> Use at your own risk. Contributions and feedback are welcome, but compatibility with external environments is not guaranteed.

## Features

- 🔐 **Complete OAuth2 Implementation**: Full OAuth2 password flow with JWT tokens
- 📧 **Email Verification**: Built-in email verification system with customizable templates
- 👤 **User Management**: Ready-to-use user registration, login, and profile endpoints
- 🗄️ **SQLModel Integration**: Async PostgreSQL support with SQLModel/SQLAlchemy
- 🔑 **Secure Password Hashing**: Argon2 password hashing (winner of Password Hashing Competition)
- 🎯 **FastAPI Dependencies**: Easy-to-use dependencies for protected routes
- ⚡ **Async/Await**: Full async support for high performance
- 🎨 **Customizable**: Extend the User model with your own fields
- 📝 **Type-Safe Configuration**: Pydantic settings with environment variables
- 🔄 **Email Templates**: Jinja2 templates for verification and welcome emails

## Installation

### From PyPI (Recommended)

```bash
pip install oauth2fast-fastapi
```

### From Source

```bash
# Clone the repository
git clone https://github.com/AngelDanielSanchezCastillo/oauth2fast-fastapi.git
cd oauth2fast-fastapi

# Install in development mode
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"
```

## Quick Start

### 1. Configure Environment Variables

Create a `.env` file in your project root:

```bash
# Required JWT Configuration
SECRET_KEY=your-super-secret-key-change-this-in-production
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

> [!IMPORTANT]
> The `SECRET_KEY` is **required** and must be set in your `.env` file. Generate a secure key:
> ```bash
> python -c "import secrets; print(secrets.token_urlsafe(32))"
> ```

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

@app.get("/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    return {
        "email": current_user.email,
        "name": f"{current_user.first_name} {current_user.last_name}",
        "verified": current_user.is_verified
    }
```

### 3. Authentication Flow

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

**Login:**
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

**Access protected endpoint:**
```bash
GET /profile
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Protected Endpoints

Use the provided dependencies to protect your endpoints:

```python
from fastapi import Depends
from oauth2fast_fastapi import get_current_user, get_current_verified_user, User

# Requires authentication only
@app.get("/dashboard")
async def dashboard(user: User = Depends(get_current_user)):
    return {"message": f"Welcome {user.email}"}

# Requires authentication AND email verification
@app.get("/premium")
async def premium_feature(user: User = Depends(get_current_verified_user)):
    return {"message": "Access granted to verified users only"}
```

## Custom User Model

Extend the base User model with your own fields:

```python
from oauth2fast_fastapi.models.user_model import User as BaseUser
from sqlmodel import Field

class CustomUser(BaseUser, table=True):
    __tablename__ = "custom_users"
    
    phone_number: str | None = Field(default=None)
    company: str | None = Field(default=None)
    role: str = Field(default="user")
```

## Available Endpoints

The authentication router provides the following endpoints:

- `POST /auth/users/register` - Register a new user
- `POST /auth/users/verify-email` - Verify email with token
- `POST /auth/users/resend-verification` - Resend verification email
- `POST /auth/token` - Login and get JWT token
- `GET /auth/users/me` - Get current user profile
- `PUT /auth/users/me` - Update current user profile

## Configuration Reference

All configuration is done via environment variables with nested delimiter `__`.

### JWT Settings (Required)
- `SECRET_KEY` - **Required**: Secret key for JWT signing
- `ALGORITHM` - Default: `"HS256"`: JWT algorithm
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Default: `60`: Token expiration time in minutes

### Database Settings
- `AUTH_DB__USERNAME` - Database username
- `AUTH_DB__PASSWORD` - Database password
- `AUTH_DB__HOSTNAME` - Database host
- `AUTH_DB__NAME` - Database name
- `AUTH_DB__PORT` - Database port (default: 5432)

### Mail Settings
- `AUTH_MAIL_SERVER__USERNAME` - SMTP username
- `AUTH_MAIL_SERVER__PASSWORD` - SMTP password
- `AUTH_MAIL_SERVER__SERVER` - SMTP server
- `AUTH_MAIL_SERVER__PORT` - SMTP port
- `AUTH_MAIL_SERVER__FROM_DIRECTION` - From email address
- `AUTH_MAIL_SERVER__FROM_NAME` - From name
- `AUTH_MAIL_SERVER__STARTTLS` - Use STARTTLS (default: false)
- `AUTH_MAIL_SERVER__SSL_TLS` - Use SSL/TLS (default: true)

### Application Settings
- `PROJECT_NAME` - Application name (used in emails)
- `FRONTEND_URL` - Frontend URL (for email links)
- `AUTH_URL_PREFIX` - Auth router prefix (default: "auth")

## 📚 Documentation

- **[Usage Guide](docs/usage.md)** - Comprehensive usage guide with examples
- **[Environment Configuration](docs/env.example)** - All configuration options

## 📁 Module Structure

```
oauth2fast-fastapi/
├── pyproject.toml
├── MANIFEST.in
├── README.md
├── LICENSE
├── src/
│   └── oauth2fast_fastapi/
│       ├── __init__.py
│       ├── __version__.py
│       ├── settings.py          # Pydantic settings
│       ├── database.py          # Database engine
│       ├── dependencies.py      # FastAPI dependencies
│       ├── models/
│       │   ├── bases.py         # Base models
│       │   ├── mixins.py        # Model mixins
│       │   └── user_model.py    # User model
│       ├── routers/
│       │   ├── base_router.py   # Main router
│       │   └── users_router.py  # User endpoints
│       ├── schemas/
│       │   ├── token_schema.py  # JWT schemas
│       │   ├── user_schema.py   # User schemas
│       │   └── verification_schema.py
│       ├── utils/
│       │   ├── password_utils.py    # Password hashing
│       │   ├── token_utils.py       # JWT utilities
│       │   └── verification_utils.py
│       └── mail/
│           ├── connection.py    # SMTP connection
│           ├── service.py       # Email service
│           └── templates/       # Email templates
│               ├── verification.html
│               └── welcome.html
├── docs/
│   ├── env.example
│   └── usage.md
├── examples/
│   ├── basic_usage.py
│   ├── custom_user.py
│   └── complete_flow.py
└── tests/
```

## Dependencies

This module depends on:

- [FastAPI](https://github.com/tiangolo/fastapi) - Modern web framework (MIT License)
- [Pydantic](https://github.com/pydantic/pydantic) - Data validation (MIT License)
- [SQLModel](https://github.com/tiangolo/sqlmodel) - SQL databases with Python (MIT License)
- [SQLAlchemy](https://github.com/sqlalchemy/sqlalchemy) - Database toolkit (MIT License)
- [asyncpg](https://github.com/MagicStack/asyncpg) - PostgreSQL driver (Apache 2.0)
- [python-jose](https://github.com/mpdavis/python-jose) - JWT implementation (MIT License)
- [passlib](https://github.com/glic3rinu/passlib) - Password hashing (BSD License)
- [fastapi-mail](https://github.com/sabuhish/fastapi-mail) - Email sending (MIT License)
- [log2fast-fastapi](https://github.com/AngelDanielSanchezCastillo/log2fast-fastapi) - Logging module (MIT License)

We are grateful to the maintainers and contributors of these projects.

## Security Features

- 🔒 **Argon2 Password Hashing**: Uses Argon2, the winner of the Password Hashing Competition
- 🎫 **JWT Tokens**: Secure token-based authentication
- ✉️ **Email Verification**: Prevents fake account creation
- 🔐 **Secure Defaults**: Sensible security defaults out of the box
- 🛡️ **SQL Injection Protection**: SQLModel/SQLAlchemy ORM prevents SQL injection

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2026 Angel Daniel Sanchez Castillo

**Note**: This package is designed and maintained by the Solautyc Team for internal use. While publicly available under MIT license, use at your own risk.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions, please use the [GitHub Issues](https://github.com/AngelDanielSanchezCastillo/oauth2fast-fastapi/issues) page.
