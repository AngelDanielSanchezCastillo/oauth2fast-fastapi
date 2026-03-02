"""
Custom user model example for oauth2fast-fastapi

This example shows how to extend the base User model with custom fields.
"""

from datetime import datetime

from fastapi import Depends, FastAPI
from oauth2fast_fastapi import engine, get_current_user, AuthModel
from oauth2fast_fastapi.models.user_model import User as BaseUser
from sqlmodel import Field

# Extend the base User model with custom fields
class CustomUser(BaseUser, table=True):
    __tablename__ = "custom_users"

    # Add custom fields
    phone_number: str | None = Field(default=None, max_length=20)
    company: str | None = Field(default=None, max_length=100)
    role: str = Field(default="user", max_length=50)
    last_login: datetime | None = Field(default=None)


app = FastAPI(title="Custom User Model Example")


@app.on_event("startup")
async def startup():
    """Create database tables on startup"""
    async with engine.begin() as conn:
        await conn.run_sync(AuthModel.metadata.create_all)
    print("✅ Custom user tables created")


@app.get("/me")
async def get_current_user_info(current_user: CustomUser = Depends(get_current_user)):
    """Get current user with custom fields"""
    return {
        "email": current_user.email,
        "name": f"{current_user.first_name} {current_user.last_name}",
        "phone": current_user.phone_number,
        "company": current_user.company,
        "role": current_user.role,
        "last_login": current_user.last_login,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
