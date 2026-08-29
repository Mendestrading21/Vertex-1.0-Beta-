"""A stored snapshot that breaks its schema fails closed over HTTP (F14).

Before this guard existed, ``SnapshotContentError`` escaped the route and the
client received a generic 500 with a stack trace: the interface could not tell
"this resource is broken" from "the server crashed", and the raised text
travelled to the client. The relay now answers a stable, typed code and keeps
the reason in the server log.
"""

from __future__ import annotations

from typing import Any, Optional

import pytest
from fastapi.testclient import TestClient

from vertex_api.app import create_app
from vertex_api.auth import require_session
from vertex_api.snapshot_reader import get_snapshot_reader


class BrokenSnapshotReader:
    """SYNTHETIC reader: serves content that does not match the schema."""

    def current(self, *, kind: str, key: str) -> Optional[Any]:
        class _Snapshot:
            version = 1
            content = {"agenda": "not-a-list", "as_of": "not-a-datetime"}
            content_hash = "sha256:" + "0" * 64

        return _Snapshot()

    def head_version(self, *, kind: str, key: str) -> Optional[int]:
        return 1

    def heads_for_kind(self, *, kind: str) -> dict[str, int]:
        return {"global": 1}

    def ping(self) -> bool:
        return True


@pytest.fixture()
def client_with_broken_snapshot() -> TestClient:
    app = create_app()
    app.dependency_overrides[require_session] = lambda: None
    app.dependency_overrides[get_snapshot_reader] = BrokenSnapshotReader
    return TestClient(app, raise_server_exceptions=False)


def test_broken_snapshot_is_refused_with_a_typed_code(
    client_with_broken_snapshot: TestClient,
) -> None:
    response = client_with_broken_snapshot.get("/api/v1/calendar")

    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "SNAPSHOT_CONTENT_INVALID"
    assert "does not match the published schema" in body["detail"]


def test_the_refusal_never_leaks_the_stored_content(
    client_with_broken_snapshot: TestClient,
) -> None:
    """The stored values must not travel to the client, only a stable code."""
    raw = client_with_broken_snapshot.get("/api/v1/calendar").text

    assert "not-a-list" not in raw
    assert "not-a-datetime" not in raw
    assert "Traceback" not in raw
