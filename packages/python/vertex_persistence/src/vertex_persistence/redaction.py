"""Fail-closed redaction of outbox ``last_error`` diagnostics.

``outbox.last_error`` is a short technical diagnostic, never a carrier of
payload fragments, secrets, SQL statements, bound parameters or account-like
data. :func:`fail_outbox <vertex_persistence.repository.outbox.fail_outbox>`
never stores a free-form ``str(exc)``: it stores
``f"{code}:{type(exc).__name__}"`` plus the exception message passed through
:func:`redact_error`, which

- cuts any SQL-statement/bound-parameters tail (``[SQL: ...]``,
  ``[parameters: ...]``) appended by drivers and SQLAlchemy;
- replaces every quoted span (``'...'``, ``"..."``) — the shape of SQL
  values, tokens and identifiers in error messages;
- replaces every ``key=value`` value (``password=...``, ``account=...``);
- replaces every run of 5+ digits (ids, card/account-like numbers);
- truncates the result to a bounded length.

Over-redaction is acceptable; leakage is not.
"""

from __future__ import annotations

import re

from vertex_persistence.errors import ValidationFailedError

__all__ = ["REDACTED", "redact_error", "format_last_error"]

REDACTED = "[REDACTED]"

# Redacted messages are short by contract; the column-level cap in the outbox
# repository is a second, independent belt.
_MAX_MESSAGE_CHARS = 200

# Error codes are canonical machine tokens, never free text.
_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")

# Driver/SQLAlchemy tails carrying the statement and its bound parameters.
_SQL_TAIL_RE = re.compile(r"\[(?:SQL|parameters)\s*:.*$", re.IGNORECASE | re.DOTALL)
# ``(column)=(value)`` detail shape used by PostgreSQL constraint errors.
_PAREN_VALUE_RE = re.compile(r"=\s*\([^)]*\)")
_SINGLE_QUOTED_RE = re.compile(r"'[^']*'")
_DOUBLE_QUOTED_RE = re.compile(r'"[^"]*"')
# ``key=value``: the key (a technical name) survives, the value never does.
_KEY_VALUE_RE = re.compile(r"(?<![A-Za-z0-9_])([A-Za-z_][A-Za-z0-9_-]*)\s*=\s*[^\s;,]+")
_LONG_DIGITS_RE = re.compile(r"\d{5,}")


def redact_error(message: str) -> str:
    """Return ``message`` with anything payload/value-like removed, capped at 200 chars."""
    if not isinstance(message, str):
        raise ValidationFailedError(
            f"message: expected str, got {type(message).__name__}"
        )
    redacted = _SQL_TAIL_RE.sub(REDACTED, message)
    redacted = _PAREN_VALUE_RE.sub(f"=({REDACTED})", redacted)
    redacted = _SINGLE_QUOTED_RE.sub(REDACTED, redacted)
    redacted = _DOUBLE_QUOTED_RE.sub(REDACTED, redacted)
    redacted = _KEY_VALUE_RE.sub(rf"\1={REDACTED}", redacted)
    redacted = _LONG_DIGITS_RE.sub(REDACTED, redacted)
    return redacted.strip()[:_MAX_MESSAGE_CHARS]


def format_last_error(code: str, exc: BaseException) -> str:
    """Render the only ``last_error`` format allowed: ``CODE:ExcType[: redacted message]``.

    ``code`` must be a canonical uppercase token (``^[A-Z][A-Z0-9_]{0,63}$``)
    and ``exc`` a real exception instance — a free string is refused so no
    caller can smuggle an unredacted diagnostic through this boundary.
    """
    if not isinstance(code, str) or not _CODE_RE.match(code):
        raise ValidationFailedError(
            "code: expected a canonical uppercase error code "
            f"(pattern {_CODE_RE.pattern}), got {code!r}"
        )
    if not isinstance(exc, BaseException):
        raise ValidationFailedError(
            "exc: expected an exception instance, got "
            f"{type(exc).__name__}; free-form error strings are forbidden"
        )
    head = f"{code}:{type(exc).__name__}"
    message = redact_error(str(exc))
    return f"{head}: {message}" if message else head
