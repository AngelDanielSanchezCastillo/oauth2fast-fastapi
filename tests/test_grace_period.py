"""
Integration tests for the unconditional email-verification policy (0.4.8).

Email verification is ALWAYS enforced in ``POST /auth/token``. The flag
``enforce_email_verification`` no longer toggles verification; it only
controls whether the grace period (``verification_grace_days``) applies to
unverified users:

- ``enforce_email_verification=False`` (default): unverified users are
  blocked immediately (403) — grace does NOT apply, even if
  ``verification_grace_days`` is configured.
- ``enforce_email_verification=True`` + ``verification_grace_days=None``:
  unverified users are blocked immediately (403).
- ``enforce_email_verification=True`` + ``verification_grace_days=int``:
  unverified users within the grace period (counted from ``user.created_at``,
  naive datetimes assumed UTC) can log in; beyond it they get 403.

Empty lines in ``.env`` never crash: ``ENFORCE_EMAIL_VERIFICATION=`` maps to
``False`` and ``VERIFICATION_GRACE_DAYS=`` maps to ``None`` (fail-closed).
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from oauth2fast_fastapi import (
    AuthModel,
    router,
    settings,
    shutdown_database,
    startup_database,
)
from oauth2fast_fastapi.routers.base_router import _days_since_creation
from oauth2fast_fastapi.settings import Settings
from oauth2fast_fastapi.utils.verification_utils import create_verification_token
from pgsqlasync2fast_fastapi import get_manager

PASSWORD = "SecurePassword123"


@pytest.fixture(scope="module")
def app():
    """Crea la aplicación FastAPI para testing."""
    test_app = FastAPI()
    test_app.include_router(router, tags=["Authentication"])
    return test_app


@pytest.fixture
async def setup_database():
    """Prepara la base de datos para testing (crea y limpia las tablas)."""
    await startup_database()

    manager = get_manager()
    engine = manager.get_engine("auth")

    async with engine.begin() as conn:
        await conn.run_sync(AuthModel.metadata.create_all)

    yield

    async with engine.begin() as conn:
        for table in reversed(AuthModel.metadata.sorted_tables):
            await conn.execute(text(f"DROP TABLE IF EXISTS {table.name} CASCADE"))

    await shutdown_database()


@pytest.fixture
async def client(app, setup_database):
    """Crea un cliente async de pruebas."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def restore_settings():
    """Restaura los valores originales de settings tras cada test."""
    original_enforce = settings.enforce_email_verification
    original_grace = settings.verification_grace_days
    yield
    settings.enforce_email_verification = original_enforce
    settings.verification_grace_days = original_grace


async def register_user(
    client: AsyncClient, email: str, name: str = "Grace User"
) -> None:
    """Registra un usuario (queda no verificado)."""
    response = await client.post(
        "/auth/users/",
        json={"email": email, "password": PASSWORD, "name": name},
    )
    assert response.status_code == 200


async def login(client: AsyncClient, email: str) -> AsyncClient:
    """Intenta iniciar sesión en /auth/token."""
    return await client.post(
        "/auth/token",
        data={"username": email, "password": PASSWORD},
    )


async def backdate_created_at(email: str, days: int) -> None:
    """Retrasa created_at del usuario N días (UTC) para simular cuentas antiguas."""
    manager = get_manager()
    engine = manager.get_engine("auth")
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE users SET created_at = :ts WHERE email = :email"),
            {
                "ts": datetime.now(timezone.utc) - timedelta(days=days),
                "email": email,
            },
        )


# ============ Comportamiento de /auth/token con el periodo de gracia ============


async def test_default_config_unverified_user_blocked(client: AsyncClient):
    """Config por defecto (enforce=False): la verificación de email es SIEMPRE
    incondicional — usuario no verificado recibe 403 inmediato (comportamiento
    nuevo desde 0.4.6; antes hacía login sin verificar)."""
    email = "default-config@example.com"
    await register_user(client, email)

    response = await login(client, email)

    assert response.status_code == 403
    data = response.json()
    assert data["success"] is False
    assert "Email no verificado" in data["message"]
    assert "periodo de gracia ha expirado" not in data["message"]


async def test_flag_false_with_grace_configured_still_blocks(client: AsyncClient):
    """enforce=False explícito + grace_days configurado: la indulgencia NO
    aplica sin el flag — usuario no verificado recibe 403 inmediato."""
    settings.enforce_email_verification = False
    settings.verification_grace_days = 10

    email = "flag-off-with-grace@example.com"
    await register_user(client, email)

    response = await login(client, email)

    assert response.status_code == 403
    data = response.json()
    assert data["success"] is False
    assert "Email no verificado" in data["message"]
    assert "periodo de gracia ha expirado" not in data["message"]


# ============ Settings: parseo de variables de entorno (fail-closed) ============


