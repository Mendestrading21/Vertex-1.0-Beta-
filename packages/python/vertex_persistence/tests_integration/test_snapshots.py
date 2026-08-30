"""Snapshots: versioning, the transactional head pointer, append-only rows.

``snapshots`` rows are immutable versions: UPDATE and DELETE are forbidden by
the same SQL trigger as observations/ledger_transactions (migration 0003).
``snapshot_heads`` stays mutable on purpose — it is the moving pointer.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from vertex_persistence.models import Snapshot, SnapshotHead
from vertex_persistence.repository import get_current_snapshot, publish_snapshot

UTC = UTC
T0 = datetime(2026, 8, 28, 12, 0, 0, tzinfo=UTC)


def test_first_publish_creates_version_one_and_head(db_session: Session) -> None:
    published = publish_snapshot(
        db_session, kind="market_overview", key="SYN", content={"state": "a"}, as_of=T0
    )
    db_session.commit()
    assert published.version == 1
    assert published.content_hash.startswith("sha256:")
    head = db_session.execute(select(SnapshotHead)).scalar_one()
    assert (head.kind, head.key, head.version) == ("market_overview", "SYN", 1)


def test_versions_accumulate_and_head_follows(db_session: Session) -> None:
    for index in range(3):
        publish_snapshot(
            db_session,
            kind="market_overview",
            key="SYN",
            content={"state": index},
            as_of=T0 + timedelta(minutes=index),
        )
        db_session.commit()
    versions = (
        db_session.execute(select(Snapshot.version).order_by(Snapshot.version)).scalars().all()
    )
    assert versions == [1, 2, 3]
    current = get_current_snapshot(db_session, kind="market_overview", key="SYN")
    assert current is not None
    assert current.version == 3
    assert current.content == {"state": 2}


def test_head_update_is_transactional_with_version_insert(db_session: Session) -> None:
    publish_snapshot(db_session, kind="k", key="x", content={"v": 1}, as_of=T0)
    db_session.commit()

    # A publish that rolls back leaves neither a version row nor a moved head.
    publish_snapshot(
        db_session, kind="k", key="x", content={"v": 2}, as_of=T0 + timedelta(minutes=1)
    )
    db_session.rollback()

    assert db_session.execute(select(func.count()).select_from(Snapshot)).scalar_one() == 1
    head = db_session.execute(select(SnapshotHead)).scalar_one()
    assert head.version == 1
    current = get_current_snapshot(db_session, kind="k", key="x")
    assert current is not None and current.content == {"v": 1}

    # The next successful publish still gets version 2 (no burned version).
    published = publish_snapshot(
        db_session, kind="k", key="x", content={"v": 2}, as_of=T0 + timedelta(minutes=2)
    )
    db_session.commit()
    assert published.version == 2
    head = db_session.execute(select(SnapshotHead)).scalar_one()
    assert head.version == 2


def test_keys_and_kinds_are_independent(db_session: Session) -> None:
    publish_snapshot(db_session, kind="a", key="x", content={"n": 1}, as_of=T0)
    publish_snapshot(db_session, kind="a", key="y", content={"n": 2}, as_of=T0)
    publish_snapshot(db_session, kind="b", key="x", content={"n": 3}, as_of=T0)
    db_session.commit()
    for kind, key, expected in (("a", "x", 1), ("a", "y", 2), ("b", "x", 3)):
        current = get_current_snapshot(db_session, kind=kind, key=key)
        assert current is not None
        assert current.version == 1
        assert current.content == {"n": expected}


def test_absent_snapshot_returns_none_not_empty(db_session: Session) -> None:
    assert get_current_snapshot(db_session, kind="never", key="published") is None


def test_snapshot_update_forbidden_by_trigger(db_session: Session) -> None:
    """A stored snapshot version is immutable, even through raw SQL."""
    publish_snapshot(db_session, kind="k", key="x", content={"v": 1}, as_of=T0)
    db_session.commit()
    with pytest.raises(DBAPIError, match="append-only"):
        db_session.execute(text("UPDATE snapshots SET content_hash = 'tampered'"))
    db_session.rollback()


def test_snapshot_delete_forbidden_by_trigger(db_session: Session) -> None:
    """Snapshot history cannot be deleted; supersede it with a new version."""
    publish_snapshot(db_session, kind="k", key="x", content={"v": 1}, as_of=T0)
    db_session.commit()
    # The head references the version; delete the head first so the FK cannot
    # mask the trigger (the trigger must fire, not the FK violation).
    db_session.execute(text("DELETE FROM snapshot_heads"))
    with pytest.raises(DBAPIError, match="append-only"):
        db_session.execute(text("DELETE FROM snapshots"))
    db_session.rollback()
    assert db_session.execute(select(func.count()).select_from(Snapshot)).scalar_one() == 1


def test_snapshot_heads_stays_mutable(db_session: Session) -> None:
    """The head pointer is NOT append-only: it moves with each publish."""
    publish_snapshot(db_session, kind="k", key="x", content={"v": 1}, as_of=T0)
    publish_snapshot(
        db_session, kind="k", key="x", content={"v": 2}, as_of=T0 + timedelta(minutes=1)
    )
    db_session.commit()
    head = db_session.execute(select(SnapshotHead)).scalar_one()
    assert head.version == 2  # an UPDATE on snapshot_heads succeeded
