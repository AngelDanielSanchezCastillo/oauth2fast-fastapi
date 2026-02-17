"""
Integration tests for OAuth2Fast-FastAPI with external modules.

Tests the integration of pgsqlasync2fast-fastapi and mailing2fast-fastapi
with the OAuth2Fast authentication system.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlmodel import SQLModel

# Import from oauth2fast_fastapi
from oauth2fast_fastapi import (
    User,
    UserCreate,
    AuthModel,
    get_auth_session,
    get_current_user,
    router,
    settings,
    shutdown_database,
    startup_database,
)

# Import from external modules
from pgsqlasync2fast_fastapi import get_db_engine, get_manager
from httpx import AsyncClient, ASGITransport


@pytest.fixture(scope="module")
def app():
    """Create FastAPI app for testing."""
    test_app = FastAPI()
    # Router already has a prefix configured in settings (default: /auth)
    test_app.include_router(router, tags=["Authentication"])
    
    @test_app.get("/protected")
    async def protected_route(current_user: User = pytest.importorskip("fastapi").Depends(get_current_user)):
        return {"message": f"Hello {current_user.email}!"}
    
    return test_app


@pytest.fixture
async def setup_database():
    """Setup database for testing."""
    # Initialize database connections
    await startup_database()
    
    # Get engine for auth connection using manager directly
    manager = get_manager()
    engine = manager.get_engine("auth")
    
    # Create tables using AuthModel metadata directly
    # Note: AuthModel uses a custom metadata instance to isolate auth tables
    async with engine.begin() as conn:
        await conn.run_sync(AuthModel.metadata.create_all)
    
    yield
    
    # Cleanup: Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(AuthModel.metadata.drop_all)
    
    # Shutdown database connections
    await shutdown_database()


@pytest.fixture
async def client(app, setup_database):
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_database_connection(setup_database):
    """Test that database connection works."""
    manager = get_manager()
    engine = manager.get_engine("auth")
    
    async with engine.connect() as conn:
        result = await conn.execute(pytest.importorskip("sqlalchemy").text("SELECT 1"))
        assert result.scalar() == 1


@pytest.mark.asyncio
async def test_user_table_created(setup_database):
    """Test that User table is created in database."""
    from sqlalchemy import inspect
    
    manager = get_manager()
    engine = manager.get_engine("auth")
    
    async with engine.connect() as conn:
        # Check if user table exists
        def check_table(connection):
            inspector = inspect(connection)
            tables = inspector.get_table_names()
            return "users" in tables
        
        table_exists = await conn.run_sync(check_table)
        assert table_exists, "User table was not created"


@pytest.mark.asyncio
async def test_user_registration(client: AsyncClient):
    """Test user registration endpoint."""
    response = await client.post(
        "/auth/users/",
        json={
            "email": "test@example.com",
            "password": "SecurePassword123",
            "name": "Test User",
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["name"] == "Test User"
    assert data["is_verified"] is False
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_duplicate_user_registration(client: AsyncClient):
    """Test that duplicate email registration fails."""
    # First registration
    await client.post(
        "/auth/users/",
        json={
            "email": "duplicate@example.com",
            "password": "Password123",
            "name": "First User",
        },
    )
    
    # Duplicate registration
    response = await client.post(
        "/auth/users/",
        json={
            "email": "duplicate@example.com",
            "password": "Password456",
            "name": "Second User",
        },
    )
    
    assert response.status_code == 400
    assert "email ya existe" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_user_login(client: AsyncClient):
    """Test user login and token generation."""
    # Register user
    await client.post(
        "/auth/users/",
        json={
            "email": "login@example.com",
            "password": "LoginPassword123",
            "name": "Login User",
        },
    )
    
    # Login
    response = await client.post(
        "/auth/token",
        data={
            "username": "login@example.com",
            "password": "LoginPassword123",
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(client: AsyncClient):
    """Test that protected endpoint requires authentication."""
    response = await client.get("/protected")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_with_token(client: AsyncClient):
    """Test protected endpoint with valid token."""
    # Register and login
    await client.post(
        "/auth/users/",
        json={
            "email": "protected@example.com",
            "password": "ProtectedPassword123",
            "name": "Protected User",
        },
    )
    
    login_response = await client.post(
        "/auth/token",
        data={
            "username": "protected@example.com",
            "password": "ProtectedPassword123",
        },
    )
    
    token = login_response.json()["access_token"]
    
    # Access protected endpoint
    response = await client.get(
        "/protected",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "protected@example.com" in data["message"]


@pytest.mark.asyncio
async def test_email_verification_token_generation():
    """Test that verification tokens can be generated."""
    from oauth2fast_fastapi.utils.verification_utils import (
        create_verification_token,
        verify_verification_token,
    )
    
    email = "verify@example.com"
    token = create_verification_token(email)
    
    assert token is not None
    assert isinstance(token, str)
    
    # Verify token
    decoded_email = verify_verification_token(token)
    assert decoded_email == email


@pytest.mark.asyncio
async def test_email_verification_flow(client: AsyncClient):
    """Test complete email verification flow."""
    from oauth2fast_fastapi.utils.verification_utils import create_verification_token
    
    # Register user
    response = await client.post(
        "/auth/users/",
        json={
            "email": "emailverify@example.com",
            "password": "VerifyPassword123",
            "name": "Email Verify User",
        },
    )
    
    assert response.json()["is_verified"] is False
    
    # Generate verification token
    token = create_verification_token("emailverify@example.com")
    
    # Verify email
    verify_response = await client.post(
        "/auth/confirm-email",
        json={"token": token},
    )
    
    assert verify_response.status_code == 200
    data = verify_response.json()
    assert data["success"] is True
    assert "verificado" in data["message"].lower()


@pytest.mark.asyncio
async def test_get_users_list(client: AsyncClient):
    """Test getting list of all users."""
    # Register a user
    await client.post(
        "/auth/users/",
        json={
            "email": "listuser@example.com",
            "password": "ListPassword123",
            "name": "List User",
        },
    )
    
    # Get users list
    response = await client.get("/auth/users/")
    
    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, list)
    assert len(users) > 0
    
    # Check that our user is in the list
    emails = [user["email"] for user in users]
    assert "listuser@example.com" in emails


@pytest.mark.asyncio
async def test_get_user_by_email(client: AsyncClient):
    """Test getting user by email."""
    # Register a user
    await client.post(
        "/auth/users/",
        json={
            "email": "getuser@example.com",
            "password": "GetPassword123",
            "name": "Get User",
        },
    )
    
    # Get user by email
    response = await client.get("/auth/users/by-email/getuser@example.com")
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "getuser@example.com"
    assert data["name"] == "Get User"


@pytest.mark.asyncio
async def test_settings_configuration():
    """Test that settings are properly configured."""
    assert settings.project_name is not None
    assert settings.frontend_url is not None
    assert settings.secret_key is not None
    assert settings.algorithm == "HS256"
    assert settings.access_token_expire_minutes > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
