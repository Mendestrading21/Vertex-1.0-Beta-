"""Integration tests of wake-up semantics: polling is the guarantee,
LISTEN/NOTIFY is only an accelerator whose loss is tolerated by design."""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime

from vertex_core.synthetic import generate_envelopes
from vertex_worker.handlers import DEV_SYNTHETIC_CONFIG, build_registry
from vertex_worker.ingest import OUTBOX_NOTIFY_CHANNEL, ingest_envelope
from vertex_worker.runner import (
    PostgresNotifyListener,
    WorkerRunner,
    sqlalchemy_url_to_conninfo,
)

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)


def _wait_for(predicate, timeout_seconds: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def _make_runner(session_factory, *, poll_interval_seconds: float) -> WorkerRunner:
    clock = lambda: NOW  # noqa: E731 - deterministic injected clock
    registry = build_registry(clock=clock, fusion_config=DEV_SYNTHETIC_CONFIG)
    return WorkerRunner(
        session_factory=session_factory,
        registry=registry,
        poll_interval_seconds=poll_interval_seconds,
        clock=clock,
    )


def _ingest_one(session_factory) -> None:
    envelope = generate_envelopes(seed=7, count=1, base_time=NOW)[0]
    with session_factory() as session:
        result = ingest_envelope(session, envelope)
        assert result.inserted is True
        session.commit()  # NOTIFY (if anyone listens) fires here


def test_polling_alone_delivers_lost_notifications(session_factory) -> None:
    """No listener at all: every NOTIFY is lost, polling still delivers."""
    runner = _make_runner(session_factory, poll_interval_seconds=0.1)
    thread = threading.Thread(target=runner.run)
    thread.start()
    try:
        time.sleep(0.15)  # the runner is already idle-polling
        _ingest_one(session_factory)
        assert _wait_for(lambda: runner.stats().acked >= 1)
    finally:
        runner.request_stop()
        thread.join(timeout=5.0)
    assert not thread.is_alive()
    assert runner.stats().failed == 0


def test_notify_listener_wakes_a_long_poll(session_factory, database_url) -> None:
    """With a long poll interval, the NOTIFY listener wakes the runner early."""
    runner = _make_runner(session_factory, poll_interval_seconds=30.0)
    listener = PostgresNotifyListener(
        conninfo=sqlalchemy_url_to_conninfo(database_url),
        channel=OUTBOX_NOTIFY_CHANNEL,
        on_notify=runner.wake,
        poll_timeout_seconds=0.2,
    )
    thread = threading.Thread(target=runner.run)
    listener.start()
    thread.start()
    try:
        time.sleep(0.3)  # runner sleeps on its 30 s interval; listener is up
        started = time.monotonic()
        _ingest_one(session_factory)
        assert _wait_for(lambda: runner.stats().acked >= 1)
        # Far faster than the 30 s poll interval: the wake-up worked.
        assert time.monotonic() - started < 15.0
        assert listener.failed is False
    finally:
        runner.request_stop()
        listener.stop()
        thread.join(timeout=5.0)
    assert not thread.is_alive()
