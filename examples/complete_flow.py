"""
Complete authentication flow example for oauth2fast-fastapi

This example demonstrates:
- User registration
- Email verification
- Login with JWT tokens
- Protected endpoints
- Verified-only endpoints
"""

from fastapi import Depends, FastAPI
from oauth2fast_fastapi import (
    User,
    engine,
    get_current_user,
    get_current_verified_user,
    router,
)
from sqlmodel import SQLModel

app = FastAPI(
    title="Complete Auth Flow Example",
    description="Full authentication flow with email verification",
)

# Include authentication router
app.include_router(router, prefix="/auth", tags=["Authentication"])


@app.on_event("startup")
async def startup():
    """Create database tables on startup"""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    print("✅ Database ready")
    print("\n📋 Authentication Flow:")
    print("1. Register: POST /auth/users/register")
    print("2. Verify email: POST /auth/users/verify-email")
    print("3. Login: POST /auth/token")
    print("4. Access protected: GET /dashboard (with Authorization header)")
    print("5. Access verified-only: GET /premium (requires verified email)\n")


@app.get("/")
async def root():
    """Public homepage"""
    return {
        "app": "OAuth2Fast Complete Example",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/dashboard")
async def dashboard(current_user: User = Depends(get_current_user)):
    """
    Protected endpoint - requires authentication
    Any authenticated user can access this
    """
    return {
        "message": f"Welcome to your dashboard, {current_user.first_name}!",
        "user": {
            "email": current_user.email,
            "verified": current_user.is_verified,
            "active": current_user.is_active,
        },
        "note": "This endpoint requires authentication but not email verification",
    }


@app.get("/premium")
async def premium_feature(current_user: User = Depends(get_current_verified_user)):
    """
    Verified-only endpoint - requires authentication AND email verification
    Only users with verified emails can access this
    """
    return {
        "message": f"Welcome to premium features, {current_user.first_name}!",
        "user": {
            "email": current_user.email,
            "verified": current_user.is_verified,
        },
        "note": "This endpoint requires both authentication AND email verification",
    }


@app.get("/public")
async def public_endpoint():
    """Public endpoint - no authentication required"""
    return {
        "message": "This is a public endpoint",
        "note": "Anyone can access this without authentication",
    }


if __name__ == "__main__":
    import uvicorn

    print("\n🚀 Starting OAuth2Fast Complete Example")
    print("📖 Visit http://localhost:8000/docs for API documentation\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
