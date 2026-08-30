"""Canonical enum family per ADR-014: exact member sets, str-based wire values."""

import pytest

from vertex_core.contracts import (
    AFFIRMATIVE_STATUSES,
    NON_AFFIRMATIVE_STATUSES,
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


class TestStatusPartition:
    """La partition affirmative / non affirmative est UNE seule autorité.

    Deux littéraux concurrents avaient dérivé : `vertex_worker.opportunities`
    comptait `OBSERVE` parmi les statuts qualifiés, une campagne de dégradation
    ne le comptait pas. Un scénario produisant `OBSERVE` aurait donc satisfait
    un invariant écrit pour l'interdire. Ces tests empêchent la dérive de
    revenir.
    """

    def test_la_partition_couvre_exactement_AdviceStatus(self) -> None:
        assert AFFIRMATIVE_STATUSES | NON_AFFIRMATIVE_STATUSES == set(AdviceStatus)

    def test_les_deux_groupes_sont_disjoints(self) -> None:
        assert AFFIRMATIVE_STATUSES & NON_AFFIRMATIVE_STATUSES == set()

    def test_aucun_groupe_n_est_vide(self) -> None:
        # Une partition dont un côté serait vide passerait les deux tests
        # précédents tout en ne partitionnant rien.
        assert AFFIRMATIVE_STATUSES
        assert NON_AFFIRMATIVE_STATUSES

    def test_un_statut_ferme_n_est_jamais_affirmatif(self) -> None:
        assert AdviceStatus.BLOCKED in NON_AFFIRMATIVE_STATUSES
        assert AdviceStatus.INSUFFICIENT_DATA in NON_AFFIRMATIVE_STATUSES

    def test_observe_est_affirmatif(self) -> None:
        """Le point exact de la dérive : `OBSERVE` met une carte devant l'œil.

        `vertex_worker.opportunities` route `OBSERVE` dans le groupe qualifié,
        donc un dossier `OBSERVE` atteint l'utilisateur comme une opportunité.
        Le traiter comme non affirmatif ouvrirait un trou dans tout invariant
        de dégradation.
        """
        assert AdviceStatus.OBSERVE in AFFIRMATIVE_STATUSES
