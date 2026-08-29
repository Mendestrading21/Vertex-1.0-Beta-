"""Versioned snapshots with a transactional current-version head pointer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from vertex_core.contracts import canonical_json_hash

from vertex_persistence.errors import SnapshotStateError
from vertex_persistence.json_codec import to_jsonb_object
from vertex_persistence.models import Snapshot, SnapshotHead
from vertex_persistence.repository._validation import require_aware_utc, require_non_empty_str

__all__ = ["PublishedSnapshot", "CurrentSnapshot", "publish_snapshot", "get_current_snapshot"]


@dataclass(frozen=True)
class PublishedSnapshot:
    """Immutable receipt of one published snapshot version."""

    kind: str
    key: str
    version: int
    content_hash: str
    as_of: datetime


@dataclass(frozen=True)
class CurrentSnapshot:
    """Immutable view of the current version of one (kind, key)."""

    kind: str
    key: str
    version: int
    content: dict[str, Any]
    content_hash: str
    as_of: datetime


def publish_snapshot(
    session: Session,
    *,
    kind: str,
    key: str,
    content: Any,
    as_of: datetime,
) -> PublishedSnapshot:
    """Write the next version of (kind, key) and move its head, in one transaction.

    The head row is locked ``FOR UPDATE`` so concurrent publishers of the same
    key serialize; the version row and the head update commit or roll back
    together with the caller's transaction (nothing is committed here). Two
    concurrent *first* publishes of a brand-new key are not serialized by a
    lock; the loser fails on the primary-key/unique constraint and must retry
    — fail-closed, never a silent overwrite.
    """
    kind = require_non_empty_str("kind", kind)
    key = require_non_empty_str("key", key)
    as_of = require_aware_utc("as_of", as_of)
    encoded = to_jsonb_object("content", content)
    content_hash = canonical_json_hash(encoded)

    head = session.execute(
        select(SnapshotHead)
        .where(SnapshotHead.kind == kind, SnapshotHead.key == key)
        .with_for_update()
    ).scalar_one_or_none()

    next_version = 1 if head is None else head.version + 1
    session.add(
        Snapshot(
            kind=kind,
            key=key,
            version=next_version,
            content=encoded,
            content_hash=content_hash,
            as_of=as_of,
        )
    )
    if head is None:
        session.add(SnapshotHead(kind=kind, key=key, version=next_version, updated_at=as_of))
    else:
        head.version = next_version
        head.updated_at = as_of
    session.flush()
    return PublishedSnapshot(
        kind=kind, key=key, version=next_version, content_hash=content_hash, as_of=as_of
    )


def get_current_snapshot(session: Session, *, kind: str, key: str) -> Optional[CurrentSnapshot]:
    """Return the head version of (kind, key), or ``None`` if never published.

    Absence is returned as ``None`` — never as an empty snapshot. A head
    pointing at a missing version row is a broken invariant and raises
    :class:`SnapshotStateError` (fail-closed).
    """
    kind = require_non_empty_str("kind", kind)
    key = require_non_empty_str("key", key)
    head = session.execute(
        select(SnapshotHead).where(SnapshotHead.kind == kind, SnapshotHead.key == key)
    ).scalar_one_or_none()
    if head is None:
        return None
    row = session.execute(
        select(Snapshot).where(
            Snapshot.kind == kind, Snapshot.key == key, Snapshot.version == head.version
        )
    ).scalar_one_or_none()
    if row is None:
        raise SnapshotStateError(
            f"snapshot head ({kind!r}, {key!r}) points at missing version {head.version}"
        )
    return CurrentSnapshot(
        kind=row.kind,
        key=row.key,
        version=row.version,
        content=row.content,
        content_hash=row.content_hash,
        as_of=row.as_of,
    )
