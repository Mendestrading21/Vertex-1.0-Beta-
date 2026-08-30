"""Session-aware freshness policies and evaluation (DATA_QUALITY.md).

TTL is never one global number: each named, versioned policy binds a data
usage to one TTL per market-session context (``OPEN`` / ``CLOSED``). The
registry values below are **provisional policy values** — versioned
configuration owned by the data_quality module, not market truths; changing
any TTL requires a policy version bump.

Fail-closed rules:

- an unknown policy name raises :class:`UnknownFreshnessPolicyError`; there is
  no silent default TTL;
- a naive datetime is rejected (``ValueError`` via ``ensure_utc``);
- an observation timestamped in the future (``now < as_of``) is explicitly
  :attr:`FreshnessStatus.INVALID`, never silently treated as fresh or stale.

Pure module: no network, no system clock — the caller injects ``now``.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from enum import Enum, unique
from types import MappingProxyType

from vertex_core.contracts.types import ContractModel, NonEmptyStr, PositiveInt, ensure_utc

__all__ = [
    "FRESHNESS_POLICIES",
    "FRESHNESS_REGISTRY_VERSION",
    "FreshnessPolicy",
    "FreshnessStatus",
    "SessionState",
    "UnknownFreshnessPolicyError",
    "evaluate_freshness",
    "get_freshness_policy",
]


@unique
class SessionState(str, Enum):
    """Market-session context used to select a policy TTL."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"


@unique
class FreshnessStatus(str, Enum):
    """Outcome of one freshness evaluation.

    ``INVALID`` marks an observation dated in the future relative to the
    injected clock (``now < as_of``): a temporal incoherence, distinct from
    both fresh and stale data.
    """

    FRESH = "FRESH"
    STALE = "STALE"
    INVALID = "INVALID"


class UnknownFreshnessPolicyError(KeyError):
    """Raised when a policy name is not in the registry (no silent default TTL)."""


class FreshnessPolicy(ContractModel):
    """One named, versioned freshness policy with a TTL per session context.

    TTLs are policy configuration, not market data; they are versioned and a
    change to either TTL requires a version bump of the policy.
    """

    name: NonEmptyStr
    version: NonEmptyStr
    ttl_open_seconds: PositiveInt
    ttl_closed_seconds: PositiveInt

    def ttl_seconds_for(self, session_state: SessionState) -> int:
        """Return the TTL in seconds for ``session_state`` (fail-closed on type)."""
        if not isinstance(session_state, SessionState):
            raise TypeError("session_state must be a SessionState member")
        if session_state is SessionState.OPEN:
            return self.ttl_open_seconds
        return self.ttl_closed_seconds


FRESHNESS_REGISTRY_VERSION = "1.0.0"
"""Version of the policy registry as a whole; bumped with any policy change."""

_POLICIES: tuple[FreshnessPolicy, ...] = (
    # All TTLs below are provisional versioned policy values (initial guesses
    # to be tuned with operational evidence), never observed market truths.
    FreshnessPolicy(
        name="intraday_quote", version="1.0.0", ttl_open_seconds=5, ttl_closed_seconds=900
    ),
    FreshnessPolicy(
        name="selected_option_quote", version="1.0.0", ttl_open_seconds=10, ttl_closed_seconds=900
    ),
    FreshnessPolicy(
        name="option_surface", version="1.0.0", ttl_open_seconds=300, ttl_closed_seconds=3600
    ),
    # A daily bar remains usable through the next session; the CLOSED TTL
    # covers a normal weekend (72h) but not an extended halt.
    FreshnessPolicy(
        name="daily_bar", version="1.0.0", ttl_open_seconds=86400, ttl_closed_seconds=259200
    ),
    FreshnessPolicy(
        name="news_attention", version="1.0.0", ttl_open_seconds=900, ttl_closed_seconds=3600
    ),
    FreshnessPolicy(
        name="corporate_event", version="1.0.0", ttl_open_seconds=86400, ttl_closed_seconds=86400
    ),
    FreshnessPolicy(
        name="fundamental_filing",
        version="1.0.0",
        ttl_open_seconds=604800,
        ttl_closed_seconds=604800,
    ),
    # Valuation mark of the manually declared portfolio (user declarations
    # only — never a broker account read).
    FreshnessPolicy(
        name="portfolio_mark", version="1.0.0", ttl_open_seconds=300, ttl_closed_seconds=86400
    ),
)

FRESHNESS_POLICIES: Mapping[str, FreshnessPolicy] = MappingProxyType(
    {policy.name: policy for policy in _POLICIES}
)
"""Read-only registry: policy name -> versioned :class:`FreshnessPolicy`."""


def get_freshness_policy(name: str) -> FreshnessPolicy:
    """Return the registered policy for ``name``.

    Raises :class:`UnknownFreshnessPolicyError` for any unregistered name —
    an unknown usage never silently receives a default TTL.
    """
    if not isinstance(name, str):
        raise TypeError("policy name must be a str")
    try:
        return FRESHNESS_POLICIES[name]
    except KeyError:
        raise UnknownFreshnessPolicyError(
            f"unknown freshness policy {name!r}: no default TTL exists (fail-closed)"
        ) from None


def evaluate_freshness(
    policy: FreshnessPolicy,
    *,
    as_of: datetime,
    now: datetime,
    session_state: SessionState,
) -> FreshnessStatus:
    """Evaluate the freshness of an observation dated ``as_of`` at instant ``now``.

    - ``now < as_of`` (future observation) -> :attr:`FreshnessStatus.INVALID`;
    - age ``<=`` the session TTL -> :attr:`FreshnessStatus.FRESH` (the boundary
      instant ``age == ttl`` is still fresh);
    - otherwise -> :attr:`FreshnessStatus.STALE`.

    Both datetimes must be timezone-aware (naive input raises ``ValueError``);
    they are compared as instants after normalization to UTC. The caller
    injects ``now`` — this function never reads a system clock.
    """
    if not isinstance(policy, FreshnessPolicy):
        raise TypeError("policy must be a FreshnessPolicy")
    if not isinstance(session_state, SessionState):
        raise TypeError("session_state must be a SessionState member")
    if not isinstance(as_of, datetime) or not isinstance(now, datetime):
        raise TypeError("as_of and now must be datetime instances")
    as_of_utc = ensure_utc(as_of)
    now_utc = ensure_utc(now)
    if now_utc < as_of_utc:
        return FreshnessStatus.INVALID
    age = now_utc - as_of_utc
    ttl = timedelta(seconds=policy.ttl_seconds_for(session_state))
    if age <= ttl:
        return FreshnessStatus.FRESH
    return FreshnessStatus.STALE
