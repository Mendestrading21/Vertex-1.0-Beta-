"""Unit tests of the pure attention-content builder (no database).

Covers: deterministic dedup + ranking, the 15-item cap, <=3 relevance
reasons, provenance, explained rejections, and the SYNTHETIC population
boundary guard (a single synthetic entry labels the whole snapshot; a
production-like registry gates synthetic data out entirely).
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest

from vertex_core.synthetic import SYNTHETIC_RIGHTS, SYNTHETIC_SOURCE, generate_envelopes
from vertex_worker.calendar import CALENDAR_EVENT_SCHEMA_PREFIXES
from vertex_worker.handlers import (
    CONTENT_SCHEMA_PREFIXES,
    DEV_SYNTHETIC_CONFIG,
    MAX_ATTENTION_ITEMS,
    POPULATION_EMPTY,
    POPULATION_REAL,
    POPULATION_SYNTHETIC,
    FusionConfig,
    ObservationRecord,
    build_attention_content,
    is_synthetic_record,
    load_recent_observation_records_by_instrument,
)

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)
BASE_TIME = NOW - timedelta(minutes=30)

DEMO_SOURCE = "demo-feed"
DEMO_RIGHTS = "DEMO"

MIXED_CONFIG = FusionConfig(
    allowed_sources=frozenset({SYNTHETIC_SOURCE, DEMO_SOURCE}),
    usable_rights=frozenset({SYNTHETIC_RIGHTS, DEMO_RIGHTS}),
    source_tiers={SYNTHETIC_SOURCE: "P4", DEMO_SOURCE: "P3"},
)


def record_from_envelope(envelope) -> ObservationRecord:
    return ObservationRecord(
        event_id=envelope.event_id,
        source=envelope.source,
        source_event_id=envelope.source_event_id,
        instrument_ref=envelope.instrument_id,
        published_at=envelope.published_at,
        received_at=envelope.received_at,
        as_of=envelope.as_of,
        quality_status=envelope.quality_status.value,
        rights=envelope.rights,
        schema_version=envelope.schema_version,
        payload=envelope.payload,
    )


def demo_record(number: int, *, title: str | None = None) -> ObservationRecord:
    """A non-synthetic, DEMO-labeled fixture record (never presented as real)."""
    published = BASE_TIME + timedelta(seconds=45 * number)
    return ObservationRecord(
        event_id=f"demo:{number:04d}",
        source=DEMO_SOURCE,
        source_event_id=f"demo-native-{number:04d}",
        instrument_ref=f"DEMO{number}",
        published_at=published,
        received_at=published + timedelta(seconds=10),
        as_of=published + timedelta(seconds=10),
        quality_status="VALID",
        rights=DEMO_RIGHTS,
        schema_version="demo-news/1.0",
        payload={
            "type": "news",
            "title": title or f"Demo fixture headline number {number:04d}",
            "canonical_url": f"https://demo.invalid/news/{number:04d}",
            "entities": [f"DEMO{number}"],
        },
    )


def synthetic_records(count: int = 40, seed: int = 1234) -> list[ObservationRecord]:
    envelopes = generate_envelopes(seed=seed, count=count, base_time=BASE_TIME)
    unique = {e.event_id: e for e in envelopes}
    return [record_from_envelope(e) for e in unique.values()]


class TestDeterminismAndDedup:
    def test_same_records_any_order_identical_content(self) -> None:
        records = synthetic_records()
        shuffled = list(records)
        random.Random(99).shuffle(shuffled)
        first = build_attention_content(records, now=NOW, config=DEV_SYNTHETIC_CONFIG)
        second = build_attention_content(shuffled, now=NOW, config=DEV_SYNTHETIC_CONFIG)
        assert first == second

    def test_duplicates_are_clustered_not_repeated(self) -> None:
        records = synthetic_records()
        content = build_attention_content(records, now=NOW, config=DEV_SYNTHETIC_CONFIG)
        coverage = content["coverage"]
        # Multi-level duplicates guarantee fewer clusters than content rows.
        assert coverage["clusters"] < coverage["content_observations"]
        # No published item shares a cluster with another one.
        cluster_ids = [item["provenance"]["cluster_id"] for item in content["items"]]
        assert len(cluster_ids) == len(set(cluster_ids))
        item_ids = [item["item_id"] for item in content["items"]]
        assert len(item_ids) == len(set(item_ids))

    def test_duplicate_event_id_in_input_is_refused(self) -> None:
        records = synthetic_records()
        with pytest.raises(ValueError):
            build_attention_content(
                [*records, records[0]], now=NOW, config=DEV_SYNTHETIC_CONFIG
            )

    def test_naive_now_rejected(self) -> None:
        with pytest.raises(ValueError):
            build_attention_content(
                [], now=datetime(2026, 8, 25, 12, 0, 0), config=DEV_SYNTHETIC_CONFIG  # noqa: DTZ001 (naïf délibéré : rejet vérifié)
            )


class TestBudgetAndReasons:
    def test_at_most_fifteen_items(self) -> None:
        records = [demo_record(n) for n in range(1, 31)]
        config = FusionConfig(
            allowed_sources=frozenset({DEMO_SOURCE}),
            usable_rights=frozenset({DEMO_RIGHTS}),
        )
        content = build_attention_content(records, now=NOW, config=config)
        assert len(content["items"]) == MAX_ATTENTION_ITEMS
        assert content["coverage"]["truncated_ranked"] == 30 - MAX_ATTENTION_ITEMS

    def test_relevance_reasons_bounded_to_three(self) -> None:
        records = synthetic_records()
        content = build_attention_content(records, now=NOW, config=DEV_SYNTHETIC_CONFIG)
        assert content["items"], "expected at least one ranked item"
        for item in content["items"]:
            assert 1 <= len(item["relevance_reasons"]) <= 3

    def test_provenance_and_as_of_are_present(self) -> None:
        records = synthetic_records()
        content = build_attention_content(records, now=NOW, config=DEV_SYNTHETIC_CONFIG)
        assert content["as_of"] == NOW.isoformat()
        for item in content["items"]:
            provenance = item["provenance"]
            assert provenance["member_event_ids"]
            assert provenance["sources"] == [SYNTHETIC_SOURCE]
            assert provenance["rights"] == [SYNTHETIC_RIGHTS]
            assert provenance["last_received_at"] is not None

    def test_rejections_are_explained_not_silent(self) -> None:
        records = synthetic_records()
        content = build_attention_content(records, now=NOW, config=DEV_SYNTHETIC_CONFIG)
        coverage = content["coverage"]
        # STALE-quality synthetic items are gated out by QUALITY_OK.
        assert coverage["rejected"] == len(content["rejected"])
        assert coverage["clusters"] == coverage["ranked"] + coverage["rejected"]
        for rejection in content["rejected"]:
            assert rejection["failed_gates"]
            assert rejection["filtered_reason"].endswith("_FAILED")


class TestSyntheticBoundary:
    def test_all_synthetic_population_is_synthetic(self) -> None:
        records = synthetic_records()
        content = build_attention_content(records, now=NOW, config=DEV_SYNTHETIC_CONFIG)
        assert content["population"] == POPULATION_SYNTHETIC
        assert all(item["synthetic"] is True for item in content["items"])

    def test_single_synthetic_entry_labels_whole_snapshot(self) -> None:
        records = [demo_record(n) for n in range(1, 6)]
        records += synthetic_records(count=1, seed=5)
        content = build_attention_content(records, now=NOW, config=MIXED_CONFIG)
        assert content["population"] == POPULATION_SYNTHETIC

    def test_mixed_items_each_list_their_nature(self) -> None:
        records = [demo_record(n) for n in range(1, 4)]
        records += synthetic_records(count=1, seed=5)
        content = build_attention_content(records, now=NOW, config=MIXED_CONFIG)
        assert content["population"] == POPULATION_SYNTHETIC
        natures = {item["item_id"]: item["synthetic"] for item in content["items"]}
        assert True in natures.values()
        assert False in natures.values()
        for item in content["items"]:
            assert isinstance(item["synthetic"], bool)

    def test_all_demo_population_is_real_family_not_synthetic(self) -> None:
        records = [demo_record(n) for n in range(1, 4)]
        config = FusionConfig(
            allowed_sources=frozenset({DEMO_SOURCE}),
            usable_rights=frozenset({DEMO_RIGHTS}),
        )
        content = build_attention_content(records, now=NOW, config=config)
        assert content["population"] == POPULATION_REAL

    def test_empty_window_population_is_empty(self) -> None:
        content = build_attention_content([], now=NOW, config=DEV_SYNTHETIC_CONFIG)
        assert content["population"] == POPULATION_EMPTY
        assert content["items"] == []

    def test_production_like_registry_gates_synthetic_out(self) -> None:
        """SYNTHETIC never crosses a production boundary: with a registry
        that does not declare the synthetic source/rights, every synthetic
        item is refused at the RIGHTS gate and none is ever ranked."""
        production_config = FusionConfig(
            allowed_sources=frozenset({DEMO_SOURCE}),
            usable_rights=frozenset({DEMO_RIGHTS}),
        )
        records = synthetic_records()
        content = build_attention_content(records, now=NOW, config=production_config)
        assert content["items"] == []
        assert content["coverage"]["ranked"] == 0
        assert content["rejected"], "synthetic items must be explicitly rejected"
        for rejection in content["rejected"]:
            assert rejection["filtered_reason"] == "RIGHTS_OK_FAILED"
        # And the snapshot still confesses its synthetic input population.
        assert content["population"] == POPULATION_SYNTHETIC

    def test_is_synthetic_record_matches_generator_markers(self) -> None:
        synthetic = synthetic_records(count=1, seed=5)[0]
        assert is_synthetic_record(synthetic) is True
        assert is_synthetic_record(demo_record(1)) is False


class TestQuotesAndCoverage:
    def test_quotes_without_title_are_counted_not_ranked(self) -> None:
        records = synthetic_records(count=60, seed=7)
        content = build_attention_content(records, now=NOW, config=DEV_SYNTHETIC_CONFIG)
        coverage = content["coverage"]
        assert coverage["non_content_observations"] > 0
        assert (
            coverage["content_observations"] + coverage["non_content_observations"]
            == coverage["observations_considered"]
        )


def polarity_record(number: int, *, title: str, native_id: str) -> ObservationRecord:
    """A DEMO record sharing ``native_id`` with its twin (level-1 cluster)."""
    published = BASE_TIME + timedelta(seconds=45 * number)
    return ObservationRecord(
        event_id=f"demo:{number:04d}",
        source=DEMO_SOURCE,
        source_event_id=native_id,
        instrument_ref="SPX",
        published_at=published,
        received_at=published + timedelta(seconds=10),
        as_of=published + timedelta(seconds=10),
        quality_status="VALID",
        rights=DEMO_RIGHTS,
        schema_version="demo-news/1.0",
        payload={"type": "news", "title": title, "entities": ["SPX"]},
    )


DEMO_ONLY_CONFIG = FusionConfig(
    allowed_sources=frozenset({DEMO_SOURCE}),
    usable_rights=frozenset({DEMO_RIGHTS}),
)


class TestPolarityConflictIsNeverResolvedByElection:
    """A cluster holding two opposite polarities must not be represented by
    one blindly elected member: a rise would be published in place of a fall
    with no contradiction visible anywhere."""

    def _conflicted(self):
        return [
            polarity_record(1, title="SPX -3,2 % sur la seance", native_id="n-spx"),
            polarity_record(2, title="SPX +3,2 % sur la seance", native_id="n-spx"),
        ]

    def test_conflicted_cluster_is_not_published_as_one_item(self) -> None:
        content = build_attention_content(
            self._conflicted(), now=NOW, config=DEMO_ONLY_CONFIG
        )
        assert content["coverage"]["clusters"] == 1
        assert content["items"] == [], (
            "one polarity was published as the representative of a "
            f"contradictory cluster: {content['items']}"
        )

    def test_conflict_is_published_not_silently_dropped(self) -> None:
        content = build_attention_content(
            self._conflicted(), now=NOW, config=DEMO_ONLY_CONFIG
        )
        conflicts = content["conflicts"]
        assert len(conflicts) == 1
        conflict = conflicts[0]
        assert conflict["kind"] == "POLARITY"
        assert conflict["scope"] == "INTRA_CLUSTER"
        assert sorted(conflict["member_event_ids"]) == ["demo:0001", "demo:0002"]
        assert content["coverage"]["polarity_conflicts"] == 1
        assert content["rejected"], "the conflicted cluster must be explained"

    def test_agreeing_cluster_is_still_published(self) -> None:
        """The fix must not reject ordinary clusters: same sign, one item."""
        records = [
            polarity_record(1, title="SPX -3,2 % sur la seance", native_id="n-spx"),
            polarity_record(2, title="SPX -3,2 % a la cloture", native_id="n-spx"),
        ]
        content = build_attention_content(records, now=NOW, config=DEMO_ONLY_CONFIG)
        assert content["coverage"]["clusters"] == 1
        assert len(content["items"]) == 1
        assert content["conflicts"] == []
        assert content["coverage"]["polarity_conflicts"] == 0

    def test_coverage_still_accounts_for_every_cluster(self) -> None:
        records = [*self._conflicted(), demo_record(9)]
        content = build_attention_content(records, now=NOW, config=DEMO_ONLY_CONFIG)
        coverage = content["coverage"]
        assert coverage["rejected"] == len(content["rejected"])
        assert coverage["clusters"] == coverage["ranked"] + coverage["rejected"]

    def test_conflicted_content_is_order_independent(self) -> None:
        records = [*self._conflicted(), demo_record(9)]
        shuffled = list(reversed(records))
        first = build_attention_content(records, now=NOW, config=DEMO_ONLY_CONFIG)
        second = build_attention_content(shuffled, now=NOW, config=DEMO_ONLY_CONFIG)
        assert first == second


class TestDeclaredContentFamilies:
    """La fenêtre est cadrée par les familles que le consommateur DÉCLARE.

    Mesuré le 2026-09-03 : les 500 observations les plus récentes étaient
    toutes des cotations instantanées, et la file d'attention servait 0 item
    sur données réelles. Le registre déclare donc les familles de contenu, et
    la couverture publiée les répète.
    """

    def test_default_families_are_the_worker_content_families(self) -> None:
        assert DEV_SYNTHETIC_CONFIG.content_schema_prefixes == CONTENT_SCHEMA_PREFIXES
        assert "synthetic-news/" in CONTENT_SCHEMA_PREFIXES
        assert "ibkr.news-headline/" in CONTENT_SCHEMA_PREFIXES

    @pytest.mark.parametrize(
        "instantanee",
        ["ibkr.quote/1", "ibkr.daily-quote/1", "synthetic-daily-quote/1.0", "ibkr.bars/1"],
    )
    def test_market_families_are_never_declared_as_content(self, instantanee: str) -> None:
        assert not instantanee.startswith(CONTENT_SCHEMA_PREFIXES)

    @pytest.mark.parametrize("prefixes", [(), ("",), ("  ",), ("synthetic-news/", 3), "x/"])
    def test_config_refuses_an_empty_or_malformed_declaration(self, prefixes: object) -> None:
        with pytest.raises(ValueError, match="content_schema_prefixes"):
            FusionConfig(
                allowed_sources=frozenset({DEMO_SOURCE}),
                usable_rights=frozenset({DEMO_RIGHTS}),
                content_schema_prefixes=cast("tuple[str, ...]", prefixes),
            )

    def test_coverage_publishes_the_declared_families(self) -> None:
        by_default = build_attention_content([demo_record(1)], now=NOW, config=DEMO_ONLY_CONFIG)
        assert by_default["coverage"]["content_schema_prefixes"] == list(CONTENT_SCHEMA_PREFIXES)
        declared = FusionConfig(
            allowed_sources=frozenset({DEMO_SOURCE}),
            usable_rights=frozenset({DEMO_RIGHTS}),
            content_schema_prefixes=("demo-news/",),
        )
        explicit = build_attention_content([demo_record(1)], now=NOW, config=declared)
        assert explicit["coverage"]["content_schema_prefixes"] == ["demo-news/"]

    def test_calendar_events_are_served_by_their_own_page_not_by_the_queue(self) -> None:
        """TÉMOIN d'un comportement DÉCLARÉ (pas un reproducteur) : un événement
        de calendrier porte un titre mais n'est pas une dépêche. La page
        Calendrier le sert (`CALENDAR_EVENT_SCHEMA_PREFIXES`), la file
        d'attention ne le lit pas. Le réintroduire est une décision de
        produit qui passe par `CONTENT_SCHEMA_PREFIXES`, jamais par une
        borne plus large — ce test la rendra visible."""
        assert CALENDAR_EVENT_SCHEMA_PREFIXES, "la page Calendrier déclare ses familles"
        for famille in (*CALENDAR_EVENT_SCHEMA_PREFIXES, "synthetic-calendar-event/1.0"):
            assert not famille.startswith(CONTENT_SCHEMA_PREFIXES), famille
        title_bearing_event = ObservationRecord(
            event_id="cal-1",
            source=SYNTHETIC_SOURCE,
            source_event_id="cal-1",
            instrument_ref="SYN-0001",
            published_at=BASE_TIME,
            received_at=BASE_TIME,
            as_of=BASE_TIME,
            quality_status="VALID",
            rights=SYNTHETIC_RIGHTS,
            schema_version="synthetic-calendar-event/1.0",
            payload={"title": "[SYNTHETIC] résultats trimestriels", "ticker": "SYN-0001"},
        )
        # Le constructeur pur, lui, lirait ce titre : c'est bien la DÉCLARATION
        # (appliquée par le chargeur, avant la borne) qui tient l'événement
        # hors de la file, pas une absence de titre.
        content = build_attention_content(
            [title_bearing_event], now=NOW, config=DEV_SYNTHETIC_CONFIG
        )
        assert content["coverage"]["content_observations"] == 1
        assert "synthetic-calendar-event/" not in content["coverage"]["content_schema_prefixes"]


class TestPerInstrumentWindowDeclaration:
    """`load_recent_observation_records_by_instrument` refuse une demande vide
    ou mal formée AVANT toute lecture — même règle que pour les familles :
    rien de déclaré, rien de lu, et le refus est explicite."""

    @pytest.mark.parametrize("refs", [(), ("",), ("  ",), ("208813720", 3), "208813720"])
    def test_refuses_an_empty_or_malformed_reference_list(self, refs: object) -> None:
        with pytest.raises(ValueError, match="instrument_refs"):
            load_recent_observation_records_by_instrument(
                cast(Any, None),
                now=NOW,
                lookback=timedelta(hours=72),
                limit=10,
                schema_prefixes=CONTENT_SCHEMA_PREFIXES,
                instrument_refs=cast(Any, refs),
            )

    def test_refuses_an_empty_family_declaration(self) -> None:
        with pytest.raises(ValueError, match="schema_prefixes"):
            load_recent_observation_records_by_instrument(
                cast(Any, None),
                now=NOW,
                lookback=timedelta(hours=72),
                limit=10,
                schema_prefixes=(),
                instrument_refs=("208813720",),
            )
