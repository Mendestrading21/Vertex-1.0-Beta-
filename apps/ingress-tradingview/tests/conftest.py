"""Fakes and builders for the ingress tests (SYNTHETIC data only).

No network, no real clock, no real market data: every fixture is fabricated,
deterministic and clearly synthetic. Nothing here may cross a production
boundary.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from vertex_ingress_tv.orchestrator import (
    QUEUE_ENVELOPE_SCHEMA_ID,
    QueueMessage,
    Quote,
    TriggerState,
)
from vertex_ingress_tv.registry import AlertRegistry, RegisteredAlert, RegistryRejection

# Deterministic synthetic instants.
T0 = datetime(2026, 8, 29, 12, 0, 0, tzinfo=UTC)


class FixedClock:
    """Injected clock: starts at ``start`` and only moves when told to."""

    def __init__(self, start: datetime = T0) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now = self.now + timedelta(seconds=seconds)


class FakeQueueClient:
    """In-memory queue with redelivery of un-acked messages."""

    def __init__(self) -> None:
        self._messages: list[QueueMessage] = []
        self.acked: list[str] = []

    def push(self, message: QueueMessage) -> None:
        self._messages.append(message)

    def pull(self, max_messages: int) -> Sequence[QueueMessage]:
        pending = [m for m in self._messages if m.message_id not in self.acked]
        return pending[:max_messages]

    def ack(self, message_id: str) -> None:
        self.acked.append(message_id)

    def is_acked(self, message_id: str) -> bool:
        return message_id in self.acked


class FakeStore:
    """Idempotent in-memory store with injectable failure (SYNTHETIC)."""

    def __init__(self) -> None:
        self.records: dict[str, Mapping[str, Any]] = {}
        self.states: dict[str, list[tuple]] = {}
        self.persist_calls = 0
        self.fail_persist_with: Exception | None = None

    def persist_signal(self, event_id: str, record: Mapping[str, Any]) -> bool:
        self.persist_calls += 1
        if self.fail_persist_with is not None:
            raise self.fail_persist_with
        if event_id in self.records:
            return False
        self.records[event_id] = dict(record)
        return True

    def set_state(self, event_id: str, state: TriggerState, reason: str | None) -> None:
        self.states.setdefault(event_id, []).append((state, reason))

    def get_state(self, event_id: str) -> TriggerState | None:
        history = self.states.get(event_id)
        return history[-1][0] if history else None

    def state_history(self, event_id: str) -> list[TriggerState]:
        return [state for state, _ in self.states.get(event_id, [])]

    def last_reason(self, event_id: str) -> str | None:
        history = self.states.get(event_id)
        return history[-1][1] if history else None


class FakeQuoteProvider:
    """Returns a scripted sequence of quotes (then repeats the last entry)."""

    def __init__(self, responses: list[Quote | None] | None = None) -> None:
        self.responses: list[Quote | None] = list(responses or [])
        self.calls: list[tuple] = []

    def get_quote(self, exchange: str, ticker: str) -> Quote | None:
        self.calls.append((exchange, ticker))
        if not self.responses:
            return None
        if len(self.responses) == 1:
            return self.responses[0]
        return self.responses.pop(0)


def make_alert_payload(**overrides: Any) -> dict[str, Any]:
    """Complete, contract-valid synthetic alert payload."""
    payload: dict[str, Any] = {
        "schema": "vertex.tradingview.alert.v1",
        "alert_id": "syn-market-regime-v1",
        "script_version": "2026-08-29.1",
        "sent_at": "2026-08-29T11:59:30Z",
        "bar_time": "2026-08-29T11:55:00Z",
        "exchange": "SYNTH",
        "ticker": "FAKE",
        "interval": "5",
        "signal": "REGIME_CHANGE",
        "price": "123.45",
        "values": {"nonce": "1787999700000", "volume": "1000"},
    }
    payload.update(overrides)
    return payload


def make_envelope_body(
    alert: Mapping[str, Any] | None = None,
    *,
    received_at: str = "2026-08-29T11:59:59Z",
    schema: str = QUEUE_ENVELOPE_SCHEMA_ID,
) -> bytes:
    alert = dict(alert) if alert is not None else make_alert_payload()
    envelope = {
        "schema": schema,
        "event_id": f"{alert.get('alert_id', '?')}:{(alert.get('values') or {}).get('nonce', '?')}",
        "received_at": received_at,
        "alert": alert,
    }
    return json.dumps(envelope).encode("utf-8")


def make_message(
    message_id: str = "msg-1",
    alert: Mapping[str, Any] | None = None,
    *,
    received_at: str = "2026-08-29T11:59:59Z",
    body: bytes | None = None,
) -> QueueMessage:
    if body is None:
        body = make_envelope_body(alert, received_at=received_at)
    return QueueMessage(message_id=message_id, body=body)


def fresh_quote(clock: FixedClock, *, epoch: int = 1, offset_seconds: float = 1.0) -> Quote:
    return Quote(observed_at=clock.now + timedelta(seconds=offset_seconds), connection_epoch=epoch)


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock()


@pytest.fixture
def registry_audit() -> list[RegistryRejection]:
    return []


@pytest.fixture
def registry(clock: FixedClock, registry_audit: list[RegistryRejection]) -> AlertRegistry:
    entries = [
        RegisteredAlert(
            alert_id="syn-market-regime-v1",
            expected_script_version="2026-08-29.1",
            expected_exchange="SYNTH",
            expected_ticker="FAKE",
            expected_interval="5",
        ),
        RegisteredAlert(alert_id="syn-macro-cpi-v1", expected_script_version="2026-08-29.1"),
        RegisteredAlert(
            alert_id="syn-revoked-v1", expected_script_version="2026-08-29.1", active=False
        ),
    ]
    return AlertRegistry(entries, clock=clock, audit_sink=registry_audit.append)
