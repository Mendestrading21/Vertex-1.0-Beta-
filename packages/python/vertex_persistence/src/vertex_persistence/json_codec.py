"""Fail-closed encoding of Python payloads to JSONB-safe structures.

The encoding mirrors the canonical-JSON rules of
``vertex_core.contracts.hashing`` so that a stored payload and its
``canonical_json_hash`` always describe the same bytes:

- ``Decimal`` -> exact string form (``str``), non-finite rejected, ``-0``
  normalized to ``0`` (exponent preserved);
- ``datetime`` -> ISO-8601 string in UTC; **naive datetimes are rejected**;
- ``date`` -> ISO-8601 string;
- ``float`` -> finite only (NaN/infinity rejected), ``-0.0`` normalized;
- ``Enum`` -> its value, encoded recursively;
- pydantic models -> mapping of their declared fields;
- mappings -> ``dict`` with string keys only; sequences -> ``list``;
- ``None``/``bool``/``str``/``int`` pass through — **absence stays ``None``,
  it never becomes zero or an empty value**;
- bytes, sets and arbitrary objects are rejected with
  :class:`~vertex_persistence.errors.JsonEncodingError`.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel

from vertex_persistence.errors import JsonEncodingError

__all__ = ["to_jsonb", "to_jsonb_object"]


def to_jsonb(value: Any) -> Any:
    """Return a JSONB-safe structure for ``value``; raise :class:`JsonEncodingError` otherwise."""
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise JsonEncodingError("non-finite float rejected: NaN/Infinity cannot be stored")
        return 0.0 if value == 0.0 else value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise JsonEncodingError("non-finite Decimal rejected: NaN/Infinity cannot be stored")
        if value.is_zero() and value.is_signed():
            value = value.copy_negate()
        return str(value)
    if isinstance(value, datetime):
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise JsonEncodingError(
                "naive datetime rejected: a timezone-aware datetime is required"
            )
        return value.astimezone(UTC).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return to_jsonb(value.value)
    if isinstance(value, BaseModel):
        return {name: to_jsonb(getattr(value, name)) for name in type(value).model_fields}
    if isinstance(value, Mapping):
        encoded: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise JsonEncodingError(
                    f"mapping key of type {type(key).__name__} rejected: string keys are required"
                )
            encoded[key] = to_jsonb(item)
        return encoded
    if isinstance(value, (bytes, bytearray, memoryview)):
        raise JsonEncodingError("binary payload rejected: JSONB stores no raw bytes")
    if isinstance(value, (set, frozenset)):
        raise JsonEncodingError("unordered set rejected: order would be invented at encoding time")
    if isinstance(value, Sequence):
        return [to_jsonb(item) for item in value]
    raise JsonEncodingError(f"object of type {type(value).__name__} cannot be stored as JSONB")


def to_jsonb_object(label: str, value: Any) -> dict[str, Any]:
    """Encode ``value`` and require the result to be a JSON object (``dict``).

    Structured columns (observation payloads, outbox payloads, instruments)
    store JSON objects, never bare scalars or arrays.
    """
    encoded = to_jsonb(value)
    if not isinstance(encoded, dict):
        raise JsonEncodingError(f"{label}: a JSON object is required, got {type(encoded).__name__}")
    return encoded
