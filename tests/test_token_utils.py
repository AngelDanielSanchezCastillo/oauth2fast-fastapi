"""
Unit tests for token verification helpers.

Covers the detailed verifier added in 0.6.0: it preserves the failure reason
(``expired`` / ``invalid`` / ``malformed``) instead of collapsing every
``JWTError`` to ``None``. This reason drives the RFC 6750 challenge and the
``error.type`` discriminator of the auth error envelope.
"""

from datetime import timedelta

from jose import jwt

from oauth2fast_fastapi.settings import settings
from oauth2fast_fastapi.utils.token_utils import (
    create_access_token,
    verify_token,
    verify_token_detailed,
)


def test_valid_token_returns_payload_and_no_reason():
    """RED: a valid token yields its payload and a null reason."""
    token = create_access_token({"sub": "user@example.com"})

    payload, reason = verify_token_detailed(token)

    assert reason is None
    assert payload is not None
    assert payload["sub"] == "user@example.com"


def test_expired_token_reports_expired():
    """RED: an expired token is reported as ``expired``, not just invalid."""
    token = create_access_token(
        {"sub": "user@example.com"},
        expires_delta=timedelta(seconds=-5),
    )

    payload, reason = verify_token_detailed(token)

    assert payload is None
    assert reason == "expired"


def test_malformed_token_reports_malformed():
    """RED: a non-JWT string is reported as ``malformed``."""
    payload, reason = verify_token_detailed("definitely-not-a-jwt")

    assert payload is None
    assert reason == "malformed"


def test_bad_signature_reports_invalid():
    """RED: a well-formed token with a wrong signature is ``invalid``."""
    token = jwt.encode(
        {"sub": "user@example.com"},
        "a-completely-different-secret",
        algorithm=settings.algorithm,
    )

    payload, reason = verify_token_detailed(token)

    assert payload is None
    assert reason == "invalid"


def test_verify_token_stays_backward_compatible():
    """RED: the legacy verifier still returns payload or None only."""
    valid = create_access_token({"sub": "user@example.com"})
    expired = create_access_token(
        {"sub": "user@example.com"},
        expires_delta=timedelta(seconds=-5),
    )

    assert verify_token(valid) is not None
    assert verify_token(expired) is None
