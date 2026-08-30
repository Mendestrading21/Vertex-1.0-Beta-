"""Outbox worker daemon loop (ADR-006 consumer side).

Cycle: claim a batch of due messages on the registered topics (SKIP LOCKED,
lease), commit the claim, then handle each message in its own transaction —
handler effects and the ack commit together; a handler exception rolls the
transaction back and records a failed attempt (``fail_outbox`` with a
canonical error code) in a fresh transaction. Nothing is ever swallowed
silently: every outcome is counted (``stats()``), logged with technical
identifiers only (never payloads), and every failure lands in the outbox row.

Wake-up: polling with a configurable interval is the delivery guarantee.
LISTEN/NOTIFY (:class:`PostgresNotifyListener`) is an optional accelerator
only — a lost notification is tolerated by design because the next poll
finds the message anyway (ADR-006: NOTIFY is a signal, tables are the queue).

Shutdown: SIGTERM/SIGINT request a graceful stop — the batch currently being
processed is finished (each message reaches ack or fail), then the loop
exits. No message is abandoned mid-flight without its lease protecting it.
"""

from __future__ import annotations

import logging
import re
import signal
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from vertex_persistence.backoff import DEFAULT_MAX_ATTEMPTS

# Autorité unique de la conversion SQLAlchemy -> libpq : elle appartient à
# la persistance, pas au worker, et les outils d'exploitation doivent
# pouvoir l'utiliser sans importer le worker.
from vertex_persistence.dsn import sqlalchemy_url_to_conninfo
from vertex_persistence.enums import OutboxStatus
from vertex_persistence.errors import OutboxLeaseError
from vertex_persistence.repository.outbox import (
    ClaimedOutboxMessage,
    ack_outbox,
    claim_outbox_batch,
    fail_outbox,
)
from vertex_worker.errors import GENERIC_HANDLER_CODE, HandlerError, UnregisteredTopicError
from vertex_worker.registry import HandlerRegistry

__all__ = [
    "OutboxGateway",
    "PostgresNotifyListener",
    "RepositoryOutboxGateway",
    "WorkerRunner",
    "WorkerStats",
    "sqlalchemy_url_to_conninfo",
]

log = logging.getLogger("vertex_worker.runner")

Clock = Callable[[], datetime]
SessionFactory = Callable[[], Session]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _require_aware_utc_now(now: datetime) -> datetime:
    if not isinstance(now, datetime):
        raise TypeError(f"clock returned {type(now).__name__}, expected datetime")
    if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
        raise ValueError("clock returned a naive datetime; aware UTC required")
    return now.astimezone(UTC)


@dataclass(frozen=True)
class WorkerStats:
    """Immutable snapshot of the runner counters."""

    batches: int
    claimed: int
    acked: int
    failed: int
    dead: int
    lease_lost: int


class RepositoryOutboxGateway:
    """Default gateway: delegates to the ``vertex_persistence`` repository."""

    def claim(
        self,
        session: Session,
        topics: Sequence[str],
        limit: int,
        lease_seconds: int,
        now: datetime,
    ) -> list[ClaimedOutboxMessage]:
        return claim_outbox_batch(
            session, topics, limit, lease_seconds, now=now
        )

    def ack(
        self, session: Session, message_id: int, *, lease_token: str, now: datetime
    ) -> None:
        ack_outbox(session, message_id, lease_token=lease_token, now=now)

    def fail(
        self,
        session: Session,
        message_id: int,
        exc: BaseException,
        *,
        code: str,
        lease_token: str,
        now: datetime,
        max_attempts: int,
    ) -> str:
        return fail_outbox(
            session,
            message_id,
            exc,
            code=code,
            lease_token=lease_token,
            now=now,
            max_attempts=max_attempts,
        )


OutboxGateway = RepositoryOutboxGateway
"""Structural contract of the outbox gateway (tests may substitute fakes)."""


