"""Unit tests of the outbox worker runner (fakes only, no database)."""

from __future__ import annotations

import signal
import threading
import time
from datetime import datetime

import pytest

from vertex_persistence.enums import OutboxStatus
from vertex_worker.errors import HandlerError
from vertex_worker.registry import HandlerRegistry
from vertex_worker.runner import WorkerRunner, WorkerStats

from worker_fakes import (
    FIXED_NOW,
    FakeGateway,
    FakeSessionFactory,
    fixed_clock,
    make_message,
)


def make_runner(registry, gateway, **kwargs):
    defaults = dict(
        session_factory=FakeSessionFactory(),
        registry=registry,
        poll_interval_seconds=0.02,
        clock=fixed_clock,
        gateway=gateway,
    )
    defaults.update(kwargs)
    return WorkerRunner(**defaults)


def make_registry(handler, topic: str = "observation.ingested") -> HandlerRegistry:
    registry = HandlerRegistry()
    registry.register(topic, handler)
    return registry


class TestDispatch:
    def test_dispatches_registered_handler_and_acks(self) -> None:
        seen = []
        registry = make_registry(lambda session, message: seen.append(message))
        gateway = FakeGateway()
        gateway.pending = [[make_message(1), make_message(2)]]
        runner = make_runner(registry, gateway)

        assert runner.run_once() == 2
        assert [m.id for m in seen] == [1, 2]
        assert gateway.acked == [1, 2]
        stats = runner.stats()
        assert stats == WorkerStats(
            batches=1, claimed=2, acked=2, failed=0, dead=0, lease_lost=0
        )

    def test_claims_only_registered_topics(self) -> None:
        registry = HandlerRegistry()
        registry.register("b.topic", lambda s, m: None)
        registry.register("a.topic", lambda s, m: None)
        gateway = FakeGateway()
        runner = make_runner(registry, gateway)
        runner.run_once()
        assert gateway.claim_calls[0]["topics"] == ("a.topic", "b.topic")
        assert gateway.claim_calls[0]["now"] == FIXED_NOW

    def test_claim_transaction_committed_before_processing(self) -> None:
        factory = FakeSessionFactory()
        registry = make_registry(lambda s, m: None)
        gateway = FakeGateway()
        gateway.pending = [[make_message(1)]]
        runner = make_runner(registry, gateway, session_factory=factory)
        runner.run_once()
        # First session is the claim transaction: committed and closed.
        assert factory.sessions[0].committed == 1
        assert factory.sessions[0].closed is True
        # Second session carries handler + ack in ONE transaction.
        assert factory.sessions[1].committed == 1

    def test_empty_claim_returns_zero_without_counting_a_batch(self) -> None:
        runner = make_runner(make_registry(lambda s, m: None), FakeGateway())
        assert runner.run_once() == 0
        assert runner.stats().batches == 0

    def test_unregistered_topic_fails_with_explicit_code(self) -> None:
        registry = make_registry(lambda s, m: None, topic="observation.ingested")
        gateway = FakeGateway()
        gateway.pending = [[make_message(7, topic="unknown.topic")]]
        runner = make_runner(registry, gateway)
        # The runner claims only registered topics; a foreign topic is a
        # registry/claim divergence and must be failed, never dropped.
        runner._process_one(make_message(7, topic="unknown.topic"))
        assert gateway.failed[0]["code"] == "UNREGISTERED_TOPIC"


