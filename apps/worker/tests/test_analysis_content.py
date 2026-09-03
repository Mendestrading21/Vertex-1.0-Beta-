"""Unit tests of the pure analysis dossier builder.

The verdict assertions verify HONESTY, not success: absent certified
entitlement/session/liquidity/contradiction/constraint facts, the single
AdviceEngine must return INSUFFICIENT_DATA with every blocking gate at
UNEVALUABLE — the builder never forces a status.  Population labels inside
AdviceResult must agree with the retained REAL or SYNTHETIC inputs.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from vertex_core.synthetic import SYNTHETIC_RIGHTS, SYNTHETIC_SOURCE
from vertex_worker.analysis import (
    ANALYSIS_SCHEMA_VERSION,
    DEV_SYNTHETIC_ANALYSIS_CONFIG,
    REASON_INVALID_ADJUSTMENT_BASIS,
    REASON_INVALID_BAR,
    REASON_INVALID_CURRENCY,
    REASON_INVALID_TRADING_DAY,
    REASON_NO_HEALTHY_CONTRACT,
    REASON_NO_OPTION_CHAIN,
    REASON_SOURCE_NOT_ALLOWED,
    TOPIC_ANALYSIS_INGESTED,
    AnalysisConfig,
    BarRecord,
    build_analysis_content,
    is_daily_bars_schema,
)
from vertex_worker.handlers import DEV_SYNTHETIC_CONFIG, ObservationRecord, build_registry

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)
INSTRUMENT = "SYN-TECH-01"

CONFIG = AnalysisConfig(
    instruments=("SYN-TECH-01", "SYN-TECH-02"),
    allowed_sources=frozenset({SYNTHETIC_SOURCE}),
    usable_rights=frozenset({SYNTHETIC_RIGHTS}),
)

REAL_INSTRUMENT = "ACME"
REAL_SOURCE = "ibkr"
REAL_RIGHTS = "IBKR_MARKET_DATA_DISPLAY_ONLY"
REAL_CONFIG = AnalysisConfig(
    instruments=(REAL_INSTRUMENT,),
    allowed_sources=frozenset({REAL_SOURCE}),
    usable_rights=frozenset({REAL_RIGHTS}),
)


def bar(day: str, o: str, h: str, low: str, c: str, volume: int = 1000) -> dict:
    return {"trading_day": day, "open": o, "high": h, "low": low, "close": c, "volume": volume}


def good_bars() -> list[dict]:
    return [
        bar("2026-08-21", "100.00", "103.00", "99.00", "102.00"),
        bar("2026-08-22", "102.00", "102.50", "97.50", "98.00"),
        bar("2026-08-24", "98.00", "105.00", "98.00", "104.50"),
    ]


_UNSET = object()


def bars_record(
    *,
    ticker: str = INSTRUMENT,
    bars: list[dict] | None = None,
    event_id: str = "synthetic-dev:t:db0001",
    source: str = SYNTHETIC_SOURCE,
    rights: str = SYNTHETIC_RIGHTS,
    as_of: datetime | None = None,
    quality: str = "VALID",
    currency: object = "SYN",
    adjustment_basis: object = "synthetic-unadjusted",
) -> BarRecord:
    payload: dict = {
        "type": "daily_bars",
        "synthetic": True,
        "ticker": ticker,
        "sector": "SYN-TECH",
        "bars": bars if bars is not None else good_bars(),
    }
    if currency is not _UNSET:
        payload["currency"] = currency
    if adjustment_basis is not _UNSET:
        payload["adjustment_basis"] = adjustment_basis
    return BarRecord(
        event_id=event_id,
        source=source,
        instrument_ref=ticker,
        as_of=as_of or NOW - timedelta(hours=2),
        quality_status=quality,
        rights=rights,
        schema_version="synthetic-daily-bars/1.0",
        payload=payload,
    )


def real_bars_record() -> BarRecord:
    return BarRecord(
        event_id="ibkr:daily-bars:acme:2026-08-24",
        source=REAL_SOURCE,
        instrument_ref=REAL_INSTRUMENT,
        as_of=NOW - timedelta(hours=2),
        quality_status="VALID",
        rights=REAL_RIGHTS,
        schema_version="ibkr.daily-bars/1.0",
        payload={
            "type": "daily_bars",
            "ticker": REAL_INSTRUMENT,
            "currency": "USD",
            "adjustment_basis": "split_adjusted",
            "bars": good_bars(),
        },
    )


def news_record(
    event_id: str,
    title: str,
    *,
    ticker: str = INSTRUMENT,
    native_id: str | None = None,
) -> ObservationRecord:
    return ObservationRecord(
        event_id=event_id,
        source=SYNTHETIC_SOURCE,
        source_event_id=native_id or f"native-{event_id}",
        instrument_ref=ticker,
        published_at=NOW - timedelta(hours=3),
        received_at=NOW - timedelta(hours=3),
        as_of=NOW - timedelta(hours=3),
        quality_status="VALID",
        rights=SYNTHETIC_RIGHTS,
        schema_version="synthetic-news/1.0",
        payload={
            "type": "news",
            "synthetic": True,
            "title": title,
            "canonical_url": f"https://synthetic.invalid/{event_id}",
            "entities": [ticker],
        },
    )


def healthy_chain_content() -> dict:
    return {
        "schema_version": "vertex.option-chain/1.0",
        "underlying": INSTRUMENT,
        "spot": {"value": "100.00", "currency": "SYN"},
        "assumptions": {"rate": "0.02", "dividend_yield": "0.00"},
        "expirations": [
            {
                "expiration": "2026-09-22",
                "trading_class": INSTRUMENT,
                "maturity_years": "0.076712",
                "contracts": [
                    {
                        "con_id": 900000001,
                        "strike": "100.00",
                        "right": "CALL",
                        "expiration": "2026-09-22",
                        "trading_class": INSTRUMENT,
                        "multiplier": 100,
                        "currency": "SYN",
                        "quote": {"bid": "3.50", "ask": "3.70", "status": "OK"},
                        "iv": {"status": "OK", "value": "0.25"},
                    }
                ],
            }
        ],
    }


def build(
    records=None,
    *,
    evidence=(),
    chain=None,
    chain_version=None,
    config=CONFIG,
) -> dict:
    return build_analysis_content(
        records if records is not None else [bars_record()],
        instrument=INSTRUMENT,
        evidence_records=evidence,
        option_chain_content=chain,
        option_chain_version=chain_version,
        now=NOW,
        config=config,
    )


def test_schema_predicate_and_registry_topic() -> None:
    assert is_daily_bars_schema("synthetic-daily-bars/1.0") is True
    assert is_daily_bars_schema("synthetic-daily-quote/1.0") is False
    registry = build_registry(clock=lambda: NOW, fusion_config=DEV_SYNTHETIC_CONFIG)
    assert TOPIC_ANALYSIS_INGESTED in registry.topics


def test_bars_are_relayed_verbatim_with_last_close() -> None:
    content = build()
    assert content["schema_version"] == ANALYSIS_SCHEMA_VERSION
    assert content["population"] == "SYNTHETIC"
    bars_block = content["bars"]
    assert bars_block["status"] == "OK"
    assert bars_block["count"] == 3
    assert bars_block["last_close"] == "104.50"
    assert bars_block["first_trading_day"] == "2026-08-21"
    assert bars_block["last_trading_day"] == "2026-08-24"
    assert bars_block["bars"][0]["open"] == "100.00"
    assert bars_block["discarded"] == []
    assert bars_block["fresh"] is True
    advice = content["advice"]
    assert advice["risk_summary"] == (
        "SYNTHETIC development population retained; no authoritative "
        "market risk assessment exists for this instrument"
    )
    assert advice["explanation_facts"][:2] == [
        "3 SYNTHETIC daily bars from 2026-08-21 to 2026-08-24",
        "last SYNTHETIC close 104.50 SYN",
    ]
    assert "SYNTHETIC development population" in advice["limitations"]


def test_real_population_never_publishes_synthetic_advice_wording() -> None:
    content = build_analysis_content(
        [real_bars_record()],
        instrument=REAL_INSTRUMENT,
        evidence_records=(),
        option_chain_content=None,
        option_chain_version=None,
        now=NOW,
        config=REAL_CONFIG,
    )

    assert content["population"] == "REAL"
    advice = content["advice"]
    assert advice["risk_summary"] == (
        "REAL observation population retained; no authoritative market "
        "risk assessment exists for this instrument"
    )
    assert advice["explanation_facts"] == [
        "3 REAL daily bars from 2026-08-21 to 2026-08-24",
        "last REAL close 104.50 USD",
    ]
    assert all("synthetic" not in text.lower() for text in advice["explanation_facts"])
    assert "synthetic" not in advice["risk_summary"].lower()
    assert all("synthetic" not in text.lower() for text in advice["limitations"])


@pytest.mark.parametrize(
    ("age", "expected_fresh", "expected_reason"),
    [
        (timedelta(hours=48), True, "FRESH_AND_COHERENT"),
        (timedelta(hours=48, seconds=1), False, "STALE_SNAPSHOT"),
        (timedelta(hours=71), False, "STALE_SNAPSHOT"),
        (timedelta(seconds=-1), False, "STALE_SNAPSHOT"),
    ],
)
def test_freshness_gate_uses_the_declared_48h_window(
    age: timedelta, expected_fresh: bool, expected_reason: str
) -> None:
    content = build([bars_record(as_of=NOW - age)])
    bars_block = content["bars"]
    assert bars_block["age_seconds"] == int(age.total_seconds())
    assert bars_block["fresh"] is expected_fresh
    gates = {gate["gate_id"]: gate for gate in content["advice"]["gates"]}
    assert gates["snapshot_fresh_and_coherent"]["reason_code"] == expected_reason


@pytest.mark.parametrize(
    "bad",
    [
        bar("2026-08-23", "100.00", "99.00", "98.00", "100.00"),  # high < max(o,c)
        bar("2026-08-23", "100.00", "101.00", "100.50", "100.00"),  # low > min
        bar("2026-08-23", "100.00", "101.00", "99.00", "junk"),  # non-decimal
        bar("2026-08-23", "100.00", "101.00", "99.00", "100.00", volume=-1),
        {"trading_day": "2026-08-23"},  # missing fields
    ],
)
def test_invalid_bars_are_discarded_with_reason(bad) -> None:
    content = build([bars_record(bars=[*good_bars(), bad])])
    bars_block = content["bars"]
    assert bars_block["count"] == 3
    assert bars_block["discarded"] == [{"index": 3, "reason": REASON_INVALID_BAR}]
    # A partial series honestly degrades the snapshot quality fact.
    gates = {g["gate_id"]: g for g in content["advice"]["gates"]}
    assert gates["snapshot_fresh_and_coherent"]["reason_code"] == "PARTIAL_SNAPSHOT"


def test_advice_is_the_engines_honest_verdict_never_forced() -> None:
    content = build(evidence=[news_record("e1", "[SYNTHETIC] item one")])
    advice = content["advice"]
    # The synthetic population cannot prove entitlements, session, liquidity,
    # contradictions or constraints: INSUFFICIENT_DATA is the WANTED result.
    assert advice["status"] == "INSUFFICIENT_DATA"
    assert advice["direction"] == "UNKNOWN"
    gates = {g["gate_id"]: g for g in advice["gates"]}
    assert len(gates) == 10
    for gate_id in (
        "entitlements_sufficient",
        "session_and_event_known",
        "minimum_liquidity",
        "critical_contradictions_resolved",
        "user_constraints_versioned",
    ):
        assert gates[gate_id]["status"] == "BLOCK"
        assert gates[gate_id]["reason_code"] == "UNEVALUABLE"
    assert gates["instrument_resolved"]["status"] == "DEGRADE"
    assert gates["instrument_resolved"]["reason_code"] == "RESOLVED_WITHOUT_CONID"
    assert gates["snapshot_fresh_and_coherent"]["status"] == "PASS"
    assert gates["manual_portfolio_risk_available"]["reason_code"] == "NOT_REQUIRED"
    assert gates["probability_calibrated_if_used"]["status"] == "PASS"
    assert advice["probability_evidence"] is None
    assert "SYNTHETIC development population" in advice["limitations"]


def test_evidence_clusters_come_from_fusion_for_this_ticker_only() -> None:
    evidence = [
        news_record("e1", "[SYNTHETIC] story one about SYN-TECH-01"),
        # NATIVE duplicate of e1: same provider native id -> same cluster.
        news_record("e2", "[SYNTHETIC] rewritten story one", native_id="native-e1"),
        news_record("e3", "[SYNTHETIC] other ticker story", ticker="SYN-UTIL-04"),
    ]
    content = build(evidence=evidence)
    block = content["evidence"]
    assert block["source"] == "fusion"
    assert block["considered"] == 2  # the SYN-UTIL-04 story is out of scope
    assert block["clusters_total"] == 1
    (cluster,) = block["clusters"]
    assert cluster["member_count"] == 2
    assert set(cluster["member_event_ids"]) == {"e1", "e2"}
    assert cluster["synthetic"] is True
    assert content["advice"]["evidence_ids"] == [cluster["cluster_id"]]


def test_scenarios_absent_without_chain_snapshot() -> None:
    content = build(chain=None)
    assert content["scenarios"] == {
        "status": "ABSENT",
        "reason": REASON_NO_OPTION_CHAIN,
    }
    assert content["advice"]["scenario_ids"] == []
    gates = {g["gate_id"]: g for g in content["advice"]["gates"]}
    # No calculation ran: gate 6 stays honestly unevaluable.
    assert gates["calculations_valid"]["reason_code"] == "UNEVALUABLE"


def test_scenarios_absent_without_a_healthy_contract() -> None:
    chain = healthy_chain_content()
    chain["expirations"][0]["contracts"][0]["iv"] = {
        "status": "ABSENT",
        "reason": "crossed_quote",
    }
    content = build(chain=chain)
    assert content["scenarios"] == {
        "status": "ABSENT",
        "reason": REASON_NO_HEALTHY_CONTRACT,
    }


def test_scenarios_grid_via_the_single_authority_when_contract_is_healthy() -> None:
    content = build(chain=healthy_chain_content(), chain_version=4)
    scenarios = content["scenarios"]
    assert scenarios["status"] == "OK"
    assert scenarios["value_nature"] == "THEORETICAL"
    basis = scenarios["basis"]
    assert basis["right"] == "CALL"
    assert basis["premium"] == "3.70"
    assert basis["premium_side"] == "ASK"
    assert basis["chain_snapshot_version"] == 4
    assert len(scenarios["spot_grid"]) == 5
    assert len(scenarios["time_grid_years"]) == 3
    grid = scenarios["grid"]
    assert len(grid) == 1  # one scenario: IV unchanged
    assert len(grid[0]) == 3 and all(len(row) == 5 for row in grid[0])
    assert all(isinstance(cell, str) for row in grid[0] for cell in row)
    calc = scenarios["calculation"]
    assert calc["calculation_id"] == "options.scenario_grid"
    assert calc["input_hash"].startswith("sha256:")
    # The scenario id and the calculation status feed the advice honestly.
    assert content["advice"]["scenario_ids"] == [calc["input_hash"]]
    gates = {g["gate_id"]: g for g in content["advice"]["gates"]}
    assert gates["calculations_valid"]["reason_code"] == "ALL_CALCULATIONS_VALID"


def test_deny_by_default_sources_and_rights() -> None:
    records = [
        bars_record(event_id="bad", source="unknown-source"),
    ]
    content = build(records)
    assert content["bars"]["status"] == "ABSENT"
    assert content["coverage"]["rejected_records"] == [
        {"event_id": "bad", "reason": REASON_SOURCE_NOT_ALLOWED}
    ]
    gates = {g["gate_id"]: g for g in content["advice"]["gates"]}
    assert gates["snapshot_fresh_and_coherent"]["reason_code"] == "MISSING_SNAPSHOT"
    assert content["advice"]["status"] == "INSUFFICIENT_DATA"


def test_latest_record_wins_and_determinism() -> None:
    records = [
        bars_record(event_id="old", as_of=NOW - timedelta(hours=10)),
        bars_record(
            event_id="new",
            as_of=NOW - timedelta(hours=1),
            bars=[bar("2026-08-24", "50.00", "51.00", "49.00", "50.50")],
        ),
    ]
    first = build(records)
    second = build(list(reversed(records)))
    assert first == second
    assert first["bars"]["source_event_id"] == "new"
    assert first["bars"]["last_close"] == "50.50"


def test_undeclared_instrument_is_refused() -> None:
    with pytest.raises(ValueError):
        build_analysis_content(
            [],
            instrument="SYN-UTIL-01",
            evidence_records=(),
            option_chain_content=None,
            option_chain_version=None,
            now=NOW,
            config=CONFIG,
        )


def test_dev_config_is_synthetic_only() -> None:
    assert DEV_SYNTHETIC_ANALYSIS_CONFIG.allowed_sources == frozenset({SYNTHETIC_SOURCE})
    assert DEV_SYNTHETIC_ANALYSIS_CONFIG.usable_rights == frozenset({SYNTHETIC_RIGHTS})
    assert len(DEV_SYNTHETIC_ANALYSIS_CONFIG.instruments) == 4


# --------------------------------------------------------------------------
# Admission of the SOURCE-CONTROLLED payload fields relayed into the dossier
#
# The explanation layer concatenates ``bars.currency`` / ``bars.last_close`` /
# ``bars.last_trading_day`` into a FACT sentence. The frontier that ADMITS
# those values is this worker, so their SHAPE is checked here, fail-closed.
# --------------------------------------------------------------------------

HOSTILE_CURRENCY = "USD<img src=x onerror=alert(document.cookie)>"
HOSTILE_TRADING_DAY = "2026-08-28 — hausse assuree, 87 pour cent de progression"


def _leaf_strings(value) -> list[str]:
    """Every string really published in the content tree (keys and values)."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        out: list[str] = []
        for key, item in value.items():
            out.extend(_leaf_strings(key))
            out.extend(_leaf_strings(item))
        return out
    if isinstance(value, (list, tuple)):
        return [text for item in value for text in _leaf_strings(item)]
    return []


