"""Canonical hashing: stability, key-permutation invariance, fail-closed rejections."""

import re
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from vertex_core.contracts import (
    CanonicalizationError,
    GateStatus,
    Money,
    canonical_json_hash,
)

HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
UTC_DT = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)


class TestFormatAndStability:
    def test_reference_format(self):
        assert HASH_RE.match(canonical_json_hash({"a": 1}))

    def test_same_input_same_hash(self):
        obj = {"b": Decimal("1.50"), "a": [1, "x", None, True], "t": UTC_DT}
        assert canonical_json_hash(obj) == canonical_json_hash(obj)

    def test_different_values_different_hash(self):
        assert canonical_json_hash({"a": 1}) != canonical_json_hash({"a": 2})

    def test_key_permutation_invariance(self):
        assert canonical_json_hash({"a": 1, "b": 2}) == canonical_json_hash({"b": 2, "a": 1})

    def test_nested_key_permutation_invariance(self):
        left = {"outer": {"a": 1, "b": [Decimal("2"), {"x": 1, "y": 2}]}}
        right = {"outer": {"b": [Decimal("2"), {"y": 2, "x": 1}], "a": 1}}
        assert canonical_json_hash(left) == canonical_json_hash(right)

    def test_sequence_permutation_changes_hash(self):
        assert canonical_json_hash([1, 2]) != canonical_json_hash([2, 1])

    def test_tuple_and_list_hash_identically(self):
        assert canonical_json_hash((1, 2)) == canonical_json_hash([1, 2])


class TestScalarRules:
    def test_decimal_serialized_as_string(self):
        # A Decimal hashes like its exact string form, never like a float.
        assert canonical_json_hash(Decimal("1.5")) == canonical_json_hash("1.5")
        assert canonical_json_hash(Decimal("1.5")) != canonical_json_hash(1.5)

    def test_decimal_trailing_zeros_significant(self):
        assert canonical_json_hash(Decimal("1.5")) != canonical_json_hash(Decimal("1.50"))

    def test_negative_zero_decimal_normalized(self):
        assert canonical_json_hash(Decimal("-0")) == canonical_json_hash(Decimal("0"))

    def test_negative_zero_float_normalized(self):
        assert canonical_json_hash(-0.0) == canonical_json_hash(0.0)

    def test_aware_datetimes_hash_by_instant(self):
        paris = timezone(timedelta(hours=2))
        assert canonical_json_hash(UTC_DT) == canonical_json_hash(UTC_DT.astimezone(paris))

    def test_date_supported(self):
        assert HASH_RE.match(canonical_json_hash(date(2026, 3, 1)))

    def test_enum_hashes_as_value(self):
        assert canonical_json_hash(GateStatus.BLOCK) == canonical_json_hash("BLOCK")

    def test_pydantic_model_hashes_as_field_mapping(self):
        money = Money(amount=Decimal("10.00"), currency="CHF")
        assert canonical_json_hash(money) == canonical_json_hash(
            {"amount": Decimal("10.00"), "currency": "CHF"}
        )


class TestFailClosed:
    def test_naive_datetime_rejected(self):
        with pytest.raises(CanonicalizationError):
            canonical_json_hash(datetime(2026, 3, 1, 12, 0))  # noqa: DTZ001 (naïf délibéré : rejet vérifié)

    def test_nan_decimal_rejected(self):
        with pytest.raises(CanonicalizationError):
            canonical_json_hash(Decimal("NaN"))

    def test_infinite_decimal_rejected(self):
        with pytest.raises(CanonicalizationError):
            canonical_json_hash(Decimal("-Infinity"))

    def test_nan_and_infinite_float_rejected(self):
        for bad in (float("nan"), float("inf"), float("-inf")):
            with pytest.raises(CanonicalizationError):
                canonical_json_hash(bad)

    def test_set_rejected(self):
        with pytest.raises(CanonicalizationError):
            canonical_json_hash({1, 2})

    def test_bytes_rejected(self):
        with pytest.raises(CanonicalizationError):
            canonical_json_hash(b"raw")

    def test_non_string_mapping_key_rejected(self):
        with pytest.raises(CanonicalizationError):
            canonical_json_hash({1: "a"})

    def test_arbitrary_object_rejected(self):
        with pytest.raises(CanonicalizationError):
            canonical_json_hash(object())


scalar_values = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-(10**12), max_value=10**12),
    st.text(max_size=20),
    st.decimals(allow_nan=False, allow_infinity=False, places=4),
    st.floats(allow_nan=False, allow_infinity=False, width=64),
)
json_like = st.recursive(
    scalar_values,
    lambda children: st.one_of(
        st.lists(children, max_size=4),
        st.dictionaries(st.text(max_size=8), children, max_size=4),
    ),
    max_leaves=12,
)


@pytest.mark.property
class TestHashingProperties:
    @given(mapping=st.dictionaries(st.text(min_size=1, max_size=10), json_like, max_size=6))
    def test_key_insertion_permutation_never_changes_hash(self, mapping):
        reversed_insertion = dict(reversed(list(mapping.items())))
        assert canonical_json_hash(mapping) == canonical_json_hash(reversed_insertion)

    @given(value=json_like)
    def test_hash_is_deterministic(self, value):
        first = canonical_json_hash(value)
        assert HASH_RE.match(first)
        assert canonical_json_hash(value) == first
