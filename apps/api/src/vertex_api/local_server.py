"""Loopback-only local runner for the Vertex One API (fail-closed binding).

The API is strictly private in Beta (SECURITY_CONTROLS / ADR-002 / ADR-009:
loopback listening only, no LAN or public exposure). If ``VERTEX_API_HOST``
is set to anything but exactly ``127.0.0.1`` or ``localhost``, startup is
refused with a typed error — the process never silently rebinds elsewhere.
"""

import os
from collections.abc import Mapping

import uvicorn

__all__ = [
    "ALLOWED_LOOPBACK_HOSTS",
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "InvalidPortError",
    "LoopbackHostError",
    "main",
    "resolve_host",
    "resolve_port",
]

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000

ALLOWED_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost"})
"""The only accepted bind hosts. Exact string match, no normalization."""


class LoopbackHostError(ValueError):
    """``VERTEX_API_HOST`` requested a non-loopback bind; startup is refused."""


class InvalidPortError(ValueError):
    """``VERTEX_API_PORT`` is not a valid TCP port number."""


def resolve_host(configured_host: str | None) -> str:
    """Return the bind host; refuse anything that is not exactly loopback.

    ``None`` (variable unset) binds the default ``127.0.0.1``. Any set value
    — including an empty string or a value with whitespace or a port suffix —
    must match ``127.0.0.1`` or ``localhost`` exactly; nothing is trimmed,
    lowered or reinterpreted (fail-closed).
    """
    if configured_host is None:
        return DEFAULT_HOST
    if configured_host not in ALLOWED_LOOPBACK_HOSTS:
        raise LoopbackHostError(
            f"refusing to start: VERTEX_API_HOST={configured_host!r} is not a "
            "loopback host (allowed: '127.0.0.1', 'localhost'); the Vertex One "
            "API is local-only and is never exposed beyond loopback"
        )
    return configured_host


def resolve_port(configured_port: str | None) -> int:
    """Return the bind port; refuse anything that is not a valid TCP port.

    ``None`` (variable unset) uses the default. A set value must parse as an
    integer in ``[1, 65535]``; anything else raises :class:`InvalidPortError`.
    """
    if configured_port is None:
        return DEFAULT_PORT
    try:
        port = int(configured_port)
    except ValueError as exc:
        raise InvalidPortError(
            f"refusing to start: VERTEX_API_PORT={configured_port!r} is not an integer"
        ) from exc
    if not 1 <= port <= 65535:
        raise InvalidPortError(
            f"refusing to start: VERTEX_API_PORT={port} is outside [1, 65535]"
        )
    return port


def main(environ: Mapping[str, str] | None = None) -> None:
    """Validate the binding from the environment, then start uvicorn.

    Configuration is injected (``environ``) for unit testing; the process
    entry point passes the real ``os.environ``. Host validation happens
    BEFORE any server object is created, so a forbidden host never binds.
    """
    env = os.environ if environ is None else environ
    host = resolve_host(env.get("VERTEX_API_HOST"))
    port = resolve_port(env.get("VERTEX_API_PORT"))
    uvicorn.run("vertex_api.app:create_app", factory=True, host=host, port=port)
