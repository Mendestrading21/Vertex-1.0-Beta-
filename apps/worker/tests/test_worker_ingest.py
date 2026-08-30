"""Unit tests of ``ingest_envelope`` (repository calls monkeypatched).

The full transactional behavior runs against real PostgreSQL in
``tests_integration``; here we verify the atomicity contract shape: same
session for insert and enqueue, no enqueue on duplicate, no commit inside.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

import vertex_worker.ingest as ingest_module
from vertex_core.synthetic import generate_envelopes
from vertex_worker.ingest import TOPIC_OBSERVATION_INGESTED, ingest_envelope

BASE_TIME = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)


class RecordingSession:
    def __init__(self) -> None:
        self.committed = 0
        self.executed: list[tuple] = []

    def commit(self) -> None:  # pragma: no cover - must never be called
        self.committed += 1

    def execute(self, statement, params=None):
        self.executed.append((statement, params))


@pytest.fixture()
def envelope():
    return generate_envelopes(seed=1, count=1, base_time=BASE_TIME)[0]


def test_insert_and_enqueue_share_the_session(monkeypatch, envelope) -> None:
    calls: dict[str, object] = {}

    def fake_insert(session, **kwargs):
        calls["insert_session"] = session
        calls["insert_kwargs"] = kwargs
        return True

    enqueues: list[tuple[object, str, object]] = []

    def fake_enqueue(session, topic, payload):
        enqueues.append((session, topic, payload))
        return 42

    monkeypatch.setattr(ingest_module, "insert_observation", fake_insert)
    monkeypatch.setattr(ingest_module, "enqueue_outbox", fake_enqueue)
    session = RecordingSession()

    result = ingest_envelope(session, envelope)

    assert calls["insert_session"] is session
    # A generic (non-quote) envelope enqueues its fusion job and the review
    # queue refresh (page 09) — both on the SAME session/transaction.
    expected_payload = {
        "event_id": envelope.event_id,
        "source": envelope.source,
        "schema_version": envelope.schema_version,
    }
    assert [(topic, payload) for _, topic, payload in enqueues] == [
        (TOPIC_OBSERVATION_INGESTED, expected_payload),
        ("review_queue.refresh", expected_payload),
    ]
    assert all(enqueue_session is session for enqueue_session, _, _ in enqueues)
    assert result.inserted is True
    assert result.outbox_message_id == 42
    assert result.event_id == envelope.event_id
    # The caller owns the transaction: ingest never commits.
    assert session.committed == 0
    # A NOTIFY wake-up signal is emitted inside the same transaction.
    assert len(session.executed) == 1


def test_envelope_fields_are_forwarded_exactly(monkeypatch, envelope) -> None:
    captured: dict[str, object] = {}

    def fake_insert(session, **kwargs):
        captured.update(kwargs)
        return True

    monkeypatch.setattr(ingest_module, "insert_observation", fake_insert)
    monkeypatch.setattr(ingest_module, "enqueue_outbox", lambda *a, **k: 1)

    ingest_envelope(RecordingSession(), envelope)

    assert captured["event_id"] == envelope.event_id
    assert captured["source"] == envelope.source
    assert captured["instrument_ref"] == envelope.instrument_id
    assert captured["rights"] == envelope.rights
    assert captured["quality_status"] == envelope.quality_status.value
    assert captured["delay_status"] == envelope.delay_status.value
    assert captured["payload"] == envelope.payload


def test_duplicate_event_id_enqueues_nothing(monkeypatch, envelope) -> None:
    monkeypatch.setattr(ingest_module, "insert_observation", lambda s, **k: False)

    def fail_enqueue(*args, **kwargs):  # pragma: no cover - must not run
        raise AssertionError("enqueue_outbox must not be called for a duplicate")

    monkeypatch.setattr(ingest_module, "enqueue_outbox", fail_enqueue)
    session = RecordingSession()

    result = ingest_envelope(session, envelope)

    assert result.inserted is False
    assert result.outbox_message_id is None
    # No NOTIFY either: nothing new was written.
    assert session.executed == []


def test_non_envelope_rejected() -> None:
    with pytest.raises(TypeError):
        ingest_envelope(RecordingSession(), {"event_id": "x"})  # type: ignore[arg-type]


def test_calendar_event_enqueues_calendar_and_opportunities(monkeypatch) -> None:
    from vertex_core.synthetic import generate_calendar_event_envelopes

    envelope = generate_calendar_event_envelopes(seed=1, base_time=BASE_TIME)[0]
    monkeypatch.setattr(ingest_module, "insert_observation", lambda s, **k: True)
    enqueues: list[str] = []
    monkeypatch.setattr(
        ingest_module,
        "enqueue_outbox",
        lambda session, topic, payload: enqueues.append(topic) or 1,
    )

    ingest_envelope(RecordingSession(), envelope)

    # Calendar job BEFORE opportunities job: a drained outbox recomputes the
    # calendar snapshot before the opportunities handler reads catalysts.
    assert enqueues == [
        TOPIC_OBSERVATION_INGESTED,
        "calendar.ingested",
        "opportunities.refresh",
        "review_queue.refresh",
    ]


def test_daily_bars_enqueue_analysis_and_opportunities(monkeypatch) -> None:
    from vertex_core.synthetic import generate_daily_bar_envelopes

    envelope = generate_daily_bar_envelopes(seed=1, base_time=BASE_TIME)[0]
    monkeypatch.setattr(ingest_module, "insert_observation", lambda s, **k: True)
    enqueues: list[str] = []
    monkeypatch.setattr(
        ingest_module,
        "enqueue_outbox",
        lambda session, topic, payload: enqueues.append(topic) or 1,
    )

    ingest_envelope(RecordingSession(), envelope)

    assert enqueues == [
        TOPIC_OBSERVATION_INGESTED,
        "analysis.ingested",
        "opportunities.refresh",
        "review_queue.refresh",
    ]
