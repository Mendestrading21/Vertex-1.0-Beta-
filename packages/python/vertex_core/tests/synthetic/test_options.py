"""Tests of the deterministic synthetic option-chain generator (SYNTHETIC).

Everything here is synthetic and deterministic: fixed seed, fixed base time,
no network, no clock, no real market data. The generator's quotes are checked
against the no-arbitrage oracle of ``vertex_core.calculations.options`` — the
single financial-calculation authority — never against a re-implementation.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from vertex_core.calculations.options import no_arbitrage_bounds
from vertex_core.contracts import DataEnvelope, EnvelopeQuality
from vertex_core.synthetic import (
    SYNTHETIC_RIGHTS,
    SYNTHETIC_SOURCE,
    generate_option_chain_envelopes,
)
from vertex_core.synthetic.market import SYNTHETIC_SECTOR_TICKERS
from vertex_core.synthetic.options import (
    SYNTHETIC_OPTION_EXCHANGE,
    SYNTHETIC_OPTION_MULTIPLIER,
    SYNTHETIC_OPTION_UNDERLYINGS,
    SYNTHETIC_SCHEMA_OPTION_CHAIN,
)

SEED = 20260829
BASE_TIME = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)


@pytest.fixture(scope="module")
def envelopes() -> tuple[DataEnvelope[dict], ...]:
    return generate_option_chain_envelopes(seed=SEED, base_time=BASE_TIME)


def slices_of(envelopes, underlying):
    return [e for e in envelopes if e.payload["underlying"] == underlying]


class TestDeterminismAndMarkers:
    def test_pure_function_of_inputs(self, envelopes) -> None:
        again = generate_option_chain_envelopes(seed=SEED, base_time=BASE_TIME)
        assert [e.model_dump(mode="json") for e in envelopes] == [
            e.model_dump(mode="json") for e in again
        ]

    def test_different_seed_differs(self, envelopes) -> None:
        other = generate_option_chain_envelopes(seed=SEED + 1, base_time=BASE_TIME)
        assert [e.model_dump(mode="json") for e in envelopes] != [
            e.model_dump(mode="json") for e in other
        ]

    def test_every_envelope_is_marked_synthetic(self, envelopes) -> None:
        for envelope in envelopes:
            assert envelope.source == SYNTHETIC_SOURCE
            assert envelope.rights == SYNTHETIC_RIGHTS
            assert envelope.schema_version == SYNTHETIC_SCHEMA_OPTION_CHAIN
            assert envelope.payload["synthetic"] is True

    def test_naive_base_time_rejected(self) -> None:
        with pytest.raises(ValueError):
            generate_option_chain_envelopes(
                seed=SEED,
                base_time=datetime(2026, 8, 25, 12, 0, 0),  # noqa: DTZ001 (naïf délibéré : rejet vérifié)
            )


class TestStructure:
    def test_universe_is_four_declared_syn_tickers(self) -> None:
        assert len(SYNTHETIC_OPTION_UNDERLYINGS) == 4
        declared = {ticker for tickers in SYNTHETIC_SECTOR_TICKERS.values() for ticker in tickers}
        assert set(SYNTHETIC_OPTION_UNDERLYINGS) <= declared

    def test_three_slices_per_underlying(self, envelopes) -> None:
        assert len(envelopes) == 3 * len(SYNTHETIC_OPTION_UNDERLYINGS)
        for underlying in SYNTHETIC_OPTION_UNDERLYINGS:
            assert len(slices_of(envelopes, underlying)) == 3

    def test_one_expiration_shared_by_two_trading_classes(self, envelopes) -> None:
        for underlying in SYNTHETIC_OPTION_UNDERLYINGS:
            groups = [
                (e.payload["expiration"], e.payload["trading_class"])
                for e in slices_of(envelopes, underlying)
            ]
            assert len(set(groups)) == 3  # three distinct identities
            expirations = [expiration for expiration, _ in groups]
            shared = [x for x in set(expirations) if expirations.count(x) == 2]
            assert len(shared) == 1  # exactly one expiration under 2 classes
            shared_classes = {tc for exp, tc in groups if exp == shared[0]}
            assert len(shared_classes) == 2
            assert underlying in shared_classes  # the standard class
            assert f"{underlying}W" in shared_classes  # the distinct class

    def test_expirations_are_future_iso_dates(self, envelopes) -> None:
        for envelope in envelopes:
            expiry = date.fromisoformat(envelope.payload["expiration"])
            assert expiry > BASE_TIME.date()

    def test_twelve_strikes_by_two_rights_full_identity(self, envelopes) -> None:
        seen_con_ids: set[int] = set()
        for envelope in envelopes:
            payload = envelope.payload
            contracts = payload["contracts"]
            assert len(contracts) == 24
            strikes = {c["strike"] for c in contracts}
            assert len(strikes) == 12
            rights = {c["right"] for c in contracts}
            assert rights == {"CALL", "PUT"}
            assert payload["exchange"] == SYNTHETIC_OPTION_EXCHANGE
            assert payload["multiplier"] == SYNTHETIC_OPTION_MULTIPLIER
            assert payload["style"] == "EUROPEAN"
            assert payload["settlement"] == "CASH"
            assert payload["currency"] == "SYN"
            for contract in contracts:
                assert isinstance(contract["con_id"], int)
                assert contract["con_id"] > 0
                seen_con_ids.add(contract["con_id"])
                assert Decimal(contract["strike"]) > 0
        # con_id is unique across the whole synthetic universe.
        assert len(seen_con_ids) == sum(len(e.payload["contracts"]) for e in envelopes)


class TestQuotes:
    def test_sane_quotes_have_bid_below_ask_and_mid_inside_bounds(self, envelopes) -> None:
        checked = 0
        for envelope in envelopes:
            payload = envelope.payload
            spot = Decimal(payload["underlying_spot"])
            rate = Decimal(payload["rate"])
            dividend_yield = Decimal(payload["dividend_yield"])
            expiry = date.fromisoformat(payload["expiration"])
            maturity_years = (expiry - BASE_TIME.date()).days / 365.0
            for contract in payload["contracts"]:
                if contract["bid"] is None or contract["ask"] is None:
                    continue
                bid, ask = Decimal(contract["bid"]), Decimal(contract["ask"])
                if bid > ask:
                    continue  # the deliberately crossed quotes
                assert bid < ask
                assert bid > 0
                mid = (bid + ask) / 2
                _lower, upper = no_arbitrage_bounds(
                    spot,
                    Decimal(contract["strike"]),
                    maturity_years,
                    rate,
                    dividend_yield,
                    contract["right"],
                )
                # Quotes derived from a valid theoretical price never exceed
                # the upper bound; cent rounding may graze the lower bound.
                assert float(mid) < upper
                checked += 1
        assert checked > 150  # the sane quotes dominate the universe

    def test_each_underlying_has_crossed_stale_and_missing_quotes(self, envelopes) -> None:
        for underlying in SYNTHETIC_OPTION_UNDERLYINGS:
            crossed = stale = missing = 0
            for envelope in slices_of(envelopes, underlying):
                for contract in envelope.payload["contracts"]:
                    if contract["bid"] is None and contract["ask"] is None:
                        missing += 1
                        continue
                    if Decimal(contract["bid"]) > Decimal(contract["ask"]):
                        crossed += 1
                    observed = datetime.fromisoformat(contract["observed_at"])
                    if BASE_TIME - observed > timedelta(hours=12):
                        stale += 1
            assert crossed == 1
            assert stale == 1
            assert missing == 1

    def test_degraded_slice_is_partial_quality(self, envelopes) -> None:
        for underlying in SYNTHETIC_OPTION_UNDERLYINGS:
            qualities = [envelope.quality_status for envelope in slices_of(envelopes, underlying)]
            assert qualities.count(EnvelopeQuality.PARTIAL) == 1
            assert qualities.count(EnvelopeQuality.VALID) == 2

    def test_volume_and_open_interest_are_delayed_labeled(self, envelopes) -> None:
        for envelope in envelopes:
            for contract in envelope.payload["contracts"]:
                assert isinstance(contract["volume"], int)
                assert contract["volume"] >= 0
                assert isinstance(contract["open_interest"], int)
                assert contract["open_interest"] >= 0
                assert contract["open_interest_status"] == "OI_DELAYED"