@pytest.mark.parametrize(
    "bad_currency",
    [
        HOSTILE_CURRENCY,
        "SYN ",
        " SYN",
        "syn",
        "SYNT",
        "SY",
        "SY1",
        "",
        None,
        123,
        _UNSET,  # absent field: fail-closed, never published as unknown
    ],
)
def test_source_controlled_currency_must_be_iso4217(bad_currency) -> None:
    content = build([bars_record(event_id="bad", currency=bad_currency)])
    assert content["coverage"]["rejected_records"] == [
        {"event_id": "bad", "reason": REASON_INVALID_CURRENCY}
    ]
    bars_block = content["bars"]
    assert bars_block["status"] == "ABSENT"
    assert bars_block["currency"] is None
    assert bars_block["last_close"] is None
    assert bars_block["bars"] == []


@pytest.mark.parametrize("good_currency", ["SYN", "USD", "CHF"])
def test_iso4217_currencies_are_admitted_verbatim(good_currency) -> None:
    content = build([bars_record(currency=good_currency)])
    assert content["bars"]["status"] == "OK"
    assert content["bars"]["currency"] == good_currency
    assert content["coverage"]["rejected_records"] == []


@pytest.mark.parametrize(
    "bad_basis",
    ["basis <script>alert(1)</script>", "basis with spaces", "", None, 7, "-bad", _UNSET],
)
def test_source_controlled_adjustment_basis_must_be_a_code(bad_basis) -> None:
    content = build([bars_record(event_id="bad", adjustment_basis=bad_basis)])
    assert content["coverage"]["rejected_records"] == [
        {"event_id": "bad", "reason": REASON_INVALID_ADJUSTMENT_BASIS}
    ]
    assert content["bars"]["status"] == "ABSENT"
    assert content["bars"]["adjustment_basis"] is None