class WorkerRunner:
    """Single-threaded outbox consumer with graceful shutdown and counters."""

    def __init__(
        self,
        *,
        session_factory: SessionFactory,
        registry: HandlerRegistry,
        batch_limit: int = 25,
        lease_seconds: int = 60,
        poll_interval_seconds: float = 1.0,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        clock: Clock | None = None,
        gateway: RepositoryOutboxGateway | None = None,
    ) -> None:
        if not registry.topics:
            raise ValueError("registry has no registered topic; nothing to claim")
        if not isinstance(batch_limit, int) or batch_limit < 1:
            raise ValueError("batch_limit: must be an int >= 1")
        if not isinstance(lease_seconds, int) or lease_seconds < 1:
            raise ValueError("lease_seconds: must be an int >= 1")
        if not (poll_interval_seconds > 0):
            raise ValueError("poll_interval_seconds: must be > 0")
        self._session_factory = session_factory
        self._registry = registry
        self._batch_limit = batch_limit
        self._lease_seconds = lease_seconds
        self._poll_interval = float(poll_interval_seconds)
        self._max_attempts = max_attempts
        self._clock: Clock = clock if clock is not None else _utc_now
        self._gateway = gateway if gateway is not None else RepositoryOutboxGateway()
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._lock = threading.Lock()
        self._batches = 0
        self._claimed = 0
        self._acked = 0
        self._failed = 0
        self._dead = 0
        self._lease_lost = 0

    # -- introspection ----------------------------------------------------

    def stats(self) -> WorkerStats:
        """Return an immutable snapshot of the counters."""
        with self._lock:
            return WorkerStats(
                batches=self._batches,
                claimed=self._claimed,
                acked=self._acked,
                failed=self._failed,
                dead=self._dead,
                lease_lost=self._lease_lost,
            )

    @property
    def stop_requested(self) -> bool:
        return self._stop.is_set()

    # -- control ----------------------------------------------------------

    def request_stop(self) -> None:
        """Ask the loop to exit after the batch currently in flight."""
        self._stop.set()
        self._wake.set()

    def wake(self) -> None:
        """Interrupt the idle wait early (e.g. on a NOTIFY signal)."""
        self._wake.set()

    def install_signal_handlers(self) -> None:
        """Install SIGTERM/SIGINT handlers requesting a graceful stop.

        Main thread only (a Python constraint on ``signal.signal``).
        """
        signal.signal(signal.SIGTERM, self._on_signal)
        signal.signal(signal.SIGINT, self._on_signal)

    def _on_signal(self, signum: int, frame: object) -> None:
        log.info("signal %s received; finishing current batch then exiting", signum)
        self.request_stop()

    # -- processing -------------------------------------------------------

    def _now(self) -> datetime:
        return _require_aware_utc_now(self._clock())

    def run_once(self) -> int:
        """Claim and fully process one batch; return how many were claimed.

        The claim is committed before any handler runs (the lease must be
        visible to concurrent workers and to the reaper). Every claimed
        message is then driven to ack or fail — including after a stop
        request: the batch in flight is always finished.
        """
        now = self._now()
        with self._session_factory() as session:
            messages = self._gateway.claim(
                session,
                self._registry.topics,
                self._batch_limit,
                self._lease_seconds,
                now,
            )
            session.commit()
        if not messages:
            return 0
        with self._lock:
            self._batches += 1
            self._claimed += len(messages)
        for message in messages:
            self._process_one(message)
        return len(messages)

    def _process_one(self, message: ClaimedOutboxMessage) -> None:
        handler = self._registry.get(message.topic)
        try:
            if handler is None:
                raise UnregisteredTopicError(message.topic)
            with self._session_factory() as session:
                handler(session, message)
                self._gateway.ack(
                    session,
                    message.id,
                    lease_token=message.lease_token,
                    now=self._now(),
                )
                session.commit()
        except OutboxLeaseError:
            # The lease expired and was reaped or the row was re-claimed:
            # the attempt is already recorded elsewhere; discard the result.
            with self._lock:
                self._lease_lost += 1
            log.warning(
                "lease lost on message_id=%s topic=%s; result discarded",
                message.id,
                message.topic,
            )
        except Exception as exc:
            # KeyboardInterrupt/SystemExit deliberately propagate.
            self._record_failure(message, exc)
        else:
            with self._lock:
                self._acked += 1
            log.debug("acked message_id=%s topic=%s", message.id, message.topic)

    def _record_failure(self, message: ClaimedOutboxMessage, exc: Exception) -> None:
        code = exc.code if isinstance(exc, HandlerError) else GENERIC_HANDLER_CODE
        # Technical identifiers only — never str(exc), never the payload.
        log.error(
            "handler failed message_id=%s topic=%s code=%s exc_type=%s",
            message.id,
            message.topic,
            code,
            type(exc).__name__,
        )
        try:
            with self._session_factory() as session:
                status = self._gateway.fail(
                    session,
                    message.id,
                    exc,
                    code=code,
                    lease_token=message.lease_token,
                    now=self._now(),
                    max_attempts=self._max_attempts,
                )
                session.commit()
        except OutboxLeaseError:
            with self._lock:
                self._lease_lost += 1
            log.warning(
                "lease lost while failing message_id=%s topic=%s",
                message.id,
                message.topic,
            )
            return
        with self._lock:
            self._failed += 1
            if status == OutboxStatus.DEAD.value:
                self._dead += 1
        if status == OutboxStatus.DEAD.value:
            log.error(
                "message_id=%s topic=%s is DEAD after max attempts",
                message.id,
                message.topic,
            )

    # -- loops ------------------------------------------------------------

    def drain(self, *, max_batches: int) -> int:
        """Bounded processing (tests, one-shot runs): claim and process
        batches until the outbox is empty or ``max_batches`` is reached.
        Returns the total number of processed messages. Never blocks waiting
        for new work.
        """
        if not isinstance(max_batches, int) or max_batches < 1:
            raise ValueError("max_batches: must be an int >= 1")
        total = 0
        for _ in range(max_batches):
            processed = self.run_once()
            total += processed
            if processed == 0 or self._stop.is_set():
                break
        return total

    def run(self) -> None:
        """Daemon loop: process batches, sleep on the polling interval when
        idle, exit gracefully on a stop request (current batch finished
        first). Infrastructure exceptions propagate — a broken database is
        never retried silently inside this loop (fail-closed; the supervisor
        owns the restart policy).
        """
        log.info(
            "worker loop started topics=%s poll_interval=%.3fs",
            ",".join(self._registry.topics),
            self._poll_interval,
        )
        try:
            while not self._stop.is_set():
                processed = self.run_once()
                if processed == 0 and not self._stop.is_set():
                    self._wake.clear()
                    self._wake.wait(timeout=self._poll_interval)
        finally:
            log.info("worker loop stopped; stats=%s", self.stats())


