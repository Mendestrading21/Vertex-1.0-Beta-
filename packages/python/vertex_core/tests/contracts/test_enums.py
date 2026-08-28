"""Canonical enum family per ADR-014: exact member sets, str-based wire values."""

import pytest

from vertex_core.contracts import (
    AdviceStatus,
    AssetClass,
    CalculationStatus,
    DelayStatus,
    Direction,
    DirectionHypothesis,
    EnvelopeQuality,
    ExerciseStyle,
    GateStatus,
    IdentityStatus,
    OptionRight,
    SettlementType,
    SnapshotQuality,
    SourceCapabilityStatus,
)

EXPECTED_MEMBERS = {
    AdviceStatus: {"BLOCKED", "INSUFFICIENT_DATA", "OBSERVE", "REVIEW", "QUALIFIED"},
    Direction: {"BULLISH", "BEARISH", "NEUTRAL", "MIXED", "UNKNOWN"},
    GateStatus: {"PASS", "DEGRADE", "BLOCK"},
    DirectionHypothesis: {"UP", "DOWN", "VOLATILITY", "HEDGE_LIKELY", "MIXED", "UNKNOWN"},
    EnvelopeQuality: {"VALID", "PARTIAL", "STALE", "INVALID", "CONFLICT", "INSUFFICIENT_DATA"},
    DelayStatus: {"LIVE", "FROZEN", "DELAYED", "DELAYED_FROZEN", "UNKNOWN"},
    SnapshotQuality: {"GOOD", "PARTIAL", "DEGRADED", "MISSING", "CONTRADICTORY"},
    IdentityStatus: {"RESOLVED", "AMBIGUOUS", "UNRESOLVED"},
    AssetClass: {"STOCK", "ETF", "INDEX", "OPTION"},
    OptionRight: {"CALL", "PUT"},
    ExerciseStyle: {"AMERICAN", "EUROPEAN"},
    SettlementType: {"PHYSICAL", "CASH"},
    SourceCapabilityStatus: {
        "AVAILABLE",
        "DELAYED",
        "NOT_ENTITLED",
        "UNSUPPORTED",
        "ERROR",
        "MANUAL_EXPORT",
    },
    CalculationStatus: {"OK", "INVALID", "NOT_IMPLEMENTED"},
}


@pytest.mark.parametrize("enum_cls", sorted(EXPECTED_MEMBERS, key=lambda c: c.__name__))
def test_exact_member_set(enum_cls):
    assert {member.name for member in enum_cls} == EXPECTED_MEMBERS[enum_cls]


@pytest.mark.parametrize("enum_cls", sorted(EXPECTED_MEMBERS, key=lambda c: c.__name__))
def test_values_equal_names_and_are_str(enum_cls):
    for member in enum_cls:
        assert isinstance(member, str)
        assert member.value == member.name


def test_no_legacy_vocabulary():
    # ADR-014: REJECT/WATCH/RESEARCH and gate WARN/UNKNOWN must not reappear.
    assert not {"REJECT", "WATCH", "RESEARCH"} & {m.name for m in AdviceStatus}
    assert not {"WARN", "UNKNOWN"} & {m.name for m in GateStatus}


def test_quality_namespaces_are_distinct_types():
    assert EnvelopeQuality.PARTIAL is not SnapshotQuality.PARTIAL
    assert EnvelopeQuality.PARTIAL.__class__ is not SnapshotQuality.PARTIAL.__class__