@pytest.mark.parametrize(
    "bad_day",
    [
        HOSTILE_TRADING_DAY,
        "2026-08-28 ",
        "2026-8-1",
        "26-08-28",
        "2026-02-30",  # well-formed but not a real calendar day
        "2026-13-01",
        "not-a-day",
        "",
        None,
        20260828,
    ],
)
def test_source_controlled_trading_day_must_be_an_iso_date(bad_day) -> None:
    content = build(
        [bars_record(bars=[*good_bars(), bar(bad_day, "100.00", "101.00", "99.00", "100.00")])]
    )
    bars_block = content["bars"]
    # The bar is discarded WITH its typed reason; the healthy series remains.
    assert bars_block["discarded"] == [{"index": 3, "reason": REASON_INVALID_TRADING_DAY}]
    assert bars_block["count"] == 3
    assert bars_block["last_trading_day"] == "2026-08-24"
    assert all(entry["trading_day"] != bad_day for entry in bars_block["bars"])


@pytest.mark.parametrize(
    "bad_price",
    ["\n100.00\n", " 100.00 ", "1E+2", "1_0", "+100.00", "010.00", "١٠٠", "100,00"],
)
def test_prices_relayed_verbatim_must_be_plain_decimal_strings(bad_price) -> None:
    """``Decimal`` accepts all of these; a value relayed VERBATIM into a FACT
    sentence must not. Out of shape -> the bar is discarded, never repaired."""
    content = build(
        [
            bars_record(
                bars=[*good_bars(), bar("2026-08-25", bad_price, "999.00", "0.01", bad_price)]
            )
        ]
    )
    bars_block = content["bars"]
    assert bars_block["discarded"] == [{"index": 3, "reason": REASON_INVALID_BAR}]
    assert bars_block["last_close"] == "104.50"
    assert bad_price not in _leaf_strings(content)


