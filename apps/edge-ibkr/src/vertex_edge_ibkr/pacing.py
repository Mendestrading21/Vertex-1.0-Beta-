"""Voluntary IBKR pacing: message budget, priority queues, line ceiling.

Policy (docs/04-integrations/IBKR.md and IBKR_ENTITLEMENT_PROBE.md):

- voluntary budget of 35-40 messages/second (default 38) even though the
  provider disconnects at 50 — a configured budget above 40 is refused;
- never use more than 80% of the detected market-data lines;
- bounded queues with strict priorities: P0 control > P1 user request >
  P2 durable > P3 background;
- a full queue REFUSES explicitly (exception with counters); nothing is ever
  dropped silently — in particular no P2 message ever disappears.

Deterministic: the clock is injected (monotonic seconds); no thread, no
implicit time source.
"""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import IntEnum, unique
from typing import Any

__all__ = [
    "DEFAULT_MESSAGES_PER_SECOND",
    "HARD_MESSAGE_BUDGET_CEILING",
    "MAX_LINE_USAGE_FRACTION",
    "LineBudget",
    "LineBudgetExceededError",
    "MessagePacer",
    "PacingCounters",
    "Priority",
    "QueueRefusalError",
]

#: Voluntary default budget (within the documented 35-40 msg/s window).
DEFAULT_MESSAGES_PER_SECOND = 38.0

#: Absolute local ceiling — the provider cuts at 50; Vertex never configures >40.
HARD_MESSAGE_BUDGET_CEILING = 40.0

#: Never use more than this fraction of the detected market-data lines.
MAX_LINE_USAGE_FRACTION = 0.80


@unique
class Priority(IntEnum):
    """Dispatch priority: lower value dispatches first."""

    P0_CONTROL = 0
    P1_USER = 1
    P2_DURABLE = 2
    P3_BACKGROUND = 3


class QueueRefusalError(RuntimeError):
    """Explicit refusal: the bounded queue for this priority is full.

    The submitted item is NOT enqueued and NOT dropped silently — the caller
    is told exactly what was refused and why.
    """

    def __init__(self, priority: Priority, capacity: int, pending: int) -> None:
        super().__init__(
            f"queue full for {priority.name}: capacity={capacity} pending={pending}; "
            "message refused explicitly (never dropped silently)"
        )
        self.priority = priority
        self.capacity = capacity
        self.pending = pending


class LineBudgetExceededError(RuntimeError):
    """Explicit refusal: acquiring another market-data line would exceed the cap."""

    def __init__(self, in_use: int, max_usable: int) -> None:
        super().__init__(
            f"market data line budget exceeded: in_use={in_use} max_usable={max_usable}"
        )
        self.in_use = in_use
        self.max_usable = max_usable


@dataclass
class PacingCounters:
    """Observable counters — refusals are visible, never silent."""

    submitted: dict[Priority, int] = field(default_factory=lambda: dict.fromkeys(Priority, 0))
    enqueued: dict[Priority, int] = field(default_factory=lambda: dict.fromkeys(Priority, 0))
    dispatched: dict[Priority, int] = field(default_factory=lambda: dict.fromkeys(Priority, 0))
    refused: dict[Priority, int] = field(default_factory=lambda: dict.fromkeys(Priority, 0))


