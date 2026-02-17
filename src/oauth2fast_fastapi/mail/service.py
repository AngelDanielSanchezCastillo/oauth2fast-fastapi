"""
Email service for OAuth2Fast-FastAPI.

This module uses mailing2fast-fastapi for email sending.
The email configuration is handled via environment variables with the prefix MAIL_SMTP_ACCOUNTS__AUTH__
"""

from mailing2fast_fastapi import EmailMessage, EmailSender, get_email_sender

from ..settings import settings


def get_verification_email_html(
    email: str, project_name: str, verification_url: str, support_email: str
) -> str:
    """
    Generate HTML for verification email.
    
    Args:
        email: User's email address
        project_name: Name of the project
        verification_url: URL for email verification
        support_email: Support email address
        
    Returns:
        HTML string for the email
    """
    return f"""<!DOCTYPE html>
<html lang="es">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verifica tu cuenta - {project_name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px 20px;
            line-height: 1.6;
        }}

        .email-container {{
            max-width: 600px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px 30px;
            text-align: center;
        }}

        .header h1 {{
            color: #ffffff;
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 10px;
        }}

        .header p {{
            color: rgba(255, 255, 255, 0.9);
            font-size: 16px;
        }}

        .content {{
            padding: 40px 30px;
        }}

        .greeting {{
            font-size: 20px;
            color: #2d3748;
            margin-bottom: 20px;
            font-weight: 600;
        }}

        .message {{
            color: #4a5568;
            font-size: 16px;
            margin-bottom: 30px;
            line-height: 1.8;
        }}

        .verification-box {{
            background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
            border-radius: 12px;
            padding: 30px;
            text-align: center;
            margin: 30px 0;
            border: 2px solid #e2e8f0;
        }}

        .verification-box p {{
            color: #4a5568;
            margin-bottom: 20px;
            font-size: 15px;
        }}

        .verify-button {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #ffffff;
            text-decoration: none;
            padding: 16px 40px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 16px;
            transition: transform 0.2s, box-shadow 0.2s;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }}

        .verify-button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        }}

        .divider {{
            height: 1px;
            background: linear-gradient(to right, transparent, #cbd5e0, transparent);
            margin: 30px 0;
        }}

        .alternative-text {{
            color: #718096;
            font-size: 14px;
            margin-top: 20px;
            line-height: 1.6;
        }}

        .link-box {{
            background: #f7fafc;
            border: 1px dashed #cbd5e0;
            border-radius: 8px;
            padding: 15px;
            margin-top: 15px;
            word-break: break-all;
        }}

        .link-box a {{
            color: #667eea;
            text-decoration: none;
            font-size: 13px;
        }}

        .footer {{
            background: #f7fafc;
            padding: 30px;
            text-align: center;
            color: #718096;
            font-size: 14px;
        }}

        .footer p {{
            margin-bottom: 10px;
        }}

        .footer a {{
            color: #667eea;
            text-decoration: none;
        }}

        .security-note {{
            background: #fff5f5;
            border-left: 4px solid #fc8181;
            padding: 15px;
            margin-top: 30px;
            border-radius: 4px;
        }}

        .security-note p {{
            color: #742a2a;
            font-size: 14px;
            margin: 0;
        }}

        @media only screen and (max-width: 600px) {{
            body {{
                padding: 20px 10px;
            }}

            .header h1 {{
                font-size: 24px;
            }}

            .content {{
                padding: 30px 20px;
            }}

            .verify-button {{
                padding: 14px 30px;
                font-size: 15px;
            }}
        }}
    </style>
</head>

<body>
    <div class="email-container">
        <div class="header">
            <h1>🎉 ¡Bienvenido a {project_name}!</h1>
            <p>Estamos emocionados de tenerte con nosotros</p>
        </div>

        <div class="content">
            <p class="greeting">Hola {email},</p>

            <p class="message">
                Gracias por registrarte en <strong>{project_name}</strong>. Para completar tu registro y comenzar a
                disfrutar de todos nuestros servicios, necesitamos verificar tu dirección de correo electrónico.
            </p>

            <div class="verification-box">
                <p><strong>Verifica tu cuenta ahora</strong></p>
                <a href="{verification_url}" class="verify-button">Verificar mi cuenta</a>
            </div>

            <p class="message">
                Este enlace de verificación es válido por <strong>24 horas</strong>. Si no solicitaste esta cuenta,
                puedes ignorar este correo de forma segura.
            </p>

            <div class="divider"></div>

            <p class="alternative-text">
                <strong>¿El botón no funciona?</strong><br>
                Copia y pega el siguiente enlace en tu navegador:
            </p>
            <div class="link-box">
                <a href="{verification_url}">{verification_url}</a>
            </div>

            <div class="security-note">
                <p>
                    <strong>⚠️ Nota de seguridad:</strong> Nunca compartas este enlace con nadie. Nuestro equipo nunca
                    te pedirá tu contraseña por correo electrónico.
                </p>
            </div>
        </div>

        <div class="footer">
            <p><strong>{project_name}</strong></p>
            <p>Este es un correo automático, por favor no respondas a este mensaje.</p>
            <p>Si necesitas ayuda, contáctanos en <a href="mailto:{support_email}">{support_email}</a></p>
        </div>
    </div>
</body>

</html>"""


async def send_verification_email(email: str, verification_url: str) -> None:
    """
    Send verification email to user using mailing2fast-fastapi.
    
    This function uses the "auth" SMTP account configured in environment variables.
    
    Args:
        email: User's email address
        verification_url: Complete URL for email verification
        
    Raises:
        Exception: If email sending fails
    """
    from mailing2fast_fastapi import get_manager
    
    # Get sender for "auth" account using the manager directly
    manager = get_manager()
    sender = manager.get_sender("auth")
    
    # Get support email from the auth account settings
    from mailing2fast_fastapi import settings as mail_settings
    support_email = mail_settings.get_smtp_account("auth").from_email
    
    # Generate HTML content
    html_content = get_verification_email_html(
        email=email,
        project_name=settings.project_name,
        verification_url=verification_url,
        support_email=support_email,
    )
    
    # Create email message
    message = EmailMessage(
        to=[email],
        subject=f"Verifica tu cuenta - {settings.project_name}",
        html=html_content,
        smtp_account="auth",  # Use the "auth" SMTP account
    )
    
    # Send email
    result = await sender.send_email(message)
    
    if not result.is_success():
        raise Exception(f"Failed to send verification email: {result.error}")


__all__ = ["send_verification_email"]
