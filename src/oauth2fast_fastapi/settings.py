import os

from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Find .env in the application's root directory (where the app is installed)
# This allows the module to work independently in any application
BASE_DIR = os.getcwd()
DOTENV_PATH = os.path.join(BASE_DIR, ".env")


class DatabaseSettings(BaseModel):
    username: str = "DefaultUser"
    password: SecretStr = SecretStr("DefaultPassword")
    hostname: str = "localhost"
    name: str = "DefaultDatabase"
    port: int = 5432


class MailSettings(BaseModel):
    username: str = "DefaultUser"
    password: SecretStr = SecretStr("DefaultPassword")
    server: str = "localhost"
    port: int = 465
    from_direction: str = "email@email.test"
    from_name: str = "Your Service Name"
    starttls: bool = False
    ssl_tls: bool = True


class Settings(BaseSettings):
    project_name: str = "OAuth2Fast"
    frontend_url: str = "https://example.com/"
    auth_url_prefix: SecretStr = SecretStr("auth")

    # JWT Configuration
    secret_key: SecretStr  # Required - no default value
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Database configurations
    auth_db: DatabaseSettings = DatabaseSettings()

    # Mail configuration
    auth_mail_server: MailSettings = MailSettings()

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
