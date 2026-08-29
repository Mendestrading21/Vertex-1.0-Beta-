"""SYNTHETIC test doubles for the snapshot-backed routes (unit tests only).

Everything here carries explicit SYNTHETIC status and reaches the
application exclusively through ``app.dependency_overrides`` — no production
code path can construct or receive these objects.
"""

from __future__ import annotations

from typing import Mapping, Optional

from vertex_api.auth import SessionContext
from vertex_persistence.repository.snapshots import CurrentSnapshot

__all__ = ["FakeSnapshotReader", "synthetic_session"]


def synthetic_session() -> SessionContext:
    """Explicit SYNTHETIC session: only reachable via dependency_overrides."""
    return SessionContext(subject="synthetic-test-user", established_via="TEST_OVERRIDE")


class FakeSnapshotReader:
    """SYNTHETIC in-memory implementation of the ``SnapshotReader`` protocol."""

    def __init__(
        self,
        snapshots: Optional[Mapping[tuple[str, str], CurrentSnapshot]] = None,
        *,
        db_ok: bool = True,
    ) -> None:
        self.snapshots: dict[tuple[str, str], CurrentSnapshot] = dict(snapshots or {})
        self.db_ok = db_ok

    def current(self, *, kind: str, key: str) -> Optional[CurrentSnapshot]:
        return self.snapshots.get((kind, key))

    def head_version(self, *, kind: str, key: str) -> Optional[int]:
        snapshot = self.snapshots.get((kind, key))
        return None if snapshot is None else snapshot.version

    def heads_for_kind(self, *, kind: str) -> dict[str, int]:
        return {
            key: snapshot.version
            for (snapshot_kind, key), snapshot in self.snapshots.items()
            if snapshot_kind == kind
        }

    def ping(self) -> bool:
        return self.db_ok
