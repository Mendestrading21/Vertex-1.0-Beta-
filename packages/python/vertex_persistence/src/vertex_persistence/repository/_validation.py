"""Shared strict validators of the repository layer (fail-closed)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from vertex_persistence.errors import ClockError, ValidationFailedError

__all__ = [
    "require_aware_utc",
    "require_now",
    "require_non_empty_str",
    "require_optional_str",
    "require_currency",
    "require_decimal",
    "require_optional_decimal",
    "require_positive_int",
]

_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


def require_aware_utc(label: str, value: datetime) -> datetime:
    """Return ``value`` normalized to UTC; reject non-datetimes and naive datetimes."""
    if not isinstance(value, datetime):
        raise ValidationFailedError(f"{label}: expected datetime, got {type(value).__name__}")
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValidationFailedError(f"{label}: naive datetime rejected, aware UTC required")
    return value.astimezone(timezone.utc)


def require_now(now: datetime) -> datetime:
    """Validate an injected clock instant (aware, normalized to UTC)."""
    if not isinstance(now, datetime):
        raise ClockError(f"now: expected datetime, got {type(now).__name__}")
    if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
        raise ClockError("now: naive datetime rejected, aware UTC required")
    return now.astimezone(timezone.utc)


def require_non_empty_str(label: str, value: str) -> str:
    if not isinstance(value, str):
        raise ValidationFailedError(f"{label}: expected str, got {type(value).__name__}")
    if not value.strip():
        raise ValidationFailedError(f"{label}: empty string rejected")
    return value


def require_optional_str(label: str, value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return require_non_empty_str(label, value)


def require_currency(label: str, value: str) -> str:
    value = require_non_empty_str(label, value)
    if not _CURRENCY_RE.match(value):
        raise ValidationFailedError(f"{label}: {value!r} is not an ISO-4217-style uppercase code")
    return value


def require_decimal(label: str, value: Decimal) -> Decimal:
    """Require an exact ``Decimal`` (floats are rejected — no silent conversion)."""
    if not isinstance(value, Decimal):
        raise ValidationFailedError(f"{label}: expected Decimal, got {type(value).__name__}")
    if not value.is_finite():
        raise ValidationFailedError(f"{label}: non-finite Decimal rejected")
    if value.is_zero() and value.is_signed():
        return value.copy_negate()
    return value


def require_optional_decimal(label: str, value: Optional[Decimal]) -> Optional[Decimal]:
    if value is None:
        return None
    return require_decimal(label, value)


def require_positive_int(label: str, value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationFailedError(f"{label}: expected int, got {type(value).__name__}")
    if value < 1:
        raise ValidationFailedError(f"{label}: must be >= 1, got {value}")
    return value
