---
name: oauth2fast-fastapi
description: "Trigger: working on or with oauth2fast-fastapi. Stateless JWT auth for FastAPI: OAuth2 password grant, User/AuthModel bases, get_current_user deps, email verification. Prevails over the 2fast-handbook base skill for this package."
license: MIT
metadata:
  author: AngelDanielSanchezCastillo
  version: "1.0"
---

## Purpose

Stateless JWT auth: OAuth2 **password grant** (`POST /token`) + email
verification. No social providers, no sessions, no refresh tokens. Downstream
base for tenants2fast/permissions2fast (`AuthModel`, `User`, deps, JWT utils).

## Import quirk

- Dist `oauth2fast-fastapi` → import `oauth2fast_fastapi` (dash→underscore only).
- `engine` is NOT exported — use `get_db_engine("auth")` (README examples are stale).
- `AuthModel` is reachable from 3 paths (top-level, `models`, `models.bases`) — keep all working.

## Public API

- `router` — prefix baked from `AUTH_URL_PREFIX` (default `/auth`): include WITHOUT an extra prefix. Endpoints: `POST /auth/users/`, `GET /auth/users/` (**unprotected, lists all users — testing only**), `GET /auth/users/by-email/{email}`, `POST /auth/confirm-email`, `POST /auth/resend-verification`, `POST /auth/token`.
- Deps: `get_current_user` (JWT → email → DB), `get_current_verified_user` (403 if unverified).
- Utils: `create_access_token`, `verify_token`, `hash_password` (Argon2), `create_verification_token` / `verify_verification_token`.
- `get_auth_session` = partial of `pgsqlasync2fast_fastapi.get_db_session` bound to connection **"auth"** (hard-coded in 5+ places; configure `DB_CONNECTIONS__AUTH__*`).

## Architecture

- `AuthModel` (id + created_at/updated_at from tools2fast mixins) uses a **shared custom `metadata`** (`oauth2fast_fastapi.models.bases.metadata`). Auth tables are created with `AuthModel.metadata.create_all`; downstream models extending `AuthModel` MUST stay on this metadata.
- Access token: `{"sub": <email>, "exp"}` — **`sub` is the EMAIL, not the id** (tenants2fast middleware depends on this).
- Verification token: separate JWT with `"type": "email_verification"`, 24h expiry; access JWTs are rejected.
- Custom user: subclass `User` with `table=True` + new `__tablename__`, but `get_current_user` queries the base `User` — override the dep for a fully custom model.

## Email verification (0.4.6+)

- **Unconditional at login**: unverified users are blocked at `POST /token` regardless of settings.
- `ENFORCE_EMAIL_VERIFICATION` now only enables a grace window when True (with `VERIFICATION_GRACE_DAYS` int): strict `age > grace_days` → 403. Default False → immediate 403.

## Settings

Top-level env (NOT `AUTH_`-prefixed): `SECRET_KEY` (**required**, no default),
`ALGORITHM` (HS256), `ACCESS_TOKEN_EXPIRE_MINUTES` (60), `AUTH_URL_PREFIX` (auth),
`FRONTEND_URL`, `ENFORCE_EMAIL_VERIFICATION` (False), `VERIFICATION_GRACE_DAYS`
(10; empty → None). Reads `.env` from **process CWD**; empty values fail closed.
DB/mail vars belong to pgsqlasync2fast/mailing2fast (`DB_CONNECTIONS__AUTH__*`,
`MAIL_SMTP_ACCOUNTS__AUTH__*`).

## Non-obvious

- No refresh/revocation/logout — tokens valid until `exp`.
- Silent email failures: registration succeeds even if the verification email fails to send (message printed).
- Registration defaults `is_verified=False` → login blocked until verified.
- `GET /auth/users/` needs NO auth — never treat it as a protected listing.
- Wiring: `startup_database()` → `get_db_engine("auth")` → `AuthModel.metadata.create_all` (no Alembic).

## Conventions

- Spanish response messages; envelope `{success, error_type, message, ...}` from tools2fast `APIResponse`.
- Singular PascalCase models / plural snake_case tables / alphabetical join names.

## Golden rule (inherited)

Follow the 2fast-handbook base skill for layout/versioning/naming/README/commits/release.
Local edits are fine; NEVER bump/publish on your own — prepare the exact command and hand it to the developer.