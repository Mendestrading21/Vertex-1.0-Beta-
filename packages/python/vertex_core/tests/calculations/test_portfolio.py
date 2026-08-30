"""portfolio calculations: fx conversion, realized/unrealized P&L, concentration."""

from datetime import UTC, datetime
from decimal import Decimal, localcontext

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from vertex_core.calculations.portfolio import (
    DECIMAL_PRECISION,
    FX_ROUND_TRIP_RELATIVE_TOLERANCE,
    WEIGHT_SUM_TOLERANCE,
    ClosingTransaction,
    ConcentrationError,
    CurrencyMismatchError,
    Fee,
    FxRateError,
    LedgerError,
    LotConservationError,
    MarkError,
    PositionLot,
    concentration,
    fx_conversion,
    realized_pnl,
    unrealized_pnl,
)

OPENED_AT = datetime(2026, 1, 5, 14, 30, tzinfo=UTC)
CLOSED_AT = datetime(2026, 2, 10, 15, 0, tzinfo=UTC)
QUOTE_AS_OF = datetime(2026, 2, 2, 16, 0, tzinfo=UTC)

ONE = Decimal("1")


def make_lot(lot_id="L1", quantity="100", unit_cost="10.00", currency="USD"):
    return PositionLot(
        lot_id=lot_id,
        quantity=Decimal(quantity),
        unit_cost=Decimal(unit_cost),
        currency=currency,
        opened_at=OPENED_AT,
    )


def make_tx(transaction_id="T1", lot_id="L1", quantity="40", unit_price="12.50", currency="USD"):
    return ClosingTransaction(
        transaction_id=transaction_id,
        lot_id=lot_id,
        quantity=Decimal(quantity),
        unit_price=Decimal(unit_price),
        currency=currency,
        closed_at=CLOSED_AT,
    )


def make_fee(fee_id="F1", applies_to="T1", amount="1.00", currency="USD"):
    return Fee(fee_id=fee_id, applies_to=applies_to, amount=Decimal(amount), currency=currency)


class TestInputModels:
    def test_naive_opened_at_rejected(self):
        with pytest.raises(ValidationError, match="naive"):
            PositionLot(
                lot_id="L1",
                quantity=Decimal("1"),
                unit_cost=Decimal("1"),
                currency="USD",
                opened_at=datetime(2026, 1, 5, 14, 30),  # noqa: DTZ001 (naïf délibéré : rejet vérifié)
            )

    def test_non_positive_quantity_rejected(self):
        with pytest.raises(ValidationError):
            make_lot(quantity="0")

    def test_nan_unit_cost_rejected(self):
        with pytest.raises(ValidationError):
            make_lot(unit_cost="NaN")

    def test_lot_is_frozen(self):
        lot = make_lot()
        with pytest.raises(ValidationError):
            lot.quantity = Decimal("2")

    def test_negative_fee_amount_rejected(self):
        with pytest.raises(ValidationError):
            make_fee(amount="-1")


