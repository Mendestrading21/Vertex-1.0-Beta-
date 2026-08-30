"""Pacing: voluntary budget, priority queues, explicit refusals, line cap."""

from __future__ import annotations

import pytest

from vertex_edge_ibkr.pacing import (
    DEFAULT_MESSAGES_PER_SECOND,
    LineBudget,
    LineBudgetExceededError,
    MessagePacer,
    Priority,
    QueueRefusalError,
)


class ManualClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def make_pacer(**kwargs) -> tuple[MessagePacer, ManualClock]:
    clock = ManualClock()
    kwargs.setdefault("clock", clock)
    return MessagePacer(**kwargs), clock


def test_default_budget_is_38_within_the_35_40_window() -> None:
    assert DEFAULT_MESSAGES_PER_SECOND == 38.0
    pacer, _clock = make_pacer()
    assert pacer.available_tokens() == 38


@pytest.mark.parametrize("budget", [40.5, 41, 50, 0, 0.5])
def test_budget_outside_1_to_40_is_refused(budget) -> None:
    clock = ManualClock()
    with pytest.raises(ValueError):
        MessagePacer(messages_per_second=budget, clock=clock)


def test_clock_injection_is_mandatory() -> None:
    with pytest.raises(ValueError):
        MessagePacer()


def test_burst_beyond_budget_is_queued_never_dropped() -> None:
    pacer, clock = make_pacer(messages_per_second=38.0, queue_capacity=100)
    for index in range(50):
        pacer.submit(f"m{index}", Priority.P1_USER)
    first = pacer.drain()
    assert len(first) == 38  # one second of budget
    assert pacer.pending(Priority.P1_USER) == 12  # the rest is queued, not dropped
    clock.advance(1.0)
    second = pacer.drain()
    assert len(second) == 12
    assert first + second == [f"m{i}" for i in range(50)]  # FIFO preserved


def test_priorities_dispatch_control_first() -> None:
    pacer, _clock = make_pacer(messages_per_second=35.0)
    pacer.submit("background", Priority.P3_BACKGROUND)
    pacer.submit("durable", Priority.P2_DURABLE)
    pacer.submit("user", Priority.P1_USER)
    pacer.submit("control", Priority.P0_CONTROL)
    assert pacer.drain() == ["control", "user", "durable", "background"]


def test_full_p2_queue_refuses_explicitly_and_never_drops() -> None:
    pacer, _clock = make_pacer(
        messages_per_second=38.0,
        queue_capacity={
            Priority.P0_CONTROL: 4,
            Priority.P1_USER: 4,
            Priority.P2_DURABLE: 2,
            Priority.P3_BACKGROUND: 4,
        },
    )
    pacer.submit("d1", Priority.P2_DURABLE)
    pacer.submit("d2", Priority.P2_DURABLE)
    with pytest.raises(QueueRefusalError) as refusal:
        pacer.submit("d3", Priority.P2_DURABLE)
    assert refusal.value.priority is Priority.P2_DURABLE
    assert refusal.value.capacity == 2
    # Nothing already accepted was dropped, and the refusal is counted.
    assert pacer.pending(Priority.P2_DURABLE) == 2
    assert pacer.counters.refused[Priority.P2_DURABLE] == 1
    assert pacer.drain() == ["d1", "d2"]
    # Accounting closes: submitted == enqueued + refused, dispatched == enqueued.
    assert pacer.counters.submitted[Priority.P2_DURABLE] == 3
    assert pacer.counters.enqueued[Priority.P2_DURABLE] == 2
    assert pacer.counters.dispatched[Priority.P2_DURABLE] == 2


def test_tokens_refill_continuously_and_cap_at_budget() -> None:
    pacer, clock = make_pacer(messages_per_second=40.0, queue_capacity=200)
    for index in range(80):
        pacer.submit(index, Priority.P3_BACKGROUND)
    assert len(pacer.drain()) == 40
    clock.advance(0.5)  # half a second refills half a budget
    assert len(pacer.drain()) == 20
    clock.advance(100.0)  # the bucket never exceeds one second of budget
    assert len(pacer.drain()) == 20


def test_counters_track_every_priority() -> None:
    pacer, _clock = make_pacer()
    pacer.submit("a", Priority.P0_CONTROL)
    pacer.submit("b", Priority.P2_DURABLE)
    pacer.drain()
    assert pacer.counters.dispatched[Priority.P0_CONTROL] == 1
    assert pacer.counters.dispatched[Priority.P2_DURABLE] == 1
    assert pacer.counters.refused[Priority.P0_CONTROL] == 0


def test_line_budget_caps_at_80_percent_of_detected_lines() -> None:
    budget = LineBudget(detected_lines=100)
    assert budget.max_usable == 80
    budget2 = LineBudget(detected_lines=10)
    assert budget2.max_usable == 8


def test_line_budget_refuses_beyond_the_cap() -> None:
    budget = LineBudget(detected_lines=5)  # floor(5 * 0.8) == 4
    assert budget.max_usable == 4
    for _ in range(4):
        assert budget.try_acquire() is True
    assert budget.try_acquire() is False
    with pytest.raises(LineBudgetExceededError):
        budget.acquire()
    budget.release()
    assert budget.try_acquire() is True


def test_line_budget_hard_cap_lowers_the_ceiling() -> None:
    budget = LineBudget(detected_lines=100, hard_cap=2)
    assert budget.max_usable == 2
    assert budget.try_acquire(2) is True
    assert budget.try_acquire() is False


def test_line_budget_fraction_cannot_exceed_80_percent() -> None:
    with pytest.raises(ValueError):
        LineBudget(detected_lines=10, usage_fraction=0.9)
