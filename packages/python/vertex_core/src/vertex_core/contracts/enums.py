"""Canonical enumerations for Vertex contracts.

Single authoritative vocabulary per ADR-014 (canonical enums). Every member is
a ``str``-based enum whose value equals its name, so members serialize to their
canonical wire form. No concurrent vocabulary may be declared elsewhere; the
historical ``REJECT/WATCH/RESEARCH`` and ``WARN/UNKNOWN`` gate words map onto
this family and are never re-introduced.
"""

from enum import Enum, unique

__all__ = [
    "AFFIRMATIVE_STATUSES",
    "NON_AFFIRMATIVE_STATUSES",
    "AdviceStatus",
    "AssetClass",
    "CalculationStatus",
    "DelayStatus",
    "Direction",
    "DirectionHypothesis",
    "EnvelopeQuality",
    "ExerciseStyle",
    "GateStatus",
    "IdentityStatus",
    "OptionRight",
    "SettlementType",
    "SnapshotQuality",
    "SourceCapabilityStatus",
]


@unique
class AdviceStatus(str, Enum):
    """Canonical verdict status of an ``AdviceResult`` (ADR-014).

    ``BLOCKED`` (a gate closed), ``INSUFFICIENT_DATA`` (required inputs
    missing), ``OBSERVE`` (valid data, not enough for study), ``REVIEW``
    (worth analytical study), ``QUALIFIED`` (passes all gates). Distinct from
    :class:`Direction`; never a transactional instruction.
    """

    BLOCKED = "BLOCKED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    OBSERVE = "OBSERVE"
    REVIEW = "REVIEW"
    QUALIFIED = "QUALIFIED"


#: Statuses that make a POSITIVE claim about an opportunity — the ones that put
#: a card in front of the user. This is the partition the product already used,
#: written down once instead of three times: ``vertex_worker.opportunities``
#: routes exactly these three into its qualified group.
#:
#: It exists because two competing literals had drifted apart: production
#: counted ``OBSERVE`` as affirmative while a degradation campaign's own literal
#: did not, so a scenario that produced ``OBSERVE`` would have satisfied an
#: invariant meant to forbid it. One authority, imported everywhere.
AFFIRMATIVE_STATUSES: frozenset[AdviceStatus] = frozenset(
    {AdviceStatus.OBSERVE, AdviceStatus.REVIEW, AdviceStatus.QUALIFIED}
)

#: The complement. Together with :data:`AFFIRMATIVE_STATUSES` it covers
#: ``AdviceStatus`` exactly; a sixth member added tomorrow breaks the exhaustivity
#: test rather than silently falling on the permissive side.
NON_AFFIRMATIVE_STATUSES: frozenset[AdviceStatus] = frozenset(
    {AdviceStatus.BLOCKED, AdviceStatus.INSUFFICIENT_DATA}
)


@unique
class Direction(str, Enum):
    """Analytical directional reading attached to a verdict (ADR-014)."""

    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


@unique
class GateStatus(str, Enum):
    """Result of one decision gate: ``PASS``, ``DEGRADE`` or ``BLOCK``.

    A gate that cannot be evaluated is ``BLOCK`` with
    ``reason_code = "UNEVALUABLE"`` (fail-closed); there is no ``UNKNOWN``
    gate state (ADR-014).
    """

    PASS = "PASS"  # noqa: S105 (faux positif : pas un secret)
    DEGRADE = "DEGRADE"
    BLOCK = "BLOCK"


@unique
class DirectionHypothesis(str, Enum):
    """Options-flow anomaly hypothesis. Qualifies a hypothesis, never a verdict."""

    UP = "UP"
    DOWN = "DOWN"
    VOLATILITY = "VOLATILITY"
    HEDGE_LIKELY = "HEDGE_LIKELY"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


@unique
class EnvelopeQuality(str, Enum):
    """Quality of a single sourced observation carried by a ``DataEnvelope``."""

    VALID = "VALID"
    PARTIAL = "PARTIAL"
    STALE = "STALE"
    INVALID = "INVALID"
    CONFLICT = "CONFLICT"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@unique
class DelayStatus(str, Enum):
    """Delay state of a market observation as delivered by its source."""

    LIVE = "LIVE"
    FROZEN = "FROZEN"
    DELAYED = "DELAYED"
    DELAYED_FROZEN = "DELAYED_FROZEN"
    UNKNOWN = "UNKNOWN"


@unique
class SnapshotQuality(str, Enum):
    """Quality of an evidence snapshot (namespace distinct from ``EnvelopeQuality``).

    Neither quality namespace converts implicitly into the other (ADR-014).
    """

    GOOD = "GOOD"
    PARTIAL = "PARTIAL"
    DEGRADED = "DEGRADED"
    MISSING = "MISSING"
    CONTRADICTORY = "CONTRADICTORY"


@unique
class IdentityStatus(str, Enum):
    """Resolution state of an instrument identity. Collisions stay ``UNRESOLVED``."""

    RESOLVED = "RESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"


@unique
class AssetClass(str, Enum):
    """Canonical asset class of an identified instrument."""

    STOCK = "STOCK"
    ETF = "ETF"
    INDEX = "INDEX"
    OPTION = "OPTION"


@unique
class OptionRight(str, Enum):
    """Right of an option contract."""

    CALL = "CALL"
    PUT = "PUT"


@unique
class ExerciseStyle(str, Enum):
    """Exercise style of an option contract."""

    AMERICAN = "AMERICAN"
    EUROPEAN = "EUROPEAN"


@unique
class SettlementType(str, Enum):
    """Settlement type of an option contract."""

    PHYSICAL = "PHYSICAL"
    CASH = "CASH"


@unique
class SourceCapabilityStatus(str, Enum):
    """Effective availability of one data-source capability (market data only)."""

    AVAILABLE = "AVAILABLE"
    DELAYED = "DELAYED"
    NOT_ENTITLED = "NOT_ENTITLED"
    UNSUPPORTED = "UNSUPPORTED"
    ERROR = "ERROR"
    MANUAL_EXPORT = "MANUAL_EXPORT"


@unique
class CalculationStatus(str, Enum):
    """Outcome of a deterministic calculation.

    ``NOT_IMPLEMENTED`` names an absent capability honestly; it is never
    presented as a pending automation.
    """

    OK = "OK"
    INVALID = "INVALID"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