class TestFailurePath:
    def test_handler_error_fails_with_its_code(self) -> None:
        def handler(session, message):
            raise HandlerError("boom", code="FUSION_INPUT_INVALID")

        gateway = FakeGateway()
        gateway.pending = [[make_message(3)]]
        runner = make_runner(make_registry(handler), gateway)
        runner.run_once()
        assert gateway.acked == []
        assert gateway.failed == [
            {
                "message_id": 3,
                "exc_type": "HandlerError",
                "code": "FUSION_INPUT_INVALID",
                "max_attempts": 8,
            }
        ]
        stats = runner.stats()
        assert (stats.failed, stats.dead, stats.acked) == (1, 0, 0)

    def test_generic_exception_uses_generic_code(self) -> None:
        def handler(session, message):
            raise ValueError("unexpected")

        gateway = FakeGateway()
        gateway.pending = [[make_message(4)]]
        runner = make_runner(make_registry(handler), gateway)
        runner.run_once()
        assert gateway.failed[0]["code"] == "HANDLER_EXCEPTION"

    def test_dead_status_is_counted(self) -> None:
        def handler(session, message):
            raise HandlerError("boom", code="ALWAYS_FAILS")

        gateway = FakeGateway()
        gateway.fail_status = OutboxStatus.DEAD.value
        gateway.pending = [[make_message(5)]]
        runner = make_runner(make_registry(handler), gateway)
        runner.run_once()
        stats = runner.stats()
        assert (stats.failed, stats.dead) == (1, 1)

    def test_max_attempts_is_forwarded(self) -> None:
        def handler(session, message):
            raise HandlerError("boom", code="ALWAYS_FAILS")

        gateway = FakeGateway()
        gateway.pending = [[make_message(6)]]
        runner = make_runner(make_registry(handler), gateway, max_attempts=2)
        runner.run_once()
        assert gateway.failed[0]["max_attempts"] == 2

    def test_lease_lost_on_ack_is_counted_not_crashed(self) -> None:
        gateway = FakeGateway()
        gateway.lease_error_on_ack = {8}
        gateway.pending = [[make_message(8)]]
        runner = make_runner(make_registry(lambda s, m: None), gateway)
        runner.run_once()
        stats = runner.stats()
        assert (stats.acked, stats.failed, stats.lease_lost) == (0, 0, 1)

    def test_lease_lost_on_fail_is_counted_not_crashed(self) -> None:
        def handler(session, message):
            raise HandlerError("boom", code="ALWAYS_FAILS")

        gateway = FakeGateway()
        gateway.lease_error_on_fail = {9}
        gateway.pending = [[make_message(9)]]
        runner = make_runner(make_registry(handler), gateway)
        runner.run_once()
        stats = runner.stats()
        assert (stats.failed, stats.lease_lost) == (0, 1)

    def test_keyboard_interrupt_is_never_swallowed(self) -> None:
        def handler(session, message):
            raise KeyboardInterrupt()

        gateway = FakeGateway()
        gateway.pending = [[make_message(10)]]
        runner = make_runner(make_registry(handler), gateway)
        with pytest.raises(KeyboardInterrupt):
            runner.run_once()
        assert gateway.failed == []

    def test_one_failure_does_not_stop_the_batch(self) -> None:
        def handler(session, message):
            if message.id == 2:
                raise HandlerError("boom", code="ALWAYS_FAILS")

        gateway = FakeGateway()
        gateway.pending = [[make_message(1), make_message(2), make_message(3)]]
        runner = make_runner(make_registry(handler), gateway)
        runner.run_once()
        assert gateway.acked == [1, 3]
        assert [f["message_id"] for f in gateway.failed] == [2]


class TestClockValidation:
    def test_naive_clock_is_rejected(self) -> None:
        runner = make_runner(
            make_registry(lambda s, m: None),
            FakeGateway(),
            clock=lambda: datetime(2026, 8, 25, 12, 0, 0),
        )
        with pytest.raises(ValueError):
            runner.run_once()


