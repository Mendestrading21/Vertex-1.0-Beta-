"""Storage vocabularies of the persistence layer.

Two families live here:

- **Persistence-owned enums** (:class:`OutboxStatus`, :class:`LedgerEventKind`,
  :class:`PositionLotSource`): storage lifecycle vocabulary that belongs to the
  persistence module. They carry no financial rule — they only name the states
  a stored row may take.
- **Mirrors of canonical contract enums**: ``observations.quality_status`` and
  ``observations.delay_status`` accept exactly the values of
  :class:`vertex_core.contracts.EnvelopeQuality` and
  :class:`vertex_core.contracts.DelayStatus`. The value sets are derived from
  ``vertex_core`` at import time so no concurrent vocabulary can drift here.

Validation is fail-closed: an unknown value raises
:class:`~vertex_persistence.errors.EnumValidationError`, it is never coerced,
defaulted or stored raw.
"""

from __future__ import annotations

from enum import Enum, unique

from vertex_core.contracts import DelayStatus, EnvelopeQuality

from vertex_persistence.errors import EnumValidationError

__all__ = [
    "OutboxStatus",
    "LedgerEventKind",
    "PositionLotSource",
    "ThesisRevisionAction",
    "OBSERVATION_QUALITY_STATUSES",
    "OBSERVATION_DELAY_STATUSES",
    "OUTBOX_STATUSES",
    "LEDGER_EVENT_KINDS",
    "POSITION_LOT_SOURCES",
    "THESIS_REVISION_ACTIONS",
    "validate_enum_value",
]


@unique
class OutboxStatus(str, Enum):
    """Lifecycle status of one outbox message (ADR-006, at-least-once)."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    FAILED = "FAILED"
    DEAD = "DEAD"


@unique
class LedgerEventKind(str, Enum):
    """Kind of one manually recorded ledger fact.

    Every kind names a **past fact typed in by the user** after it happened
    outside Vertex (``docs/03-domain/PORTFOLIO_MANUAL.md``). None of these is
    an instruction, an order or a transmissible ticket.
    """

    BUY_RECORDED = "BUY_RECORDED"
    SELL_RECORDED = "SELL_RECORDED"
    OPTION_OPEN = "OPTION_OPEN"
    OPTION_CLOSE = "OPTION_CLOSE"
    DIVIDEND = "DIVIDEND"
    INTEREST = "INTEREST"
    FEE = "FEE"
    TAX = "TAX"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    FX_CONVERSION = "FX_CONVERSION"
    CORPORATE_ACTION = "CORPORATE_ACTION"
    ADJUSTMENT = "ADJUSTMENT"


@unique
class PositionLotSource(str, Enum):
    """Provenance of a manually declared lot or ledger fact.

    ``MANUAL`` is direct user input; ``IMPORT_CONFIRMED`` is a user-confirmed
    import of a document the user supplied. No source is a broker account
    feed; external sources never overwrite the user's declarations.
    """

    MANUAL = "MANUAL"
    IMPORT_CONFIRMED = "IMPORT_CONFIRMED"


@unique
class ThesisRevisionAction(str, Enum):
    """Action of one appended thesis revision (page 09 — follow-up queue).

    Each action is a **past fact of the user's review discipline**, recorded
    append-only. The current status of a thesis (ACTIVE / SNOOZED / ARCHIVED)
    is never stored: it is a pure projection of these revisions, recomputed by
    :func:`vertex_persistence.repository.theses.project_thesis_state`.
    """

    CREATED = "CREATED"
    REVIEWED = "REVIEWED"
    SNOOZED = "SNOOZED"
    NOTE_UPDATED = "NOTE_UPDATED"
    ARCHIVED = "ARCHIVED"
    REACTIVATED = "REACTIVATED"


# Canonical value sets, derived — never re-declared — from vertex_core.
OBSERVATION_QUALITY_STATUSES: frozenset[str] = frozenset(m.value for m in EnvelopeQuality)
OBSERVATION_DELAY_STATUSES: frozenset[str] = frozenset(m.value for m in DelayStatus)
OUTBOX_STATUSES: frozenset[str] = frozenset(m.value for m in OutboxStatus)
LEDGER_EVENT_KINDS: frozenset[str] = frozenset(m.value for m in LedgerEventKind)
POSITION_LOT_SOURCES: frozenset[str] = frozenset(m.value for m in PositionLotSource)
THESIS_REVISION_ACTIONS: frozenset[str] = frozenset(m.value for m in ThesisRevisionAction)


def validate_enum_value(label: str, value: object, allowed: frozenset[str]) -> str:
    """Return ``value`` as ``str`` if it belongs to ``allowed``; fail closed otherwise.

    ``value`` may be a plain string or a ``str``-based Enum member. Anything
    else, including ``None``, raises :class:`EnumValidationError` — absence is
    never replaced by a default.
    """
    if isinstance(value, Enum):
        value = value.value
    if not isinstance(value, str):
        raise EnumValidationError(
            f"{label}: expected a canonical string value, got {type(value).__name__}"
        )
    if value not in allowed:
        raise EnumValidationError(
            f"{label}: {value!r} is not a canonical value (allowed: {sorted(allowed)})"
        )
    return value
