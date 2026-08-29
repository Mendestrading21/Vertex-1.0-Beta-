"""Unit tests of storage vocabularies and their anti-drift guards.

Also proves the frozen CHECK lists of migration 0001 stay identical to the
canonical vocabularies (a vocabulary change must be a new migration).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from vertex_core.contracts import DelayStatus, EnvelopeQuality

from vertex_persistence.enums import (
    LEDGER_EVENT_KINDS,
    OBSERVATION_DELAY_STATUSES,
    OBSERVATION_QUALITY_STATUSES,
    OUTBOX_STATUSES,
    POSITION_LOT_SOURCES,
    LedgerEventKind,
    OutboxStatus,
    PositionLotSource,
    validate_enum_value,
)
from vertex_persistence.errors import EnumValidationError

_MIGRATION_PATH = (
    Path(__file__).resolve().parent.parent / "migrations" / "versions" / "0001_initial.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("migration_0001_initial", _MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_observation_statuses_mirror_vertex_core_exactly() -> None:
    assert OBSERVATION_QUALITY_STATUSES == frozenset(m.value for m in EnvelopeQuality)
    assert OBSERVATION_DELAY_STATUSES == frozenset(m.value for m in DelayStatus)


def test_outbox_statuses() -> None:
    assert OUTBOX_STATUSES == {"PENDING", "IN_PROGRESS", "DONE", "FAILED", "DEAD"}
    assert OutboxStatus("PENDING") is OutboxStatus.PENDING


def test_ledger_event_kinds_complete() -> None:
    assert LEDGER_EVENT_KINDS == {
        "BUY_RECORDED",
        "SELL_RECORDED",
        "OPTION_OPEN",
        "OPTION_CLOSE",
        "DIVIDEND",
        "INTEREST",
        "FEE",
        "TAX",
        "DEPOSIT",
        "WITHDRAWAL",
        "FX_CONVERSION",
        "CORPORATE_ACTION",
        "ADJUSTMENT",
    }


def test_position_lot_sources() -> None:
    assert POSITION_LOT_SOURCES == {"MANUAL", "IMPORT_CONFIRMED"}


def test_values_equal_names_serialize_canonically() -> None:
    for enum_type in (OutboxStatus, LedgerEventKind, PositionLotSource):
        for member in enum_type:
            assert member.value == member.name


def test_validate_enum_value_accepts_member_and_string() -> None:
    assert validate_enum_value("status", OutboxStatus.DEAD, OUTBOX_STATUSES) == "DEAD"
    assert validate_enum_value("status", "DONE", OUTBOX_STATUSES) == "DONE"


@pytest.mark.parametrize("bad", ["done", "UNKNOWN_STATE", "", None, 3, b"DONE"])
def test_validate_enum_value_fails_closed(bad: object) -> None:
    with pytest.raises(EnumValidationError):
        validate_enum_value("status", bad, OUTBOX_STATUSES)


def test_migration_check_lists_match_canonical_vocabularies() -> None:
    migration = _load_migration()
    assert frozenset(migration.OBSERVATION_QUALITY_STATUSES) == OBSERVATION_QUALITY_STATUSES
    assert frozenset(migration.OBSERVATION_DELAY_STATUSES) == OBSERVATION_DELAY_STATUSES
    assert frozenset(migration.OUTBOX_STATUSES) == OUTBOX_STATUSES
    assert frozenset(migration.LEDGER_EVENT_KINDS) == LEDGER_EVENT_KINDS
    assert frozenset(migration.POSITION_LOT_SOURCES) == POSITION_LOT_SOURCES
