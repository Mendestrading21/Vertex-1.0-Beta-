"""Theses and revisions: transactional create, idempotency, append-only, queue.

All data is SYNTHETIC user input — no market data, no broker concept.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from vertex_persistence.errors import (
    IdempotencyKeyReuseError,
    UnknownPortfolioError,
    UnknownThesisError,
    ValidationFailedError,
)
from vertex_persistence.models import Thesis, ThesisRevision
from vertex_persistence.repository import (
    create_portfolio,
    create_thesis,
    list_revisions,
    list_theses,
    record_thesis_revision,
    review_queue_due,
)

UTC = timezone.utc
T0 = datetime(2026, 8, 1, 12, 0, 0, tzinfo=UTC)
NOW = T0 + timedelta(days=10)
INSTRUMENT = {"symbol": "SYN", "asset_class": "STOCK", "exchange": "SYNTH", "currency": "USD"}


def _create(session: Session, key: str = "synthetic-create-1", **overrides):
    values = dict(
        title="Synthetic breakout thesis",
        hypotheses="SYNTHETIC: sector momentum persists over one quarter",
        invalidation="SYNTHETIC: weekly close below the declared support level",
        idempotency_key=key,
        now=T0,
        instrument=INSTRUMENT,
        horizon="3M",
        review_due_at=T0 + timedelta(days=7),
        note="initial statement",
    )
    values.update(overrides)
    return create_thesis(session, **values)


def _counts(session: Session) -> tuple[int, int]:
    theses = session.execute(select(func.count()).select_from(Thesis)).scalar_one()
    revisions = session.execute(select(func.count()).select_from(ThesisRevision)).scalar_one()
    return int(theses), int(revisions)


# --- create_thesis: transactional pair, idempotent replay -------------------


def test_create_thesis_writes_thesis_and_created_revision_together(
    db_session: Session,
) -> None:
    result = _create(db_session)
    db_session.commit()
    assert result.created is True
    thesis = db_session.get(Thesis, result.thesis_id)
    revision = db_session.get(ThesisRevision, result.revision_id)
    assert thesis is not None and revision is not None
    assert thesis.title == "Synthetic breakout thesis"
    assert thesis.instrument == INSTRUMENT
    assert thesis.portfolio_id is None
    assert thesis.created_at == T0
    assert revision.thesis_id == thesis.id
    assert revision.action == "CREATED"
    assert revision.author == "local-user"
    assert revision.content_hash.startswith("sha256:")
    assert revision.snooze_until is None


def test_create_thesis_rollback_removes_both_rows(db_session: Session) -> None:
    _create(db_session)
    assert _counts(db_session) == (1, 1)  # visible inside the transaction
    db_session.rollback()
    assert _counts(db_session) == (0, 0)  # neither thesis nor revision survived


def test_create_thesis_replay_ten_times_creates_one_thesis(db_session: Session) -> None:
    first = _create(db_session)
    db_session.commit()
    assert first.created is True
    for _ in range(10):
        replay = _create(db_session)
        assert replay.created is False
        assert replay.thesis_id == first.thesis_id
        assert replay.revision_id == first.revision_id
    db_session.commit()
    assert _counts(db_session) == (1, 1)


def test_create_key_reused_for_non_create_fails_closed(db_session: Session) -> None:
    result = _create(db_session)
    record_thesis_revision(
        db_session,
        thesis_id=result.thesis_id,
        action="REVIEWED",
        idempotency_key="synthetic-review-1",
        recorded_at=T0 + timedelta(days=1),
    )
    db_session.commit()
    with pytest.raises(IdempotencyKeyReuseError):
        _create(db_session, key="synthetic-review-1")
    db_session.rollback()


def test_create_thesis_blank_invalidation_rejected_by_repository(
    db_session: Session,
) -> None:
    with pytest.raises(ValidationFailedError):
        _create(db_session, invalidation="   ")
    db_session.rollback()


def test_blank_invalidation_rejected_by_database_check(db_session: Session) -> None:
    """The refusal holds for every SQL client, not only the repository."""
    with pytest.raises(IntegrityError, match="invalidation_not_blank"):
        db_session.execute(
            text(
                "INSERT INTO theses (title, hypotheses, invalidation, created_at)"
                " VALUES ('t', 'h', '   ', now())"
            )
        )
    db_session.rollback()


def test_create_thesis_unknown_portfolio_rejected(db_session: Session) -> None:
    with pytest.raises(UnknownPortfolioError):
        _create(db_session, portfolio_id=424242)
    db_session.rollback()


def test_create_thesis_with_portfolio_links_it(db_session: Session) -> None:
    portfolio_id = create_portfolio(db_session, name="synthetic-main", base_currency="CHF")
    result = _create(db_session, portfolio_id=portfolio_id)
    db_session.commit()
    thesis = db_session.get(Thesis, result.thesis_id)
    assert thesis is not None and thesis.portfolio_id == portfolio_id


# --- record_thesis_revision: idempotency and validation ---------------------


def test_record_revision_ten_replays_one_row(db_session: Session) -> None:
    thesis_id = _create(db_session).thesis_id
    db_session.commit()
    results = [
        record_thesis_revision(
            db_session,
            thesis_id=thesis_id,
            action="REVIEWED",
            idempotency_key="synthetic-review-1",
            recorded_at=T0 + timedelta(days=1),
            note="reviewed, thesis intact",
        )
        for _ in range(10)
    ]
    db_session.commit()
    assert [r.created for r in results] == [True] + [False] * 9
    assert len({r.revision_id for r in results}) == 1  # every replay names the same row
    assert _counts(db_session) == (1, 2)  # CREATED + one REVIEWED


def test_record_revision_key_reuse_for_other_operation_fails_closed(
    db_session: Session,
) -> None:
    first = _create(db_session, key="synthetic-create-1")
    second = _create(db_session, key="synthetic-create-2", title="Second synthetic thesis")
    record_thesis_revision(
        db_session,
        thesis_id=first.thesis_id,
        action="REVIEWED",
        idempotency_key="synthetic-shared-key",
        recorded_at=T0 + timedelta(days=1),
    )
    db_session.commit()
    # Same key, different thesis: not a replay — a caller bug.
    with pytest.raises(IdempotencyKeyReuseError):
        record_thesis_revision(
            db_session,
            thesis_id=second.thesis_id,
            action="REVIEWED",
            idempotency_key="synthetic-shared-key",
            recorded_at=T0 + timedelta(days=2),
        )
    db_session.rollback()
    # Same key, same thesis, different action: also refused.
    with pytest.raises(IdempotencyKeyReuseError):
        record_thesis_revision(
            db_session,
            thesis_id=first.thesis_id,
            action="ARCHIVED",
            idempotency_key="synthetic-shared-key",
            recorded_at=T0 + timedelta(days=2),
        )
    db_session.rollback()


def test_record_revision_created_action_reserved(db_session: Session) -> None:
    thesis_id = _create(db_session).thesis_id
    db_session.commit()
    with pytest.raises(ValidationFailedError, match="reserved"):
        record_thesis_revision(
            db_session,
            thesis_id=thesis_id,
            action="CREATED",
            idempotency_key="synthetic-x",
            recorded_at=T0,
        )
    db_session.rollback()


def test_record_revision_snooze_pairing_enforced(db_session: Session) -> None:
    thesis_id = _create(db_session).thesis_id
    db_session.commit()
    with pytest.raises(ValidationFailedError, match="snooze_until"):
        record_thesis_revision(
            db_session,
            thesis_id=thesis_id,
            action="SNOOZED",
            idempotency_key="synthetic-x",
            recorded_at=T0,
        )
    db_session.rollback()
    with pytest.raises(ValidationFailedError, match="snooze_until"):
        record_thesis_revision(
            db_session,
            thesis_id=thesis_id,
            action="REVIEWED",
            idempotency_key="synthetic-x",
            recorded_at=T0,
            snooze_until=T0 + timedelta(days=1),
        )
    db_session.rollback()


def test_record_revision_unknown_thesis_rejected(db_session: Session) -> None:
    with pytest.raises(UnknownThesisError):
        record_thesis_revision(
            db_session,
            thesis_id=424242,
            action="REVIEWED",
            idempotency_key="synthetic-x",
            recorded_at=T0,
        )
    db_session.rollback()


# --- append-only enforcement ------------------------------------------------


def test_thesis_revisions_update_and_delete_forbidden(db_session: Session) -> None:
    _create(db_session)
    db_session.commit()
    with pytest.raises(DBAPIError, match="append-only"):
        db_session.execute(text("UPDATE thesis_revisions SET note = 'rewritten history'"))
    db_session.rollback()
    with pytest.raises(DBAPIError, match="append-only"):
        db_session.execute(text("DELETE FROM thesis_revisions"))
    db_session.rollback()
    with pytest.raises(DBAPIError, match="append-only"):
        db_session.execute(text("TRUNCATE thesis_revisions"))
    db_session.rollback()
    count = db_session.execute(select(func.count()).select_from(ThesisRevision)).scalar_one()
    assert count == 1


def test_theses_has_no_status_column(db_session: Session) -> None:
    """The status is a projection; a stored status column would be a second authority."""
    columns = {
        row[0]
        for row in db_session.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'theses'"
            )
        )
    }
    assert "status" not in columns
    assert columns == {
        "id",
        "portfolio_id",
        "instrument",
        "title",
        "hypotheses",
        "invalidation",
        "horizon",
        "review_due_at",
        "created_at",
    }


# --- projected listings and the review queue --------------------------------


def test_list_theses_returns_projected_state(db_session: Session) -> None:
    result = _create(db_session, review_due_at=NOW + timedelta(days=5))
    record_thesis_revision(
        db_session,
        thesis_id=result.thesis_id,
        action="SNOOZED",
        idempotency_key="synthetic-snooze-1",
        recorded_at=T0 + timedelta(days=1),
        snooze_until=NOW + timedelta(days=2),
    )
    db_session.commit()
    listed = list_theses(db_session, now=NOW)
    assert len(listed) == 1
    entry = listed[0]
    assert entry.thesis.id == result.thesis_id
    assert entry.state.status == "SNOOZED"
    assert entry.state.review_due_at == NOW + timedelta(days=2)
    assert entry.state.is_due is False
    assert entry.state.revision_count == 2


def test_list_revisions_ordered_and_bound_to_thesis(db_session: Session) -> None:
    result = _create(db_session)
    record_thesis_revision(
        db_session,
        thesis_id=result.thesis_id,
        action="NOTE_UPDATED",
        idempotency_key="synthetic-note-1",
        recorded_at=T0 + timedelta(days=2),
        note="added context",
    )
    record_thesis_revision(
        db_session,
        thesis_id=result.thesis_id,
        action="REVIEWED",
        idempotency_key="synthetic-review-1",
        recorded_at=T0 + timedelta(days=1),
    )
    db_session.commit()
    revisions = list_revisions(db_session, result.thesis_id)
    assert [r.action for r in revisions] == ["CREATED", "REVIEWED", "NOTE_UPDATED"]
    assert all(r.thesis_id == result.thesis_id for r in revisions)
    with pytest.raises(UnknownThesisError):
        list_revisions(db_session, 424242)
    db_session.rollback()


def test_review_queue_due_matrix(db_session: Session) -> None:
    """Due = past base due, or expired snooze; never snoozed-future or archived."""
    due_past = _create(
        db_session, key="synthetic-due", title="due", review_due_at=NOW - timedelta(days=2)
    )
    _create(
        db_session,
        key="synthetic-future",
        title="not due yet",
        review_due_at=NOW + timedelta(days=2),
    )
    _create(db_session, key="synthetic-no-due", title="never scheduled", review_due_at=None)
    snoozed_future = _create(
        db_session,
        key="synthetic-snoozed",
        title="snoozed",
        review_due_at=NOW - timedelta(days=5),
    )
    record_thesis_revision(
        db_session,
        thesis_id=snoozed_future.thesis_id,
        action="SNOOZED",
        idempotency_key="synthetic-snooze-future",
        recorded_at=T0 + timedelta(days=1),
        snooze_until=NOW + timedelta(days=3),
    )
    snooze_expired = _create(
        db_session, key="synthetic-expired", title="snooze expired", review_due_at=None
    )
    record_thesis_revision(
        db_session,
        thesis_id=snooze_expired.thesis_id,
        action="SNOOZED",
        idempotency_key="synthetic-snooze-expired",
        recorded_at=T0 + timedelta(days=1),
        snooze_until=NOW - timedelta(days=1),
    )
    archived = _create(
        db_session,
        key="synthetic-archived",
        title="archived",
        review_due_at=NOW - timedelta(days=9),
    )
    record_thesis_revision(
        db_session,
        thesis_id=archived.thesis_id,
        action="ARCHIVED",
        idempotency_key="synthetic-archive-1",
        recorded_at=T0 + timedelta(days=1),
    )
    db_session.commit()

    queue = review_queue_due(db_session, now=NOW)
    assert [entry.thesis.id for entry in queue] == [
        due_past.thesis_id,  # NOW - 2d: most overdue first
        snooze_expired.thesis_id,  # NOW - 1d: expired snooze is due again
    ]
    assert all(entry.state.is_due for entry in queue)

    # The same database an hour before the snooze expiry: only the past due.
    earlier_queue = review_queue_due(db_session, now=NOW - timedelta(days=1, hours=1))
    assert [entry.thesis.id for entry in earlier_queue] == [due_past.thesis_id]


def test_archived_then_reactivated_returns_to_queue(db_session: Session) -> None:
    result = _create(db_session, review_due_at=NOW - timedelta(days=1))
    record_thesis_revision(
        db_session,
        thesis_id=result.thesis_id,
        action="ARCHIVED",
        idempotency_key="synthetic-archive-1",
        recorded_at=T0 + timedelta(days=1),
    )
    db_session.commit()
    assert review_queue_due(db_session, now=NOW) == ()
    record_thesis_revision(
        db_session,
        thesis_id=result.thesis_id,
        action="REACTIVATED",
        idempotency_key="synthetic-reactivate-1",
        recorded_at=T0 + timedelta(days=2),
    )
    db_session.commit()
    queue = review_queue_due(db_session, now=NOW)
    assert [entry.thesis.id for entry in queue] == [result.thesis_id]
    assert queue[0].state.status == "ACTIVE"
