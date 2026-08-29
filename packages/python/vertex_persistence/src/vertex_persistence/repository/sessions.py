"""Passkey credentials and server-side session storage (LOT-09).

Security contract of this module:

- The opaque session token is generated here (256 bits from ``secrets``),
  returned to the caller EXACTLY ONCE inside :class:`IssuedSession` and never
  persisted: only its SHA-256 hash (``session_id_hash``) reaches the
  database. The same applies to the CSRF double-submit token.
- Every lookup and comparison is fail-closed: an unknown, expired or revoked
  session — or a session bound to a revoked credential — validates to
  ``None``, never to a permissive default.
- Clone detection: :func:`update_sign_count` rejects any non-increasing
  signature counter (WebAuthn §6.1.1). On regression it revokes the
  credential AND all its sessions before raising
  :class:`SignCountRegressionError`, so the compromise is contained even if
  the caller only commits and returns a generic 401.
- Like every repository function, nothing here commits: the caller owns the
  transaction boundary.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from vertex_persistence.errors import (
    CredentialRevokedError,
    DuplicateCredentialError,
    SignCountRegressionError,
    UnknownCredentialError,
    ValidationFailedError,
)
from vertex_persistence.models import AuthSession, WebauthnCredential
from vertex_persistence.repository._validation import (
    require_non_empty_str,
    require_now,
    require_optional_str,
)

__all__ = [
    "DEFAULT_SESSION_TTL",
    "MAX_SESSION_TTL",
    "CredentialRecord",
    "IssuedSession",
    "ValidatedSession",
    "hash_token",
    "register_credential",
    "count_credentials",
    "get_credential",
    "list_active_credentials",
    "update_sign_count",
    "create_session",
    "validate_session",
    "validate_csrf",
    "revoke_session",
    "purge_expired",
]

DEFAULT_SESSION_TTL = timedelta(hours=8)
"""Short session lifetime mandated by SECURITY_CONTROLS (passkey + short session)."""

MAX_SESSION_TTL = timedelta(hours=8)
"""Hard ceiling: no caller may issue a session longer than 8 hours."""

_TOKEN_BYTES = 32  # 256 bits of entropy per opaque token.


@dataclass(frozen=True)
class CredentialRecord:
    """Immutable view of one stored WebAuthn credential (no server secret)."""

    id: int
    credential_id: bytes
    public_key: bytes
    sign_count: int
    transports: Optional[str]
    label: str
    created_at: datetime
    revoked_at: Optional[datetime]


@dataclass(frozen=True)
class IssuedSession:
    """One-time carrier of the freshly issued opaque tokens.

    ``session_token`` and ``csrf_token`` exist ONLY in this object — the
    database holds their hashes. The caller must hand them to the client
    (cookies) and drop them; they can never be re-read from storage.
    """

    session_token: str
    csrf_token: str
    credential_id: int
    created_at: datetime
    expires_at: datetime


@dataclass(frozen=True)
class ValidatedSession:
    """Immutable view of a successfully validated session."""

    id: int
    credential_id: int
    credential_label: str
    csrf_token_hash: str
    created_at: datetime
    expires_at: datetime


def hash_token(token: str) -> str:
    """SHA-256 hex digest (prefixed) of an opaque token — the only stored form."""
    token = require_non_empty_str("token", token)
    return "sha256:" + hashlib.sha256(token.encode("utf-8")).hexdigest()


def _record(row: WebauthnCredential) -> CredentialRecord:
    return CredentialRecord(
        id=row.id,
        credential_id=row.credential_id,
        public_key=row.public_key,
        sign_count=row.sign_count,
        transports=row.transports,
        label=row.label,
        created_at=row.created_at,
        revoked_at=row.revoked_at,
    )


def _require_bytes(label: str, value: bytes) -> bytes:
    if not isinstance(value, (bytes, bytearray)) or isinstance(value, bool):
        raise ValidationFailedError(f"{label}: expected bytes, got {type(value).__name__}")
    if len(value) == 0:
        raise ValidationFailedError(f"{label}: empty bytes rejected")
    return bytes(value)


def _require_sign_count(label: str, value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationFailedError(f"{label}: expected int, got {type(value).__name__}")
    if value < 0:
        raise ValidationFailedError(f"{label}: must be >= 0, got {value}")
    return value


def register_credential(
    session: Session,
    *,
    credential_id: bytes,
    public_key: bytes,
    sign_count: int,
    transports: Optional[str],
    label: str,
    now: datetime,
) -> CredentialRecord:
    """Store one verified WebAuthn credential; duplicates fail closed."""
    credential_id = _require_bytes("credential_id", credential_id)
    public_key = _require_bytes("public_key", public_key)
    sign_count = _require_sign_count("sign_count", sign_count)
    transports = require_optional_str("transports", transports)
    label = require_non_empty_str("label", label)
    now = require_now(now)

    existing = session.execute(
        select(WebauthnCredential.id).where(WebauthnCredential.credential_id == credential_id)
    ).scalar_one_or_none()
    if existing is not None:
        raise DuplicateCredentialError(
            f"credential already registered (internal id {existing})"
        )

    row = WebauthnCredential(
        credential_id=credential_id,
        public_key=public_key,
        sign_count=sign_count,
        transports=transports,
        label=label,
        created_at=now,
        revoked_at=None,
    )
    session.add(row)
    session.flush()
    return _record(row)


def count_credentials(session: Session) -> int:
    """Total credentials ever registered, INCLUDING revoked ones.

    The bootstrap rule (first registration is free only while no credential
    exists) must count revoked credentials too: after a clone-detection
    revocation, an attacker must not regain the free-registration window.
    """
    return int(
        session.execute(select(func.count()).select_from(WebauthnCredential)).scalar_one()
    )


def get_credential(session: Session, *, credential_id: bytes) -> Optional[CredentialRecord]:
    """Return the credential with this authenticator id, or ``None``.

    The record is returned with its ``revoked_at`` as stored; callers must
    treat a non-``None`` ``revoked_at`` as unusable (fail-closed).
    """
    credential_id = _require_bytes("credential_id", credential_id)
    row = session.execute(
        select(WebauthnCredential).where(WebauthnCredential.credential_id == credential_id)
    ).scalar_one_or_none()
    return None if row is None else _record(row)


def list_active_credentials(session: Session) -> tuple[CredentialRecord, ...]:
    """All non-revoked credentials, oldest first (deterministic order)."""
    rows = (
        session.execute(
            select(WebauthnCredential)
            .where(WebauthnCredential.revoked_at.is_(None))
            .order_by(WebauthnCredential.id)
        )
        .scalars()
        .all()
    )
    return tuple(_record(row) for row in rows)


def _revoke_credential_and_sessions(
    session: Session, *, internal_id: int, now: datetime
) -> None:
    session.execute(
        update(WebauthnCredential)
        .where(WebauthnCredential.id == internal_id, WebauthnCredential.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    session.execute(
        update(AuthSession)
        .where(AuthSession.credential_id == internal_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )


def update_sign_count(
    session: Session,
    *,
    credential_id: bytes,
    new_sign_count: int,
    now: datetime,
) -> CredentialRecord:
    """Advance the signature counter; a regression revokes everything.

    WebAuthn §6.1.1: when either counter is non-zero, the reported value must
    be strictly greater than the stored one. A non-increasing counter means a
    cloned authenticator — the credential and ALL its sessions are revoked in
    the caller's transaction, then :class:`SignCountRegressionError` is
    raised. Authenticators without a counter always report 0 == 0, which is
    accepted unchanged.
    """
    credential_id = _require_bytes("credential_id", credential_id)
    new_sign_count = _require_sign_count("new_sign_count", new_sign_count)
    now = require_now(now)

    row = session.execute(
        select(WebauthnCredential)
        .where(WebauthnCredential.credential_id == credential_id)
        .with_for_update()
    ).scalar_one_or_none()
    if row is None:
        raise UnknownCredentialError("credential not found")
    if row.revoked_at is not None:
        raise CredentialRevokedError("credential is revoked")

    stored = row.sign_count
    if (new_sign_count != 0 or stored != 0) and new_sign_count <= stored:
        _revoke_credential_and_sessions(session, internal_id=row.id, now=now)
        session.flush()
        raise SignCountRegressionError(
            f"sign count regression ({new_sign_count} <= {stored}): possible cloned "
            "authenticator; credential and its sessions are revoked"
        )
    row.sign_count = new_sign_count
    session.flush()
    return _record(row)


def create_session(
    session: Session,
    *,
    credential_id: bytes,
    now: datetime,
    ttl: timedelta = DEFAULT_SESSION_TTL,
) -> IssuedSession:
    """Issue a new session for a live credential; tokens are returned once.

    The opaque session token and CSRF token are generated here from
    ``secrets`` and returned only in the :class:`IssuedSession`; the database
    stores their SHA-256 hashes. ``ttl`` must be positive and at most
    :data:`MAX_SESSION_TTL` (8 hours, short-session rule).
    """
    credential_id = _require_bytes("credential_id", credential_id)
    now = require_now(now)
    if not isinstance(ttl, timedelta):
        raise ValidationFailedError(f"ttl: expected timedelta, got {type(ttl).__name__}")
    if ttl <= timedelta(0) or ttl > MAX_SESSION_TTL:
        raise ValidationFailedError(f"ttl: must be within (0, {MAX_SESSION_TTL}], got {ttl}")

    row = session.execute(
        select(WebauthnCredential).where(WebauthnCredential.credential_id == credential_id)
    ).scalar_one_or_none()
    if row is None:
        raise UnknownCredentialError("credential not found")
    if row.revoked_at is not None:
        raise CredentialRevokedError("credential is revoked")

    session_token = secrets.token_urlsafe(_TOKEN_BYTES)
    csrf_token = secrets.token_urlsafe(_TOKEN_BYTES)
    expires_at = now + ttl
    session.add(
        AuthSession(
            session_id_hash=hash_token(session_token),
            credential_id=row.id,
            csrf_token_hash=hash_token(csrf_token),
            created_at=now,
            expires_at=expires_at,
            revoked_at=None,
        )
    )
    session.flush()
    return IssuedSession(
        session_token=session_token,
        csrf_token=csrf_token,
        credential_id=row.id,
        created_at=now,
        expires_at=expires_at,
    )


def validate_session(
    session: Session, *, session_token: str, now: datetime
) -> Optional[ValidatedSession]:
    """Return the live session matching this token, or ``None`` (fail-closed).

    ``None`` — never an exception — for every rejection cause: unknown token,
    expired, revoked, or bound to a revoked credential. Callers translate
    ``None`` into a generic 401 without detail.
    """
    session_token = require_non_empty_str("session_token", session_token)
    now = require_now(now)
    row = session.execute(
        select(AuthSession, WebauthnCredential)
        .join(WebauthnCredential, WebauthnCredential.id == AuthSession.credential_id)
        .where(AuthSession.session_id_hash == hash_token(session_token))
    ).one_or_none()
    if row is None:
        return None
    auth_session, credential = row
    if auth_session.revoked_at is not None:
        return None
    if auth_session.expires_at <= now:
        return None
    if credential.revoked_at is not None:
        return None
    return ValidatedSession(
        id=auth_session.id,
        credential_id=auth_session.credential_id,
        credential_label=credential.label,
        csrf_token_hash=auth_session.csrf_token_hash,
        created_at=auth_session.created_at,
        expires_at=auth_session.expires_at,
    )


def validate_csrf(validated: ValidatedSession, csrf_token: str) -> bool:
    """Constant-time check of a presented CSRF token against the stored hash."""
    if not isinstance(csrf_token, str) or not csrf_token:
        return False
    return hmac.compare_digest(hash_token(csrf_token), validated.csrf_token_hash)


def revoke_session(session: Session, *, session_token: str, now: datetime) -> bool:
    """Revoke the session matching this token; ``True`` if one was live."""
    session_token = require_non_empty_str("session_token", session_token)
    now = require_now(now)
    result = session.execute(
        update(AuthSession)
        .where(
            AuthSession.session_id_hash == hash_token(session_token),
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    session.flush()
    return result.rowcount == 1


def purge_expired(session: Session, *, now: datetime) -> int:
    """Delete expired and revoked sessions; returns the number removed.

    Housekeeping only — validation never relies on purging (an expired row
    that is still present is rejected by :func:`validate_session` anyway).
    """
    now = require_now(now)
    result = session.execute(
        delete(AuthSession).where(
            or_(AuthSession.expires_at <= now, AuthSession.revoked_at.is_not(None))
        )
    )
    session.flush()
    return int(result.rowcount or 0)