def test_grace_days_accepts_int_or_none_and_never_crashes_on_empty(monkeypatch):
    """Contrato 0.4.8: verification_grace_days es int | None. Sin variable de
    entorno el default es 10; una línea vacía (VERIFICATION_GRACE_DAYS=) se
    interpreta como None (sin indulgencia) sin crashear."""
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.delenv("VERIFICATION_GRACE_DAYS", raising=False)
    monkeypatch.delenv("ENFORCE_EMAIL_VERIFICATION", raising=False)

    s_default = Settings()
    assert isinstance(s_default.verification_grace_days, int)
    assert s_default.verification_grace_days == 10

    monkeypatch.setenv("VERIFICATION_GRACE_DAYS", "")
    s_empty = Settings()
    assert s_empty.verification_grace_days is None


def test_empty_enforce_env_does_not_crash_and_means_false(monkeypatch):
    """ENFORCE_EMAIL_VERIFICATION= (vacío) no crashea: se interpreta como
    False (fail-closed → bloqueo inmediato de no verificados)."""
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("ENFORCE_EMAIL_VERIFICATION", "")

    s = Settings()

    assert s.enforce_email_verification is False


def test_enforce_env_parses_true_and_false(monkeypatch):
    """ENFORCE_EMAIL_VERIFICATION=true → True; =false → False."""
    monkeypatch.setenv("SECRET_KEY", "test-secret")

    monkeypatch.setenv("ENFORCE_EMAIL_VERIFICATION", "true")
    assert Settings().enforce_email_verification is True

    monkeypatch.setenv("ENFORCE_EMAIL_VERIFICATION", "false")
    assert Settings().enforce_email_verification is False


def test_grace_env_parses_int(monkeypatch):
    """VERIFICATION_GRACE_DAYS=10 → 10."""
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("VERIFICATION_GRACE_DAYS", "10")

    assert Settings().verification_grace_days == 10


async def test_enforce_with_grace_none_rejects_unverified_user(client: AsyncClient):
    """enforce=True + grace_days=None: usuario no verificado recibe 403
    inmediato (sin indulgencia)."""
    settings.enforce_email_verification = True
    settings.verification_grace_days = None

    email = "no-grace@example.com"
    await register_user(client, email)

    response = await login(client, email)

    assert response.status_code == 403
    data = response.json()
    assert data["success"] is False
    assert "Email no verificado" in data["message"]
    assert "periodo de gracia ha expirado" not in data["message"]


async def test_enforce_with_grace_allows_unverified_user_within_period(
    client: AsyncClient,
):
    """enforce=True + grace_days=10: usuario no verificado reciente puede hacer login."""
    settings.enforce_email_verification = True
    settings.verification_grace_days = 10

    email = "within-grace@example.com"
    await register_user(client, email)

    response = await login(client, email)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data["token"]


async def test_enforce_with_grace_rejects_unverified_user_beyond_period(
    client: AsyncClient,
):
    """enforce=True + grace_days=10: usuario no verificado con created_at antiguo
    recibe 403 con el mensaje de periodo de gracia expirado."""
    settings.enforce_email_verification = True
    settings.verification_grace_days = 10

    email = "beyond-grace@example.com"
    await register_user(client, email)
    await backdate_created_at(email, days=15)

    response = await login(client, email)

    assert response.status_code == 403
    data = response.json()
    assert data["success"] is False
    assert "periodo de gracia ha expirado" in data["message"]


async def test_grace_boundary_exactly_ten_days_allows_login(client: AsyncClient):
    """Borde inclusivo: a exactamente 10 días de antigüedad el login sigue
    permitido (la comparación es estricta: age_days > grace_days)."""
    settings.enforce_email_verification = True
    settings.verification_grace_days = 10

    email = "boundary-grace@example.com"
    await register_user(client, email)
    await backdate_created_at(email, days=10)

    response = await login(client, email)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.parametrize(
    ("enforce", "grace_days"),
    [(False, 10), (True, 10)],
)
async def test_verified_user_always_can_login(
    client: AsyncClient, enforce: bool, grace_days: int
):
    """Usuario verificado siempre puede hacer login, sin importar la configuración."""
    settings.enforce_email_verification = enforce
    settings.verification_grace_days = grace_days

    email = f"verified-{enforce}-{grace_days}@example.com"
    await register_user(client, email)

    # Verificar email vía el flujo real de confirmación
    token = create_verification_token(email)
    verify_response = await client.post("/auth/confirm-email", json={"token": token})
    assert verify_response.status_code == 200

    response = await login(client, email)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data["token"]


# ============ Cálculo de días desde la creación (datetimes naive/aware) ============


def test_days_since_creation_naive_datetime_assumed_utc():
    """Un datetime naive se asume UTC (no debe lanzar ni comparar con hora local)."""
    created_naive = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=5)

    assert _days_since_creation(created_naive) == 5


def test_days_since_creation_aware_datetime():
    """Un datetime aware (con zona horaria) se resta directamente."""
    created_aware = datetime.now(timezone.utc) - timedelta(days=3)

    assert _days_since_creation(created_aware) == 3


def test_days_since_creation_without_created_at_returns_zero():
    """Sin created_at se devuelve 0 (el usuario se trata como reciente)."""
    assert _days_since_creation(None) == 0
