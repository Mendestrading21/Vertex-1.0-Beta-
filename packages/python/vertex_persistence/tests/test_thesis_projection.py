"""Unit tests of the pure thesis-state projection (no database, no I/O).

``project_thesis_state`` is the ONLY authority for thesis status and the
effective review-due instant: every transition and every fail-closed branch
is exercised here on synthetic revision histories with an injected clock.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from vertex_persistence.errors import ClockError, ThesisProjectionError
from vertex_persistence.repository.theses import (
    ThesisRevisionRecord,
    ThesisStatus,
    project_thesis_state,
)

UTC = UTC
T0 = datetime(2026, 8, 1, 12, 0, 0, tzinfo=UTC)
NOW = T0 + timedelta(days=10)


def _rev(
    rev_id: int,
    action: str,
    recorded_at: datetime,
    snooze_until: datetime | None = None,
) -> ThesisRevisionRecord:
    return ThesisRevisionRecord(
        id=rev_id,
        thesis_id=1,
        action=action,
        note=None,
        snapshot_ref=None,
        content_hash="sha256:synthetic",
        idempotency_key=f"synthetic-key-{rev_id}",
        author="local-user",
        recorded_at=recorded_at,
        snooze_until=snooze_until,
    )


def _created(recorded_at: datetime = T0) -> ThesisRevisionRecord:
    return _rev(1, "CREATED", recorded_at)


# --- fail-closed history validation ---------------------------------------


def test_empty_history_fails_closed() -> None:
    with pytest.raises(ThesisProjectionError, match="empty"):
        project_thesis_state([], review_due_at=None, now=NOW)


def test_history_not_starting_with_created_fails_closed() -> None:
    with pytest.raises(ThesisProjectionError, match="CREATED"):
        project_thesis_state([_rev(1, "REVIEWED", T0)], review_due_at=None, now=NOW)


def test_duplicate_created_fails_closed() -> None:
    history = [_created(), _rev(2, "CREATED", T0 + timedelta(days=1))]
    with pytest.raises(ThesisProjectionError, match="duplicate CREATED"):
        project_thesis_state(history, review_due_at=None, now=NOW)


def test_unknown_action_fails_closed() -> None:
    history = [_created(), _rev(2, "PROMOTED", T0 + timedelta(days=1))]
    with pytest.raises(ThesisProjectionError, match="unknown"):
        project_thesis_state(history, review_due_at=None, now=NOW)


def test_snoozed_without_snooze_until_fails_closed() -> None:
    history = [_created(), _rev(2, "SNOOZED", T0 + timedelta(days=1), snooze_until=None)]
    with pytest.raises(ThesisProjectionError, match="snooze_until"):
        project_thesis_state(history, review_due_at=None, now=NOW)


def test_naive_now_rejected() -> None:
    with pytest.raises(ClockError):
        project_thesis_state([_created()], review_due_at=None, now=datetime(2026, 8, 2))  # noqa: DTZ001 (naïf délibéré : rejet vérifié)


# --- CREATED baseline ------------------------------------------------------


def test_created_is_active_with_base_review_due() -> None:
    due = NOW + timedelta(days=5)
    state = project_thesis_state([_created()], review_due_at=due, now=NOW)
    assert state.status == ThesisStatus.ACTIVE.value
    assert state.review_due_at == due
    assert state.is_due is False
    assert state.snooze_until is None
    assert state.last_reviewed_at is None
    assert state.last_action == "CREATED"
    assert state.revision_count == 1


def test_created_without_review_due_is_never_due() -> None:
    state = project_thesis_state([_created()], review_due_at=None, now=NOW)
    assert state.status == ThesisStatus.ACTIVE.value
    assert state.review_due_at is None
    assert state.is_due is False


def test_created_with_past_review_due_is_due() -> None:
    due = NOW - timedelta(hours=1)
    state = project_thesis_state([_created()], review_due_at=due, now=NOW)
    assert state.status == ThesisStatus.ACTIVE.value
    assert state.is_due is True
    assert state.review_due_at == due


def test_review_due_exactly_now_is_due() -> None:
    state = project_thesis_state([_created()], review_due_at=NOW, now=NOW)
    assert state.is_due is True


# --- SNOOZED ---------------------------------------------------------------


def test_unexpired_snooze_defers_and_overrides_base_due() -> None:
    wake = NOW + timedelta(days=3)
    history = [_created(), _rev(2, "SNOOZED", T0 + timedelta(days=1), snooze_until=wake)]
    state = project_thesis_state(history, review_due_at=NOW - timedelta(days=1), now=NOW)
    assert state.status == ThesisStatus.SNOOZED.value
    assert state.review_due_at == wake  # snooze overrides the (past) base due
    assert state.is_due is False
    assert state.snooze_until == wake


def test_expired_snooze_becomes_active_and_due_again() -> None:
    wake = NOW - timedelta(hours=2)
    history = [_created(), _rev(2, "SNOOZED", T0 + timedelta(days=1), snooze_until=wake)]
    state = project_thesis_state(history, review_due_at=None, now=NOW)
    assert state.status == ThesisStatus.ACTIVE.value
    assert state.review_due_at == wake  # the expired snooze instant is the due
    assert state.is_due is True


def test_snooze_expiring_exactly_now_is_due() -> None:
    history = [_created(), _rev(2, "SNOOZED", T0 + timedelta(days=1), snooze_until=NOW)]
    state = project_thesis_state(history, review_due_at=None, now=NOW)
    assert state.status == ThesisStatus.ACTIVE.value
    assert state.is_due is True


def test_later_snooze_replaces_earlier_snooze() -> None:
    first_wake = NOW + timedelta(days=1)
    second_wake = NOW + timedelta(days=9)
    history = [
        _created(),
        _rev(2, "SNOOZED", T0 + timedelta(days=1), snooze_until=first_wake),
        _rev(3, "SNOOZED", T0 + timedelta(days=2), snooze_until=second_wake),
    ]
    state = project_thesis_state(history, review_due_at=None, now=NOW)
    assert state.status == ThesisStatus.SNOOZED.value
    assert state.review_due_at == second_wake


# --- REVIEWED --------------------------------------------------------------


def test_reviewed_consumes_pending_snooze_and_restores_base_due() -> None:
    wake = NOW + timedelta(days=3)
    base_due = NOW + timedelta(days=30)
    history = [
        _created(),
        _rev(2, "SNOOZED", T0 + timedelta(days=1), snooze_until=wake),
        _rev(3, "REVIEWED", T0 + timedelta(days=2)),
    ]
    state = project_thesis_state(history, review_due_at=base_due, now=NOW)
    assert state.status == ThesisStatus.ACTIVE.value
    assert state.snooze_until is None
    assert state.review_due_at == base_due
    assert state.is_due is False
    assert state.last_reviewed_at == T0 + timedelta(days=2)


def test_reviewed_does_not_silently_move_a_past_base_due() -> None:
    """Scheduling the next review is an explicit SNOOZED, never implicit."""
    base_due = NOW - timedelta(days=1)
    history = [_created(), _rev(2, "REVIEWED", T0 + timedelta(days=2))]
    state = project_thesis_state(history, review_due_at=base_due, now=NOW)
    assert state.status == ThesisStatus.ACTIVE.value
    assert state.is_due is True  # still due until deferred or archived explicitly


# --- NOTE_UPDATED ----------------------------------------------------------


def test_note_updated_changes_nothing_in_the_lifecycle() -> None:
    wake = NOW + timedelta(days=3)
    history = [
        _created(),
        _rev(2, "SNOOZED", T0 + timedelta(days=1), snooze_until=wake),
        _rev(3, "NOTE_UPDATED", T0 + timedelta(days=2)),
    ]
    state = project_thesis_state(history, review_due_at=None, now=NOW)
    assert state.status == ThesisStatus.SNOOZED.value
    assert state.review_due_at == wake
    assert state.last_action == "NOTE_UPDATED"
    assert state.revision_count == 3


# --- ARCHIVED / REACTIVATED ------------------------------------------------


def test_archived_is_never_due_even_with_past_base_due() -> None:
    history = [_created(), _rev(2, "ARCHIVED", T0 + timedelta(days=1))]
    state = project_thesis_state(history, review_due_at=NOW - timedelta(days=5), now=NOW)
    assert state.status == ThesisStatus.ARCHIVED.value
    assert state.review_due_at is None
    assert state.is_due is False


def test_archived_clears_pending_snooze() -> None:
    wake = NOW - timedelta(hours=1)  # would be an expired snooze if not archived
    history = [
        _created(),
        _rev(2, "SNOOZED", T0 + timedelta(days=1), snooze_until=wake),
        _rev(3, "ARCHIVED", T0 + timedelta(days=2)),
    ]
    state = project_thesis_state(history, review_due_at=None, now=NOW)
    assert state.status == ThesisStatus.ARCHIVED.value
    assert state.snooze_until is None
    assert state.is_due is False


def test_reviewed_and_snoozed_on_archived_thesis_do_not_resurrect_it() -> None:
    history = [
        _created(),
        _rev(2, "ARCHIVED", T0 + timedelta(days=1)),
        _rev(3, "REVIEWED", T0 + timedelta(days=2)),
        _rev(4, "SNOOZED", T0 + timedelta(days=3), snooze_until=NOW + timedelta(days=1)),
    ]
    state = project_thesis_state(history, review_due_at=NOW - timedelta(days=1), now=NOW)
    assert state.status == ThesisStatus.ARCHIVED.value
    assert state.is_due is False
    # The review is still remembered as a fact, without changing the status.
    assert state.last_reviewed_at == T0 + timedelta(days=2)


def test_archived_then_reactivated_is_active_with_base_due() -> None:
    base_due = NOW - timedelta(hours=1)
    history = [
        _created(),
        _rev(2, "ARCHIVED", T0 + timedelta(days=1)),
        _rev(3, "REACTIVATED", T0 + timedelta(days=2)),
    ]
    state = project_thesis_state(history, review_due_at=base_due, now=NOW)
    assert state.status == ThesisStatus.ACTIVE.value
    assert state.review_due_at == base_due
    assert state.is_due is True
    assert state.last_action == "REACTIVATED"


def test_reactivated_does_not_restore_a_pre_archive_snooze() -> None:
    history = [
        _created(),
        _rev(2, "SNOOZED", T0 + timedelta(days=1), snooze_until=NOW + timedelta(days=9)),
        _rev(3, "ARCHIVED", T0 + timedelta(days=2)),
        _rev(4, "REACTIVATED", T0 + timedelta(days=3)),
    ]
    state = project_thesis_state(history, review_due_at=None, now=NOW)
    assert state.status == ThesisStatus.ACTIVE.value
    assert state.snooze_until is None
    assert state.review_due_at is None
    assert state.is_due is False


# --- determinism and ordering ----------------------------------------------


def test_out_of_order_input_is_sorted_by_recorded_at_then_id() -> None:
    wake = NOW + timedelta(days=3)
    history = [
        _rev(3, "REVIEWED", T0 + timedelta(days=2)),
        _created(),
        _rev(2, "SNOOZED", T0 + timedelta(days=1), snooze_until=wake),
    ]
    state = project_thesis_state(history, review_due_at=None, now=NOW)
    # Sorted order is CREATED -> SNOOZED -> REVIEWED: the review consumed the snooze.
    assert state.status == ThesisStatus.ACTIVE.value
    assert state.snooze_until is None
    assert state.last_action == "REVIEWED"


def test_same_instant_ties_break_by_id() -> None:
    instant = T0 + timedelta(days=1)
    history = [
        _created(),
        _rev(3, "REACTIVATED", instant),
        _rev(2, "ARCHIVED", instant),
    ]
    state = project_thesis_state(history, review_due_at=None, now=NOW)
    assert state.status == ThesisStatus.ACTIVE.value  # id 2 (ARCHIVED) then id 3


def test_projection_is_pure_and_repeatable() -> None:
    history = [
        _created(),
        _rev(2, "SNOOZED", T0 + timedelta(days=1), snooze_until=NOW - timedelta(hours=1)),
    ]
    first = project_thesis_state(history, review_due_at=None, now=NOW)
    second = project_thesis_state(list(reversed(history)), review_due_at=None, now=NOW)
    assert first == second
