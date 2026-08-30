"""Layered envelope-quality evaluation and coverage reporting (DATA_QUALITY.md).

The document's ten validation layers — schema, identity, unit, time,
entitlement, bounds, bid/ask & OHLC coherence, coverage, session-aware
freshness, cross-source conflict — are each a pure function returning typed
:class:`QualityViolation` items. Aggregation is fail-closed, in this
precedence order:

1. any BLOCKING violation      -> ``EnvelopeQuality.INVALID``
2. else any CONFLICT violation -> ``EnvelopeQuality.CONFLICT``
3. else any STALE violation    -> ``EnvelopeQuality.STALE``
4. else any PARTIAL violation  -> ``EnvelopeQuality.PARTIAL``
5. else                        -> ``EnvelopeQuality.VALID``

``EnvelopeQuality.INSUFFICIENT_DATA`` is never produced here: it labels an
envelope whose payload could not be assembled at all and is assigned upstream
by the collector, before any layered evaluation is possible.

Facts the caller could not assess arrive as explicit ``None`` and fail closed
(a required unverified layer is a BLOCKING violation). Absent numeric values
stay ``None`` and are NEVER treated as zero: absence is handled by the
coverage layer, not by the bounds layer.

Pure module: no network, no system clock — freshness arrives pre-evaluated
(:func:`vertex_core.data.freshness.evaluate_freshness` with an injected
``now``).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal
from enum import Enum, unique
from types import MappingProxyType
from typing import Annotated, Any

from pydantic import Field, model_validator

from vertex_core.contracts.enums import DelayStatus, EnvelopeQuality, IdentityStatus
from vertex_core.contracts.types import (
    ContractModel,
    FiniteDecimal,
    FrozenStrMapping,
    NonEmptyStr,
    NonNegativeDecimal,
    UtcDatetime,
)
from vertex_core.data.conflict import ConflictRecord
from vertex_core.data.freshness import FreshnessStatus

__all__ = [
    "CoverageReport",
    "QualityChecks",
    "QualityLayer",
    "QualityViolation",
    "ViolationSeverity",
    "aggregate_violations",
    "check_bounds",
    "check_conflicts",
    "check_coverage",
    "check_entitlement",
    "check_freshness",
    "check_identity",
    "check_price_coherence",
    "check_schema",
    "check_time_order",
    "check_units",
    "collect_violations",
    "coverage_ratio",
    "evaluate_envelope_quality",
]

NonNegativeInt = Annotated[int, Field(ge=0)]
"""Integer greater than or equal to zero (strict: bool rejected)."""


@unique
class QualityLayer(str, Enum):
    """The ten validation layers, in canonical DATA_QUALITY.md order."""

    SCHEMA = "SCHEMA"
    IDENTITY = "IDENTITY"
    UNIT = "UNIT"
    TIME = "TIME"
    ENTITLEMENT = "ENTITLEMENT"
    BOUNDS = "BOUNDS"
    COHERENCE = "COHERENCE"
    COVERAGE = "COVERAGE"
    FRESHNESS = "FRESHNESS"
    CONFLICT = "CONFLICT"


@unique
class ViolationSeverity(str, Enum):
    """Severity of one violation; drives aggregation precedence.

    ``BLOCKING > CONFLICT > STALE > PARTIAL`` — the worst present severity
    determines the aggregated :class:`EnvelopeQuality`.
    """

    BLOCKING = "BLOCKING"
    CONFLICT = "CONFLICT"
    STALE = "STALE"
    PARTIAL = "PARTIAL"


def _empty_frozen_mapping() -> MappingProxyType[str, Any]:
    return MappingProxyType({})


class QualityViolation(ContractModel):
    """One typed violation raised by one validation layer."""

    layer: QualityLayer
    severity: ViolationSeverity
    code: NonEmptyStr
    message: str
    observed: FrozenStrMapping = Field(default_factory=_empty_frozen_mapping)


class CoverageReport(ContractModel):
    """Coverage of one collection: expected, received, valid, delayed, stale, missing.

    ``coverage_ratio`` is the usable coverage ``valid / expected`` (exactly
    ``1`` when ``expected == 0`` — vacuously complete). ``max_age_seconds`` is
    the age of the oldest received item; it stays ``None`` when no item was
    received or the age is unknown — absence is never reported as zero.
    """

    expected: NonNegativeInt
    received: NonNegativeInt
    valid: NonNegativeInt
    delayed: NonNegativeInt
    stale: NonNegativeInt
    missing: NonNegativeInt
    coverage_ratio: FiniteDecimal
    max_age_seconds: NonNegativeDecimal | None = None

    @model_validator(mode="after")
    def _check_consistency(self) -> CoverageReport:
        if self.received > self.expected:
            raise ValueError("received must not exceed expected")
        if self.valid + self.delayed + self.stale > self.received:
            raise ValueError("valid + delayed + stale must not exceed received")
        if self.missing != self.expected - self.received:
            raise ValueError("missing must equal expected - received")
        if not (Decimal(0) <= self.coverage_ratio <= Decimal(1)):
            raise ValueError("coverage_ratio must lie in [0, 1]")
        return self


def coverage_ratio(
    *,
    expected: int,
    received: int,
    valid: int,
    delayed: int,
    stale: int,
    missing: int,
    max_age_seconds: Decimal | None = None,
) -> CoverageReport:
    """Build a validated :class:`CoverageReport` from raw collection counts.

    The usable-coverage rate is ``valid / expected`` as an exact ``Decimal``
    division (``1`` when ``expected == 0``). All count invariants
    (``expected >= received``, ``valid + delayed + stale <= received``,
    ``missing == expected - received``, non-negative counts) are enforced by
    the model; any inconsistency raises ``pydantic.ValidationError``
    (fail-closed). ``max_age_seconds`` stays ``None`` when unknown — it is
    never defaulted to zero.
    """
    for name, count in (
        ("expected", expected),
        ("received", received),
        ("valid", valid),
        ("delayed", delayed),
        ("stale", stale),
        ("missing", missing),
    ):
        if isinstance(count, bool) or not isinstance(count, int):
            raise TypeError(f"{name} must be an int")
    ratio = Decimal(1) if expected == 0 else Decimal(valid) / Decimal(expected)
    return CoverageReport(
        expected=expected,
        received=received,
        valid=valid,
        delayed=delayed,
        stale=stale,
        missing=missing,
        coverage_ratio=ratio,
        max_age_seconds=max_age_seconds,
    )


class QualityChecks(ContractModel):
    """Typed facts feeding the ten validation layers for one envelope.

    The six assessment facts (``schema_valid``, ``identity_status``,
    ``unit_consistent``, ``rights_known``, ``delay_status``, ``freshness``)
    are required: the caller must state each one explicitly, and an explicit
    ``None`` means "not assessed", which fails closed as a BLOCKING violation.

    Numeric fields default to ``None`` when the source did not publish them;
    such absence is data shape (coverage concern), never a zero and never a
    bounds violation by itself.
    """

    schema_valid: bool | None
    identity_status: IdentityStatus | None
    unit_consistent: bool | None
    rights_known: bool | None
    delay_status: DelayStatus | None
    freshness: FreshnessStatus | None
    observed_at: UtcDatetime | None = None
    received_at: UtcDatetime | None = None
    bid: FiniteDecimal | None = None
    ask: FiniteDecimal | None = None
    last: FiniteDecimal | None = None
    open_price: FiniteDecimal | None = None
    high_price: FiniteDecimal | None = None
    low_price: FiniteDecimal | None = None
    close_price: FiniteDecimal | None = None
    volume: FiniteDecimal | None = None
    crossed_market_explained: bool | None = None
    coverage: CoverageReport | None = None
    conflicts: tuple[ConflictRecord, ...] = ()


def _violation(
    layer: QualityLayer,
    severity: ViolationSeverity,
    code: str,
    message: str,
    observed: Mapping[str, Any] | None = None,
) -> QualityViolation:
    return QualityViolation(
        layer=layer,
        severity=severity,
        code=code,
        message=message,
        observed=dict(observed) if observed is not None else {},
    )


# ---------------------------------------------------------------------------
# Layer 1 — schema and type
# ---------------------------------------------------------------------------


def check_schema(*, schema_valid: bool | None) -> tuple[QualityViolation, ...]:
    """Layer 1: the payload validated against its declared schema.

    ``None`` (never validated) fails closed exactly like ``False``.
    """
    if schema_valid is None:
        return (
            _violation(
                QualityLayer.SCHEMA,
                ViolationSeverity.BLOCKING,
                "SCHEMA_UNVERIFIED",
                "payload schema validation was never performed",
            ),
        )
    if not schema_valid:
        return (
            _violation(
                QualityLayer.SCHEMA,
                ViolationSeverity.BLOCKING,
                "SCHEMA_INVALID",
                "payload does not validate against its declared schema",
            ),
        )
    return ()


# ---------------------------------------------------------------------------
# Layer 2 — instrument identity
# ---------------------------------------------------------------------------


def check_identity(*, identity_status: IdentityStatus | None) -> tuple[QualityViolation, ...]:
    """Layer 2: the observation is bound to an unambiguously resolved identity."""
    if identity_status is None:
        return (
            _violation(
                QualityLayer.IDENTITY,
                ViolationSeverity.BLOCKING,
                "IDENTITY_UNVERIFIED",
                "instrument identity resolution was never assessed",
            ),
        )
    if identity_status is not IdentityStatus.RESOLVED:
        return (
            _violation(
                QualityLayer.IDENTITY,
                ViolationSeverity.BLOCKING,
                f"IDENTITY_{identity_status.value}",
                f"instrument identity is {identity_status.value}",
                {"identity_status": identity_status.value},
            ),
        )
    return ()


# ---------------------------------------------------------------------------
# Layer 3 — unit, currency and multiplier
# ---------------------------------------------------------------------------


def check_units(*, unit_consistent: bool | None) -> tuple[QualityViolation, ...]:
    """Layer 3: unit, currency and multiplier are declared and consistent."""
    if unit_consistent is None:
        return (
            _violation(
                QualityLayer.UNIT,
                ViolationSeverity.BLOCKING,
                "UNIT_UNVERIFIED",
                "unit/currency/multiplier consistency was never assessed",
            ),
        )
    if not unit_consistent:
        return (
            _violation(
                QualityLayer.UNIT,
                ViolationSeverity.BLOCKING,
                "UNIT_INCONSISTENT",
                "unit, currency or multiplier is inconsistent with the contract",
            ),
        )
    return ()


# ---------------------------------------------------------------------------
# Layer 4 — timestamps, temporal order and clock drift
# ---------------------------------------------------------------------------


def check_time_order(
    *,
    observed_at: UtcDatetime | None,
    received_at: UtcDatetime | None,
) -> tuple[QualityViolation, ...]:
    """Layer 4: an observation cannot be observed after it was received.

    Both timestamps are optional (absent metadata stays ``None``); the order
    is only checkable — and checked — when both are present.
    """
    if observed_at is not None and received_at is not None and observed_at > received_at:
        return (
            _violation(
                QualityLayer.TIME,
                ViolationSeverity.BLOCKING,
                "OBSERVED_AFTER_RECEIVED",
                "observed_at is later than received_at (clock incoherence)",
                {
                    "observed_at": observed_at.isoformat(),
                    "received_at": received_at.isoformat(),
                },
            ),
        )
    return ()


# ---------------------------------------------------------------------------
# Layer 5 — entitlement and live/delayed type
# ---------------------------------------------------------------------------


def check_entitlement(
    *,
    rights_known: bool | None,
    delay_status: DelayStatus | None,
) -> tuple[QualityViolation, ...]:
    """Layer 5: rights are known and the delay dimension is declared.

    ``delay_status=None`` means the delay dimension was never assessed and
    fails closed; the explicit member ``DelayStatus.UNKNOWN`` is an honest
    declared state and is NOT a quality violation by itself (downstream gates
    requiring live data fail closed on it separately).
    """
    violations: list[QualityViolation] = []
    if rights_known is None or not rights_known:
        violations.append(
            _violation(
                QualityLayer.ENTITLEMENT,
                ViolationSeverity.BLOCKING,
                "RIGHTS_UNKNOWN",
                "data rights/entitlement for this observation are not established",
            )
        )
    if delay_status is None:
        violations.append(
            _violation(
                QualityLayer.ENTITLEMENT,
                ViolationSeverity.BLOCKING,
                "DELAY_STATUS_MISSING",
                "live/delayed type was never assessed "
                "(use DelayStatus.UNKNOWN to declare it unknown)",
            )
        )
    return tuple(violations)


# ---------------------------------------------------------------------------
# Layer 6 — physical and financial bounds
# ---------------------------------------------------------------------------


def check_bounds(
    *,
    bid: Decimal | None = None,
    ask: Decimal | None = None,
    last: Decimal | None = None,
    open_price: Decimal | None = None,
    high_price: Decimal | None = None,
    low_price: Decimal | None = None,
    close_price: Decimal | None = None,
    volume: Decimal | None = None,
) -> tuple[QualityViolation, ...]:
    """Layer 6: prices and sizes respect physical/financial bounds.

    Only PRESENT values are checked: an absent value stays ``None`` and never
    becomes zero, so absence alone can never raise a bounds violation.
    Non-finite values are rejected earlier at the DTO boundary.
    """
    violations: list[QualityViolation] = []
    for name, value in (
        ("bid", bid),
        ("ask", ask),
        ("last", last),
        ("open_price", open_price),
        ("high_price", high_price),
        ("low_price", low_price),
        ("close_price", close_price),
    ):
        if value is not None and value < 0:
            violations.append(
                _violation(
                    QualityLayer.BOUNDS,
                    ViolationSeverity.BLOCKING,
                    "NEGATIVE_PRICE",
                    f"{name} is negative, outside financial bounds for this payload",
                    {name: str(value)},
                )
            )
    if volume is not None and volume < 0:
        violations.append(
            _violation(
                QualityLayer.BOUNDS,
                ViolationSeverity.BLOCKING,
                "NEGATIVE_VOLUME",
                "volume is negative, outside physical bounds",
                {"volume": str(volume)},
            )
        )
    return tuple(violations)


# ---------------------------------------------------------------------------
# Layer 7 — bid/ask and OHLC coherence
# ---------------------------------------------------------------------------


def check_price_coherence(
    *,
    bid: Decimal | None = None,
    ask: Decimal | None = None,
    crossed_market_explained: bool | None = None,
    open_price: Decimal | None = None,
    high_price: Decimal | None = None,
    low_price: Decimal | None = None,
    close_price: Decimal | None = None,
) -> tuple[QualityViolation, ...]:
    """Layer 7: bid/ask and OHLC internal coherence.

    An unexplained ``bid > ask`` is a violation; a crossed market explicitly
    flagged by the source (``crossed_market_explained=True``) is kept as data.
    ``crossed_market_explained=None`` counts as unexplained (fail-closed).
    Each OHLC rule is only checkable when both of its operands are present.
    """
    violations: list[QualityViolation] = []
    if bid is not None and ask is not None and bid > ask:
        if crossed_market_explained is not True:
            violations.append(
                _violation(
                    QualityLayer.COHERENCE,
                    ViolationSeverity.BLOCKING,
                    "BID_ABOVE_ASK_UNEXPLAINED",
                    "bid exceeds ask without a source-documented crossed-market explanation",
                    {"bid": str(bid), "ask": str(ask)},
                )
            )
    if high_price is not None and low_price is not None and high_price < low_price:
        violations.append(
            _violation(
                QualityLayer.COHERENCE,
                ViolationSeverity.BLOCKING,
                "OHLC_HIGH_BELOW_LOW",
                "high is below low",
                {"high_price": str(high_price), "low_price": str(low_price)},
            )
        )
    for name, value in (("open_price", open_price), ("close_price", close_price)):
        if value is None:
            continue
        if (high_price is not None and value > high_price) or (
            low_price is not None and value < low_price
        ):
            violations.append(
                _violation(
                    QualityLayer.COHERENCE,
                    ViolationSeverity.BLOCKING,
                    "OHLC_VALUE_OUTSIDE_RANGE",
                    f"{name} lies outside the [low, high] range",
                    {name: str(value)},
                )
            )
    return tuple(violations)


# ---------------------------------------------------------------------------
# Layer 8 — coverage required by the usage
# ---------------------------------------------------------------------------


def check_coverage(*, coverage: CoverageReport | None) -> tuple[QualityViolation, ...]:
    """Layer 8: collection coverage. ``None`` = not a collection (no violation).

    A coverage ratio below 1 marks the observation PARTIAL; the report keeps
    the exact expected/received/valid/delayed/stale/missing counts so the UI
    can never claim a "complete chain" without proof.
    """
    if coverage is None:
        return ()
    if coverage.coverage_ratio < 1:
        return (
            _violation(
                QualityLayer.COVERAGE,
                ViolationSeverity.PARTIAL,
                "COVERAGE_PARTIAL",
                "collection coverage is below the full expected set",
                {
                    "expected": coverage.expected,
                    "received": coverage.received,
                    "valid": coverage.valid,
                    "delayed": coverage.delayed,
                    "stale": coverage.stale,
                    "missing": coverage.missing,
                    "coverage_ratio": str(coverage.coverage_ratio),
                },
            ),
        )
    return ()


# ---------------------------------------------------------------------------
# Layer 9 — session-aware freshness
# ---------------------------------------------------------------------------


def check_freshness(*, freshness: FreshnessStatus | None) -> tuple[QualityViolation, ...]:
    """Layer 9: pre-evaluated session-aware freshness.

    ``None`` (never evaluated) fails closed; ``INVALID`` (observation dated in
    the future) is BLOCKING; ``STALE`` degrades the envelope to STALE.
    """
    if freshness is None:
        return (
            _violation(
                QualityLayer.FRESHNESS,
                ViolationSeverity.BLOCKING,
                "FRESHNESS_UNVERIFIED",
                "freshness was never evaluated against a named policy",
            ),
        )
    if freshness is FreshnessStatus.INVALID:
        return (
            _violation(
                QualityLayer.FRESHNESS,
                ViolationSeverity.BLOCKING,
                "FUTURE_OBSERVATION",
                "observation is dated in the future relative to the evaluation clock",
                {"freshness": freshness.value},
            ),
        )
    if freshness is FreshnessStatus.STALE:
        return (
            _violation(
                QualityLayer.FRESHNESS,
                ViolationSeverity.STALE,
                "STALE_OBSERVATION",
                "observation is outside its policy freshness window",
                {"freshness": freshness.value},
            ),
        )
    return ()


# ---------------------------------------------------------------------------
# Layer 10 — cross-source conflict
# ---------------------------------------------------------------------------


def check_conflicts(*, conflicts: tuple[ConflictRecord, ...]) -> tuple[QualityViolation, ...]:
    """Layer 10: detected cross-source conflicts (both sides preserved upstream)."""
    violations: list[QualityViolation] = []
    for record in conflicts:
        sources = ", ".join(sorted({obs.source for obs in record.observations}))
        violations.append(
            _violation(
                QualityLayer.CONFLICT,
                ViolationSeverity.CONFLICT,
                f"SOURCE_CONFLICT_{record.code}",
                f"unresolved conflict on field {record.field_name!r} between sources {sources}",
                {"field_name": record.field_name, "code": record.code},
            )
        )
    return tuple(violations)


# ---------------------------------------------------------------------------
# Orchestration and aggregation
# ---------------------------------------------------------------------------


def collect_violations(checks: QualityChecks) -> tuple[QualityViolation, ...]:
    """Run the ten layers in canonical order and concatenate their violations."""
    if not isinstance(checks, QualityChecks):
        raise TypeError("checks must be a QualityChecks instance")
    violations: list[QualityViolation] = []
    violations.extend(check_schema(schema_valid=checks.schema_valid))
    violations.extend(check_identity(identity_status=checks.identity_status))
    violations.extend(check_units(unit_consistent=checks.unit_consistent))
    violations.extend(
        check_time_order(observed_at=checks.observed_at, received_at=checks.received_at)
    )
    violations.extend(
        check_entitlement(rights_known=checks.rights_known, delay_status=checks.delay_status)
    )
    violations.extend(
        check_bounds(
            bid=checks.bid,
            ask=checks.ask,
            last=checks.last,
            open_price=checks.open_price,
            high_price=checks.high_price,
            low_price=checks.low_price,
            close_price=checks.close_price,
            volume=checks.volume,
        )
    )
    violations.extend(
        check_price_coherence(
            bid=checks.bid,
            ask=checks.ask,
            crossed_market_explained=checks.crossed_market_explained,
            open_price=checks.open_price,
            high_price=checks.high_price,
            low_price=checks.low_price,
            close_price=checks.close_price,
        )
    )
    violations.extend(check_coverage(coverage=checks.coverage))
    violations.extend(check_freshness(freshness=checks.freshness))
    violations.extend(check_conflicts(conflicts=checks.conflicts))
    return tuple(violations)


def aggregate_violations(violations: Sequence[QualityViolation]) -> EnvelopeQuality:
    """Aggregate typed violations into one :class:`EnvelopeQuality` (fail-closed).

    Precedence: BLOCKING -> INVALID, then CONFLICT, then STALE, then PARTIAL,
    else VALID. ``INSUFFICIENT_DATA`` is assigned upstream, never here.
    """
    severities = set()
    for violation in violations:
        if not isinstance(violation, QualityViolation):
            raise TypeError("every violation must be a QualityViolation")
        severities.add(violation.severity)
    if ViolationSeverity.BLOCKING in severities:
        return EnvelopeQuality.INVALID
    if ViolationSeverity.CONFLICT in severities:
        return EnvelopeQuality.CONFLICT
    if ViolationSeverity.STALE in severities:
        return EnvelopeQuality.STALE
    if ViolationSeverity.PARTIAL in severities:
        return EnvelopeQuality.PARTIAL
    return EnvelopeQuality.VALID


def evaluate_envelope_quality(checks: QualityChecks) -> EnvelopeQuality:
    """Evaluate one envelope's quality through the ten layers, fail-closed."""
    return aggregate_violations(collect_violations(checks))
