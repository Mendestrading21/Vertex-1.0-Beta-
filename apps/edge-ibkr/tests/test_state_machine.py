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
    delays = [machine.on_transport_error()]
    for _ in range(7):
        machine.begin_connect()
        delays.append(machine.on_connect_failed())
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
    machine.begin_connect()
    machine.on_connect_failed()
    assert machine.transport_failures == 2
    connect(machine)
    assert machine.transport_failures == 0


def test_duplicate_502_reuses_one_backoff_within_an_incident() -> None:
    """Deux callbacks du même incident ne redessinent ni jitter ni échec."""
    machine = make_machine(seed=9)
    first = machine.on_error_code(502)
    duplicate = machine.on_error_code(502)

    assert duplicate == first
    assert machine.transport_failures == 1


def test_duplicate_1101_bumps_epoch_once_while_resubscription_is_open() -> None:
    machine = make_machine()
    connect(machine)
    machine.on_error_code(1100)
    machine.on_error_code(1101)
    epoch = machine.connection_epoch
    machine.on_error_code(1101)

    assert machine.connection_epoch == epoch
    assert machine.resubscribe_required


def test_502_then_restoration_preserves_transport_down_and_obligations() -> None:
    machine = make_machine()
    connect(machine)
    epoch = machine.connection_epoch

    machine.on_error_code(502)
    machine.on_error_code(1101)
    machine.on_error_code(1102)

    assert machine.state is ConnectionState.DOWN
    assert machine.connection_epoch == epoch + 1
    assert machine.resubscribe_required
    assert machine.awaiting_post_reconnect_observation
    assert machine.pending_transport_backoff is not None

    machine.begin_connect()
    machine.on_connected()
    assert machine.state is ConnectionState.DEGRADED
    machine.mark_resubscribed()
    assert machine.state is ConnectionState.RECOVERING


@pytest.mark.parametrize(
    ("restoration_code", "state_after_reconnect", "epoch_increase"),
    [
        pytest.param(1101, ConnectionState.DEGRADED, 2, id="502-then-1101"),
        pytest.param(1102, ConnectionState.RECOVERING, 1, id="502-then-1102"),
    ],
)
def test_transport_failure_dominates_restoration_until_a_new_connection(
    restoration_code: int,
    state_after_reconnect: ConnectionState,
    epoch_increase: int,
) -> None:
    machine = make_machine(seed=17)
    connect(machine)
    initial_epoch = machine.connection_epoch
    backoff = machine.on_error_code(502)

    machine.on_error_code(restoration_code)

    assert machine.state is ConnectionState.DOWN
    assert machine.pending_transport_backoff == backoff
    assert machine.observation_is_fresh(machine.connection_epoch) is False

    machine.begin_connect()
    machine.on_connected()

    assert machine.state is state_after_reconnect
    assert machine.connection_epoch == initial_epoch + epoch_increase
    assert machine.pending_transport_backoff is None
    assert machine.transport_failures == 0
    if restoration_code == 1101:
        machine.mark_resubscribed()
    else:
        assert machine.record_observation(machine.connection_epoch) is True
    assert machine.state is ConnectionState.HEALTHY


def test_1100_then_1101_then_1102_keeps_both_recovery_obligations() -> None:
    machine = make_machine()
    connect(machine)
    initial_epoch = machine.connection_epoch

    for code in (1100, 1101, 1102):
        machine.on_error_code(code)

    assert machine.state is ConnectionState.DEGRADED
    assert machine.connection_epoch == initial_epoch + 1
    assert machine.resubscribe_required is True
    assert machine.awaiting_post_reconnect_observation is True
    # A current-epoch observation cannot bypass the resubscription debt.
    assert machine.record_observation(machine.connection_epoch) is False
    assert machine.awaiting_post_reconnect_observation is True

    machine.mark_resubscribed()
    assert machine.state is ConnectionState.RECOVERING
    assert machine.record_observation(machine.connection_epoch) is True
    assert machine.state is ConnectionState.HEALTHY