class PostgresNotifyListener:
    """Best-effort LISTEN wake-up for the worker (never the delivery path).

    Runs a daemon thread holding one dedicated autocommit connection with
    ``LISTEN <channel>`` and invokes ``on_notify`` for each notification.
    Any listener failure is logged and ends the thread WITHOUT affecting the
    worker: lost notifications are tolerated by design because polling
    remains the delivery guarantee (ADR-006). The failure is still exposed
    via :attr:`failed` — degraded, but never silent.
    """

    _CHANNEL_RE = re.compile(r"^[a-z_][a-z0-9_]*$")

    def __init__(
        self,
        *,
        conninfo: str,
        channel: str,
        on_notify: Callable[[], None],
        poll_timeout_seconds: float = 1.0,
    ) -> None:
        if not self._CHANNEL_RE.match(channel):
            raise ValueError(f"channel: invalid identifier {channel!r}")
        if not (poll_timeout_seconds > 0):
            raise ValueError("poll_timeout_seconds: must be > 0")
        self._conninfo = conninfo
        self._channel = channel
        self._on_notify = on_notify
        self._poll_timeout = float(poll_timeout_seconds)
        self._stopped = threading.Event()
        self._thread: threading.Thread | None = None
        self._failed = False
        self._last_error_type: str | None = None

    @property
    def failed(self) -> bool:
        return self._failed

    @property
    def last_error_type(self) -> str | None:
        return self._last_error_type

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("listener already started")
        self._thread = threading.Thread(
            target=self._loop, name="vertex-outbox-listener", daemon=True
        )
        self._thread.start()

    def stop(self, *, join_timeout_seconds: float = 5.0) -> None:
        self._stopped.set()
        if self._thread is not None:
            self._thread.join(timeout=join_timeout_seconds)

    def _loop(self) -> None:
        import psycopg

        try:
            with psycopg.connect(self._conninfo, autocommit=True) as connection:
                connection.execute(f'LISTEN "{self._channel}"')
                while not self._stopped.is_set():
                    for _ in connection.notifies(timeout=self._poll_timeout):
                        self._on_notify()
        except Exception as exc:
            # Degraded mode, not silence: recorded, logged (type only) and
            # harmless — the worker's polling still delivers every message.
            self._failed = True
            self._last_error_type = type(exc).__name__
            log.warning(
                "notify listener stopped (%s); polling continues to deliver",
                type(exc).__name__,
            )
