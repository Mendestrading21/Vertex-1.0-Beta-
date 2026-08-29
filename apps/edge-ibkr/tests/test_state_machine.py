"""ConnectionStateMachine: codes 1100/1101/1102/1300/502, epochs, lock."""

from __future__ import annotations

import random

import pytest

from vertex_edge_ibkr.state import (
    ConnectionState,
    ConnectionStateMachine,
    InvalidTransitionError,
    PortRereadRequiredError,
    ReconnectInProgressError,
)


def make_machine(seed: int = 42, **kwargs) -> ConnectionStateMachine:
    return ConnectionStateMachine(rng=random.Random(seed), **kwargs)


def connect(machine: ConnectionStateMachine) -> None:
    machine.begin_connect()
    machine.on_connected()


def test_initial_state_and_epoch() -> None:
    machine = make_machine()
    assert machine.state is ConnectionState.STARTING
    assert machine.connection_epoch == 0


def test_successful_connect_increments_epoch_and_goes_healthy() -> None:
    machine = make_machine()
    connect(machine)
    assert machine.state is ConnectionState.HEALTHY
    assert machine.connection_epoch == 1


def test_1100_goes_down_and_blocks_fresh_results() -> None:
    machine = make_machine()
    connect(machine)
    epoch = machine.connection_epoch
    machine.on_error_code(1100)
    assert machine.state is ConnectionState.DOWN
    # Even a current-epoch observation is not fresh while DOWN.
    assert machine.record_observation(epoch) is False
    assert machine.observation_is_fresh(epoch) is False


def test_1101_bumps_epoch_and_requires_resubscription() -> None:
    machine = make_machine()
    connect(machine)
    old_epoch = machine.connection_epoch
    machine.on_error_code(1100)
    machine.on_error_code(1101)
    assert machine.connection_epoch == old_epoch + 1
    assert machine.resubscribe_required is True
    assert machine.state is ConnectionState.DEGRADED
    # Not healthy until resubscribed.
    assert machine.record_observation(machine.connection_epoch) is False
    machine.mark_resubscribed()
    assert machine.state is ConnectionState.HEALTHY
    assert machine.resubscribe_required is False


def test_1102_waits_for_one_post_reconnection_observation() -> None:
    machine = make_machine()
    connect(machine)
    machine.on_error_code(1100)
    machine.on_error_code(1102)
    assert machine.state is ConnectionState.RECOVERING
    assert machine.awaiting_post_reconnect_observation is True
    # An old-epoch observation never satisfies the wait.
    assert machine.record_observation(machine.connection_epoch - 1) is False
    assert machine.state is ConnectionState.RECOVERING
    # The first current-epoch observation promotes to HEALTHY.
    assert machine.record_observation(machine.connection_epoch) is True
    assert machine.state is ConnectionState.HEALTHY
    assert machine.awaiting_post_reconnect_observation is False


def test_1300_requires_port_reread_before_reconnect() -> None:
    machine = make_machine()
    connect(machine)
    machine.on_error_code(1300)
    assert machine.state is ConnectionState.DOWN
    assert machine.reread_port_required is True
    with pytest.raises(PortRereadRequiredError):
        machine.begin_connect()
    machine.mark_port_reread()
    machine.begin_connect()
    machine.on_connected()
    assert machine.state is ConnectionState.HEALTHY
    assert machine.connection_epoch == 2


def test_transport_error_backoff_is_seeded_and_deterministic() -> None:
    machine_a = make_machine(seed=7)
    machine_b = make_machine(seed=7)
    delays_a = [machine_a.on_transport_error() for _ in range(6)]
    delays_b = [machine_b.on_transport_error() for _ in range(6)]
    assert delays_a == delays_b  # injected seeded generator => deterministic
    assert machine_a.state is ConnectionState.DOWN


def test_transport_error_backoff_grows_and_stays_capped() -> None:
    machine = make_machine(
        seed=3, base_backoff_seconds=1.0, backoff_multiplier=2.0, max_backoff_seconds=8.0
    )
    delays = [machine.on_transport_error() for _ in range(8)]
    for attempt, delay in enumerate(delays):
        capped = min(8.0, 1.0 * (2.0**attempt))
        assert capped / 2.0 <= delay <= capped
    # Once the cap is reached, every jittered delay stays within [cap/2, cap].
    assert all(4.0 <= delay <= 8.0 for delay in delays[3:])


def test_502_is_a_transport_error_with_backoff() -> None:
    machine = make_machine()
    delay = machine.on_error_code(502)
    assert delay is not None and delay > 0
    assert machine.state is ConnectionState.DOWN
    assert machine.transport_failures == 1


def test_successful_reconnect_resets_backoff() -> None:
    machine = make_machine()
    machine.on_transport_error()
    machine.on_transport_error()
    assert machine.transport_failures == 2
    connect(machine)
    assert machine.transport_failures == 0


def test_reconnection_lock_allows_a_single_concurrent_attempt() -> None:
    machine = make_machine()
    machine.begin_connect()
    with pytest.raises(ReconnectInProgressError):
        machine.begin_connect()
    machine.on_connected()
    assert machine.reconnect_in_progress is False


def test_failed_attempt_releases_the_lock_and_returns_backoff() -> None:
    machine = make_machine()
    machine.begin_connect()
    delay = machine.on_connect_failed()
    assert delay > 0
    assert machine.state is ConnectionState.DOWN
    machine.begin_connect()  # the slot is free again
    machine.on_connected()
    assert machine.state is ConnectionState.HEALTHY


def test_epoch_is_strictly_increasing_across_reconnects() -> None:
    machine = make_machine()
    seen = [machine.connection_epoch]
    for _ in range(3):
        machine.on_transport_error()
        machine.begin_connect()
        machine.on_connected()
        seen.append(machine.connection_epoch)
    assert seen == sorted(set(seen))
    assert seen[-1] == 3


def test_old_epoch_observation_is_never_fresh() -> None:
    machine = make_machine()
    connect(machine)
    old_epoch = machine.connection_epoch
    machine.on_error_code(1101)  # bumps the epoch
    machine.mark_resubscribed()
    assert machine.state is ConnectionState.HEALTHY
    assert machine.observation_is_fresh(old_epoch) is False
    assert machine.record_observation(old_epoch) is False
    assert machine.observation_is_fresh(machine.connection_epoch) is True


def test_stop_is_terminal() -> None:
    machine = make_machine()
    connect(machine)
    machine.stop()
    assert machine.state is ConnectionState.STOPPED
    with pytest.raises(InvalidTransitionError):
        machine.begin_connect()
    assert machine.on_error_code(1100) is None
    assert machine.state is ConnectionState.STOPPED


def test_unknown_code_is_ignored() -> None:
    machine = make_machine()
    connect(machine)
    assert machine.on_error_code(2104) is None
    assert machine.state is ConnectionState.HEALTHY
