import os

from pydantic import SecretStr
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

