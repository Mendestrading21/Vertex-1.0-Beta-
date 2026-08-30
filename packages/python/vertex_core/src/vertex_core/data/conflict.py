"""Cross-source conflict detection (DATA_QUALITY.md, "Conflits").

Two observations of the same field coming from different sources are never
merged: when they diverge beyond the caller-supplied tolerance, a
:class:`ConflictRecord` preserves BOTH sides (all sides, when more than two
sources observed the field). No majority vote, no averaging, no winner — a
financial contradiction is surfaced, never resolved automatically.

Two observations from the *same* source are revisions, not conflicts; they
are kept upstream as revisions and never compared here.

Pure module: deterministic output for any permutation of the input.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from pydantic import Field, model_validator

from vertex_core.contracts.types import (
    ContractModel,
    FiniteDecimal,
    NonEmptyStr,
    NonNegativeDecimal,
    UtcDatetime,
)

__all__ = [
    "CONFLICT_CODE_UNIT_MISMATCH",
    "CONFLICT_CODE_VALUE_DIVERGENCE",
    "ConflictRecord",
    "FieldObservation",
    "detect_conflicts",
]

CONFLICT_CODE_VALUE_DIVERGENCE = "VALUE_DIVERGENCE"
"""Two sources report values further apart than the tolerance."""

CONFLICT_CODE_UNIT_MISMATCH = "UNIT_MISMATCH"
"""Two sources report the same field in incomparable units (fail-closed)."""


class FieldObservation(ContractModel):
    """One sourced observation of one named field.

    ``value`` is a finite ``Decimal`` (NaN/infinity rejected at the boundary).
    An absent observation is simply not present in the input sequence — it is
    never represented by a zero-valued observation.
    """

    source: NonEmptyStr
    field_name: NonEmptyStr
    value: FiniteDecimal
    as_of: UtcDatetime
    unit: NonEmptyStr | None = None
    event_id: NonEmptyStr | None = None


class ConflictRecord(ContractModel):
    """One unresolved contradiction between sources for one field.

    The record lists every observation of the contested field (at least two,
    from at least two distinct sources). It deliberately carries NO resolved,
    merged, averaged or majority value: resolution is a human analytical act.

    ``divergence`` is the maximum absolute cross-source difference for
    ``VALUE_DIVERGENCE`` records; it stays ``None`` for ``UNIT_MISMATCH``
    records, where the values are not comparable at all.
    """

    field_name: NonEmptyStr
    code: NonEmptyStr
    observations: tuple[FieldObservation, ...] = Field(min_length=2)
    tolerance: NonNegativeDecimal
    divergence: NonNegativeDecimal | None = None
    message: str

    @model_validator(mode="after")
    def _check_invariants(self) -> ConflictRecord:
        if any(obs.field_name != self.field_name for obs in self.observations):
            raise ValueError("every observation must concern the record's field_name")
        if len({obs.source for obs in self.observations}) < 2:
            raise ValueError("a conflict requires observations from at least two distinct sources")
        return self


def _observation_sort_key(
    obs: FieldObservation,
) -> tuple[str, datetime, Decimal, str, str]:
    """Deterministic ordering key: input permutation never changes the output."""
    return (obs.source, obs.as_of, obs.value, obs.unit or "", obs.event_id or "")


def detect_conflicts(
    observations: Sequence[FieldObservation],
    *,
    tolerance: Decimal,
) -> tuple[ConflictRecord, ...]:
    """Detect cross-source conflicts among ``observations``.

    For each field name observed by at least two distinct sources:

    - if the sources disagree on the unit (including declared vs undeclared),
      the values are incomparable: one ``UNIT_MISMATCH`` record lists every
      observation of the field (fail-closed — no implicit unit conversion);
    - otherwise, if any pair of observations from *different* sources differs
      by more than ``tolerance`` in absolute value, one ``VALUE_DIVERGENCE``
      record lists every observation of the field and carries the maximum
      cross-source divergence.

    Both (all) sides are always preserved; nothing is voted, averaged or
    dropped. Records are sorted by field name and observations inside each
    record are deterministically ordered, so any permutation of the input
    yields the same result.
    """
    if not isinstance(tolerance, Decimal):
        raise TypeError("tolerance must be a Decimal")
    if not tolerance.is_finite():
        raise ValueError("tolerance must be a finite Decimal")
    if tolerance < 0:
        raise ValueError("tolerance must be >= 0")
    for obs in observations:
        if not isinstance(obs, FieldObservation):
            raise TypeError("every observation must be a FieldObservation")

    grouped: dict[str, list[FieldObservation]] = {}
    for obs in observations:
        grouped.setdefault(obs.field_name, []).append(obs)

    records: list[ConflictRecord] = []
    for field_name in sorted(grouped):
        group = sorted(grouped[field_name], key=_observation_sort_key)
        sources = {obs.source for obs in group}
        if len(sources) < 2:
            # Single-source observations are revisions at most, never conflicts.
            continue
        units = {obs.unit for obs in group}
        if len(units) > 1:
            unit_names = ", ".join(sorted(u if u is not None else "<unspecified>" for u in units))
            records.append(
                ConflictRecord(
                    field_name=field_name,
                    code=CONFLICT_CODE_UNIT_MISMATCH,
                    observations=tuple(group),
                    tolerance=tolerance,
                    divergence=None,
                    message=(
                        f"field {field_name!r} observed in incomparable units ({unit_names}); "
                        "both sides kept, no conversion attempted"
                    ),
                )
            )
            continue
        max_divergence: Decimal | None = None
        for i, left in enumerate(group):
            for right in group[i + 1 :]:
                if left.source == right.source:
                    continue
                difference = abs(left.value - right.value)
                if max_divergence is None or difference > max_divergence:
                    max_divergence = difference
        if max_divergence is not None and max_divergence > tolerance:
            source_names = ", ".join(sorted(sources))
            records.append(
                ConflictRecord(
                    field_name=field_name,
                    code=CONFLICT_CODE_VALUE_DIVERGENCE,
                    observations=tuple(group),
                    tolerance=tolerance,
                    divergence=max_divergence,
                    message=(
                        f"sources {source_names} diverge on field {field_name!r} by "
                        f"{max_divergence} (> tolerance {tolerance}); both values kept, "
                        "no vote and no average"
                    ),
                )
            )
    return tuple(records)
