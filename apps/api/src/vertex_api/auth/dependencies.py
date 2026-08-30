"""Session authentication dependency of the protected routes (fail-closed).

``require_session`` validates the opaque session cookie against the
``auth_sessions`` table (hash lookup, expiry, revocation, credential
revocation) and, for every mutating HTTP method, enforces the CSRF
double-submit contract: the ``X-Vertex-CSRF`` header must equal the
non-HttpOnly CSRF cookie AND hash to the value stored with the session.

Every rejection — missing cookie, unknown/expired/revoked session, CSRF
mismatch, even a missing database configuration — answers the same generic
401 with code ``AUTH_REQUIRED`` and no further detail (an authentication
error never reveals resource existence or server state).

There is no bypass mode: no environment flag, header or configuration can
make this dependency succeed without a live database session row. Tests
either override the dependency explicitly (synthetic ``TEST_OVERRIDE``
context) or create a real session in the test database.
"""

from __future__ import annotations

import hmac
from datetime import UTC, datetime
from typing import Literal

from fastapi import HTTPException, Request, status
from pydantic import BaseModel, ConfigDict

from vertex_api.auth.db import DatabaseNotConfiguredError, open_db_session
from vertex_core.contracts.types import NonEmptyStr
from vertex_persistence.repository.sessions import (
    ValidatedSession,
    validate_csrf,
    validate_session,
)

__all__ = [
    "AUTH_REQUIRED",
    "CSRF_COOKIE_NAME",
    "CSRF_HEADER_NAME",
    "SESSION_COOKIE_NAME",
    "SessionContext",
    "authenticate_request",
    "require_session",
    "unauthorized",
    "utc_now",
]

AUTH_REQUIRED = "AUTH_REQUIRED"
"""Error code of every generic 401: authentication required, no detail."""

SESSION_COOKIE_NAME = "vertex_session"
CSRF_COOKIE_NAME = "vertex_csrf"
CSRF_HEADER_NAME = "X-Vertex-CSRF"

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


class SessionContext(BaseModel):
    """An authenticated session principal.

    ``established_via`` is ``"WEBAUTHN"`` for every production session (the
    only real authenticator). ``"TEST_OVERRIDE"`` exists exclusively for
    explicit ``app.dependency_overrides`` in tests — no production code path
    constructs it.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    subject: NonEmptyStr
    established_via: Literal["WEBAUTHN", "TEST_OVERRIDE"]


def utc_now() -> datetime:
    """Aware UTC instant — the only clock read of the auth adapter."""
    return datetime.now(UTC)


def unauthorized() -> HTTPException:
    """The single, generic 401. Same shape for every rejection cause."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": AUTH_REQUIRED, "message": "authentication required"},
        headers={"WWW-Authenticate": "Session"},
    )


def _check_csrf(request: Request, validated: ValidatedSession) -> None:
    """Enforce the CSRF double-submit contract on mutating methods."""
    header_value = request.headers.get(CSRF_HEADER_NAME)
    cookie_value = request.cookies.get(CSRF_COOKIE_NAME)
    if not header_value or not cookie_value:
        raise unauthorized()
    if not hmac.compare_digest(header_value, cookie_value):
        raise unauthorized()
    if not validate_csrf(validated, header_value):
        raise unauthorized()


def authenticate_request(request: Request) -> ValidatedSession:
    """Validate the session cookie (and CSRF for mutations) or raise 401."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise unauthorized()
    try:
        with open_db_session(request.app) as db:
            validated = validate_session(db, session_token=token, now=utc_now())
    except DatabaseNotConfiguredError:
        # Fail closed with the same generic 401: a server that cannot check
        # sessions authenticates nobody and explains nothing to the client.
        raise unauthorized() from None
    if validated is None:
        raise unauthorized()
    if request.method.upper() not in _SAFE_METHODS:
        _check_csrf(request, validated)
    return validated


def require_session(request: Request) -> SessionContext:
    """FastAPI dependency of every protected route (see module docstring)."""
    validated = authenticate_request(request)
    return SessionContext(subject=validated.credential_label, established_via="WEBAUTHN")
