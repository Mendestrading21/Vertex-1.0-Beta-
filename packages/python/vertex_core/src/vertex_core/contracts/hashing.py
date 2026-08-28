"""Canonical JSON hashing for contract payloads and calculation lineage.

``canonical_json_hash`` maps a supported Python object to a deterministic
``"sha256:<hex>"`` reference. Canonical form rules:

- JSON with sorted keys and compact separators, ASCII-escaped output;
- ``Decimal`` serialized as its exact string form (``str(d)``): exponent and
  trailing zeros are significant; negative zero is normalized to zero;
  non-finite Decimals are rejected;
- ``datetime`` must be timezone-aware and is serialized as ISO-8601 in UTC;
  naive datetimes are rejected; ``date`` is serialized as ISO-8601;
- ``float`` must be finite (NaN/infinity rejected); ``-0.0`` is normalized to
  ``0.0``; finite floats use Python's shortest round-trip repr via ``json``;
- ``Enum`` members hash as their value; pydantic models hash as the mapping of
  their declared fields; mappings require string keys; sequences keep their
  element sequence as-is;
- anything else (sets, bytes, arbitrary objects) is rejected with
  :class:`CanonicalizationError` — fail-closed, no silent ``str()`` fallback.

Same input therefore always yields the same hash, and mapping key insertion
permutations never change it.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping, Sequence

from pydantic import BaseModel

__all__ = ["CanonicalizationError", "canonical_json_hash"]


class CanonicalizationError(TypeError):
    """Raised when an object cannot be represented in canonical JSON form."""


def _canonicalize(obj: Any) -> Any:
    """Convert ``obj`` to a canonical JSON-serializable structure (fail-closed)."""
    if obj is None or isinstance(obj, (bool, str)):
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise CanonicalizationError("non-finite float cannot be canonicalized")
        return 0.0 if obj == 0.0 else obj
    if isinstance(obj, Decimal):
        if not obj.is_finite():
            raise CanonicalizationError("non-finite Decimal cannot be canonicalized")
        if obj.is_zero() and obj.is_signed():
            obj = obj.copy_negate()
        return str(obj)
    if isinstance(obj, datetime):
        if obj.tzinfo is None or obj.tzinfo.utcoffset(obj) is None:
            raise CanonicalizationError("naive datetime cannot be canonicalized: UTC-aware required")
        return obj.astimezone(timezone.utc).isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return _canonicalize(obj.value)
    if isinstance(obj, BaseModel):
        fields = type(obj).model_fields
        return {name: _canonicalize(getattr(obj, name)) for name in fields}
    if isinstance(obj, Mapping):
        out: dict[str, Any] = {}
        for key, value in obj.items():
            if not isinstance(key, str):
                raise CanonicalizationError(
                    f"mapping key of type {type(key).__name__} cannot be canonicalized: string keys required"
                )
            out[key] = _canonicalize(value)
        return out
    if isinstance(obj, (bytes, bytearray, memoryview)):
        raise CanonicalizationError("binary payloads cannot be canonicalized")
    if isinstance(obj, (set, frozenset)):
        raise CanonicalizationError("unordered sets cannot be canonicalized")
    if isinstance(obj, Sequence):
        return [_canonicalize(item) for item in obj]
    raise CanonicalizationError(f"object of type {type(obj).__name__} cannot be canonicalized")


def canonical_json_hash(obj: Any) -> str:
    """Return the ``"sha256:<hex>"`` digest of the canonical JSON form of ``obj``.

    Deterministic: identical inputs always produce identical digests, and the
    digest is independent of mapping key insertion sequence. Raises
    :class:`CanonicalizationError` for unsupported or ambiguous values.
    """
    canonical = _canonicalize(obj)
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()
