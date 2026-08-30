"""Deterministic in-memory fakes for worker unit tests (status: SYNTHETIC).

These fakes never cross a production boundary: they exist only to test the
runner's dispatch, failure and shutdown logic without a database.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from vertex_persistence.enums import OutboxStatus
from vertex_persistence.errors import OutboxLeaseError
from vertex_persistence.repository.outbox import ClaimedOutboxMessage

FIXED_NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)


def fixed_clock() -> datetime:
    return FIXED_NOW


def make_message(
    message_id: int = 1,
    topic: str = "observation.ingested",
    payload: dict[str, Any] | None = None,
    attempts: int = 0,
) -> ClaimedOutboxMessage:
    return ClaimedOutboxMessage(
        id=message_id,
        topic=topic,
        payload=payload if payload is not None else {"event_id": f"evt-{message_id}"},
        attempts=attempts,
        lease_until=FIXED_NOW + timedelta(seconds=60),
        lease_token=f"token-{message_id}",
    )


class FakeSession:
    """Records commits/rollbacks; supports the context-manager protocol."""

    def __init__(self) -> None:
        self.committed = 0
        self.rolled_back = 0
        self.closed = False

    def commit(self) -> None:
        self.committed += 1

    def rollback(self) -> None:
        self.rolled_back += 1

    def __enter__(self) -> FakeSession:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.closed = True


class FakeSessionFactory:
    def __init__(self) -> None:
        self.sessions: list[FakeSession] = []

    def __call__(self) -> FakeSession:
        session = FakeSession()
        self.sessions.append(session)
        return session


class FakeGateway:
    """In-memory outbox gateway with scriptable behavior.

    ``pending`` holds batches to hand out on successive claims; ``fail_status``
    scripts what ``fail`` reports; ``lease_error_on`` makes ack/fail raise
    :class:`OutboxLeaseError` for the listed message ids.
    """

    def __init__(self) -> None:
        self.pending: list[list[ClaimedOutboxMessage]] = []
        self.claim_calls: list[dict[str, Any]] = []
        self.acked: list[int] = []
        self.failed: list[dict[str, Any]] = []
        self.fail_status: str = OutboxStatus.FAILED.value
        self.lease_error_on_ack: set[int] = set()
        self.lease_error_on_fail: set[int] = set()

    def claim(self, session, topics, limit, lease_seconds, now):
        self.claim_calls.append(
            {
                "topics": tuple(topics),
                "limit": limit,
                "lease_seconds": lease_seconds,
                "now": now,
            }
        )
        if self.pending:
            return self.pending.pop(0)
        return []

    def ack(self, session, message_id, *, lease_token, now):
        if message_id in self.lease_error_on_ack:
            raise OutboxLeaseError(f"message {message_id} not held under this token")
        self.acked.append(message_id)

    def fail(self, session, message_id, exc, *, code, lease_token, now, max_attempts):
        if message_id in self.lease_error_on_fail:
            raise OutboxLeaseError(f"message {message_id} not held under this token")
        self.failed.append(
            {
                "message_id": message_id,
                "exc_type": type(exc).__name__,
                "code": code,
                "max_attempts": max_attempts,
            }
        )
        return self.fail_status