@pytest.mark.parametrize(
    ("record_kwargs", "expected_payload"),
    [
        ({"currency": HOSTILE_CURRENCY}, HOSTILE_CURRENCY),
        (
            {
                "bars": [
                    {
                        "trading_day": HOSTILE_TRADING_DAY,
                        "open": "10",
                        "high": "11",
                        "low": "9",
                        "close": "10.5",
                        "volume": 100,
                    }
                ]
            },
            HOSTILE_TRADING_DAY,
        ),
    ],
)
def test_hostile_source_payloads_never_reach_the_published_content(
    record_kwargs, expected_payload
) -> None:
    content = build([bars_record(**record_kwargs)])
    published = _leaf_strings(content)
    assert expected_payload not in published
    # Not merely absent as a whole: no fragment of it is relayed either.
    assert not any("onerror" in text or "hausse assuree" in text for text in published)


def test_out_of_shape_exclusion_is_motivated_and_keeps_the_rest_of_the_dossier() -> None:
    """Fail-closed never means silent: the exclusion carries its reason, and
    evidence, scenarios and the engine verdict are still produced."""
    content = build(
        [bars_record(event_id="hostile", currency=HOSTILE_CURRENCY)],
        evidence=[news_record("e1", "[SYNTHETIC] item one")],
        chain=healthy_chain_content(),
        chain_version=2,
    )
    coverage = content["coverage"]
    assert coverage["observations_considered"] == 1
    assert coverage["rejected_records"] == [
        {"event_id": "hostile", "reason": REASON_INVALID_CURRENCY}
    ]
    # The rest of the dossier is intact.
    assert content["evidence"]["clusters_total"] == 1
    assert content["scenarios"]["status"] == "OK"
    assert content["advice"]["status"] == "INSUFFICIENT_DATA"
    gates = {g["gate_id"]: g for g in content["advice"]["gates"]}
    assert gates["snapshot_fresh_and_coherent"]["reason_code"] == "MISSING_SNAPSHOT"
    # Population reflects what was REALLY retained (the evidence rail only).
    assert content["population"] == "SYNTHETIC"