class MessagePacer:
    """Token-bucket pacer with bounded priority queues.

    ``clock`` returns monotonic seconds and is injected for determinism.
    ``submit`` enqueues (or refuses explicitly); ``drain`` dispatches what the
    budget allows now, strictly by priority then FIFO.
    """

    def __init__(
        self,
        *,
        messages_per_second: float = DEFAULT_MESSAGES_PER_SECOND,
        queue_capacity: int | Mapping[Priority, int] = 256,
        clock: Callable[[], float] | None = None,
    ) -> None:
        if not (1.0 <= messages_per_second <= HARD_MESSAGE_BUDGET_CEILING):
            raise ValueError(
                "messages_per_second must stay within [1, 40]: the voluntary "
                "budget never exceeds 40 even though the provider cuts at 50"
            )
        if clock is None:
            raise ValueError("clock must be injected (monotonic seconds); no implicit time source")
        self._rate = float(messages_per_second)
        self._clock = clock
        if isinstance(queue_capacity, Mapping):
            self._capacity = {p: int(queue_capacity.get(p, 0)) for p in Priority}
        else:
            self._capacity = {p: int(queue_capacity) for p in Priority}
        for priority, capacity in self._capacity.items():
            if capacity < 1:
                raise ValueError(f"queue capacity for {priority.name} must be >= 1")
        self._queues: dict[Priority, deque[Any]] = {p: deque() for p in Priority}
        self._tokens = float(self._rate)  # allow an initial burst of one second
        self._last_refill = float(self._clock())
        self.counters = PacingCounters()

    # -- queries -----------------------------------------------------------

    def pending(self, priority: Priority | None = None) -> int:
        if priority is not None:
            return len(self._queues[priority])
        return sum(len(q) for q in self._queues.values())

    def capacity(self, priority: Priority) -> int:
        return self._capacity[priority]

    def available_tokens(self) -> int:
        self._refill()
        return math.floor(self._tokens)

    # -- submission and dispatch ------------------------------------------

    def submit(self, item: Any, priority: Priority) -> None:
        """Enqueue ``item`` or refuse explicitly when the queue is full."""
        self.counters.submitted[priority] += 1
        queue = self._queues[priority]
        if len(queue) >= self._capacity[priority]:
            self.counters.refused[priority] += 1
            raise QueueRefusalError(priority, self._capacity[priority], len(queue))
        queue.append(item)
        self.counters.enqueued[priority] += 1

    def drain(self) -> list[Any]:
        """Dispatch every item the current budget allows, priority first.

        Items beyond the budget stay queued (never dropped); the next call
        after the bucket refills dispatches them.
        """
        self._refill()
        dispatched: list[Any] = []
        while self._tokens >= 1.0:
            item, priority = self._pop_highest()
            if priority is None:
                break
            self._tokens -= 1.0
            self.counters.dispatched[priority] += 1
            dispatched.append(item)
        return dispatched

    def _pop_highest(self) -> tuple[Any, Priority | None]:
        for priority in Priority:
            queue = self._queues[priority]
            if queue:
                return queue.popleft(), priority
        return None, None

    def _refill(self) -> None:
        now = float(self._clock())
        elapsed = now - self._last_refill
        if elapsed < 0:
            # A monotonic clock never goes backwards; fail closed by not refilling.
            self._last_refill = now
            return
        self._last_refill = now
        self._tokens = min(float(self._rate), self._tokens + elapsed * self._rate)


class LineBudget:
    """Market-data line ceiling: at most 80% of the detected lines.

    ``hard_cap`` optionally lowers the ceiling further (e.g. the entitlement
    probe caps itself at 2 simultaneous lines). Acquisition beyond the ceiling
    is refused explicitly.
    """

    def __init__(
        self,
        detected_lines: int,
        *,
        usage_fraction: float = MAX_LINE_USAGE_FRACTION,
        hard_cap: int | None = None,
    ) -> None:
        if detected_lines < 0:
            raise ValueError("detected_lines must be >= 0")
        if not (0.0 < usage_fraction <= MAX_LINE_USAGE_FRACTION):
            raise ValueError("usage_fraction must be in (0, 0.80]")
        if hard_cap is not None and hard_cap < 1:
            raise ValueError("hard_cap must be >= 1 when present")
        ceiling = math.floor(detected_lines * usage_fraction)
        if hard_cap is not None:
            ceiling = min(ceiling, hard_cap)
        self._max_usable = ceiling
        self._in_use = 0

    @property
    def max_usable(self) -> int:
        return self._max_usable

    @property
    def in_use(self) -> int:
        return self._in_use

    def try_acquire(self, lines: int = 1) -> bool:
        """Acquire ``lines`` if the ceiling allows it; False otherwise."""
        if lines < 1:
            raise ValueError("lines must be >= 1")
        if self._in_use + lines > self._max_usable:
            return False
        self._in_use += lines
        return True

    def acquire(self, lines: int = 1) -> None:
        """Acquire or raise ``LineBudgetExceededError`` (explicit refusal)."""
        if not self.try_acquire(lines):
            raise LineBudgetExceededError(self._in_use, self._max_usable)

    def release(self, lines: int = 1) -> None:
        if lines < 1:
            raise ValueError("lines must be >= 1")
        if lines > self._in_use:
            raise ValueError("cannot release more lines than are in use")
        self._in_use -= lines
