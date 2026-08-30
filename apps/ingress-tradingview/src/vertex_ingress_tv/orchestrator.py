"""Local orchestration of TradingView triggers (LOT-05, socle local).

State machine, per trigger (``event_id = alert_id + ":" + nonce``)::

    RECEIVED -> PERSISTED -> WAITING_FOR_IBKR -> REVALIDATED
                                             -> BLOCKED  (reasoned)
                                             -> EXPIRED  (HP-02 deadline)

Guarantees (all fail-closed):

- messages are pulled from an injected :class:`QueueClient` (fakes in tests);
- the envelope ``received_at`` is stamped by the Cloudflare Worker and travels
  on the wire, so it is EXTERNAL input: it is bounded against the injected
  ingress clock before anything is anchored on it. Beyond
  ``max_received_at_skew`` ahead it is ``received_at_in_future``; beyond
  ``max_received_at_age`` behind it is ``received_at_too_old``. Without that
  bound both the HP-02 deadline and the anti-replay window would be anchored
  on a value nobody local controls, hence self-referential and inert;
- persistence is idempotent through an injected :class:`SignalStore` keyed by
  ``event_id``: 100 redeliveries of the same alert produce exactly ONE signal;
- a message is acknowledged ONLY after the store confirmed persistence; a
  crash/failure before persistence leaves the message un-acked for redelivery;
- revalidation requires a fresh IBKR quote with ``observed_at >=
  trigger.received_at``, ``observed_at`` no further ahead of the ingress clock
  than ``max_received_at_skew``, AND the CURRENT connection epoch; anything
  else is ``BLOCKED`` with an explicit reason;
- past the HP-02 deadline (10 s by default, injected) without a quote the
  trigger becomes ``EXPIRED``. ``EXPIRED`` is a terminal ingress status and
  NEVER a verdict: this module produces no ``AdviceResult``, no direction, no
  score — the downstream deterministic pipeline owns those, after its own
  quality gates;
- the alert is NEVER a price proof: the transported price is persisted only as
  explicitly non-authoritative context (``price_context.authoritative=False``).

No wall clock, no network, no logging of payload bodies: clock, epoch, queue,
store and quote provider are all injected.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum, unique
from typing import Any, Callable, Dict, List, Mapping, Optional, Protocol, Sequence

from vertex_ingress_tv.registry import AlertRegistry
from vertex_ingress_tv.schema import (
    MAX_PAYLOAD_BYTES,
    AlertRejected,
    TradingViewAlertV1,
    ensure_sent_at_in_window,
    parse_alert,
)

__all__ = [
    "DEFAULT_MAX_RECEIVED_AT_AGE",
    "DEFAULT_MAX_RECEIVED_AT_SKEW",
    "QUEUE_ENVELOPE_SCHEMA_ID",
    "IngestOutcome",
    "IngressRejection",
    "Quote",
    "QueueClient",
    "QueueMessage",
    "QuoteProvider",
    "SignalStore",
    "TradingViewOrchestrator",
    "TriggerState",
]

QUEUE_ENVELOPE_SCHEMA_ID = "vertex.tradingview.queue-envelope.v1"

#: HP-02 (docs/06-quality/DATA_LATENCY_BUDGETS.md): pull -> fresh IBKR quote or
#: explained blocking, hard deadline 10 000 ms.
DEFAULT_REVALIDATION_DEADLINE = timedelta(seconds=10.0)
DEFAULT_SENT_AT_WINDOW = timedelta(seconds=300)

#: Clock skew tolerated between the Cloudflare ingress (which stamps
#: ``received_at``) and the local ingress clock. It MUST stay strictly below
#: the HP-02 deadline, otherwise a wire timestamp could extend that deadline.
DEFAULT_MAX_RECEIVED_AT_SKEW = timedelta(seconds=2)

#: Replay horizon for the ingress receipt. A receipt older than this could
#: never be revalidated anyway (the HP-02 deadline is 10 s), so admitting it
#: would only write a trigger record that is dead on arrival. Inside the
#: horizon the documented behaviour is unchanged: an outage backlog is still
#: routed and expires on its deadline instead of being re-qualified.
DEFAULT_MAX_RECEIVED_AT_AGE = DEFAULT_SENT_AT_WINDOW


@unique
class TriggerState(str, Enum):
    """Ingress states of one trigger. None of them is a verdict."""

    RECEIVED = "RECEIVED"
    PERSISTED = "PERSISTED"
    WAITING_FOR_IBKR = "WAITING_FOR_IBKR"
    REVALIDATED = "REVALIDATED"
    BLOCKED = "BLOCKED"
    EXPIRED = "EXPIRED"


# Terminal states: once reached, a trigger is never re-qualified by a replay.
_TERMINAL_STATES = frozenset({TriggerState.REVALIDATED, TriggerState.BLOCKED, TriggerState.EXPIRED})


@dataclass(frozen=True)
class QueueMessage:
    """One pulled queue message (body = queue envelope JSON bytes)."""

    message_id: str
    body: bytes
    attempt: int = 1


class QueueClient(Protocol):
    """Outbound-pull queue interface (Cloudflare Queues HTTP pull, faked in tests)."""

    def pull(self, max_messages: int) -> Sequence[QueueMessage]: ...

    def ack(self, message_id: str) -> None: ...


class SignalStore(Protocol):
    """Idempotent persistence boundary (PostgreSQL later, fake in tests).

    ``persist_signal`` MUST be idempotent on ``event_id`` and MUST only return
    once the record is durably committed. Returns True when the record was
    created, False when the same ``event_id`` already existed. Raising means
    "not persisted" (the caller must NOT ack).
    """

    def persist_signal(self, event_id: str, record: Mapping[str, Any]) -> bool: ...

    def set_state(self, event_id: str, state: TriggerState, reason: Optional[str]) -> None: ...

    def get_state(self, event_id: str) -> Optional[TriggerState]: ...


@dataclass(frozen=True)
class Quote:
    """Minimal synthetic view of one IBKR market observation used for gating.

    Only temporality and epoch matter to the ingress: the actual market fields
    live in the edge-ibkr envelopes and are never duplicated here.
    """

    observed_at: datetime
    connection_epoch: int
    source: str = "ibkr"


class QuoteProvider(Protocol):
    """Provider of the freshest available IBKR observation for an instrument."""

    def get_quote(self, exchange: str, ticker: str) -> Optional[Quote]: ...


@dataclass(frozen=True)
class IngressRejection:
    """Auditable record of one refused queue message (no body content)."""

    occurred_at: datetime
    message_id: str
    reason_code: str
    detail: str = ""


@dataclass(frozen=True)
class IngestOutcome:
    """Result of processing one queue message or one revalidation step."""

    message_id: Optional[str]
    event_id: Optional[str]
    status: str  # PERSISTED | DUPLICATE | REJECTED | PERSIST_FAILED |
    #              WAITING | REVALIDATED | BLOCKED | EXPIRED
    reason: Optional[str] = None


@dataclass
class _PendingTrigger:
    event_id: str
    alert: TradingViewAlertV1
    received_at: datetime
    deadline: datetime
    state: TriggerState = TriggerState.WAITING_FOR_IBKR


def _ensure_aware_utc(value: datetime, what: str) -> datetime:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise AlertRejected("naive_timestamp", f"{what} must be timezone-aware")
    return value.astimezone(timezone.utc)


class TradingViewOrchestrator:
    """Drives triggers through the ingress state machine (everything injected)."""

    def __init__(
        self,
        *,
        queue: QueueClient,
        store: SignalStore,
        quote_provider: QuoteProvider,
        registry: AlertRegistry,
        clock: Callable[[], datetime],
        epoch_provider: Callable[[], int],
        audit_sink: Callable[[IngressRejection], None],
        sent_at_window: timedelta = DEFAULT_SENT_AT_WINDOW,
        revalidation_deadline: timedelta = DEFAULT_REVALIDATION_DEADLINE,
        max_received_at_skew: timedelta = DEFAULT_MAX_RECEIVED_AT_SKEW,
        max_received_at_age: timedelta = DEFAULT_MAX_RECEIVED_AT_AGE,
    ) -> None:
        if revalidation_deadline <= timedelta(0):
            raise ValueError("revalidation_deadline must be strictly positive")
        if sent_at_window <= timedelta(0):
            raise ValueError("sent_at_window must be strictly positive")
        if max_received_at_skew < timedelta(0):
            raise ValueError("max_received_at_skew must be >= 0")
        if max_received_at_skew >= revalidation_deadline:
            raise ValueError(
                "max_received_at_skew must stay strictly below revalidation_deadline: "
                "a wire timestamp must never be able to extend the HP-02 deadline"
            )
        if max_received_at_age <= timedelta(0):
            raise ValueError("max_received_at_age must be strictly positive")
        self._queue = queue
        self._store = store
        self._quotes = quote_provider
        self._registry = registry
        self._clock = clock
        self._epoch = epoch_provider
        self._audit = audit_sink
        self._window = sent_at_window
        self._deadline = revalidation_deadline
        self._max_received_at_skew = max_received_at_skew
        self._max_received_at_age = max_received_at_age
        self._pending: Dict[str, _PendingTrigger] = {}

    # ------------------------------------------------------------------ pull

    def pull_and_ingest(self, max_messages: int = 10) -> List[IngestOutcome]:
        """Pull up to ``max_messages`` and ingest each one independently."""
        return [self.ingest_message(msg) for msg in self._queue.pull(max_messages)]

    def ingest_message(self, message: QueueMessage) -> IngestOutcome:
        """RECEIVED -> PERSISTED (ack only after confirmed persistence)."""
        now = self._clock()
        _ensure_aware_utc(now, "clock()")

        try:
            envelope = self._decode_envelope(message, now=now)
            alert = parse_alert(envelope["alert"])
            received_at = envelope["received_at"]
            # Anti-replay window is anchored on the ingress receipt time, which
            # ``_decode_envelope`` has just bounded against the injected ingress
            # clock. Inside that horizon a queue drained after an outage still
            # routes old messages (they expire on the HP-02 deadline; they are
            # never re-qualified).
            ensure_sent_at_in_window(alert, reference=received_at, window=self._window)
        except AlertRejected as exc:
            return self._reject(message, exc.reason_code, exc.detail)

        decision = self._registry.check(alert)
        if not decision.accepted:
            assert decision.rejection is not None
            # The registry already pushed its own auditable rejection.
            return self._reject(
                message,
                f"registry:{decision.rejection.reason.value}",
                decision.rejection.detail,
                audited_by_registry=True,
            )

        event_id = alert.event_id
        record = self._normalized_record(alert, received_at)

        try:
            created = self._store.persist_signal(event_id, record)
        except Exception:
            # NOT persisted -> NOT acked: the message must be redelivered.
            return IngestOutcome(
                message_id=message.message_id,
                event_id=event_id,
                status="PERSIST_FAILED",
                reason="store_unavailable",
            )

        # Persistence confirmed: acknowledging is now safe.
        self._queue.ack(message.message_id)

        if created:
            self._store.set_state(event_id, TriggerState.PERSISTED, None)
            self._store.set_state(event_id, TriggerState.WAITING_FOR_IBKR, None)
            self._pending[event_id] = _PendingTrigger(
                event_id=event_id,
                alert=alert,
                received_at=received_at,
                deadline=received_at + self._deadline,
            )
            return IngestOutcome(message_id=message.message_id, event_id=event_id, status="PERSISTED")

        # Redelivery of an already-persisted signal: keep counting nothing,
        # change nothing terminal, but re-attach a lost pending entry (e.g.
        # crash after persist and before ack in a previous run).
        state = self._store.get_state(event_id)
        if state is not None and state not in _TERMINAL_STATES and event_id not in self._pending:
            self._pending[event_id] = _PendingTrigger(
                event_id=event_id,
                alert=alert,
                received_at=received_at,
                deadline=received_at + self._deadline,
            )
        return IngestOutcome(
            message_id=message.message_id,
            event_id=event_id,
            status="DUPLICATE",
            reason="event_id_already_persisted",
        )

    # ----------------------------------------------------------- revalidate

    def advance_pending(self) -> List[IngestOutcome]:
        """WAITING_FOR_IBKR -> REVALIDATED | BLOCKED | EXPIRED.

        Deadline is evaluated FIRST: a quote arriving after the HP-02 deadline
        cannot resurrect an expired trigger. A returned quote is then judged
        once — aware, not dated ahead of the ingress clock, current-epoch and
        observed at or after the trigger means REVALIDATED (a full downstream
        re-evaluation request, not a verdict); anything else means BLOCKED
        with an explicit reason. No quote means the trigger keeps WAITING.
        """
        outcomes: List[IngestOutcome] = []
        for event_id in list(self._pending):
            trigger = self._pending[event_id]
            now = self._clock()
            _ensure_aware_utc(now, "clock()")

            if now >= trigger.deadline:
                outcomes.append(self._finish(trigger, TriggerState.EXPIRED, "IBKR_QUOTE_DEADLINE_EXCEEDED"))
                continue

            quote = self._quotes.get_quote(trigger.alert.exchange, trigger.alert.ticker)
            if quote is None:
                outcomes.append(
                    IngestOutcome(
                        message_id=None,
                        event_id=event_id,
                        status="WAITING",
                        reason="no_quote_available_yet",
                    )
                )
                continue

            observed_at = quote.observed_at
            if observed_at.tzinfo is None or observed_at.tzinfo.utcoffset(observed_at) is None:
                outcomes.append(self._finish(trigger, TriggerState.BLOCKED, "QUOTE_TIMESTAMP_NAIVE"))
                continue
            # Freshness is proved by ``observed_at >= received_at`` below, and
            # ``observed_at`` is provider-supplied: without an upper bound
            # against the ingress clock, a future-dated quote would prove its
            # own freshness. Same bound as the envelope receipt.
            if observed_at - now > self._max_received_at_skew:
                outcomes.append(
                    self._finish(trigger, TriggerState.BLOCKED, "QUOTE_OBSERVED_IN_FUTURE")
                )
                continue
            current_epoch = self._epoch()
            if quote.connection_epoch != current_epoch:
                outcomes.append(self._finish(trigger, TriggerState.BLOCKED, "STALE_CONNECTION_EPOCH"))
                continue
            if observed_at < trigger.received_at:
                outcomes.append(
                    self._finish(trigger, TriggerState.BLOCKED, "QUOTE_OBSERVED_BEFORE_TRIGGER")
                )
                continue

            outcomes.append(
                self._finish(
                    trigger,
                    TriggerState.REVALIDATED,
                    f"quote_observed_at={observed_at.isoformat()};epoch={quote.connection_epoch}",
                )
            )
        return outcomes

    def pending_event_ids(self) -> List[str]:
        """Event ids currently waiting for an IBKR observation."""
        return list(self._pending)

    # -------------------------------------------------------------- helpers

    def _finish(self, trigger: _PendingTrigger, state: TriggerState, reason: str) -> IngestOutcome:
        self._store.set_state(trigger.event_id, state, reason)
        del self._pending[trigger.event_id]
        return IngestOutcome(message_id=None, event_id=trigger.event_id, status=state.value, reason=reason)

    def _reject(
        self,
        message: QueueMessage,
        reason_code: str,
        detail: str,
        *,
        audited_by_registry: bool = False,
    ) -> IngestOutcome:
        """Auditable rejection: record, THEN ack (a poison message must not loop)."""
        if not audited_by_registry:
            self._audit(
                IngressRejection(
                    occurred_at=self._clock(),
                    message_id=message.message_id,
                    reason_code=reason_code,
                    detail=detail,
                )
            )
        self._queue.ack(message.message_id)
        return IngestOutcome(
            message_id=message.message_id, event_id=None, status="REJECTED", reason=reason_code
        )

    def _decode_envelope(self, message: QueueMessage, *, now: datetime) -> Mapping[str, Any]:
        """Decode and check the queue envelope against the ingress clock (fail-closed).

        ``now`` is the injected ingress clock. It is what makes ``received_at``
        an audited input rather than a self-declared one.
        """
        if len(message.body) > MAX_PAYLOAD_BYTES * 2:
            # Envelope = alert (<=16 KiB at the Worker) + bounded metadata.
            raise AlertRejected("oversize_envelope", f"{len(message.body)} bytes")
        try:
            decoded = json.loads(message.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AlertRejected("invalid_envelope_json", str(exc)) from exc
        if not isinstance(decoded, dict):
            raise AlertRejected("invalid_envelope", "envelope must be a JSON object")
        if decoded.get("schema") != QUEUE_ENVELOPE_SCHEMA_ID:
            raise AlertRejected("unknown_envelope_schema", str(decoded.get("schema"))[:64])
        raw_received = decoded.get("received_at")
        if not isinstance(raw_received, str):
            raise AlertRejected("missing_received_at")
        try:
            received_at = datetime.fromisoformat(raw_received.replace("Z", "+00:00"))
        except ValueError as exc:
            raise AlertRejected("invalid_received_at", raw_received[:64]) from exc
        received_at = _ensure_aware_utc(received_at, "received_at")
        # HARD BOUND on the wire receipt. Everything downstream is anchored on
        # this field (HP-02 deadline, anti-replay window, quote ordering), so
        # an unbounded value would make all three self-referential. Details
        # carry durations only — never payload content.
        ahead = received_at - now
        if ahead > self._max_received_at_skew:
            raise AlertRejected(
                "received_at_in_future",
                f"{ahead.total_seconds():.3f}s ahead of the ingress clock",
            )
        behind = now - received_at
        if behind > self._max_received_at_age:
            raise AlertRejected(
                "received_at_too_old",
                f"{behind.total_seconds():.0f}s behind the ingress clock",
            )
        alert = decoded.get("alert")
        if not isinstance(alert, dict):
            raise AlertRejected("missing_alert")
        return {"received_at": received_at, "alert": alert}

    def _normalized_record(
        self, alert: TradingViewAlertV1, received_at: datetime
    ) -> Mapping[str, Any]:
        """Normalized trigger record: provenance kept, price non-authoritative."""
        return {
            "schema": QUEUE_ENVELOPE_SCHEMA_ID,
            "event_id": alert.event_id,
            "alert_id": alert.alert_id,
            "script_version": alert.script_version,
            "signal": alert.signal.value,
            "exchange": alert.exchange,
            "ticker": alert.ticker,
            "interval": alert.interval,
            "sent_at": alert.sent_at.isoformat(),
            "bar_time": alert.bar_time.isoformat(),
            "received_at": received_at.isoformat(),
            # The alert is NEVER a price proof — context only:
            "price_context": dict(alert.price_context()),
            "values": dict(alert.values) if alert.values is not None else None,
            "source": "tradingview_alert",
            "authoritative_market_data": False,
        }
