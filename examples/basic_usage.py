"""
Basic usage example for oauth2fast-fastapi

This example shows how to integrate oauth2fast-fastapi into a FastAPI application.
"""

from fastapi import Depends, FastAPI
from oauth2fast_fastapi import User, engine, get_current_user, router, AuthModel

app = FastAPI(
    title="OAuth2Fast Example",
    description="Basic authentication example using oauth2fast-fastapi",
)

# Include the authentication router
app.include_router(router, prefix="/auth", tags=["Authentication"])


@app.on_event("startup")
async def startup():
    """Create database tables on startup"""
    async with engine.begin() as conn:
        await conn.run_sync(AuthModel.metadata.create_all)
    print("✅ Database tables created")
    print("📝 Register a user at: POST /auth/users/register")
    print("🔐 Login at: POST /auth/token")


@app.get("/")
async def root():
    """Public endpoint - no authentication required"""
    return {
        "message": "Welcome to OAuth2Fast Example",
        "endpoints": {
            "register": "POST /auth/users/register",
            "login": "POST /auth/token",
            "profile": "GET /profile (requires authentication)",
        },
    }


@app.get("/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    """Protected endpoint - requires authentication"""
    return {
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "is_verified": current_user.is_verified,
        "is_active": current_user.is_active,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
