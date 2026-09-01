"""Unit tests of the pure markets overview content builder (LOT-13).

Everything here is SYNTHETIC and deterministic: records are built in memory
from explicit decimal strings; no database, no clock, no network.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from vertex_core.synthetic import SYNTHETIC_RIGHTS, SYNTHETIC_SOURCE
from vertex_core.version import ENGINE_VERSION
from vertex_worker.markets import (
    DEV_SYNTHETIC_MARKETS_CONFIG,
    MARKETS_SCHEMA_VERSION,
    REASON_MISSING_CLOSE,
    REASON_RIGHTS_NOT_USABLE,
    REASON_SOURCE_NOT_ALLOWED,
    REASON_TICKER_NOT_IN_UNIVERSE,
    MarketsConfig,
    QuoteRecord,
    build_markets_overview_content,
    is_daily_quote_schema,
)

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)

SMALL_CONFIG = MarketsConfig(
    universe={
        "SYN-AAA": ("SYN-AAA-01", "SYN-AAA-02"),
        "SYN-BBB": ("SYN-BBB-01", "SYN-BBB-02"),
    },
    sector_labels={"SYN-AAA": "Secteur AAA", "SYN-BBB": "Secteur BBB"},
    allowed_sources=frozenset({SYNTHETIC_SOURCE}),
    usable_rights=frozenset({SYNTHETIC_RIGHTS}),
    coverage_threshold=Decimal("0.5"),
)


def quote(
    ticker: str,
    sector: str,
    day: str,
    close: str,
    *,
    quality: str = "VALID",
    source: str = SYNTHETIC_SOURCE,
    rights: str = SYNTHETIC_RIGHTS,
    as_of: datetime | None = None,
    event_id: str | None = None,
    basis: str = "synthetic-unadjusted",
) -> QuoteRecord:
    return QuoteRecord(
        event_id=event_id or f"{source}:t:{ticker}:{day}",
        source=source,
        instrument_ref=ticker,
        as_of=as_of or NOW - timedelta(hours=1),
        quality_status=quality,
        rights=rights,
        schema_version="synthetic-daily-quote/1.0",
        payload={
            "type": "daily_quote",
            "synthetic": True,
            "ticker": ticker,
            "sector": sector,
            "trading_day": day,
            "close": close,
            "currency": "SYN",
            "adjustment_basis": basis,
        },
    )


def full_records() -> list[QuoteRecord]:
    return [
        quote("SYN-AAA-01", "SYN-AAA", "2026-08-23", "100.00"),
        quote("SYN-AAA-01", "SYN-AAA", "2026-08-24", "110.00"),
        quote("SYN-AAA-02", "SYN-AAA", "2026-08-23", "50.00"),
        quote("SYN-AAA-02", "SYN-AAA", "2026-08-24", "45.00"),
        quote("SYN-BBB-01", "SYN-BBB", "2026-08-23", "20.00"),
        quote("SYN-BBB-01", "SYN-BBB", "2026-08-24", "20.00"),
        quote("SYN-BBB-02", "SYN-BBB", "2026-08-23", "80.00"),
        quote("SYN-BBB-02", "SYN-BBB", "2026-08-24", "88.00"),
    ]


def test_schema_predicate() -> None:
    assert is_daily_quote_schema("synthetic-daily-quote/1.0") is True
    assert is_daily_quote_schema("synthetic-quote/1.0") is False
    assert is_daily_quote_schema("synthetic-news/1.0") is False
    assert is_daily_quote_schema("") is False


def test_full_coverage_content() -> None:
    content = build_markets_overview_content(
        full_records(), now=NOW, config=SMALL_CONFIG
    )
    assert content["schema_version"] == MARKETS_SCHEMA_VERSION
    assert content["as_of"] == NOW.isoformat()
    assert content["population"] == "SYNTHETIC"
    assert content["data_state"] == "ok"
    assert content["engine_version"] == ENGINE_VERSION

    coverage = content["coverage"]
    assert coverage["expected"] == 4
    assert coverage["received"] == 4
    assert coverage["covered"] == 4
    assert coverage["discarded"] == 0
    assert coverage["discarded_tickers"] == []
    assert coverage["rejected_records"] == []

    sectors = {s["sector"]: s for s in content["sectors"]}
    assert set(sectors) == {"SYN-AAA", "SYN-BBB"}
    assert sectors["SYN-AAA"]["label"] == "Secteur AAA"

    aaa = {t["ticker"]: t for t in sectors["SYN-AAA"]["tickers"]}
    t1 = aaa["SYN-AAA-01"]
    # last close is the EXACT decimal string, verbatim.
    assert t1["last_close"] == "110.00"
    assert t1["previous_close"] == "100.00"
    # simple_return(100, 110): honest float64 result (shortest repr), and the
    # display percentage rendered server-side.
    assert t1["return_1d"] == "0.10000000000000009"
    assert t1["return_1d_pct"] == "+10.00"
    assert t1["synthetic"] is True
    assert t1["quality"] == "VALID"
    # CalculationRecord lineage preserved.
    calc = t1["calculation"]
    assert calc["calculation_id"] == "market.simple_return"
    assert calc["engine_version"] == ENGINE_VERSION
    assert calc["input_hash"].startswith("sha256:")
    assert calc["result_hash"].startswith("sha256:")
    assert calc["status"] == "OK"

    t2 = aaa["SYN-AAA-02"]
    assert t2["return_1d_pct"] == "-10.00"

    # weights: shares of the sector by last close (110 vs 45).
    assert t1["weight_in_sector"] == "0.709677"
    assert t2["weight_in_sector"] == "0.290323"
    total = Decimal(t1["weight_global"]) + Decimal(t2["weight_global"])
    assert total < 1

    # breadth: 2 up (AAA-01 +10%, BBB-02 +10%), covered 4, universe 4.
    breadth = content["breadth"]
    assert breadth["status"] == "OK"
    assert breadth["above_count"] == 2
    assert breadth["covered_count"] == 4
    assert breadth["universe_size"] == 4
    assert breadth["value"] == "0.5"
    assert breadth["value_pct"] == "50.0"
    assert breadth["coverage_pct"] == "100.0"
    assert breadth["calculation"]["calculation_id"] == "market.breadth"

    conclusion = content["conclusion"]
    assert "4 sont couverts" in conclusion
    assert "2 en hausse" in conclusion
    assert "1 en baisse" in conclusion
    assert "1 stables" in conclusion
    assert "breadth 50.0 %" in conclusion


def test_missing_close_is_discarded_and_counted_never_interpolated() -> None:
    records = full_records()[:-1]  # SYN-BBB-02 loses its latest close
    content = build_markets_overview_content(records, now=NOW, config=SMALL_CONFIG)
    coverage = content["coverage"]
    assert coverage["covered"] == 3
    assert coverage["received"] == 4
    assert coverage["discarded"] == 1
    assert coverage["discarded_tickers"] == [
        {"ticker": "SYN-BBB-02", "reason": REASON_MISSING_CLOSE}
    ]
    published = [
        t["ticker"] for s in content["sectors"] for t in s["tickers"]
    ]
    assert "SYN-BBB-02" not in published
    assert content["data_state"] == "partial"
    # breadth still valid: coverage 3/4 >= 0.5 threshold.
    assert content["breadth"]["status"] == "OK"
    assert content["breadth"]["covered_count"] == 3


def test_breadth_fails_closed_below_coverage_threshold() -> None:
    records = full_records()[:2]  # only one ticker covered -> 1/4 < 0.5
    content = build_markets_overview_content(records, now=NOW, config=SMALL_CONFIG)
    breadth = content["breadth"]
    assert breadth["status"] == "INVALID"
    assert breadth["reason"] == "coverage_below_threshold"
    assert breadth["value"] is None
    assert breadth["value_pct"] is None
    assert breadth["calculation"] is None
    assert "breadth non calculable" in content["conclusion"]


def test_undeclared_source_rights_and_ticker_are_rejected() -> None:
    records = [
        *full_records(),
        quote("SYN-AAA-01", "SYN-AAA", "2026-08-24", "1.00", source="not-declared"),
        quote("SYN-AAA-01", "SYN-AAA", "2026-08-24", "1.00", rights="REAL", event_id="x:rights"),
        quote("SYN-ZZZ-01", "SYN-ZZZ", "2026-08-24", "1.00", event_id="x:univ"),
    ]
    content = build_markets_overview_content(records, now=NOW, config=SMALL_CONFIG)
    reasons = {r["reason"] for r in content["coverage"]["rejected_records"]}
    assert reasons == {
        REASON_SOURCE_NOT_ALLOWED,
        REASON_RIGHTS_NOT_USABLE,
        REASON_TICKER_NOT_IN_UNIVERSE,
    }
    # The declared universe values are untouched by the rejected records.
    aaa = next(s for s in content["sectors"] if s["sector"] == "SYN-AAA")
    t1 = next(t for t in aaa["tickers"] if t["ticker"] == "SYN-AAA-01")
    assert t1["last_close"] == "110.00"
    # §4.2 : ce test porte sur les MOTIFS de rejet, pas sur l'etat. Un rejet
    # est une observation NON DEMANDEE, pas un trou de couverture — il ne
    # degrade donc plus. La couverture etant complete et toutes les qualites
    # VALID, l'etat est `ok`, et les rejets restent publies avec leur motif.
    assert content["data_state"] == "ok"
    assert content["coverage"]["discarded"] == 0


def test_adjustment_basis_mismatch_discards_the_ticker() -> None:
    records = [
        quote("SYN-AAA-01", "SYN-AAA", "2026-08-23", "100.00", basis="basis-a"),
        quote("SYN-AAA-01", "SYN-AAA", "2026-08-24", "110.00", basis="basis-b"),
        *full_records()[2:],
    ]
    content = build_markets_overview_content(records, now=NOW, config=SMALL_CONFIG)
    assert {"ticker": "SYN-AAA-01", "reason": "adjustment_basis_mismatch"} in content[
        "coverage"
    ]["discarded_tickers"]


def test_degraded_quality_propagates_worst_and_partial_state() -> None:
    records = full_records()
    records[1] = quote(
        "SYN-AAA-01", "SYN-AAA", "2026-08-24", "110.00", quality="PARTIAL"
    )
    content = build_markets_overview_content(records, now=NOW, config=SMALL_CONFIG)
    aaa = next(s for s in content["sectors"] if s["sector"] == "SYN-AAA")
    t1 = next(t for t in aaa["tickers"] if t["ticker"] == "SYN-AAA-01")
    assert t1["quality"] == "PARTIAL"
    assert content["data_state"] == "partial"


def test_all_stale_covered_tickers_yield_stale_state() -> None:
    records = [
        quote("SYN-AAA-01", "SYN-AAA", "2026-08-23", "100.00", quality="STALE"),
        quote("SYN-AAA-01", "SYN-AAA", "2026-08-24", "110.00", quality="STALE"),
        quote("SYN-AAA-02", "SYN-AAA", "2026-08-23", "50.00", quality="STALE"),
        quote("SYN-AAA-02", "SYN-AAA", "2026-08-24", "45.00", quality="STALE"),
    ]
    config = MarketsConfig(
        universe={"SYN-AAA": ("SYN-AAA-01", "SYN-AAA-02")},
        sector_labels={"SYN-AAA": "Secteur AAA"},
        allowed_sources=frozenset({SYNTHETIC_SOURCE}),
        usable_rights=frozenset({SYNTHETIC_RIGHTS}),
        coverage_threshold=Decimal("0.5"),
    )
    content = build_markets_overview_content(records, now=NOW, config=config)
    assert content["data_state"] == "stale"


def test_empty_records_yield_empty_population_and_invalid_breadth() -> None:
    content = build_markets_overview_content([], now=NOW, config=SMALL_CONFIG)
    assert content["population"] == "EMPTY"
    assert content["coverage"]["received"] == 0
    assert content["coverage"]["discarded"] == 4
    assert content["breadth"]["status"] == "INVALID"


def test_determinism_and_order_insensitivity() -> None:
    records = full_records()
    a = build_markets_overview_content(records, now=NOW, config=SMALL_CONFIG)
    b = build_markets_overview_content(list(reversed(records)), now=NOW, config=SMALL_CONFIG)
    assert a == b


def test_latest_record_wins_per_ticker_day() -> None:
    older = quote(
        "SYN-AAA-01", "SYN-AAA", "2026-08-24", "999.00",
        as_of=NOW - timedelta(hours=3), event_id="dup:old",
    )
    records = [older, *full_records()]
    content = build_markets_overview_content(records, now=NOW, config=SMALL_CONFIG)
    aaa = next(s for s in content["sectors"] if s["sector"] == "SYN-AAA")
    t1 = next(t for t in aaa["tickers"] if t["ticker"] == "SYN-AAA-01")
    assert t1["last_close"] == "110.00"  # the later as_of wins, never 999.00


def test_naive_now_rejected() -> None:
    with pytest.raises(ValueError):
        build_markets_overview_content(
            [], now=NOW.replace(tzinfo=None), config=SMALL_CONFIG
        )


def test_dev_config_matches_synthetic_universe() -> None:
    assert len(DEV_SYNTHETIC_MARKETS_CONFIG.all_tickers()) == 24
    assert DEV_SYNTHETIC_MARKETS_CONFIG.coverage_threshold == Decimal("0.8")


def test_une_observation_HORS_UNIVERS_ne_degrade_pas_la_couverture() -> None:
    """§4.2 — REPRODUCTEUR. `rejected_records` ne vaut pas `partial`.

    `markets.py` declenchait `partial` sur `rejected_records`. Sur le poste de
    travail, ces enregistrements sont TROIS cotations `GNL PRE` — des
    observations EN TROP, hors univers declare, pas un trou de couverture.

    L'ecran affichait donc « Donnees partielles » puis, juste en dessous,
    « 161 couverts sur 161, 0 ecartes » : un texte qui se refute lui-meme.

    CONFUSION CORRIGEE, et les deux mots restent distincts :
      - `discarded`        = un ticker ATTENDU qui manque  -> vraie lacune ;
      - `rejected_records` = une observation NON DEMANDEE  -> aucun manque.

    Refuser une observation hors univers est le comportement voulu (le
    deny-by-default). Le compter comme une degradation punit le systeme pour
    avoir bien fait son travail.
    """
    records = [
        *full_records(),
        # Hors univers : refuse a l'entree, et c'est correct.
        quote("SYN-ZZZ-01", "SYN-ZZZ", "2026-08-24", "1.00", event_id="x:hors-univers"),
    ]
    content = build_markets_overview_content(records, now=NOW, config=SMALL_CONFIG)

    coverage = content["coverage"]
    assert coverage["rejected_records"], "le reproducteur exige un rejet, sinon il ne prouve rien"
    # `discarded` est un COMPTE, `discarded_tickers` la liste — ne pas les
    # confondre, c'est justement la confusion que ce lot corrige.
    assert coverage["discarded"] == 0, "aucun ticker attendu ne manque"
    assert coverage["discarded_tickers"] == []
    assert coverage["covered"] == coverage["expected"], "la couverture est COMPLETE"

    # L'ecran ne doit donc pas annoncer une degradation qui n'existe pas.
    assert content["data_state"] == "ok"


def test_un_ticker_ATTENDU_qui_manque_degrade_toujours() -> None:
    """La moitie qui empeche d'affaiblir la garde en la corrigeant.

    Retirer `rejected_records` du declencheur ne doit pas rendre `partial`
    inatteignable : une vraie lacune de couverture doit toujours le lever.
    """
    manquant = [r for r in full_records() if "SYN-AAA-02" not in r.instrument_ref]
    content = build_markets_overview_content(manquant, now=NOW, config=SMALL_CONFIG)

    assert content["coverage"]["discarded"] > 0, "le reproducteur exige un ticker manquant"
    assert content["data_state"] == "partial"