@pytest.mark.parametrize(
    "codes",
    [
        pytest.param((1101, 1102), id="data-lost-then-maintained"),
        pytest.param((1102, 1101), id="data-maintained-then-lost"),
    ],
)
def test_1101_and_1102_order_preserves_the_same_cumulative_obligations(
    codes: tuple[int, int],
) -> None:
    machine = make_machine()
    connect(machine)
    initial_epoch = machine.connection_epoch

    for code in codes:
        machine.on_error_code(code)

    assert machine.state is ConnectionState.DEGRADED
    assert machine.connection_epoch == initial_epoch + 1
    assert machine.resubscribe_required is True
    assert machine.awaiting_post_reconnect_observation is True

    machine.mark_resubscribed()
    assert machine.state is ConnectionState.RECOVERING
    assert machine.record_observation(machine.connection_epoch) is True
    assert machine.state is ConnectionState.HEALTHY


@pytest.mark.parametrize(
    "codes",
    [
        pytest.param((502, 502), id="duplicate-502"),
        pytest.param((502, 502, 502), id="two-duplicate-502s"),
    ],
)
def test_duplicate_502_events_share_one_failure_and_one_backoff(
    codes: tuple[int, ...],
) -> None:
    machine = make_machine(seed=23)
    delays = [machine.on_error_code(code) for code in codes]

    assert delays == [delays[0]] * len(delays)
    assert machine.pending_transport_backoff == delays[0]
    assert machine.transport_failures == 1
    assert machine.state is ConnectionState.DOWN


@pytest.mark.parametrize(
    "codes",
    [
        pytest.param((1101, 1101), id="adjacent-duplicate"),
        pytest.param((1101, 1102, 1101), id="duplicate-after-1102"),
    ],
)
def test_duplicate_1101_events_do_not_manufacture_epochs_while_debt_is_open(
    codes: tuple[int, ...],
) -> None:
    machine = make_machine()
    connect(machine)
    initial_epoch = machine.connection_epoch

    for code in codes:
        machine.on_error_code(code)

    assert machine.connection_epoch == initial_epoch + 1
    assert machine.resubscribe_required is True
    assert machine.state is ConnectionState.DEGRADED


@pytest.mark.parametrize(
    ("codes", "state_after_reconnect"),
    [
        pytest.param((1300,), ConnectionState.HEALTHY, id="port-change-only"),
        pytest.param((1300, 1101), ConnectionState.DEGRADED, id="port-change-then-1101"),
        pytest.param((1300, 1102), ConnectionState.RECOVERING, id="port-change-then-1102"),
        pytest.param(
            (1101, 1300, 1102),
            ConnectionState.DEGRADED,
            id="restoration-around-port-change",
        ),
        pytest.param(
            (502, 1300, 1101, 1102),
            ConnectionState.DEGRADED,
            id="transport-and-port-change",
        ),
    ],
)
def test_1300_dominates_other_statuses_until_port_reread_and_reconnect(
    codes: tuple[int, ...],
    state_after_reconnect: ConnectionState,
) -> None:
    machine = make_machine()
    connect(machine)

    for code in codes:
        machine.on_error_code(code)

    assert machine.state is ConnectionState.DOWN
    assert machine.reread_port_required is True
    assert machine.observation_is_fresh(machine.connection_epoch) is False
    with pytest.raises(PortRereadRequiredError):
        machine.begin_connect()

    machine.mark_port_reread()
    # Reading configuration alone never proves a new transport session.
    assert machine.state is ConnectionState.DOWN
    machine.begin_connect()
    machine.on_connected()
    assert machine.reread_port_required is False
    assert machine.state is state_after_reconnect


def test_only_a_failed_new_connection_attempt_advances_backoff() -> None:
    seed = 29
    machine = make_machine(
        seed=seed,
        base_backoff_seconds=1.0,
        backoff_multiplier=2.0,
        max_backoff_seconds=8.0,
    )
    oracle = random.Random(seed)
    expected_first = 0.5 + oracle.uniform(0.0, 0.5)
    expected_second = 1.0 + oracle.uniform(0.0, 1.0)

    first = machine.on_error_code(502)
    assert first is not None
    assert first == pytest.approx(expected_first)
    assert machine.on_error_code(502) == first
    assert machine.on_transport_error() == first
    assert machine.transport_failures == 1

    machine.begin_connect()
    assert machine.transport_failures == 1
    second = machine.on_connect_failed()
    assert second == pytest.approx(expected_second)
    assert machine.transport_failures == 2
    assert machine.on_error_code(502) == second
    assert machine.transport_failures == 2


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
