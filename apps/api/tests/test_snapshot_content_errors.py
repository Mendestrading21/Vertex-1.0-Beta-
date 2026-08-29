"""A stored snapshot that breaks its schema fails closed over HTTP (F14).

Before this guard existed, ``SnapshotContentError`` escaped the route and the
client received a generic 500 with a stack trace: the interface could not tell
"this resource is broken" from "the server crashed", and the raised text
travelled to the client. The relay now answers a stable, typed code and keeps
the reason in the server log.

Re-audit (P1-7): the guard was closed on ONE route only. Every other relay
built its wire DTO from persisted content WITHOUT checking the fields the DTO
constrains (``item_id``, ``title``, positive integers, string-keyed
mappings...), so a raw pydantic ``ValidationError`` reached the default
handler: an untyped 500 — and the pydantic message carries ``input_value``,
i.e. THE STORED VALUE, straight into the server log. This module therefore
pins, for EVERY snapshot relay route:

1. broken persisted content answers 500 with the typed
   ``SNAPSHOT_CONTENT_INVALID`` code (never an untyped "Internal Server
   Error");
2. no stored value reaches the response body;
3. no stored value reaches ANY log record (``caplog``) — the promise
   "field names only, never the stored values" is verified, not asserted in
   a docstring;
4. a malformed REQUEST still fails as a 4xx: the last-rampart handler never
   promotes a client error into a server error.

Everything here is SYNTHETIC: the readers are injected through
``app.dependency_overrides`` and no production path can reach them.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import pytest
from fastapi.testclient import TestClient

from vertex_api.app import create_app
from vertex_api.auth import require_session
from vertex_api.snapshot_reader import get_snapshot_reader

#: Fixed SYNTHETIC instants — no test ever reads the real clock.
AS_OF_DATETIME = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)
AS_OF = AS_OF_DATETIME.isoformat()

#: Recognizable values planted in the persisted content. Neither the HTTP
#: response nor any log record may contain them.
SENTINEL_INT = 4242424242
SENTINEL_TEXT = "S3NT1NEL-STORED-VALUE"


class BrokenSnapshotReader:
    """SYNTHETIC reader: serves content that does not match the schema."""

    def __init__(self, content: Any, *, version: int = 1) -> None:
        self._content = content
        self._version = version

    def current(self, *, kind: str, key: str) -> Optional[Any]:
        content = self._content
        version = self._version

        class _Snapshot:
            pass

        snapshot = _Snapshot()
        snapshot.kind = kind
        snapshot.key = key
        snapshot.version = version
        snapshot.content = content
        snapshot.content_hash = "sha256:" + "0" * 64
        snapshot.as_of = AS_OF_DATETIME
        return snapshot

    def head_version(self, *, kind: str, key: str) -> Optional[int]:
        return self._version

    def heads_for_kind(self, *, kind: str) -> dict[str, int]:
        return {"global": self._version}

    def ping(self) -> bool:
        return True


def _attention_content() -> dict[str, Any]:
    """Valid attention content EXCEPT ``items[0].title`` (an int, not a str)."""
    return {
        "as_of": AS_OF,
        "population": "SYNTHETIC",
        "coverage": {},
        "rejected": [],
        "items": [
            {
                "item_id": "synthetic-item-1",
                "title": SENTINEL_INT,
                "provenance": {"sources": ["SYNTHETIC"], "rights": ["SYNTHETIC"]},
                "relevance_reasons": ["synthetic reason"],
                "synthetic": True,
            }
        ],
    }


def _markets_content() -> dict[str, Any]:
    """Valid markets content EXCEPT ``coverage.lookback_seconds`` (negative)."""
    return {
        "as_of": AS_OF,
        "population": "SYNTHETIC",
        "data_state": "ok",
        "unit": "ratio",
        "display_unit": "percent",
        "engine_version": "vertex_core@0.1.0",
        "conclusion": "synthetic conclusion",
        "sectors": [],
        "breadth": {
            "status": "INVALID",
            "reason": "COVERAGE_BELOW_THRESHOLD",
            "value": None,
            "value_pct": None,
            "above_count": 0,
            "covered_count": 0,
            "universe_size": 1,
            "coverage_pct": "0",
            "coverage_threshold": "0.8",
            "coverage_threshold_pct": "80",
            "calculation": None,
        },
        "coverage": {
            "expected": 1,
            "received": 0,
            "covered": 0,
            "discarded": 0,
            "discarded_tickers": [],
            "rejected_records": [],
            "observations_considered": 0,
            "lookback_seconds": -SENTINEL_INT,
        },
    }


def _analysis_content() -> dict[str, Any]:
    """Valid dossier EXCEPT ``bars``: a mapping whose key is not a string."""
    return {
        "as_of": AS_OF,
        "instrument": "SYNAA",
        "population": "SYNTHETIC",
        "engine_version": "vertex_core@0.1.0",
        "bars": {SENTINEL_INT: "synthetic"},
        "evidence": {},
        "scenarios": {"status": "ABSENT", "reason": "NO_GRID"},
        "advice": {
            "advice_id": "sha256:" + "b" * 64,
            "engine_version": "vertex_core@0.1.0",
            "status": "BLOCKED",
            "gates": [],
        },
        "coverage": {},
    }


def _option_chain_content() -> dict[str, Any]:
    """Valid chain EXCEPT ``row_budget``: a mapping whose key is not a string."""
    return {
        "as_of": AS_OF,
        "underlying": "SYNAA",
        "population": "SYNTHETIC",
        "engine_version": "vertex_core@0.1.0",
        "value_nature": "THEORETICAL",
        "spot": None,
        "assumptions": None,
        "expirations": [],
        "row_budget": {SENTINEL_INT: "synthetic"},
        "coverage": {},
    }


def _opportunities_content() -> dict[str, Any]:
    """Valid envelope EXCEPT ``profile_ref.id``: no such declared profile."""
    return {
        "as_of": AS_OF,
        "profile_ref": {"id": SENTINEL_TEXT, "version": "1.0.0"},
        "qualified": [],
        "excluded": [],
        "exclusion_reasons": {},
    }


def _performance_content() -> dict[str, Any]:
    """Persisted content whose key is not a string (relayed as a mapping)."""
    return {SENTINEL_INT: "synthetic"}


#: (id, path, broken content, sentinel that must never surface).
BROKEN_RELAYS = (
    ("attention", "/api/v1/today/attention", _attention_content(), SENTINEL_INT),
    ("markets", "/api/v1/markets/overview", _markets_content(), -SENTINEL_INT),
    ("analysis", "/api/v1/analysis/SYNAA", _analysis_content(), SENTINEL_INT),
    ("option_chain", "/api/v1/options/SYNAA/chain", _option_chain_content(), SENTINEL_INT),
    ("opportunities", "/api/v1/opportunities", _opportunities_content(), SENTINEL_TEXT),
    ("performance", "/api/v1/performance/1", _performance_content(), SENTINEL_INT),
)

_RELAY_CASES = [
    pytest.param(path, content, sentinel, id=case_id)
    for case_id, path, content, sentinel in BROKEN_RELAYS
]


def _client(content: Any) -> TestClient:
    app = create_app()
    app.dependency_overrides[require_session] = lambda: None
    app.dependency_overrides[get_snapshot_reader] = lambda: BrokenSnapshotReader(content)
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def client_with_broken_snapshot() -> TestClient:
    return _client({"agenda": "not-a-list", "as_of": "not-a-datetime"})


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


@pytest.mark.parametrize(("path", "content", "sentinel"), _RELAY_CASES)
def test_every_relay_refuses_broken_content_with_a_typed_code(
    path: str, content: Any, sentinel: Any
) -> None:
    """P1-7: the fail-closed code is served by EVERY relay, not just one."""
    response = _client(content).get(path)

    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "SNAPSHOT_CONTENT_INVALID"
    assert "does not match the published schema" in body["detail"]


@pytest.mark.parametrize(("path", "content", "sentinel"), _RELAY_CASES)
def test_no_stored_value_reaches_the_response(
    path: str, content: Any, sentinel: Any
) -> None:
    response = _client(content).get(path)

    assert str(sentinel) not in response.text
    assert "Traceback" not in response.text


@pytest.mark.parametrize(("path", "content", "sentinel"), _RELAY_CASES)
def test_no_stored_value_appears_in_any_log_record(
    path: str, content: Any, sentinel: Any, caplog: pytest.LogCaptureFixture
) -> None:
    """P1-7: 'field names only, never the stored values' — verified.

    Every emitted record is inspected: its formatted message, its raw
    ``msg``/``args`` and the rendered exception text. A pydantic
    ``ValidationError`` message carries ``input_value=<stored value>``, so
    logging it (or letting it escape to the default handler) publishes a
    fragment of the persisted payload — forbidden by
    ``.claude/rules/security.md``.
    """
    with caplog.at_level(logging.DEBUG):
        response = _client(content).get(path)

    assert response.status_code == 500
    traced = [r for r in caplog.records if r.name == "vertex_api.snapshot"]
    assert traced, "the refusal must leave a server-side trace of its own"
    needle = str(sentinel)
    for record in caplog.records:
        rendered = " | ".join(
            part
            for part in (
                record.getMessage(),
                str(record.msg),
                repr(record.args),
                logging.Formatter().formatException(record.exc_info)
                if record.exc_info
                else "",
            )
            if part
        )
        assert needle not in rendered, f"stored value leaked in log: {record.name}"


def test_a_malformed_request_body_stays_a_4xx() -> None:
    """The last-rampart handler never turns a client error into a 500."""
    app = create_app()
    app.dependency_overrides[require_session] = lambda: None
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/api/v1/advice/preview", json={"instrument_id": 12})

    assert response.status_code == 422
