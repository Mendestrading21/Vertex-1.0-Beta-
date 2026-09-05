"""IBKR connection state machine (docs/04-integrations/IBKR.md, "Machine d'état").

Deterministic, side-effect free: no clock, no network, no logging. The owner
drives it with provider error codes and transport events; the machine answers
with states, epochs and backoff delays.

Semantics:

- ``1100`` -> ``DOWN``: connectivity lost, every fresh result is blocked;
- ``1101`` -> connectivity restored, data LOST: new ``connection_epoch``,
  full resubscription required before anything is healthy again;
- ``1102`` -> connectivity restored, data maintained: wait for ONE
  post-reconnection observation of the current epoch before ``HEALTHY``;
- ``1300`` -> socket port changed: the port must be re-read before any
  reconnection attempt is allowed;
- EOF/502 -> transport failure: exponential backoff with seeded jitter (the
  random generator is injected, so tests are deterministic) plus a
  reconnection lock allowing a single concurrent attempt.

Every observation is stamped with the epoch current at emission time; an
observation from an older epoch is NEVER considered fresh.
"""

from __future__ import annotations

import random
from enum import Enum, unique

__all__ = [
    "PROVIDER_STATUS_CODES",
    "TRANSPORT_ERROR_CODE_502",
    "ConnectionState",
    "ConnectionStateMachine",
    "InvalidTransitionError",
    "PortRereadRequiredError",
    "ReconnectInProgressError",
]

#: TWS "couldn't connect" transport error code, handled as EOF-equivalent.
TRANSPORT_ERROR_CODE_502 = 502

# Codes that change connection admissibility. Other IBKR messages remain
# request-scoped provider facts and never drive this machine.
PROVIDER_STATUS_CODES = frozenset({502, 1100, 1101, 1102, 1300})


@unique
class ConnectionState(str, Enum):
    """Lifecycle states of the IBKR information session."""

    STARTING = "STARTING"
    CONNECTING = "CONNECTING"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    DOWN = "DOWN"
    RECOVERING = "RECOVERING"
    STOPPED = "STOPPED"


class InvalidTransitionError(RuntimeError):
    """A transition was requested from a state that does not allow it."""


class ReconnectInProgressError(RuntimeError):
    """A second concurrent reconnection attempt was refused (single lock)."""


class PortRereadRequiredError(RuntimeError):
    """1300 was received: the socket port must be re-read before reconnecting."""


