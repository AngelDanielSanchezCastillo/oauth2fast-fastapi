from pathlib import Path

from fastapi_mail import ConnectionConfig

from ..settings import settings

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_PATH = BASE_DIR / "templates"

config = ConnectionConfig(
    MAIL_USERNAME=settings.auth_mail_server.username,
    MAIL_PASSWORD=settings.auth_mail_server.password,
    MAIL_FROM=settings.auth_mail_server.from_direction,
    MAIL_PORT=settings.auth_mail_server.port,
    MAIL_SERVER=settings.auth_mail_server.server,
    MAIL_FROM_NAME=settings.auth_mail_server.from_name,
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    TEMPLATE_FOLDER=TEMPLATES_PATH,
)
