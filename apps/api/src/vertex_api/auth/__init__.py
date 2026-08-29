"""Passkey (WebAuthn) authentication of the Vertex One API — LOT-09.

Public surface:

- :func:`require_session` / :class:`SessionContext` — the fail-closed
  dependency of every protected route (session cookie validated against the
  database, CSRF double-submit on mutations, generic 401 otherwise);
- ``auth_router`` — the ``/api/v1/auth`` ceremony routes;
- ``AUTH_REQUIRED`` — the error code carried by every generic 401.
"""

from vertex_api.auth.challenges import ChallengeStore
from vertex_api.auth.config import AuthConfig, AuthConfigError, load_auth_config
from vertex_api.auth.dependencies import (
    AUTH_REQUIRED,
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    SESSION_COOKIE_NAME,
    SessionContext,
    require_session,
)
from vertex_api.auth.routes import auth_router

__all__ = [
    "AUTH_REQUIRED",
    "AuthConfig",
    "AuthConfigError",
    "CSRF_COOKIE_NAME",
    "CSRF_HEADER_NAME",
    "ChallengeStore",
    "SESSION_COOKIE_NAME",
    "SessionContext",
    "auth_router",
    "load_auth_config",
    "require_session",
]
