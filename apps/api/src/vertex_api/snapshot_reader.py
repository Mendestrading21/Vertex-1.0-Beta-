"""Read-only snapshot access of the API (adapter over ``vertex_persistence``).

The API never computes a snapshot: it serves the last version published by
the worker, exactly as persisted. ``SnapshotReader`` is the narrow protocol
the routes depend on (injected through FastAPI dependencies so unit tests
substitute deterministic fakes); ``DbSnapshotReader`` is the real
implementation over the application's PostgreSQL engine.

``head_version`` reads ONLY the head pointer (kind, key) -> version — the
light query the SSE polling loop runs every second; content is never loaded
there. ``ping`` is the honest database health probe (``SELECT 1``): any
failure is reported as unhealthy, never masked.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable, Optional, Protocol

from fastapi import FastAPI, Request
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from vertex_api.auth.db import DatabaseNotConfiguredError, open_db_session
from vertex_persistence.models import SnapshotHead
from vertex_persistence.repository.snapshots import CurrentSnapshot, get_current_snapshot

__all__ = [
    "Clock",
    "DbSnapshotReader",
    "SnapshotReader",
    "get_clock",
    "get_snapshot_reader",
    "utc_now",
]

log = logging.getLogger("vertex_api.snapshot_reader")

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    """Aware UTC instant — the only clock read of the snapshot routes."""
    return datetime.now(timezone.utc)


class SnapshotReader(Protocol):
    """Narrow read-only view over published snapshots and database health."""

    def current(self, *, kind: str, key: str) -> Optional[CurrentSnapshot]:
        """Head version of (kind, key) with content, or ``None`` if never published."""
        ...

    def head_version(self, *, kind: str, key: str) -> Optional[int]:
        """Head version number only (no content), or ``None`` if never published."""
        ...

    def heads_for_kind(self, *, kind: str) -> dict[str, int]:
        """Every published head of ``kind`` as ``{key: version}`` (no content).

        Empty when nothing of this kind was ever published. This is the
        light query behind the prefix-watched SSE resources
        (``option_chain/*``): any key published under a watched kind is
        picked up without redeploying the API.
        """
        ...

    def ping(self) -> bool:
        """``SELECT 1`` health probe: ``True`` only when the database answers."""
        ...


class DbSnapshotReader:
    """Real reader over the application's engine (one short session per call)."""

    def __init__(self, app: FastAPI) -> None:
        self._app = app

    def current(self, *, kind: str, key: str) -> Optional[CurrentSnapshot]:
        with open_db_session(self._app) as session:
            return get_current_snapshot(session, kind=kind, key=key)

    def head_version(self, *, kind: str, key: str) -> Optional[int]:
        with open_db_session(self._app) as session:
            return session.execute(
                select(SnapshotHead.version).where(
                    SnapshotHead.kind == kind, SnapshotHead.key == key
                )
            ).scalar_one_or_none()

    def heads_for_kind(self, *, kind: str) -> dict[str, int]:
        with open_db_session(self._app) as session:
            rows = session.execute(
                select(SnapshotHead.key, SnapshotHead.version).where(
                    SnapshotHead.kind == kind
                )
            ).all()
        return {key: version for key, version in rows}

    def ping(self) -> bool:
        try:
            with open_db_session(self._app) as session:
                return session.execute(text("SELECT 1")).scalar_one() == 1
        except DatabaseNotConfiguredError:
            log.warning("db health probe failed: database not configured")
            return False
        except SQLAlchemyError as exc:
            # The probe's whole purpose is to turn a failure into an honest
            # 'error' health status; only the exception TYPE is logged.
            log.warning("db health probe failed: %s", type(exc).__name__)
            return False


def get_snapshot_reader(request: Request) -> SnapshotReader:
    """FastAPI dependency: the real reader (tests override with fakes)."""
    return DbSnapshotReader(request.app)


def get_clock() -> Clock:
    """FastAPI dependency: the UTC clock (tests override with a fixed clock)."""
    return utc_now
