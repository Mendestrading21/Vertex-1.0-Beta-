"""Wire DTOs of the authentication routes.

The WebAuthn ceremony payloads (``options`` out, ``credential`` in) are the
browser API's own JSON protocol: they are carried as plain JSON objects at
this boundary and validated immediately and strictly by ``py_webauthn`` —
never interpreted by hand. Everything Vertex-owned (flow ids, labels,
expiry) is strictly typed and closed (``extra='forbid'``).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "CeremonyOptionsResponse",
    "LoginVerifyRequest",
    "LoginVerifyResponse",
    "LogoutResponse",
    "RegisterVerifyRequest",
    "RegisterVerifyResponse",
]


class _AuthModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CeremonyOptionsResponse(_AuthModel):
    """A pending ceremony: opaque flow id + the WebAuthn options JSON."""

    flow_id: str = Field(min_length=1)
    options: dict[str, Any]


class RegisterVerifyRequest(_AuthModel):
    """Client answer to a registration ceremony."""

    flow_id: str = Field(min_length=1, max_length=128)
    label: str = Field(min_length=1, max_length=64)
    credential: dict[str, Any]


class RegisterVerifyResponse(_AuthModel):
    """Registration acknowledged. Carries no secret and no credential material."""

    registered: Literal[True]
    label: str


class LoginVerifyRequest(_AuthModel):
    """Client answer to an authentication ceremony."""

    flow_id: str = Field(min_length=1, max_length=128)
    credential: dict[str, Any]


class LoginVerifyResponse(_AuthModel):
    """Session established (tokens travel ONLY in cookies, never in the body)."""

    authenticated: Literal[True]
    expires_at: str


class LogoutResponse(_AuthModel):
    """Session revoked and cookies cleared."""

    logged_out: Literal[True]
