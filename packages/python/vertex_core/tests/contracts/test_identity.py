"""Identity contracts: strictness, immutability, UTC discipline, distinctness."""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from hypothesis import given, strategies as st
from pydantic import ValidationError

from vertex_core.contracts import (
    AssetClass,
    ExerciseStyle,
    IdentityStatus,
    InstrumentId,
    OptionContractId,
    OptionRight,
    SettlementType,
)

VALID_FROM = datetime(2026, 1, 5, 14, 30, tzinfo=timezone.utc)


def make_instrument(**overrides):
    kwargs = dict(
        instrument_id="ins-aapl-2026",
        asset_class=AssetClass.STOCK,
        canonical_symbol="AAPL",
        exchange="NASDAQ",
        currency="USD",
        valid_from=VALID_FROM,
        identity_status=IdentityStatus.RESOLVED,
    )
    kwargs.update(overrides)
    return InstrumentId(**kwargs)


def make_option(**overrides):
    kwargs = dict(
        underlying_id="ins-spx-2026",
        expiry=date(2026, 9, 18),
        strike=Decimal("5000"),
        right=OptionRight.CALL,
        exercise_style=ExerciseStyle.EUROPEAN,
        settlement_type=SettlementType.CASH,
        multiplier=100,
        currency="USD",
        exchange="CBOE",
        trading_class="SPX",
    )
    kwargs.update(overrides)
    return OptionContractId(**kwargs)


class TestInstrumentId:
    def test_valid_construction(self):
        ins = make_instrument(ibkr_con_id=265598, isin="US0378331005")
        assert ins.canonical_symbol == "AAPL"
        assert ins.valid_to is None
        assert ins.valid_from.tzinfo == timezone.utc

    def test_symbol_alone_is_never_an_identity(self):
        with pytest.raises(ValidationError):
            InstrumentId(canonical_symbol="AAPL")

    def test_naive_valid_from_rejected(self):
        with pytest.raises(ValidationError, match="naive datetime"):
            make_instrument(valid_from=datetime(2026, 1, 5, 14, 30))

    def test_aware_non_utc_normalized_to_utc(self):
        from datetime import timedelta, timezone as tz

        paris = tz(timedelta(hours=2))
        ins = make_instrument(valid_from=datetime(2026, 1, 5, 16, 30, tzinfo=paris))
        assert ins.valid_from == datetime(2026, 1, 5, 14, 30, tzinfo=timezone.utc)
        assert ins.valid_from.utcoffset().total_seconds() == 0

    def test_valid_to_before_valid_from_rejected(self):
        with pytest.raises(ValidationError, match="valid_to"):
            make_instrument(valid_to=datetime(2025, 1, 1, tzinfo=timezone.utc))

    def test_frozen(self):
        ins = make_instrument()
        with pytest.raises(ValidationError):
            ins.canonical_symbol = "MSFT"

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            make_instrument(account_id="X123")

    def test_empty_symbol_rejected(self):
        with pytest.raises(ValidationError):
            make_instrument(canonical_symbol="")

    def test_lowercase_currency_rejected(self):
        with pytest.raises(ValidationError):
            make_instrument(currency="usd")

    def test_no_account_or_transactional_field(self):
        fields = set(InstrumentId.model_fields)
        assert not any("account" in name for name in fields)


class TestOptionContractId:
    def test_valid_construction(self):
        opt = make_option()
        assert opt.strike == Decimal("5000")
        assert opt.adjustment_code is None

    def test_strike_zero_or_negative_rejected(self):
        for bad in (Decimal("0"), Decimal("-1")):
            with pytest.raises(ValidationError):
                make_option(strike=bad)

    def test_strike_nan_and_infinity_rejected(self):
        for bad in (Decimal("NaN"), Decimal("Infinity")):
            with pytest.raises(ValidationError):
                make_option(strike=bad)

    def test_multiplier_must_be_positive(self):
        with pytest.raises(ValidationError):
            make_option(multiplier=0)

    def test_trading_class_required(self):
        with pytest.raises(ValidationError):
            OptionContractId(
                underlying_id="ins-spx-2026",
                expiry=date(2026, 9, 18),
                strike=Decimal("5000"),
                right=OptionRight.CALL,
                exercise_style=ExerciseStyle.EUROPEAN,
                settlement_type=SettlementType.CASH,
                multiplier=100,
                currency="USD",
                exchange="CBOE",
            )

    def test_distinct_trading_classes_same_expiry_are_distinct_identities(self):
        spx = make_option(trading_class="SPX")
        spxw = make_option(trading_class="SPXW")
        assert spx != spxw
        assert hash(spx) != hash(spxw)

    def test_identical_contracts_are_equal_and_hash_equal(self):
        assert make_option() == make_option()
        assert hash(make_option()) == hash(make_option())

    def test_frozen(self):
        opt = make_option()
        with pytest.raises(ValidationError):
            opt.strike = Decimal("6000")

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            make_option(quantity=1)


@pytest.mark.property
class TestIdentityProperties:
    @given(
        classes=st.sets(
            st.text(
                alphabet=st.characters(min_codepoint=33, max_codepoint=126),
                min_size=1,
                max_size=12,
            ),
            min_size=2,
            max_size=2,
        )
    )
    def test_any_two_distinct_trading_classes_are_distinct_identities(self, classes):
        first, second = sorted(classes)
        a = make_option(trading_class=first)
        b = make_option(trading_class=second)
        assert a != b

    @given(
        strike=st.decimals(
            min_value=Decimal("0.01"),
            max_value=Decimal("100000"),
            allow_nan=False,
            allow_infinity=False,
            places=2,
        )
    )
    def test_positive_strikes_round_trip_exactly(self, strike):
        assert make_option(strike=strike).strike == strike
