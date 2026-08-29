"""Typed errors of the persistence package.

Fail-closed policy: every invalid input, missing configuration or impossible
state transition raises one of these exceptions. There is no silent fallback,
no coercion of absence to zero and no permissive default.
"""

from __future__ import annotations

__all__ = [
    "PersistenceError",
    "ConfigurationError",
    "ClockError",
    "JsonEncodingError",
    "EnumValidationError",
    "ValidationFailedError",
    "OutboxStateError",
    "OutboxLeaseError",
    "SnapshotStateError",
    "LedgerError",
    "UnknownPortfolioError",
    "UnknownLedgerEventError",
    "AlreadyCompensatedError",
    "AuthStorageError",
    "UnknownCredentialError",
    "CredentialRevokedError",
    "DuplicateCredentialError",
    "SignCountRegressionError",
]


class PersistenceError(Exception):
    """Base class of every typed error raised by ``vertex_persistence``."""


class ConfigurationError(PersistenceError):
    """A required configuration value (e.g. database DSN env var) is missing."""


class ClockError(PersistenceError):
    """A ``now`` argument is naive or otherwise unusable as an aware UTC instant."""


class JsonEncodingError(PersistenceError):
    """A payload cannot be encoded to JSONB without loss or ambiguity."""


class EnumValidationError(PersistenceError):
    """A value does not belong to the canonical enumeration expected here."""


class ValidationFailedError(PersistenceError):
    """A scalar input (string, Decimal, currency, id) failed strict validation."""


class OutboxStateError(PersistenceError):
    """An outbox message is missing or not in the status required by the call."""


class OutboxLeaseError(OutboxStateError):
    """The caller does not hold the lease on the outbox message it targets.

    Raised when ack/fail present a ``lease_token`` that does not match the
    row: the lease expired and was reaped (its attempt already counted), the
    message was re-claimed by another worker, or it was never claimed at all.
    The caller must discard its result and never retry the call.
    """


class SnapshotStateError(PersistenceError):
    """A snapshot head is inconsistent with the versions stored for its key."""


class LedgerError(PersistenceError):
    """Base class of manual-ledger storage errors."""


class UnknownPortfolioError(LedgerError):
    """The referenced portfolio does not exist."""


class UnknownLedgerEventError(LedgerError):
    """The referenced ledger transaction does not exist."""


class AlreadyCompensatedError(LedgerError):
    """The referenced ledger transaction already has a compensating entry."""


class AuthStorageError(PersistenceError):
    """Base class of passkey credential and session storage errors.

    These errors carry only technical identifiers — never a token, hash
    preimage or any value usable to authenticate.
    """


class UnknownCredentialError(AuthStorageError):
    """The referenced WebAuthn credential does not exist."""


class CredentialRevokedError(AuthStorageError):
    """The referenced WebAuthn credential has been revoked."""


class DuplicateCredentialError(AuthStorageError):
    """A credential with the same authenticator credential id already exists."""


class SignCountRegressionError(AuthStorageError):
    """The authenticator reported a non-increasing signature counter.

    Per WebAuthn §6.1.1 this signals a cloned authenticator. The repository
    revokes the credential and all its sessions BEFORE raising, so the caller
    only has to commit the transaction and fail the login closed.
    """
