import os

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Find .env in the application's root directory (where the app is installed)
# This allows the module to work independently in any application
BASE_DIR = os.getcwd()
DOTENV_PATH = os.path.join(BASE_DIR, ".env")


class Settings(BaseSettings):
    # Application settings
    project_name: str = "OAuth2Fast Application"
    frontend_url: str = "http://localhost:3000/"
    auth_url_prefix: SecretStr = SecretStr("auth")

    # JWT Configuration
    secret_key: SecretStr  # Required - no default value
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Email verification: SIEMPRE exigida en /auth/token (incondicional desde 0.4.6).
    # Este flag ya no activa la verificación; solo controla si se aplica la
    # indulgencia de verification_grace_days (False = bloqueo inmediato 403).
    enforce_email_verification: bool = False
    # Días de gracia para usuarios no verificados; None = bloqueo inmediato (403).
    # Una línea vacía en .env (VERIFICATION_GRACE_DAYS=) se mapea a None.
    verification_grace_days: int | None = 10

    @field_validator("enforce_email_verification", mode="before")
    @classmethod
    def _empty_enforce_is_false(cls, v: object) -> object:
        """Una línea vacía en .env (ENFORCE_EMAIL_VERIFICATION=) no debe
        crashear: se interpreta como False (fail-closed → bloqueo inmediato)."""
        if v == "":
            return False
        return v

    @field_validator("verification_grace_days", mode="before")
    @classmethod
    def _empty_grace_is_none(cls, v: object) -> object:
        """Una línea vacía en .env (VERIFICATION_GRACE_DAYS=) no debe crashear:
        se interpreta como None (sin indulgencia → bloqueo inmediato)."""
        if v == "":
            return None
        return v

    model_config = SettingsConfigDict(
        env_file=DOTENV_PATH,
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )


try:
    settings = Settings()
except Exception as e:
    # Use log2fast_fastapi for proper error logging
    from log2fast_fastapi import get_logger

    logger = get_logger(__name__)  # Uses "oauth2fast_fastapi.settings"

    logger.exception(
        "🚨 Error loading OAuth2Fast configuration",
        extra_data={
            "error": str(e),
            "dotenv_path": DOTENV_PATH,
        },
    )
    raise
