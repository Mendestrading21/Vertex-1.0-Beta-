"""Reusable validated types shared by every Vertex contract.

Fail-closed by construction:

- naive datetimes are rejected everywhere (``UtcDatetime``);
- ``NaN``, infinities and negative zero never enter a DTO (``FiniteDecimal``);
- absent data stays ``None`` — it is never converted to zero;
- all contract models are strict, frozen and reject unknown fields.

Numeric boundary policy (UNITS_TIME_AND_PRECISION): money, contractual prices
and quantities cross contract boundaries as ``Decimal``; ``float64`` is
reserved for numerical engine internals with documented tolerances.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import MappingProxyType
from typing import Annotated, Any, Mapping

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    StringConstraints,
)

__all__ = [
    "ContractModel",
    "CurrencyCode",
    "FiniteDecimal",
    "FrozenStrMapping",
    "Money",
    "NonEmptyStr",
    "NonNegativeDecimal",
    "PositiveDecimal",
    "PositiveInt",
    "Sha256Ref",
    "UtcDatetime",
    "ensure_finite_decimal",
    "ensure_utc",
    "freeze_str_mapping",
]


def ensure_utc(value: datetime) -> datetime:
    """Return ``value`` normalized to UTC; reject naive datetimes.

    A datetime without a UTC offset is ambiguous and therefore invalid
    (fail-closed). Aware datetimes in another timezone are converted to UTC,
    preserving the instant.
    """
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError("naive datetime rejected: a timezone-aware UTC datetime is required")
    return value.astimezone(timezone.utc)


def ensure_finite_decimal(value: Decimal) -> Decimal:
    """Reject non-finite Decimals; normalize negative zero to positive zero.

    ``NaN``, ``sNaN``, ``Infinity`` and ``-Infinity`` are rejected. ``-0`` is
    normalized to ``0`` with its exponent preserved (``-0.00`` becomes
    ``0.00``); no other rounding or rescaling happens here.
    """
    if not value.is_finite():
        raise ValueError("non-finite Decimal rejected: NaN and infinities are not valid contract values")
    if value.is_zero() and value.is_signed():
        return value.copy_negate()
    return value


def _ensure_non_negative_decimal(value: Decimal) -> Decimal:
    value = ensure_finite_decimal(value)
    if value < 0:
        raise ValueError("negative Decimal rejected: a non-negative value is required")
    return value


def _ensure_positive_decimal(value: Decimal) -> Decimal:
    value = ensure_finite_decimal(value)
    if value <= 0:
        raise ValueError("non-positive Decimal rejected: a strictly positive value is required")
    return value


def freeze_str_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return a read-only snapshot of ``value`` (mutation raises ``TypeError``)."""
    return MappingProxyType(dict(value))


UtcDatetime = Annotated[datetime, AfterValidator(ensure_utc)]
"""Timezone-aware datetime, normalized to UTC. Naive input is rejected."""

FiniteDecimal = Annotated[Decimal, AfterValidator(ensure_finite_decimal)]
"""Finite Decimal: NaN/infinity rejected, ``-0`` normalized to ``0``."""

NonNegativeDecimal = Annotated[Decimal, AfterValidator(_ensure_non_negative_decimal)]
"""Finite Decimal ``>= 0``."""

PositiveDecimal = Annotated[Decimal, AfterValidator(_ensure_positive_decimal)]
"""Finite Decimal ``> 0``."""

PositiveInt = Annotated[int, Field(gt=0)]
"""Integer strictly greater than zero."""

NonEmptyStr = Annotated[str, StringConstraints(min_length=1)]
"""String with at least one character."""

CurrencyCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]
"""ISO-4217 alphabetic currency code: exactly three uppercase ASCII letters."""

Sha256Ref = Annotated[str, StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$")]
"""Canonical hash reference of the form ``sha256:<64 lowercase hex digits>``."""

FrozenStrMapping = Annotated[
    Mapping[str, Any],
    AfterValidator(freeze_str_mapping),
    PlainSerializer(dict, return_type=dict),
]
"""String-keyed mapping frozen at validation time (read-only after construction)."""


class ContractModel(BaseModel):
    """Base class of every Vertex contract: strict, immutable, no extra fields."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class Money(ContractModel):
    """A monetary amount tied to an explicit ISO-4217 currency.

    ``amount`` is a finite ``Decimal``; the currency is never implicit and no
    implicit conversion between currencies exists at the contract layer.
    """

    amount: FiniteDecimal
    currency: CurrencyCode
