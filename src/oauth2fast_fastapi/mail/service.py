from fastapi import HTTPException, status
from fastapi_mail import FastMail, MessageSchema, MessageType

from ..settings import settings
from .connection import config


async def send_verification_email(email: str, verification_url: str) -> None:
    """
    Send verification email to user.

    Args:
        email: User's email address
        verification_url: Complete URL for email verification

    Raises:
        HTTPException: If email sending fails
    """
    try:
        message = MessageSchema(
            subject=f"Verifica tu cuenta - {settings.project_name}",
            recipients=[email],
            template_body={
                "email": email,
                "project_name": settings.project_name,
                "verification_url": verification_url,
                "support_email": settings.auth_mail_server.from_direction,
            },
            subtype=MessageType.html,
        )

        fm = FastMail(config)
        await fm.send_message(message, template_name="verification.html")

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending verification email: {str(e)}",
        ) from e
