"""Static and environment-derived configuration of the passkey authentication.

Fixed by design (ADR-002/ADR-009: the API is loopback-only):

- WebAuthn relying party id is ``localhost``;
- the only accepted WebAuthn origins are ``http://127.0.0.1`` and
  ``http://localhost``, optionally extended with explicit development ports
  declared in ``VERTEX_AUTH_DEV_ORIGIN_PORTS`` (comma-separated integers,
  e.g. ``5173,8000``). Anything else is rejected — no wildcard, no scheme or
  host widening.
- sessions last at most 8 hours (short-session rule).

Cookie ``Secure`` flag: the default is ``True`` (fail-closed). Because the
Beta serves plain ``http`` on loopback only, browsers that refuse ``Secure``
cookies on ``http://127.0.0.1`` need the explicit development opt-out
``VERTEX_AUTH_COOKIE_INSECURE_DEV=1``. The opt-out only ever relaxes the flag
for this loopback deployment — the listener itself can never leave loopback
(see ``vertex_api.local_server``), so the cookie still never crosses a
network boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Mapping

__all__ = [
    "AUTH_DEV_ORIGIN_PORTS_ENV_VAR",
    "AUTH_COOKIE_INSECURE_DEV_ENV_VAR",
    "AuthConfig",
    "AuthConfigError",
    "load_auth_config",
]

AUTH_DEV_ORIGIN_PORTS_ENV_VAR = "VERTEX_AUTH_DEV_ORIGIN_PORTS"
AUTH_COOKIE_INSECURE_DEV_ENV_VAR = "VERTEX_AUTH_COOKIE_INSECURE_DEV"

_RP_ID = "localhost"
_RP_NAME = "Vertex One"
_BASE_ORIGINS = ("http://127.0.0.1", "http://localhost")
_SESSION_TTL = timedelta(hours=8)


class AuthConfigError(ValueError):
    """The authentication environment configuration is invalid (fail-closed)."""


@dataclass(frozen=True)
class AuthConfig:
    """Resolved authentication configuration (immutable)."""

    rp_id: str
    rp_name: str
    expected_origins: tuple[str, ...]
    cookie_secure: bool
    session_ttl: timedelta


def _parse_dev_ports(raw: str) -> tuple[int, ...]:
    ports: list[int] = []
    for piece in raw.split(","):
        piece = piece.strip()
        if not piece:
            continue
        try:
            port = int(piece)
        except ValueError as exc:
            raise AuthConfigError(
                f"{AUTH_DEV_ORIGIN_PORTS_ENV_VAR}: {piece!r} is not an integer port"
            ) from exc
        if not 1 <= port <= 65535:
            raise AuthConfigError(
                f"{AUTH_DEV_ORIGIN_PORTS_ENV_VAR}: port {port} is outside [1, 65535]"
            )
        ports.append(port)
    return tuple(ports)


def load_auth_config(environ: Mapping[str, str]) -> AuthConfig:
    """Build the strict authentication configuration from the environment.

    An invalid dev-port list raises :class:`AuthConfigError` — the server
    never falls back to a widened or guessed origin list.
    """
    origins = list(_BASE_ORIGINS)
    for port in _parse_dev_ports(environ.get(AUTH_DEV_ORIGIN_PORTS_ENV_VAR, "")):
        for base in _BASE_ORIGINS:
            origins.append(f"{base}:{port}")
    cookie_secure = environ.get(AUTH_COOKIE_INSECURE_DEV_ENV_VAR) != "1"
    return AuthConfig(
        rp_id=_RP_ID,
        rp_name=_RP_NAME,
        expected_origins=tuple(origins),
        cookie_secure=cookie_secure,
        session_ttl=_SESSION_TTL,
    )