def test_a_bar_discarded_for_its_day_still_degrades_the_snapshot_quality() -> None:
    content = build(
        [bars_record(bars=[*good_bars(), bar(HOSTILE_TRADING_DAY, "1.00", "2.00", "0.50", "1.50")])]
    )
    assert content["bars"]["discarded"] == [{"index": 3, "reason": REASON_INVALID_TRADING_DAY}]
    gates = {g["gate_id"]: g for g in content["advice"]["gates"]}
    assert gates["snapshot_fresh_and_coherent"]["reason_code"] == "PARTIAL_SNAPSHOT"


# --------------------------------------------------------------------------
# Indicateurs techniques : une valeur tracee, jamais une interpretation
# --------------------------------------------------------------------------


def _barres_croissantes(nombre: int, depart: float = 100.0):
    """Serie OHLC coherente et deterministe.

    Les jours sont derives par arithmetique de dates : les composer a la main
    fabriquait un 29 fevrier 2026 inexistant, et `date.fromisoformat` le
    refusait — a juste titre.
    """
    premier = date(2026, 1, 2)
    barres = []
    for index in range(nombre):
        cloture = depart + index
        barres.append(
            {
                "trading_day": (premier + timedelta(days=index)).isoformat(),
                "open": f"{cloture - 0.5:.2f}",
                "high": f"{cloture + 1.0:.2f}",
                "low": f"{cloture - 1.0:.2f}",
                "close": f"{cloture:.2f}",
                "volume": 1000,
            }
        )
    return barres


class TestIndicateurs:
    """`market.realized_volatility` et `market.atr` etaient APPROUVES au
    registre et jamais appeles en production. Ces tests couvrent leur
    branchement, pas leur mathematique — celle-ci est deja testee dans
    `packages/python/vertex_core/tests/calculations/test_market.py`."""

    def test_une_serie_suffisante_produit_les_deux_indicateurs(self):
        from vertex_worker.analysis import _build_indicators

        indicateurs = _build_indicators(_barres_croissantes(60), now=NOW, source_event_id="evt-1")
        assert indicateurs["realized_volatility"]["status"] == "OK"
        assert indicateurs["atr"]["status"] == "OK"

    def test_chaque_valeur_porte_sa_tracabilite(self):
        """Une valeur financiere sans lignee n'est pas publiable."""
        from vertex_worker.analysis import _build_indicators

        indicateurs = _build_indicators(_barres_croissantes(60), now=NOW, source_event_id="evt-1")
        for nom in ("realized_volatility", "atr"):
            calcul = indicateurs[nom]["calculation"]
            assert calcul["status"] == "OK"
            assert calcul["input_hash"].startswith("sha256:")
            assert calcul["result_hash"].startswith("sha256:")
            assert calcul["engine_version"]

    def test_aucune_interpretation_n_est_publiee(self):
        """Un ATR est une amplitude, jamais un jugement. Publier « eleve »
        supposerait un seuil, et aucun seuil n'est declare."""
        from vertex_worker.analysis import _build_indicators

        indicateurs = _build_indicators(_barres_croissantes(60), now=NOW, source_event_id=None)
        interdits = {"level", "severity", "regime", "signal", "verdict", "score"}
        for bloc in indicateurs.values():
            assert not (interdits & set(bloc)), "un indicateur ne publie qu'une valeur et sa lignee"

    def test_une_fenetre_trop_courte_est_NOMMEE_jamais_approchee(self):
        """Calculer une volatilite « sur ce qu'on a » produirait un nombre
        dont personne ne connaitrait la periode."""
        from vertex_worker.analysis import (
            REASON_INSUFFICIENT_SAMPLE,
            VOLATILITY_WINDOW,
            _build_indicators,
        )

        indicateurs = _build_indicators(_barres_croissantes(5), now=NOW, source_event_id=None)
        vol = indicateurs["realized_volatility"]
        assert vol["status"] == REASON_INSUFFICIENT_SAMPLE
        assert vol["available_bars"] == 5
        assert vol["window"] == VOLATILITY_WINDOW
        assert "value" not in vol, "aucune valeur ne doit etre publiee"

    def test_une_serie_vide_ne_leve_pas(self):
        """Un instrument sans barre est un cas NORMAL, pas une panne."""
        from vertex_worker.analysis import _build_indicators

        indicateurs = _build_indicators([], now=NOW, source_event_id=None)
        assert indicateurs["realized_volatility"]["available_bars"] == 0
        assert indicateurs["atr"]["available_bars"] == 0

    def test_l_evenement_source_est_relaye_dans_la_lignee(self):
        from vertex_worker.analysis import _build_indicators

        indicateurs = _build_indicators(_barres_croissantes(60), now=NOW, source_event_id="evt-42")
        assert indicateurs["realized_volatility"]["status"] == "OK"


