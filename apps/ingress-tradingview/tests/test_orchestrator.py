"""Orchestrator tests: idempotence, ack-after-persist, revalidation, deadline.

Every dependency (queue, store, quote provider, clock, epoch) is a synthetic
fake — no network, no real clock, no real market data.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone

import pytest

from conftest import (
    FakeQueueClient,
    FakeQuoteProvider,
    FakeStore,
    FixedClock,
    fresh_quote,
    make_alert_payload,
    make_envelope_body,
    make_message,
)
from vertex_ingress_tv.orchestrator import (
    IngressRejection,
    Quote,
    TradingViewOrchestrator,
    TriggerState,
)

EVENT_ID = "syn-market-regime-v1:1787999700000"


@pytest.fixture
def queue() -> FakeQueueClient:
    return FakeQueueClient()


@pytest.fixture
def store() -> FakeStore:
    return FakeStore()


@pytest.fixture
def quotes() -> FakeQuoteProvider:
    return FakeQuoteProvider()


@pytest.fixture
def audit() -> list:
    return []


@pytest.fixture
def orchestrator(queue, store, quotes, registry, clock, audit) -> TradingViewOrchestrator:
    return TradingViewOrchestrator(
        queue=queue,
        store=store,
        quote_provider=quotes,
        registry=registry,
        clock=clock,
        epoch_provider=lambda: 1,
        audit_sink=audit.append,
        sent_at_window=timedelta(seconds=300),
        revalidation_deadline=timedelta(seconds=10.0),
    )


class TestIngestHappyPath:
    def test_valid_message_persisted_then_acked(self, orchestrator, queue, store) -> None:
        queue.push(make_message("msg-1"))
        outcomes = orchestrator.pull_and_ingest()
        assert [o.status for o in outcomes] == ["PERSISTED"]
        assert outcomes[0].event_id == EVENT_ID
        assert queue.is_acked("msg-1")
        assert EVENT_ID in store.records
        assert store.state_history(EVENT_ID) == [
            TriggerState.PERSISTED,
            TriggerState.WAITING_FOR_IBKR,
        ]

    def test_persisted_record_keeps_provenance_and_marks_price_non_authoritative(
        self, orchestrator, queue, store
    ) -> None:
        queue.push(make_message("msg-1"))
        orchestrator.pull_and_ingest()
        record = store.records[EVENT_ID]
        assert record["price_context"]["authoritative"] is False
        assert record["price_context"]["value"] == "123.45"
        assert record["authoritative_market_data"] is False
        assert record["received_at"] == "2026-08-29T11:59:59+00:00"
        assert record["signal"] == "REGIME_CHANGE"
        assert record["event_id"] == EVENT_ID


class TestIdempotence:
    def test_100_redeliveries_produce_exactly_one_signal(self, orchestrator, queue, store) -> None:
        for i in range(100):
            queue.push(make_message(f"msg-{i}"))
        outcomes = orchestrator.pull_and_ingest(max_messages=100)
        statuses = [o.status for o in outcomes]
        assert statuses.count("PERSISTED") == 1
        assert statuses.count("DUPLICATE") == 99
        assert len(store.records) == 1
        assert len(queue.acked) == 100  # every delivery acked, one signal kept

    def test_out_of_order_and_interleaved_deliveries(self, orchestrator, queue, store) -> None:
        rng = random.Random(20260829)  # seeded: no unseeded randomness in tests
        messages = []
        for n in range(5):
            alert = make_alert_payload(values={"nonce": f"178799970000{n}"})
            # three redeliveries of each distinct event, shuffled
            for r in range(3):
                messages.append(make_message(f"msg-{n}-{r}", alert))
        rng.shuffle(messages)
        for message in messages:
            queue.push(message)
        outcomes = orchestrator.pull_and_ingest(max_messages=50)
        assert len(store.records) == 5
        assert [o.status for o in outcomes].count("PERSISTED") == 5
        assert [o.status for o in outcomes].count("DUPLICATE") == 10

    def test_duplicate_never_resets_a_terminal_state(
        self, orchestrator, queue, store, quotes, clock
    ) -> None:
        queue.push(make_message("msg-1"))
        orchestrator.pull_and_ingest()
        quotes.responses = [fresh_quote(clock)]
        orchestrator.advance_pending()
        assert store.get_state(EVENT_ID) is TriggerState.REVALIDATED
        queue.push(make_message("msg-2"))
        outcomes = orchestrator.pull_and_ingest()
        assert [o.status for o in outcomes] == ["DUPLICATE"]
        assert store.get_state(EVENT_ID) is TriggerState.REVALIDATED
        assert orchestrator.pending_event_ids() == []


class TestAckAfterPersistence:
    def test_crash_before_persistence_leaves_message_unacked(
        self, orchestrator, queue, store
    ) -> None:
        store.fail_persist_with = RuntimeError("synthetic crash before commit")
        queue.push(make_message("msg-1"))
        outcomes = orchestrator.pull_and_ingest()
        assert [o.status for o in outcomes] == ["PERSIST_FAILED"]
        assert not queue.is_acked("msg-1")
        assert store.records == {}

        # Store heals: the SAME redelivered message is persisted and acked.
        store.fail_persist_with = None
        outcomes = orchestrator.pull_and_ingest()
        assert [o.status for o in outcomes] == ["PERSISTED"]
        assert queue.is_acked("msg-1")
        assert EVENT_ID in store.records

    def test_redelivery_after_crash_between_persist_and_ack(self, queue, store, quotes, registry, clock, audit) -> None:
        # First run persists but "crashes" before ack (we simply drop the
        # orchestrator without acking).
        first = TradingViewOrchestrator(
            queue=queue,
            store=store,
            quote_provider=quotes,
            registry=registry,
            clock=clock,
            epoch_provider=lambda: 1,
            audit_sink=audit.append,
        )
        queue.push(make_message("msg-1"))
        # Simulate the crash: persist happened, ack did not.
        store.persist_signal(EVENT_ID, {"event_id": EVENT_ID})
        store.set_state(EVENT_ID, TriggerState.PERSISTED, None)
        store.set_state(EVENT_ID, TriggerState.WAITING_FOR_IBKR, None)

        outcomes = first.pull_and_ingest()
        # Redelivery is recognized as duplicate, acked, and re-attached for
        # revalidation instead of being lost.
        assert [o.status for o in outcomes] == ["DUPLICATE"]
        assert queue.is_acked("msg-1")
        assert first.pending_event_ids() == [EVENT_ID]


class TestRejections:
    def push_and_ingest(self, orchestrator, queue, body=None, alert=None, **kwargs):
        queue.push(make_message("msg-r", alert, body=body, **kwargs))
        return orchestrator.pull_and_ingest()

    def test_forged_alert_rejected_acked_not_persisted(
        self, orchestrator, queue, store, audit
    ) -> None:
        forged = make_alert_payload(signal="BUY_NOW")  # not a valid enum value
        outcomes = self.push_and_ingest(orchestrator, queue, alert=forged)
        assert [o.status for o in outcomes] == ["REJECTED"]
        assert outcomes[0].reason == "contract_violation"
        assert store.records == {}
        assert queue.is_acked("msg-r")  # poison messages do not loop forever
        assert len(audit) == 1
        assert isinstance(audit[0], IngressRejection)

    def test_alert_without_nonce_rejected(self, orchestrator, queue, store, audit) -> None:
        outcomes = self.push_and_ingest(
            orchestrator, queue, alert=make_alert_payload(values={"volume": "1"})
        )
        assert [o.status for o in outcomes] == ["REJECTED"]
        assert store.records == {}

    def test_old_alert_rejected(self, orchestrator, queue, store, audit) -> None:
        old = make_alert_payload(sent_at="2026-08-29T10:00:00Z")  # ~2h before receipt
        outcomes = self.push_and_ingest(orchestrator, queue, alert=old)
        assert [o.status for o in outcomes] == ["REJECTED"]
        assert outcomes[0].reason == "sent_at_too_old"
        assert len(audit) == 1

    def test_future_alert_rejected(self, orchestrator, queue, store, audit) -> None:
        future = make_alert_payload(sent_at="2026-08-29T13:00:00Z")
        outcomes = self.push_and_ingest(orchestrator, queue, alert=future)
        assert [o.status for o in outcomes] == ["REJECTED"]
        assert outcomes[0].reason == "sent_at_in_future"

    def test_oversize_alert_rejected(self, orchestrator, queue, store, audit) -> None:
        big = make_alert_payload(values={"nonce": "1787999700000", "pad": "x" * 17000})
        outcomes = self.push_and_ingest(orchestrator, queue, alert=big)
        assert [o.status for o in outcomes] == ["REJECTED"]
        assert outcomes[0].reason == "oversize_payload"

    def test_unknown_envelope_schema_rejected(self, orchestrator, queue, store, audit) -> None:
        body = make_envelope_body(schema="vertex.tradingview.queue-envelope.v9")
        outcomes = self.push_and_ingest(orchestrator, queue, body=body)
        assert [o.status for o in outcomes] == ["REJECTED"]
        assert outcomes[0].reason == "unknown_envelope_schema"

    def test_envelope_without_received_at_rejected(self, orchestrator, queue, audit) -> None:
        envelope = json.loads(make_envelope_body().decode())
        del envelope["received_at"]
        outcomes = self.push_and_ingest(
            orchestrator, queue, body=json.dumps(envelope).encode()
        )
        assert [o.status for o in outcomes] == ["REJECTED"]
        assert outcomes[0].reason == "missing_received_at"

    def test_invalid_envelope_json_rejected(self, orchestrator, queue, audit) -> None:
        outcomes = self.push_and_ingest(orchestrator, queue, body=b"{broken")
        assert [o.status for o in outcomes] == ["REJECTED"]
        assert outcomes[0].reason == "invalid_envelope_json"

    def test_registry_unknown_alert_rejected_and_audited(
        self, orchestrator, queue, store, registry_audit
    ) -> None:
        outcomes = self.push_and_ingest(
            orchestrator, queue, alert=make_alert_payload(alert_id="forged-unknown-v1")
        )
        assert [o.status for o in outcomes] == ["REJECTED"]
        assert outcomes[0].reason == "registry:UNKNOWN_ALERT_ID"
        assert store.records == {}
        assert len(registry_audit) == 1  # auditable through the registry sink

    def test_registry_unexpected_version_rejected_and_audited(
        self, orchestrator, queue, store, registry_audit
    ) -> None:
        outcomes = self.push_and_ingest(
            orchestrator, queue, alert=make_alert_payload(script_version="2026-08-30.9")
        )
        assert [o.status for o in outcomes] == ["REJECTED"]
        assert outcomes[0].reason == "registry:UNEXPECTED_SCRIPT_VERSION"
        assert store.records == {}
        assert registry_audit[0].observed_script_version == "2026-08-30.9"

    def test_rejection_audit_never_contains_payload_body(
        self, orchestrator, queue, audit
    ) -> None:
        self.push_and_ingest(
            orchestrator, queue, alert=make_alert_payload(price="31415.92653x")
        )
        assert len(audit) == 1
        serialized = f"{audit[0].reason_code}|{audit[0].detail}"
        assert "31415.92653" not in serialized


class TestRevalidation:
    def ingest_one(self, orchestrator, queue) -> None:
        queue.push(make_message("msg-1"))
        assert [o.status for o in orchestrator.pull_and_ingest()] == ["PERSISTED"]

    def test_fresh_quote_current_epoch_revalidates(
        self, orchestrator, queue, store, quotes, clock
    ) -> None:
        self.ingest_one(orchestrator, queue)
        quotes.responses = [fresh_quote(clock, epoch=1)]
        outcomes = orchestrator.advance_pending()
        assert [o.status for o in outcomes] == ["REVALIDATED"]
        assert store.get_state(EVENT_ID) is TriggerState.REVALIDATED
        assert "epoch=1" in store.last_reason(EVENT_ID)
        assert quotes.calls == [("SYNTH", "FAKE")]

    def test_quote_observed_before_trigger_blocks(
        self, orchestrator, queue, store, quotes
    ) -> None:
        self.ingest_one(orchestrator, queue)
        stale = Quote(
            observed_at=datetime(2026, 8, 29, 11, 59, 30, tzinfo=timezone.utc),  # < received_at
            connection_epoch=1,
        )
        quotes.responses = [stale]
        outcomes = orchestrator.advance_pending()
        assert [o.status for o in outcomes] == ["BLOCKED"]
        assert outcomes[0].reason == "QUOTE_OBSERVED_BEFORE_TRIGGER"
        assert store.get_state(EVENT_ID) is TriggerState.BLOCKED

    def test_quote_from_old_epoch_blocks(self, orchestrator, queue, store, quotes, clock) -> None:
        self.ingest_one(orchestrator, queue)
        quotes.responses = [fresh_quote(clock, epoch=0)]  # current epoch is 1
        outcomes = orchestrator.advance_pending()
        assert [o.status for o in outcomes] == ["BLOCKED"]
        assert outcomes[0].reason == "STALE_CONNECTION_EPOCH"
        assert store.get_state(EVENT_ID) is TriggerState.BLOCKED

    def test_naive_quote_timestamp_blocks_fail_closed(
        self, orchestrator, queue, store, quotes
    ) -> None:
        self.ingest_one(orchestrator, queue)
        quotes.responses = [Quote(observed_at=datetime(2026, 8, 29, 12, 0, 5), connection_epoch=1)]
        outcomes = orchestrator.advance_pending()
        assert [o.status for o in outcomes] == ["BLOCKED"]
        assert outcomes[0].reason == "QUOTE_TIMESTAMP_NAIVE"

    def test_no_quote_keeps_waiting_before_deadline(
        self, orchestrator, queue, store, quotes, clock
    ) -> None:
        self.ingest_one(orchestrator, queue)
        quotes.responses = [None]
        clock.advance(3)
        outcomes = orchestrator.advance_pending()
        assert [o.status for o in outcomes] == ["WAITING"]
        assert store.get_state(EVENT_ID) is TriggerState.WAITING_FOR_IBKR
        assert orchestrator.pending_event_ids() == [EVENT_ID]

    def test_expired_at_deadline_without_quote(
        self, orchestrator, queue, store, quotes, clock
    ) -> None:
        self.ingest_one(orchestrator, queue)
        quotes.responses = [None]
        # Deadline anchors on received_at (11:59:59) + 10 s.
        clock.now = datetime(2026, 8, 29, 12, 0, 9, tzinfo=timezone.utc)
        outcomes = orchestrator.advance_pending()
        assert [o.status for o in outcomes] == ["EXPIRED"]
        assert outcomes[0].reason == "IBKR_QUOTE_DEADLINE_EXCEEDED"
        assert store.get_state(EVENT_ID) is TriggerState.EXPIRED
        assert orchestrator.pending_event_ids() == []

    def test_expired_is_terminal_and_never_a_verdict(
        self, orchestrator, queue, store, quotes, clock
    ) -> None:
        self.ingest_one(orchestrator, queue)
        quotes.responses = [fresh_quote(clock, epoch=1)]
        clock.advance(30)  # past the deadline: the late quote must NOT rescue it
        outcomes = orchestrator.advance_pending()
        assert [o.status for o in outcomes] == ["EXPIRED"]
        # EXPIRED is an ingress status: no advice, no direction, no score is
        # produced anywhere by the orchestrator.
        record = store.records[EVENT_ID]
        for forbidden in ("advice", "verdict", "direction", "score", "probability"):
            assert forbidden not in record
        # And a later advance does nothing (trigger left the pending set).
        assert orchestrator.advance_pending() == []

    def test_deadline_boundary_is_exclusive_before(self, orchestrator, queue, store, quotes, clock) -> None:
        self.ingest_one(orchestrator, queue)
        quotes.responses = [fresh_quote(clock, epoch=1)]
        # 1 ms before the deadline: still eligible for revalidation.
        clock.now = datetime(2026, 8, 29, 12, 0, 8, 999000, tzinfo=timezone.utc)
        outcomes = orchestrator.advance_pending()
        assert [o.status for o in outcomes] == ["REVALIDATED"]


class TestConstruction:
    def test_non_positive_deadline_refused(self, queue, store, quotes, registry, clock) -> None:
        with pytest.raises(ValueError):
            TradingViewOrchestrator(
                queue=queue,
                store=store,
                quote_provider=quotes,
                registry=registry,
                clock=clock,
                epoch_provider=lambda: 1,
                audit_sink=lambda r: None,
                revalidation_deadline=timedelta(0),
            )

    def test_naive_clock_is_refused_at_ingest(self, queue, store, quotes, registry) -> None:
        naive_clock = lambda: datetime(2026, 8, 29, 12, 0, 0)  # noqa: E731
        orchestrator = TradingViewOrchestrator(
            queue=queue,
            store=store,
            quote_provider=quotes,
            registry=registry,
            clock=naive_clock,
            epoch_provider=lambda: 1,
            audit_sink=lambda r: None,
        )
        queue.push(make_message("msg-1"))
        with pytest.raises(Exception):
            orchestrator.pull_and_ingest()
