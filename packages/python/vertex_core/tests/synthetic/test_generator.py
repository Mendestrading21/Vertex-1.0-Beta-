"""Tests of the deterministic synthetic envelope generator.

Invariants under test: mandatory seed, byte-level determinism, honest
SYNTHETIC labeling on every envelope, guaranteed multi-level duplicates and
plausible-but-clearly-fake content (SYN tickers, prefixed titles).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

import pytest

from vertex_core.contracts import DataEnvelope, DelayStatus, EnvelopeQuality
from vertex_core.fusion import normalize_canonical_url, title_fingerprint
from vertex_core.synthetic import (
    SYNTHETIC_RIGHTS,
    SYNTHETIC_SOURCE,
    SYNTHETIC_TITLE_PREFIX,
    generate_calendar_event_envelopes,
    generate_daily_bar_envelopes,
    generate_envelopes,
    generate_option_chain_envelopes,
    is_synthetic,
)

BASE_TIME = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)


def _generate(count: int = 40, seed: int = 1234):
    return generate_envelopes(seed=seed, count=count, base_time=BASE_TIME)


class TestInputValidation:
    def test_seed_is_mandatory_keyword(self) -> None:
        with pytest.raises(TypeError):
            generate_envelopes(count=5, base_time=BASE_TIME)  # type: ignore[call-arg]

    def test_positional_arguments_rejected(self) -> None:
        with pytest.raises(TypeError):
            generate_envelopes(1, 5, BASE_TIME)  # type: ignore[misc]

    def test_bool_seed_rejected(self) -> None:
        with pytest.raises(TypeError):
            generate_envelopes(seed=True, count=5, base_time=BASE_TIME)

    def test_naive_base_time_rejected(self) -> None:
        with pytest.raises(ValueError):
            generate_envelopes(
                seed=1,
                count=5,
                base_time=datetime(2026, 8, 25, 12, 0, 0),  # noqa: DTZ001 (naïf délibéré : rejet vérifié)
            )

    def test_zero_count_rejected(self) -> None:
        with pytest.raises(ValueError):
            generate_envelopes(seed=1, count=0, base_time=BASE_TIME)


class TestDeterminism:
    def test_same_inputs_identical_output(self) -> None:
        first = _generate()
        second = _generate()
        assert first == second

    def test_different_seed_different_output(self) -> None:
        assert _generate(seed=1234) != _generate(seed=1235)

    def test_count_is_respected(self) -> None:
        assert len(_generate(count=40)) == 40
        assert len(_generate(count=1)) == 1


class TestSyntheticLabeling:
    def test_every_envelope_has_synthetic_rights(self) -> None:
        for envelope in _generate():
            assert envelope.rights == SYNTHETIC_RIGHTS

    def test_every_envelope_has_synthetic_source(self) -> None:
        for envelope in _generate():
            assert envelope.source == SYNTHETIC_SOURCE

    def test_is_synthetic_true_for_every_generated_envelope(self) -> None:
        for envelope in _generate():
            assert is_synthetic(envelope) is True

    def test_titles_are_prefixed_and_tickers_are_syn(self) -> None:
        for envelope in _generate():
            payload = envelope.payload
            assert payload["synthetic"] is True
            assert re.fullmatch(r"SYN\d+", envelope.instrument_id)
            if payload["type"] == "news":
                assert payload["title"].startswith(SYNTHETIC_TITLE_PREFIX)

    def test_never_presented_as_live(self) -> None:
        for envelope in _generate():
            assert envelope.delay_status is DelayStatus.UNKNOWN

    def test_is_synthetic_false_for_non_synthetic_envelope(self) -> None:
        envelope = DataEnvelope[dict](
            event_id="demo:1",
            schema_version="demo-news/1.0",
            source="demo-feed",
            received_at=BASE_TIME,
            as_of=BASE_TIME,
            stale_after=BASE_TIME,
            quality_status=EnvelopeQuality.VALID,
            delay_status=DelayStatus.UNKNOWN,
            rights="DEMO",
            payload_hash="sha256:" + "0" * 64,
            payload={"title": "demo"},
        )
        assert is_synthetic(envelope) is False

    def test_is_synthetic_rejects_non_envelope(self) -> None:
        with pytest.raises(TypeError):
            is_synthetic({"rights": SYNTHETIC_RIGHTS})  # type: ignore[arg-type]


class TestDuplicateLevels:
    def test_ingest_level_duplicate_present(self) -> None:
        envelopes = _generate()
        event_ids = [e.event_id for e in envelopes]
        assert len(event_ids) > len(set(event_ids))

    def test_native_id_duplicate_present(self) -> None:
        envelopes = _generate()
        unique = {e.event_id: e for e in envelopes}.values()
        native_pairs = [(e.source, e.source_event_id) for e in unique if e.source_event_id]
        assert len(native_pairs) > len(set(native_pairs))

    def test_canonical_url_duplicate_present(self) -> None:
        unique = {e.event_id: e for e in _generate()}.values()
        urls = [
            normalize_canonical_url(e.payload["canonical_url"])
            for e in unique
            if e.payload.get("canonical_url")
        ]
        assert len(urls) > len(set(urls))

    def test_title_fingerprint_duplicate_present(self) -> None:
        unique = {e.event_id: e for e in _generate()}.values()
        fingerprints = [
            title_fingerprint(e.payload["title"], e.payload.get("entities", ()))
            for e in unique
            if e.payload.get("title")
        ]
        fingerprints = [f for f in fingerprints if f is not None]
        assert len(fingerprints) > len(set(fingerprints))


class TestEnvelopeShape:
    def test_qualities_are_varied(self) -> None:
        qualities = {e.quality_status for e in _generate()}
        assert EnvelopeQuality.VALID in qualities
        assert qualities <= {
            EnvelopeQuality.VALID,
            EnvelopeQuality.PARTIAL,
            EnvelopeQuality.STALE,
        }
        assert len(qualities) >= 2

    def test_timestamps_are_aware_and_before_base_time(self) -> None:
        for envelope in _generate():
            assert envelope.received_at.tzinfo is not None
            assert envelope.received_at <= BASE_TIME
            assert envelope.as_of <= BASE_TIME
            assert envelope.published_at is not None
            assert envelope.published_at < envelope.received_at

    def test_payload_hash_matches_canonical_hash(self) -> None:
        from vertex_core.contracts import canonical_json_hash

        for envelope in _generate(count=10):
            assert envelope.payload_hash == canonical_json_hash(envelope.payload)

    def test_no_float_in_quote_prices(self) -> None:
        for envelope in _generate(count=60, seed=7):
            if envelope.payload["type"] == "quote":
                assert isinstance(envelope.payload["bid"], str)
                assert isinstance(envelope.payload["ask"], str)


class TestRuntimeGuardTargetsTheGenericBase:
    """Régression : un garde `isinstance` ne vise JAMAIS une paramétrisation.

    Avec les génériques Pydantic, `DataEnvelope[Any]` est une classe concrète
    DISTINCTE de `DataEnvelope[dict[str, Any]]`. Un garde écrit contre
    `DataEnvelope[Any]` rejette donc toutes les enveloppes réellement
    produites par les générateurs, et casse la chaîne d'ingestion complète.
    L'annotation de signature et le contrôle runtime ne sont pas le même
    objet : l'annotation peut être paramétrée, le garde doit rester sur la
    base générique.
    """

    def test_les_parametrisations_sont_des_classes_distinctes(self) -> None:
        # C'est la propriété qui rend le défaut possible : si elle tombe, ce
        # test doit être relu, pas supprimé.
        assert DataEnvelope[Any] is not DataEnvelope[dict[str, Any]]

    @pytest.mark.parametrize(
        "generate",
        [
            lambda: generate_envelopes(seed=1, count=3, base_time=BASE_TIME),
            lambda: generate_option_chain_envelopes(seed=1, base_time=BASE_TIME),
            lambda: generate_daily_bar_envelopes(seed=1, base_time=BASE_TIME),
            lambda: generate_calendar_event_envelopes(seed=1, base_time=BASE_TIME),
        ],
        ids=["news", "option_chain", "daily_bars", "calendar_events"],
    )
    def test_toute_enveloppe_generee_traverse_le_garde(self, generate) -> None:
        envelopes = generate()
        assert envelopes, "le générateur doit produire au moins une enveloppe"
        for envelope in envelopes:
            # Échoue en TypeError si le garde vise une paramétrisation.
            assert is_synthetic(envelope) is True
