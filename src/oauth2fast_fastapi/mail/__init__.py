"""
Email module for OAuth2Fast-FastAPI.

This module uses mailing2fast-fastapi for email sending.
"""

from .service import send_verification_email

__all__ = ["send_verification_email"]