class ConnectionStateMachine:
    """State machine for one IBKR API session.

    ``rng`` MUST be injected (seeded in tests) — jitter is never drawn from an
    implicit global generator.
    """

    def __init__(
        self,
        *,
        rng: random.Random,
        base_backoff_seconds: float = 1.0,
        backoff_multiplier: float = 2.0,
        max_backoff_seconds: float = 60.0,
    ) -> None:
        if base_backoff_seconds <= 0 or max_backoff_seconds <= 0:
            raise ValueError("backoff bounds must be strictly positive")
        if backoff_multiplier < 1.0:
            raise ValueError("backoff_multiplier must be >= 1")
        self._rng = rng
        self._base = base_backoff_seconds
        self._multiplier = backoff_multiplier
        self._max = max_backoff_seconds
        self._state = ConnectionState.STARTING
        self._epoch = 0
        self._transport_failures = 0
        self._pending_transport_backoff: float | None = None
        self._reconnect_in_progress = False
        self._transport_down = False
        self._connectivity_down = False
        self._resubscribe_required = False
        self._reread_port_required = False
        self._awaiting_post_reconnect_observation = False

    # -- queries ----------------------------------------------------------

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def connection_epoch(self) -> int:
        """Strictly increasing epoch; bumped on every connect and on 1101."""
        return self._epoch

    @property
    def resubscribe_required(self) -> bool:
        return self._resubscribe_required

    @property
    def reread_port_required(self) -> bool:
        return self._reread_port_required

    @property
    def awaiting_post_reconnect_observation(self) -> bool:
        return self._awaiting_post_reconnect_observation

    @property
    def reconnect_in_progress(self) -> bool:
        return self._reconnect_in_progress

    @property
    def transport_failures(self) -> int:
        return self._transport_failures

    @property
    def pending_transport_backoff(self) -> float | None:
        """Backoff already drawn for the current transport incident, if any."""
        return self._pending_transport_backoff

    def observation_is_fresh(self, epoch: int) -> bool:
        """True only for a current-epoch observation in a HEALTHY session.

        An observation stamped with an older epoch is never fresh, whatever
        the current state (fail-closed).
        """
        return epoch == self._epoch and self._state is ConnectionState.HEALTHY

    # -- reconnection lock and connect flow -------------------------------

    def begin_connect(self) -> None:
        """Acquire the single reconnection slot and enter ``CONNECTING``.

        Refused while another attempt is in flight, while a 1300 port re-read
        is pending, or once stopped.
        """
        if self._state is ConnectionState.STOPPED:
            raise InvalidTransitionError("cannot connect a stopped session")
        if self._state is ConnectionState.HEALTHY:
            raise InvalidTransitionError("session is already healthy; no reconnect allowed")
        if self._reconnect_in_progress:
            raise ReconnectInProgressError("a reconnection attempt is already in progress")
        if self._reread_port_required:
            raise PortRereadRequiredError(
                "1300 received: re-read the socket port before reconnecting"
            )
        self._reconnect_in_progress = True
        # A new attempt owns a new failure slot. Repeated 502 callbacks before
        # this point shared the previous incident and therefore one jitter.
        self._pending_transport_backoff = None
        self._state = ConnectionState.CONNECTING

    def on_connected(self) -> None:
        """Successful (re)connection: new epoch, backoff reset, lock released."""
        if self._state is not ConnectionState.CONNECTING:
            raise InvalidTransitionError("on_connected requires state CONNECTING")
        self._epoch += 1
        self._transport_down = False
        self._transport_failures = 0
        self._pending_transport_backoff = None
        self._reconnect_in_progress = False
        self._refresh_state()

    def on_connect_failed(self) -> float:
        """Failed attempt: release the lock, go ``DOWN``, return backoff delay."""
        if self._state is not ConnectionState.CONNECTING:
            raise InvalidTransitionError("on_connect_failed requires state CONNECTING")
        self._reconnect_in_progress = False
        return self._register_transport_failure()

    def mark_port_reread(self) -> None:
        """Acknowledge that the socket port was re-read after a 1300."""
        self._reread_port_required = False
        self._refresh_state()

    def stop(self) -> None:
        """Deliberate shutdown; terminal state."""
        self._state = ConnectionState.STOPPED
        self._reconnect_in_progress = False

    # -- provider events ---------------------------------------------------

    def on_error_code(self, code: int) -> float | None:
        """Apply one provider status code; returns a backoff delay for 502."""
        if self._state is ConnectionState.STOPPED:
            return None
        if code == 1100:
            # Connectivity lost: block every fresh result.
            self._connectivity_down = True
            self._refresh_state()
            return None
        if code == 1101:
            # Restored, data lost: new epoch, full resubscription required.
            # IBKR can repeat the same status. While the resubscription debt is
            # still open, replaying 1101 must not manufacture another epoch.
            if not self._resubscribe_required:
                self._epoch += 1
            self._resubscribe_required = True
            self._connectivity_down = False
            self._refresh_state()
            return None
        if code == 1102:
            # Restored, data maintained: one observation required before HEALTHY.
            self._awaiting_post_reconnect_observation = True
            self._connectivity_down = False
            self._refresh_state()
            return None
        if code == 1300:
            # Socket port changed: re-read the port, then reconnect.
            self._reread_port_required = True
            self._transport_down = True
            self._refresh_state()
            return None
        if code == TRANSPORT_ERROR_CODE_502:
            return self.on_transport_error()
        return None

    def on_transport_error(self) -> float:
        """EOF/502: go ``DOWN`` and return the next jittered backoff delay."""
        if self._state is ConnectionState.STOPPED:
            return 0.0
        self._reconnect_in_progress = False
        if self._pending_transport_backoff is not None:
            self._transport_down = True
            self._refresh_state()
            return self._pending_transport_backoff
        return self._register_transport_failure()

    def _register_transport_failure(self) -> float:
        self._transport_failures += 1
        self._transport_down = True
        self._pending_transport_backoff = self._next_backoff_delay()
        self._refresh_state()
        return self._pending_transport_backoff

    def _refresh_state(self) -> None:
        """Reduce cumulative safety obligations to one externally visible state."""
        if self._state is ConnectionState.STOPPED:
            return
        if self._reread_port_required or self._transport_down or self._connectivity_down:
            self._state = ConnectionState.DOWN
        elif self._resubscribe_required:
            self._state = ConnectionState.DEGRADED
        elif self._awaiting_post_reconnect_observation:
            self._state = ConnectionState.RECOVERING
        else:
            self._state = ConnectionState.HEALTHY

    def _next_backoff_delay(self) -> float:
        """Capped exponential backoff with injected half-jitter.

        delay in [capped/2, capped] where capped = min(max, base * m**(n-1)).
        Deterministic for a seeded injected generator.
        """
        exponent = max(0, self._transport_failures - 1)
        capped = min(self._max, self._base * (self._multiplier**exponent))
        return capped / 2.0 + self._rng.uniform(0.0, capped / 2.0)

    # -- observations and recovery ----------------------------------------

    def mark_resubscribed(self) -> None:
        """All subscriptions were re-established after a 1101."""
        if not self._resubscribe_required:
            raise InvalidTransitionError("mark_resubscribed without a pending resubscription")
        self._resubscribe_required = False
        self._refresh_state()

    def record_observation(self, epoch: int) -> bool:
        """Record one observation stamped with ``epoch``.

        Returns True only when the observation counts as fresh. An observation
        from an older epoch never does, and never advances recovery. The first
        current-epoch observation after a 1102 promotes ``RECOVERING`` to
        ``HEALTHY``.
        """
        if epoch != self._epoch:
            return False
        if self._awaiting_post_reconnect_observation and self._state is ConnectionState.RECOVERING:
            self._awaiting_post_reconnect_observation = False
            self._refresh_state()
        return self._state is ConnectionState.HEALTHY