class TestShutdown:
    def test_signal_handler_requests_stop(self) -> None:
        runner = make_runner(make_registry(lambda s, m: None), FakeGateway())
        assert runner.stop_requested is False
        runner._on_signal(signal.SIGTERM, None)
        assert runner.stop_requested is True

    def test_install_signal_handlers_registers_both(self) -> None:
        runner = make_runner(make_registry(lambda s, m: None), FakeGateway())
        previous_term = signal.getsignal(signal.SIGTERM)
        previous_int = signal.getsignal(signal.SIGINT)
        try:
            runner.install_signal_handlers()
            assert signal.getsignal(signal.SIGTERM) == runner._on_signal
            assert signal.getsignal(signal.SIGINT) == runner._on_signal
        finally:
            signal.signal(signal.SIGTERM, previous_term)
            signal.signal(signal.SIGINT, previous_int)

    def test_stop_mid_batch_finishes_current_batch_then_exits(self) -> None:
        processed = []

        def handler(session, message):
            processed.append(message.id)
            if message.id == 1:
                runner.request_stop()

        gateway = FakeGateway()
        gateway.pending = [[make_message(1), make_message(2), make_message(3)]]
        registry = make_registry(handler)
        runner = make_runner(registry, gateway)
        runner.run()  # returns because stop was requested during the batch
        # The whole claimed batch is finished before exiting.
        assert processed == [1, 2, 3]
        assert gateway.acked == [1, 2, 3]

    def test_run_exits_promptly_when_stop_requested_while_idle(self) -> None:
        runner = make_runner(make_registry(lambda s, m: None), FakeGateway())
        thread = threading.Thread(target=runner.run)
        thread.start()
        time.sleep(0.05)
        runner.request_stop()
        thread.join(timeout=2.0)
        assert not thread.is_alive()


class TestPollingAndWake:
    def test_polling_delivers_without_any_notify(self) -> None:
        """NOTIFY loss is tolerated: polling alone finds new messages."""
        gateway = FakeGateway()
        registry = make_registry(lambda s, m: None)
        runner = make_runner(registry, gateway, poll_interval_seconds=0.02)
        thread = threading.Thread(target=runner.run)
        thread.start()
        try:
            time.sleep(0.05)  # runner is idle-polling now
            gateway.pending.append([make_message(11)])
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline and runner.stats().acked < 1:
                time.sleep(0.01)
            assert runner.stats().acked == 1
        finally:
            runner.request_stop()
            thread.join(timeout=2.0)
        assert not thread.is_alive()

    def test_wake_interrupts_long_poll_interval(self) -> None:
        gateway = FakeGateway()
        registry = make_registry(lambda s, m: None)
        runner = make_runner(registry, gateway, poll_interval_seconds=30.0)
        thread = threading.Thread(target=runner.run)
        thread.start()
        try:
            time.sleep(0.05)  # runner sleeps on the 30 s poll interval
            gateway.pending.append([make_message(12)])
            runner.wake()
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline and runner.stats().acked < 1:
                time.sleep(0.01)
            assert runner.stats().acked == 1
        finally:
            runner.request_stop()
            thread.join(timeout=2.0)
        assert not thread.is_alive()


class TestDrain:
    def test_drain_is_bounded_and_returns_total(self) -> None:
        gateway = FakeGateway()
        gateway.pending = [[make_message(1)], [make_message(2)], [make_message(3)]]
        runner = make_runner(make_registry(lambda s, m: None), gateway)
        assert runner.drain(max_batches=2) == 2
        assert runner.stats().acked == 2

    def test_drain_stops_on_empty_outbox(self) -> None:
        gateway = FakeGateway()
        gateway.pending = [[make_message(1)]]
        runner = make_runner(make_registry(lambda s, m: None), gateway)
        assert runner.drain(max_batches=50) == 1
        # One claim for the batch, one finding the outbox empty.
        assert len(gateway.claim_calls) == 2

    def test_drain_rejects_invalid_bound(self) -> None:
        runner = make_runner(make_registry(lambda s, m: None), FakeGateway())
        with pytest.raises(ValueError):
            runner.drain(max_batches=0)


class TestConstructionValidation:
    def test_empty_registry_rejected(self) -> None:
        with pytest.raises(ValueError):
            WorkerRunner(
                session_factory=FakeSessionFactory(),
                registry=HandlerRegistry(),
                gateway=FakeGateway(),
            )

    def test_stats_returns_immutable_snapshot(self) -> None:
        runner = make_runner(make_registry(lambda s, m: None), FakeGateway())
        stats = runner.stats()
        with pytest.raises(AttributeError):
            stats.acked = 99  # type: ignore[misc]
