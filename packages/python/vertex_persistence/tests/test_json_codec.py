"""Unit tests of the fail-closed JSONB codec."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum

import pytest
from pydantic import BaseModel

from vertex_persistence.errors import JsonEncodingError
from vertex_persistence.json_codec import to_jsonb, to_jsonb_object

UTC = timezone.utc


def test_decimal_becomes_exact_string() -> None:
    assert to_jsonb(Decimal("12.3400")) == "12.3400"  # trailing zeros preserved
    assert to_jsonb(Decimal("-0.00")) == "0.00"  # negative zero normalized
    assert to_jsonb(Decimal("1E+2")) == "1E+2"  # exponent form preserved exactly


def test_non_finite_decimal_rejected() -> None:
    for bad in (Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")):
        with pytest.raises(JsonEncodingError):
            to_jsonb(bad)


def test_aware_datetime_becomes_utc_iso() -> None:
    paris = timezone(timedelta(hours=2))
    value = datetime(2026, 8, 28, 16, 30, 0, tzinfo=paris)
    assert to_jsonb(value) == "2026-08-28T14:30:00+00:00"


def test_naive_datetime_rejected() -> None:
    with pytest.raises(JsonEncodingError):
        to_jsonb(datetime(2026, 8, 28, 12, 0, 0))


def test_date_becomes_iso() -> None:
    assert to_jsonb(date(2026, 8, 28)) == "2026-08-28"


def test_non_finite_float_rejected() -> None:
    for bad in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(JsonEncodingError):
            to_jsonb(bad)


def test_negative_zero_float_normalized() -> None:
    encoded = to_jsonb(-0.0)
    assert encoded == 0.0
    assert json.dumps(encoded) == "0.0"


def test_absence_stays_none_never_zero() -> None:
    encoded = to_jsonb({"bid": None, "size": 0})
    assert encoded == {"bid": None, "size": 0}
    assert encoded["bid"] is None  # absent value is not coerced to 0


def test_enum_encodes_as_value() -> None:
    class Color(str, Enum):
        GREEN = "GREEN"

    assert to_jsonb(Color.GREEN) == "GREEN"


def test_pydantic_model_encodes_declared_fields() -> None:
    class Quote(BaseModel):
        symbol: str
        last: Decimal
        as_of: datetime

    encoded = to_jsonb(
        Quote(symbol="SYN", last=Decimal("1.50"), as_of=datetime(2026, 1, 2, tzinfo=UTC))
    )
    assert encoded == {"symbol": "SYN", "last": "1.50", "as_of": "2026-01-02T00:00:00+00:00"}


def test_nested_structures() -> None:
    encoded = to_jsonb({"legs": [{"qty": Decimal("2"), "ok": True}], "note": None})
    assert encoded == {"legs": [{"qty": "2", "ok": True}], "note": None}
    json.dumps(encoded)  # fully JSON-serializable


def test_non_string_mapping_keys_rejected() -> None:
    with pytest.raises(JsonEncodingError):
        to_jsonb({1: "x"})


@pytest.mark.parametrize("bad", [b"bytes", bytearray(b"x"), {1, 2}, frozenset({3}), object()])
def test_unsupported_types_rejected(bad: object) -> None:
    with pytest.raises(JsonEncodingError):
        to_jsonb(bad)


def test_to_jsonb_object_requires_mapping() -> None:
    assert to_jsonb_object("payload", {"a": 1}) == {"a": 1}
    with pytest.raises(JsonEncodingError):
        to_jsonb_object("payload", [1, 2, 3])
    with pytest.raises(JsonEncodingError):
        to_jsonb_object("payload", "scalar")
