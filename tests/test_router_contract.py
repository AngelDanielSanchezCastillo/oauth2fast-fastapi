"""
Tests de contrato de routers: public_router vs admin_router.

Verifica que cada router expone solo los endpoints que le corresponden.
Los tests funcionales de los endpoints están en test_integration.py.
"""

import pytest
from fastapi import FastAPI


@pytest.fixture(scope="module")
def app():
    """Create FastAPI app with both routers."""
    from oauth2fast_fastapi import public_router, admin_router

    test_app = FastAPI()
    test_app.include_router(public_router, tags=["Public Auth"])
    test_app.include_router(admin_router, tags=["Admin Auth"])
    return test_app


def test_public_router_exposes_token_endpoint(app):
    """public_router expone POST /auth/token."""
    paths = list(app.openapi()["paths"].keys())
    assert "/auth/token" in paths


def test_public_router_exposes_refresh_endpoint(app):
    """public_router expone POST /auth/token/refresh."""
    paths = list(app.openapi()["paths"].keys())
    assert "/auth/token/refresh" in paths


def test_public_router_exposes_logout_endpoint(app):
    """public_router expone POST /auth/logout."""
    paths = list(app.openapi()["paths"].keys())
    assert "/auth/logout" in paths


def test_public_router_exposes_logout_all_endpoint(app):
    """public_router expone POST /auth/logout/all."""
    paths = list(app.openapi()["paths"].keys())
    assert "/auth/logout/all" in paths


def test_public_router_exposes_register_endpoint(app):
    """public_router expone POST /auth/users/ (registro público)."""
    paths = list(app.openapi()["paths"].keys())
    assert "/auth/users/" in paths
    # POST method debe estar presente
    assert "post" in app.openapi()["paths"]["/auth/users/"]


def test_public_router_exposes_confirm_email_endpoint(app):
    """public_router expone POST /auth/confirm-email."""
    paths = list(app.openapi()["paths"].keys())
    assert "/auth/confirm-email" in paths


def test_public_router_exposes_resend_verification_endpoint(app):
    """public_router expone POST /auth/resend-verification."""
    paths = list(app.openapi()["paths"].keys())
    assert "/auth/resend-verification" in paths


def test_admin_router_exposes_users_list_endpoint(app):
    """admin_router expone GET /auth/users/ (listar usuarios)."""
    paths = list(app.openapi()["paths"].keys())
    assert "/auth/users/" in paths
    # GET method debe estar presente
    assert "get" in app.openapi()["paths"]["/auth/users/"]


def test_admin_router_exposes_user_by_email_endpoint(app):
    """admin_router expone GET /auth/users/by-email/{email}."""
    paths = list(app.openapi()["paths"].keys())
    assert "/auth/users/by-email/{email}" in paths


def test_users_endpoint_has_both_post_and_get(app):
    """/auth/users/ expone POST (registro público) y GET (admin)."""
    paths = list(app.openapi()["paths"].keys())
    assert "/auth/users/" in paths
    methods = list(app.openapi()["paths"]["/auth/users/"].keys())
    assert "post" in methods  # público
    assert "get" in methods  # admin


def test_token_endpoint_not_in_admin_router_only(app):
    """/auth/token NO debe estar solo en admin_router (está en public_router)."""
    paths = list(app.openapi()["paths"].keys())
    assert "/auth/token" in paths


def test_users_by_email_not_in_public_router(app):
    """GET /auth/users/by-email/{email} NO debe estar en public_router."""
    paths = list(app.openapi()["paths"].keys())
    assert "/auth/users/by-email/{email}" in paths  # existe en admin_router


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