class TestFxConversion:
    def test_exact_multiplication(self):
        assert fx_conversion(Decimal("100.00"), Decimal("0.9250"), QUOTE_AS_OF) == Decimal("92.5")

    def test_negative_amount_allowed(self):
        assert fx_conversion(Decimal("-8"), Decimal("2"), QUOTE_AS_OF) == Decimal("-16")

    def test_negative_zero_normalized(self):
        result = fx_conversion(Decimal("-0"), Decimal("1.1"), QUOTE_AS_OF)
        assert result == 0 and not result.is_signed()

    def test_naive_quote_as_of_rejected(self):
        with pytest.raises(FxRateError, match="naive"):
            fx_conversion(Decimal("1"), Decimal("1"), datetime(2026, 2, 2, 16, 0))  # noqa: DTZ001 (naïf délibéré : rejet vérifié)

    def test_non_decimal_money_rejected(self):
        with pytest.raises(FxRateError, match="Decimal"):
            fx_conversion(100.0, Decimal("1"), QUOTE_AS_OF)

    def test_non_decimal_rate_rejected(self):
        with pytest.raises(FxRateError, match="Decimal"):
            fx_conversion(Decimal("1"), 1.1, QUOTE_AS_OF)

    def test_nan_money_rejected(self):
        with pytest.raises(FxRateError, match="finite"):
            fx_conversion(Decimal("NaN"), Decimal("1"), QUOTE_AS_OF)

    def test_infinite_rate_rejected(self):
        with pytest.raises(FxRateError):
            fx_conversion(Decimal("1"), Decimal("Infinity"), QUOTE_AS_OF)

    @pytest.mark.parametrize("rate", ["0", "-1.2"])
    def test_non_positive_rate_rejected(self, rate):
        with pytest.raises(FxRateError, match="positive"):
            fx_conversion(Decimal("1"), Decimal(rate), QUOTE_AS_OF)

    @pytest.mark.property
    @settings(max_examples=200, deadline=None)
    @given(
        money=st.decimals(
            min_value=Decimal("-1e9"),
            max_value=Decimal("1e9"),
            places=6,
            allow_nan=False,
            allow_infinity=False,
        ),
        rate=st.decimals(
            min_value=Decimal("1e-6"),
            max_value=Decimal("1e6"),
            places=8,
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    def test_round_trip_within_documented_tolerance(self, money, rate):
        converted = fx_conversion(money, rate, QUOTE_AS_OF)
        with localcontext() as ctx:
            ctx.prec = DECIMAL_PRECISION
            inverse = ONE / rate
        back = fx_conversion(converted, inverse, QUOTE_AS_OF)
        bound = FX_ROUND_TRIP_RELATIVE_TOLERANCE * max(ONE, abs(money))
        assert abs(back - money) <= bound


class TestRealizedPnl:
    @pytest.mark.golden
    def test_golden_hand_computed_single_lot(self):
        # Provenance — hand computation (documented 2026-08-28):
        #   lot L1: 100 units at unit cost 10.00 USD.
        #   closing T1: 40 units at 12.50 USD, fee F1 = 1.00 USD.
        #   proceeds = 40 * 12.50 = 500 ; cost basis = 40 * 10.00 = 400
        #   realized pnl = 500 - 400 - 1.00 = 99.00 ; remaining = 60.
        result = realized_pnl([make_lot()], [make_tx()], [make_fee()])
        assert result.currency == "USD"
        assert result.gross_proceeds == Decimal("500")
        assert result.cost_basis == Decimal("400")
        assert result.total_fees == Decimal("1.00")
        assert result.total_pnl == Decimal("99.00")
        assert len(result.lots) == 1
        entry = result.lots[0]
        assert entry.lot_id == "L1"
        assert entry.quantity_closed == Decimal("40")
        assert entry.remaining_quantity == Decimal("60")
        assert entry.pnl == Decimal("99.00")

    def test_ledger_balance_across_lots(self):
        lots = [make_lot("L1", "100", "10"), make_lot("L2", "50", "20")]
        txs = [
            make_tx("T1", "L1", "100", "11"),
            make_tx("T2", "L2", "10", "18"),
            make_tx("T3", "L2", "15", "25"),
        ]
        fees = [make_fee("F1", "T1", "0.50"), make_fee("F2", "T3", "0.25")]
        result = realized_pnl(lots, txs, fees)
        assert result.total_pnl == result.gross_proceeds - result.cost_basis - result.total_fees
        assert result.total_pnl == sum(entry.pnl for entry in result.lots)
        # L2: (10*18 - 10*20) + (15*25 - 15*20) - 0.25 = -20 + 75 - 0.25 = 54.75
        by_lot = {entry.lot_id: entry for entry in result.lots}
        assert by_lot["L2"].pnl == Decimal("54.75")
        assert by_lot["L1"].pnl == Decimal("99.50")

    def test_untouched_lot_absent_from_breakdown(self):
        result = realized_pnl([make_lot("L1"), make_lot("L2")], [make_tx("T1", "L1", "10")], [])
        assert [entry.lot_id for entry in result.lots] == ["L1"]

    def test_no_closing_transactions_is_zero_realized(self):
        # Zero closing events is a true zero of a summed event ledger,
        # distinct from absent market data.
        result = realized_pnl([make_lot()], [], [])
        assert result.total_pnl == Decimal("0")
        assert result.lots == ()

    def test_overclose_single_transaction_rejected(self):
        with pytest.raises(LotConservationError, match="exceeds"):
            realized_pnl([make_lot(quantity="100")], [make_tx(quantity="150")], [])

    def test_overclose_across_transactions_rejected(self):
        txs = [make_tx("T1", quantity="60"), make_tx("T2", quantity="60")]
        with pytest.raises(LotConservationError, match="exceeds"):
            realized_pnl([make_lot(quantity="100")], txs, [])

    def test_exact_full_close_allowed(self):
        result = realized_pnl([make_lot(quantity="100")], [make_tx(quantity="100")], [])
        assert result.lots[0].remaining_quantity == Decimal("0")

    def test_unknown_lot_reference_rejected(self):
        with pytest.raises(LedgerError, match="unknown lot"):
            realized_pnl([make_lot("L1")], [make_tx("T1", lot_id="LX")], [])

    def test_duplicate_lot_id_rejected(self):
        with pytest.raises(LedgerError, match="duplicate lot_id"):
            realized_pnl([make_lot("L1"), make_lot("L1")], [], [])

    def test_duplicate_transaction_id_rejected(self):
        with pytest.raises(LedgerError, match="duplicate transaction_id"):
            realized_pnl(
                [make_lot()], [make_tx("T1", quantity="1"), make_tx("T1", quantity="1")], []
            )

    def test_currency_mismatch_rejected(self):
        with pytest.raises(CurrencyMismatchError):
            realized_pnl([make_lot()], [make_tx(currency="EUR")], [])

    def test_mixed_lot_currencies_rejected(self):
        with pytest.raises(CurrencyMismatchError):
            realized_pnl([make_lot("L1"), make_lot("L2", currency="CHF")], [], [])

    def test_fee_referencing_unknown_transaction_rejected(self):
        with pytest.raises(LedgerError, match="unknown closing transaction"):
            realized_pnl([make_lot()], [make_tx()], [make_fee(applies_to="TX")])

    def test_empty_lot_population_rejected(self):
        with pytest.raises(LedgerError, match="empty lot population"):
            realized_pnl([], [], [])

    def test_decimal_quantities_stay_exact(self):
        lots = [make_lot(quantity="0.375", unit_cost="1234.56")]
        txs = [make_tx(quantity="0.125", unit_price="1300.01")]
        result = realized_pnl(lots, txs, [])
        # 0.125 * (1300.01 - 1234.56) = 0.125 * 65.45 = 8.181250 exactly
        assert result.total_pnl == Decimal("8.18125")


class TestUnrealizedPnl:
    @pytest.mark.golden
    def test_golden_missing_mark_excluded_never_zero(self):
        # Provenance — hand computation (documented 2026-08-28):
        #   lot A: 10 units at 100 USD, mark 105 -> 10 * (105 - 100) = +50.
        #   lot B: 5 units at 20 USD, mark ABSENT -> excluded, reported.
        #   total = 50 (lot A only). If B were silently valued at zero cost
        #   or zero mark the total would differ (-100 or +50 with B row).
        lots = [make_lot("A", "10", "100"), make_lot("B", "5", "20")]
        result = unrealized_pnl(lots, {"A": Decimal("105")})
        assert result.total_unrealized == Decimal("50")
        assert [entry.lot_id for entry in result.lots] == ["A"]
        assert result.excluded_lot_ids == ("B",)

    def test_all_marks_missing_total_is_none_not_zero(self):
        result = unrealized_pnl([make_lot("A"), make_lot("B")], {})
        assert result.total_unrealized is None
        assert result.lots == ()
        assert result.excluded_lot_ids == ("A", "B")

    def test_fees_reduce_unrealized(self):
        result = unrealized_pnl(
            [make_lot("A", "10", "100")],
            {"A": Decimal("105")},
            [make_fee("F1", applies_to="A", amount="2.50")],
        )
        assert result.total_unrealized == Decimal("47.50")

    def test_fee_on_excluded_lot_is_excluded_with_it(self):
        lots = [make_lot("A", "10", "100"), make_lot("B", "5", "20")]
        fees = [make_fee("F1", applies_to="B", amount="99")]
        result = unrealized_pnl(lots, {"A": Decimal("105")}, fees)
        assert result.total_unrealized == Decimal("50")
        assert result.excluded_lot_ids == ("B",)

    def test_unknown_mark_keys_ignored(self):
        result = unrealized_pnl([make_lot("A", "1", "1")], {"A": Decimal("2"), "ZZZ": Decimal("9")})
        assert result.total_unrealized == Decimal("1")

    def test_present_but_invalid_mark_raises(self):
        with pytest.raises(MarkError, match="finite"):
            unrealized_pnl([make_lot("A")], {"A": Decimal("NaN")})

    def test_float_mark_rejected(self):
        with pytest.raises(MarkError, match="Decimal"):
            unrealized_pnl([make_lot("A")], {"A": 105.0})

    def test_negative_mark_rejected(self):
        with pytest.raises(MarkError):
            unrealized_pnl([make_lot("A")], {"A": Decimal("-1")})

    def test_fee_referencing_unknown_lot_rejected(self):
        with pytest.raises(LedgerError, match="unknown lot"):
            unrealized_pnl([make_lot("A")], {"A": Decimal("1")}, [make_fee(applies_to="ZZ")])

    def test_empty_population_rejected(self):
        with pytest.raises(LedgerError, match="empty"):
            unrealized_pnl([], {})

    def test_mixed_currencies_rejected(self):
        with pytest.raises(CurrencyMismatchError):
            unrealized_pnl([make_lot("A"), make_lot("B", currency="EUR")], {})

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(
        entries=st.lists(
            st.tuples(
                st.decimals(
                    min_value=Decimal("0.0001"),
                    max_value=Decimal("1e4"),
                    places=4,
                    allow_nan=False,
                    allow_infinity=False,
                ),
                st.decimals(
                    min_value=Decimal("0"),
                    max_value=Decimal("1e4"),
                    places=4,
                    allow_nan=False,
                    allow_infinity=False,
                ),
                st.decimals(
                    min_value=Decimal("0"),
                    max_value=Decimal("1e4"),
                    places=4,
                    allow_nan=False,
                    allow_infinity=False,
                ),
                st.decimals(
                    min_value=Decimal("0"),
                    max_value=Decimal("100"),
                    places=2,
                    allow_nan=False,
                    allow_infinity=False,
                ),
            ),
            min_size=1,
            max_size=8,
        )
    )
    def test_aggregation_is_linear(self, entries):
        # Invariant aggregation_linear: valuing the whole population equals
        # the exact sum of valuing each lot alone (same marks, same fees).
        lots, marks, fees = [], {}, []
        for i, (quantity, unit_cost, mark, fee_amount) in enumerate(entries):
            lot_id = f"L{i}"
            lots.append(
                PositionLot(
                    lot_id=lot_id,
                    quantity=quantity,
                    unit_cost=unit_cost,
                    currency="USD",
                    opened_at=OPENED_AT,
                )
            )
            marks[lot_id] = mark
            fees.append(Fee(fee_id=f"F{i}", applies_to=lot_id, amount=fee_amount, currency="USD"))
        combined = unrealized_pnl(lots, marks, fees)
        singles = [
            unrealized_pnl([lot], marks, [fee]).total_unrealized
            for lot, fee in zip(lots, fees, strict=True)
        ]
        assert combined.total_unrealized == sum(singles)
        assert combined.total_unrealized == sum(entry.unrealized_pnl for entry in combined.lots)


class TestConcentration:
    @pytest.mark.golden
    def test_golden_weights_and_herfindahl(self):
        # Provenance — hand computation (documented 2026-08-28):
        #   values 50 / 30 / 20, total 100 -> weights 0.5 / 0.3 / 0.2
        #   herfindahl = 0.25 + 0.09 + 0.04 = 0.38
        result = concentration(
            {"tech": Decimal("50"), "health": Decimal("30"), "energy": Decimal("20")}
        )
        assert result.total_value == Decimal("100")
        assert result.weights["tech"] == Decimal("0.5")
        assert result.weights["health"] == Decimal("0.3")
        assert result.weights["energy"] == Decimal("0.2")
        assert result.herfindahl_index == Decimal("0.38")

    def test_already_normalized_weights_pass_through(self):
        result = concentration({"a": Decimal("0.6"), "b": Decimal("0.4")})
        assert result.weights["a"] == Decimal("0.6")
        assert result.weights["b"] == Decimal("0.4")

    def test_single_group_is_full_concentration(self):
        result = concentration({"only": Decimal("42")})
        assert result.weights["only"] == Decimal("1")
        assert result.herfindahl_index == Decimal("1")

    def test_zero_total_rejected(self):
        with pytest.raises(ConcentrationError, match="positive_denominator"):
            concentration({"a": Decimal("0"), "b": Decimal("0")})

    def test_negative_value_rejected(self):
        with pytest.raises(ConcentrationError, match="non-negative"):
            concentration({"a": Decimal("-1"), "b": Decimal("2")})

    def test_empty_grouping_rejected(self):
        with pytest.raises(ConcentrationError, match="empty"):
            concentration({})

    def test_non_decimal_value_rejected(self):
        with pytest.raises(ConcentrationError, match="Decimal"):
            concentration({"a": 1.0})

    def test_weights_mapping_is_frozen(self):
        result = concentration({"a": Decimal("1")})
        with pytest.raises(TypeError):
            result.weights["b"] = Decimal("1")

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(
        values=st.lists(
            st.decimals(
                min_value=Decimal("0"),
                max_value=Decimal("1e9"),
                places=4,
                allow_nan=False,
                allow_infinity=False,
            ),
            min_size=1,
            max_size=12,
        )
    )
    def test_weights_sum_to_one_within_documented_tolerance(self, values):
        grouped = {f"g{i}": value for i, value in enumerate(values)}
        if sum(values) <= 0:
            with pytest.raises(ConcentrationError):
                concentration(grouped)
            return
        result = concentration(grouped)
        total_weight = sum(result.weights.values())
        assert abs(total_weight - ONE) <= WEIGHT_SUM_TOLERANCE
        assert all(w >= 0 for w in result.weights.values())