class TestForceRelative:
    """`market.relative_strength` : la performance contre un indice DECLARE.

    Mesure du 2026-09-01 sur donnees reelles : SMI partage 244 seances avec
    SPX quand les valeurs americaines en partagent 250 — les feries suisses.
    Cet ecart est publie, jamais efface.
    """

    def _serie(self, nombre: int, pas: float, depart: float = 100.0):
        from datetime import date, timedelta

        premier = date(2026, 1, 2)
        barres = []
        for index in range(nombre):
            cloture = depart * (1.0 + pas) ** index
            barres.append(
                {
                    "trading_day": (premier + timedelta(days=index)).isoformat(),
                    "open": f"{cloture:.4f}",
                    "high": f"{cloture * 1.01:.4f}",
                    "low": f"{cloture * 0.99:.4f}",
                    "close": f"{cloture:.4f}",
                    "volume": 1000,
                }
            )
        return barres

    def test_un_actif_qui_monte_plus_vite_a_une_force_superieure_a_1(self):
        from vertex_worker.analysis import _relative_strength_block

        bloc = _relative_strength_block(
            self._serie(80, 0.002),
            self._serie(80, 0.001),
            instrument="AAA",
            benchmark="SPX",
            now=NOW,
        )
        assert bloc["status"] == "OK"
        assert float(bloc["value"]) > 1.0

    def test_un_actif_qui_monte_moins_vite_a_une_force_inferieure_a_1(self):
        from vertex_worker.analysis import _relative_strength_block

        bloc = _relative_strength_block(
            self._serie(80, 0.0005),
            self._serie(80, 0.002),
            instrument="AAA",
            benchmark="SPX",
            now=NOW,
        )
        assert bloc["status"] == "OK"
        assert float(bloc["value"]) < 1.0

    def test_sans_indice_DECLARE_l_indicateur_est_absent(self):
        """Comparer a un indice choisi par le code repondrait a une question
        que personne n'a posee."""
        from vertex_worker.analysis import REASON_NO_BENCHMARK, _relative_strength_block

        bloc = _relative_strength_block(
            self._serie(80, 0.001), None, instrument="AAA", benchmark=None, now=NOW
        )
        assert bloc["status"] == REASON_NO_BENCHMARK
        assert "value" not in bloc

    def test_un_instrument_ne_se_compare_pas_a_lui_meme(self):
        from vertex_worker.analysis import REASON_IS_BENCHMARK, _relative_strength_block

        bloc = _relative_strength_block(
            self._serie(80, 0.001),
            self._serie(80, 0.001),
            instrument="SPX",
            benchmark="SPX",
            now=NOW,
        )
        assert bloc["status"] == REASON_IS_BENCHMARK

    def test_un_indice_NON_OBSERVE_est_nomme(self):
        from vertex_worker.analysis import (
            REASON_BENCHMARK_ABSENT,
            _relative_strength_block,
        )

        bloc = _relative_strength_block(
            self._serie(80, 0.001), [], instrument="AAA", benchmark="SPX", now=NOW
        )
        assert bloc["status"] == REASON_BENCHMARK_ABSENT
        assert bloc["benchmark"] == "SPX"

    def test_les_calendriers_sont_INTERSECTES_jamais_tronques(self):
        """Deux places n'ont pas les memes feries. Tronquer comparerait des
        jours differents ; intersecter compare les memes."""
        from vertex_worker.analysis import _relative_strength_block

        actif = self._serie(80, 0.002)
        indice = self._serie(80, 0.001)
        # L'indice perd dix seances au milieu : un jour ferie de sa place.
        del indice[30:40]

        bloc = _relative_strength_block(actif, indice, instrument="AAA", benchmark="SPX", now=NOW)
        assert bloc["status"] == "OK"
        assert bloc["common_sessions"] == 70, "seules les seances PARTAGEES comptent"

    def test_trop_peu_de_seances_communes_est_NOMME_avec_le_compte(self):
        """Le chiffre dit sur quoi la comparaison aurait repose."""
        from vertex_worker.analysis import (
            REASON_INSUFFICIENT_SAMPLE,
            _relative_strength_block,
        )

        bloc = _relative_strength_block(
            self._serie(80, 0.002),
            self._serie(10, 0.001),
            instrument="AAA",
            benchmark="SPX",
            now=NOW,
        )
        assert bloc["status"] == REASON_INSUFFICIENT_SAMPLE
        assert bloc["common_sessions"] == 10
        assert "value" not in bloc

    def test_la_valeur_porte_sa_tracabilite(self):
        from vertex_worker.analysis import _relative_strength_block

        bloc = _relative_strength_block(
            self._serie(80, 0.002),
            self._serie(80, 0.001),
            instrument="AAA",
            benchmark="SPX",
            now=NOW,
        )
        calcul = bloc["calculation"]
        assert calcul["calculation_id"] == "market.relative_strength"
        assert calcul["input_hash"].startswith("sha256:")


class TestOverlaysEtOscillateurs:
    """Lot S6 : ``market.sma``, ``market.ema``, ``market.bollinger_bands``,
    ``market.rsi`` et ``market.macd`` publies dans ``indicators`` sous
    ``overlays`` et ``oscillators``. Ces tests couvrent le BRANCHEMENT ; la
    mathematique est testee dans ``packages/python/vertex_core/tests``.

    Le serveur publie des chaines rendues, des fenetres declarees et les
    noms des bandes et des lignes : la page Graphiques lit, ne calcule pas.
    """

    @staticmethod
    def _indicateurs(barres):
        from vertex_worker.analysis import _build_indicators

        return _build_indicators(barres, now=NOW, source_event_id="evt-1")

    @staticmethod
    def _cinq_blocs(indicateurs):
        return (
            indicateurs["overlays"]["sma"],
            indicateurs["overlays"]["ema"],
            indicateurs["overlays"]["bollinger_bands"],
            indicateurs["oscillators"]["rsi"],
            indicateurs["oscillators"]["macd"],
        )

    def test_une_serie_suffisante_publie_les_cinq_blocs(self):
        indicateurs = self._indicateurs(_barres_croissantes(60))
        assert set(indicateurs["overlays"]) == {"sma", "ema", "bollinger_bands"}
        assert set(indicateurs["oscillators"]) == {"rsi", "macd"}
        for bloc in self._cinq_blocs(indicateurs):
            assert bloc["status"] == "OK"

    def test_les_fenetres_les_methodes_et_les_noms_sont_declares(self):
        """Une courbe sans fenetre declaree est un nombre dont personne ne
        connait la periode ; une bande sans nom est une ligne anonyme."""
        from vertex_worker.analysis import (
            BOLLINGER_BANDS,
            BOLLINGER_WINDOW,
            EMA_WINDOW,
            MACD_FAST,
            MACD_LINES,
            MACD_SIGNAL,
            MACD_SLOW,
            RSI_WINDOW,
            SMA_WINDOW,
        )

        indicateurs = self._indicateurs(_barres_croissantes(60))
        sma, ema, bandes, rsi, macd = self._cinq_blocs(indicateurs)
        assert sma["window"] == SMA_WINDOW
        assert ema["window"] == EMA_WINDOW
        assert bandes["window"] == BOLLINGER_WINDOW
        assert bandes["num_std"] == "2"
        assert bandes["bands"] == list(BOLLINGER_BANDS) == ["lower", "middle", "upper"]
        assert rsi["window"] == RSI_WINDOW
        assert macd["windows"] == {"fast": MACD_FAST, "slow": MACD_SLOW, "signal": MACD_SIGNAL}
        assert macd["lines"] == list(MACD_LINES) == ["macd", "signal", "histogram"]
        for bloc in (sma, ema, bandes, rsi, macd):
            assert isinstance(bloc["method"], str) and bloc["method"]
            assert isinstance(bloc["unit"], str) and bloc["unit"]

    def test_les_valeurs_sont_des_chaines_rendues_jamais_des_flottants(self):
        """`.claude/rules/frontend.md` : aucun calcul financier dans le
        navigateur, donc aucun flottant a formater cote client."""
        from decimal import Decimal

        indicateurs = self._indicateurs(_barres_croissantes(60))

        def _sans_flottant(valeur):
            if isinstance(valeur, dict):
                for element in valeur.values():
                    _sans_flottant(element)
            elif isinstance(valeur, list):
                for element in valeur:
                    _sans_flottant(element)
            else:
                assert not isinstance(valeur, float), "un flottant brut n'est pas une valeur rendue"

        _sans_flottant(indicateurs["overlays"])
        _sans_flottant(indicateurs["oscillators"])
        sma, ema, bandes, rsi, macd = self._cinq_blocs(indicateurs)
        for bloc in (sma, ema, rsi):
            for point in bloc["points"]:
                assert Decimal(point["value"]).is_finite()
            assert Decimal(bloc["last"]["value"]).is_finite()
        for point in bandes["points"]:
            assert Decimal(point["lower"]) <= Decimal(point["middle"]) <= Decimal(point["upper"])
        for ligne in ("macd", "signal", "histogram"):
            for point in macd["series"][ligne]:
                assert Decimal(point["value"]).is_finite()
            assert Decimal(macd["last"][ligne]).is_finite()

    def test_les_series_sont_alignees_sur_les_jours_de_bourse(self):
        """Chaque point porte SON jour ; aucun remplissage en tete : la
        premiere valeur tombe sur la premiere fenetre complete."""
        from vertex_worker.analysis import (
            MACD_SIGNAL,
            MACD_SLOW,
            RSI_WINDOW,
            SMA_WINDOW,
        )

        barres = _barres_croissantes(60)
        indicateurs = self._indicateurs(barres)
        dernier = barres[-1]["trading_day"]
        sma, _ema, bandes, rsi, macd = self._cinq_blocs(indicateurs)

        assert len(sma["points"]) == 60 - SMA_WINDOW + 1
        assert sma["points"][0]["trading_day"] == barres[SMA_WINDOW - 1]["trading_day"]
        assert sma["points"][-1]["trading_day"] == dernier
        assert sma["last"] == sma["points"][-1]

        assert len(rsi["points"]) == 60 - RSI_WINDOW
        assert rsi["points"][-1]["trading_day"] == dernier

        assert bandes["last"]["trading_day"] == dernier
        assert len(macd["series"]["macd"]) == 60 - MACD_SLOW + 1
        assert len(macd["series"]["signal"]) == 60 - MACD_SLOW - MACD_SIGNAL + 2
        assert len(macd["series"]["histogram"]) == len(macd["series"]["signal"])
        assert macd["last"]["trading_day"] == dernier

    def test_chaque_bloc_porte_sa_tracabilite(self):
        """Une valeur financiere sans lignee n'est pas publiable."""
        indicateurs = self._indicateurs(_barres_croissantes(60))
        attendus = {
            ("overlays", "sma"): "market.sma",
            ("overlays", "ema"): "market.ema",
            ("overlays", "bollinger_bands"): "market.bollinger_bands",
            ("oscillators", "rsi"): "market.rsi",
            ("oscillators", "macd"): "market.macd",
        }
        for (famille, nom), identifiant in attendus.items():
            calcul = indicateurs[famille][nom]["calculation"]
            assert calcul["calculation_id"] == identifiant
            assert calcul["status"] == "OK"
            assert calcul["input_hash"].startswith("sha256:")
            assert calcul["result_hash"].startswith("sha256:")
            assert calcul["engine_version"]

    def test_une_fenetre_trop_courte_est_NOMMEE_jamais_approchee(self):
        """Cinq barres : aucune des cinq fenetres n'est complete. Le statut
        dit combien de barres existent ; aucune valeur n'est publiee."""
        from vertex_worker.analysis import REASON_INSUFFICIENT_SAMPLE

        indicateurs = self._indicateurs(_barres_croissantes(5))
        for bloc in self._cinq_blocs(indicateurs):
            assert bloc["status"] == REASON_INSUFFICIENT_SAMPLE
            assert bloc["available_bars"] == 5
            assert bloc["detail"]
            assert not {"points", "series", "last", "value", "calculation"} & set(bloc)

    def test_une_serie_vide_ne_leve_pas(self):
        """Un instrument sans barre est un cas NORMAL, pas une panne."""
        from vertex_worker.analysis import REASON_INSUFFICIENT_SAMPLE

        indicateurs = self._indicateurs([])
        for bloc in self._cinq_blocs(indicateurs):
            assert bloc["status"] == REASON_INSUFFICIENT_SAMPLE
            assert bloc["available_bars"] == 0

    def test_une_serie_plate_REFUSE_le_rsi_avec_sa_raison_sans_entrainer_les_autres(self):
        """AG = AL = 0 : le rapport n'existe pas, et le moteur refuse au lieu
        de publier 50. Le refus est relaye avec sa raison ; la SMA d'une
        serie plate, elle, existe."""
        from decimal import Decimal

        plates = [
            dict(barre, open="100.00", high="101.00", low="99.00", close="100.00")
            for barre in _barres_croissantes(60)
        ]
        indicateurs = self._indicateurs(plates)
        rsi = indicateurs["oscillators"]["rsi"]
        assert rsi["status"] == "REFUSED"
        assert rsi["reason"] == "flat_series"
        assert rsi["detail"]
        assert "points" not in rsi and "last" not in rsi
        assert indicateurs["overlays"]["sma"]["status"] == "OK"
        assert Decimal(indicateurs["overlays"]["sma"]["last"]["value"]) == Decimal("100")

    def test_aucune_interpretation_n_est_publiee(self):
        """Un RSI est un indice, jamais un jugement : « surachete »
        supposerait un seuil, et aucun seuil n'est declare."""
        indicateurs = self._indicateurs(_barres_croissantes(60))
        interdits = {"level", "severity", "regime", "signal", "verdict", "score", "overbought"}
        for bloc in self._cinq_blocs(indicateurs):
            assert not (interdits & set(bloc)), "un bloc ne publie qu'une serie et sa lignee"

    def test_un_refus_du_moteur_n_abat_pas_le_reste_du_dossier(self):
        """Regression du lot S6 : une cloture FINIE et strictement positive
        mais enorme met le carre de son ecart a la moyenne de la fenetre hors
        de portee de float64. Le moteur doit refuser AVEC SA RAISON typee,
        que ``_bloc_serie`` relaie en bloc ``REFUSED`` ; un ``OverflowError``
        nu n'est pas attrape et emportait le dossier ENTIER — les six autres
        blocs, dont les indicateurs deja approuves, avec lui.

        Le pic est place hors des fenetres glissantes de fin (volatilite 20,
        ATR 14) mais dans une fenetre de Bollinger : le refus doit rester
        borne au SEUL bloc qui ne peut pas etre calcule.
        """
        enorme = "1e200"
        barres = _barres_croissantes(60)
        barres[25] = dict(barres[25], open=enorme, high=enorme, low=enorme, close=enorme)

        indicateurs = self._indicateurs(barres)

        bandes = indicateurs["overlays"]["bollinger_bands"]
        assert bandes["status"] == "REFUSED"
        assert bandes["reason"] == "non_finite_result"
        assert bandes["detail"]
        assert not {"points", "last", "calculation"} & set(bandes)

        assert indicateurs["overlays"]["sma"]["status"] == "OK"
        assert indicateurs["overlays"]["ema"]["status"] == "OK"
        assert indicateurs["oscillators"]["rsi"]["status"] == "OK"
        assert indicateurs["oscillators"]["macd"]["status"] == "OK"
        assert indicateurs["realized_volatility"]["status"] == "OK"
        assert indicateurs["atr"]["status"] == "OK"

    def test_le_dossier_complet_relaie_overlays_et_oscillateurs(self):
        """Le contrat d'Analyse porte le bloc tel quel : c'est lui que la
        page Graphiques lit, par le meme client."""
        content = build([bars_record(bars=_barres_croissantes(60))])
        indicateurs = content["indicators"]
        assert indicateurs["overlays"]["ema"]["status"] == "OK"
        assert indicateurs["oscillators"]["macd"]["status"] == "OK"
        assert indicateurs["realized_volatility"]["status"] == "OK", "les blocs existants restent"
