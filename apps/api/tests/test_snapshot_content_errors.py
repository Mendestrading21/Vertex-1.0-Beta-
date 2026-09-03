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

Third re-audit (P1-G): two relays — ``GET /api/v1/performance/{id}`` and
``GET /api/v1/follow-up/queue`` — relayed their persisted content with
``content=dict(snapshot.content)`` and NO shape check at all. The only
"validation" was pydantic's strict typing of the FIRST-LEVEL KEYS of a
``FrozenStrMapping``, so anything whose keys happened to be strings was
served ``200 state="ok"``: a deeply nested object where an instant belongs,
a string carrying NUL/BEL/ANSI escapes, a 5000-character value, an entirely
foreign schema. ``/follow-up/queue`` was not even listed here. Both relays
now validate the shape of every field they publish, and BOTH appear below
with those four vectors.

Everything here is SYNTHETIC: the readers are injected through
``app.dependency_overrides`` and no production path can reach them.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from vertex_api.app import create_app
from vertex_api.auth import require_session
from vertex_api.snapshot_reader import get_clock, get_snapshot_reader

#: Fixed SYNTHETIC instants — no test ever reads the real clock.
AS_OF_DATETIME = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)
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

    def current(self, *, kind: str, key: str) -> Any | None:
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

    def head_version(self, *, kind: str, key: str) -> int | None:
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
            "down_count": 0,
            "flat_count": 0,
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


# ---------------------------------------------------------------------------
# P1-G — the two verbatim relays, with the four vectors of the third audit
# ---------------------------------------------------------------------------

#: The four shapes served ``200 state="ok"`` before P1-G was closed. Each
#: carries the sentinel, so a relay accepting one of them either surfaces the
#: value or, at the very least, fails the typed-code assertion.
CANARY_NESTED: dict[str, Any] = {"deep": {"deeper": [SENTINEL_TEXT]}}
CANARY_CONTROL_CHARS = "A\x00B\x07C\x1b[31m" + SENTINEL_TEXT
CANARY_OVERLONG = SENTINEL_TEXT + "x" * 5000
CANARY_FOREIGN_SCHEMA: dict[str, Any] = {
    "unrelated_root": SENTINEL_TEXT,
    "rows": [{"anything": SENTINEL_TEXT}],
}

#: The forged ``as_of`` vectors, applied to an otherwise VALID content: the
#: refusal must come from the field itself, not from a missing neighbour.
_AS_OF_VECTORS = (
    ("nested_object", CANARY_NESTED),
    ("control_characters", CANARY_CONTROL_CHARS),
    ("overlong_value", CANARY_OVERLONG),
)


def _valid_performance_content() -> dict[str, Any]:
    """The exact shape ``vertex_worker.performance`` publishes (SYNTHETIC)."""
    return {
        "schema_version": "vertex.performance/1.0",
        "as_of": AS_OF,
        "engine_version": "vertex_core@0.1.0",
        "portfolio": {"id": 1, "name": "SYNTHETIC", "base_currency": "SYN"},
        "population": "SYNTHETIC_MARKS_REAL_LEDGER",
        "population_components": {"marks": "SYNTHETIC", "ledger": "USER_DECLARED"},
        "currency": None,
        "lot_method": "fifo/1.0",
        "conventions": {"net_definition": "net = gross - declared fees"},
        "series": {
            "status": "INSUFFICIENT_DATA",
            "reason": "no ledger event",
            "points": [],
            "excluded_days": [],
        },
        "external_cashflows": [],
        "metrics": {
            name: {"status": "INSUFFICIENT_DATA", "reason": "no ledger event", "calculation": None}
            for name in (
                "twr_gross",
                "twr_net",
                "xirr_gross",
                "xirr_net",
                "drawdown_gross",
                "drawdown_net",
            )
        },
        "heatmap": {
            "status": "INSUFFICIENT_DATA",
            "reason": "no ledger event",
            "months": [],
            "derived_from_calculation": None,
        },
        "coverage": {
            "days_with_close": 0,
            "days_valued": 0,
            "days_excluded": 0,
            "days_before_first_ledger_event": 0,
            "coverage_ratio": None,
            "events_considered": 0,
            "external_cashflows": 0,
            "observations_considered": 0,
            "observations_truncated": False,
            "rejected_records": [],
        },
    }


def _valid_review_queue_content() -> dict[str, Any]:
    """The exact shape ``vertex_worker.follow_up`` publishes (SYNTHETIC)."""
    return {
        "schema_version": "vertex.review-queue/1.0",
        "as_of": AS_OF,
        "populations": {"theses": "USER_DECLARED", "information_context": "EMPTY"},
        "ordering": {
            "method": "lexicographic",
            "keys": ["thesis_id asc"],
            "note": "documented ordering",
        },
        "theses": [],
        "due": [],
        "coverage": {
            "theses_total": 0,
            "due_count": 0,
            "theses_with_instrument": 0,
            "theses_with_new_information": 0,
            "observations_considered": 0,
            "content_observations": 0,
            "clusters": 0,
            "lookback_seconds": 259200,
        },
    }


def _forged(builder, **overrides: Any) -> dict[str, Any]:
    content = builder()
    content.update(overrides)
    return content


def _p1g_rows() -> tuple[tuple[str, str, dict[str, Any], Any], ...]:
    rows: list[tuple[str, str, dict[str, Any], Any]] = []
    for relay_id, path, builder in (
        ("performance", "/api/v1/performance/1", _valid_performance_content),
        ("follow_up_queue", "/api/v1/follow-up/queue", _valid_review_queue_content),
    ):
        for vector_id, value in _AS_OF_VECTORS:
            rows.append(
                (
                    f"{relay_id}-as_of-{vector_id}",
                    path,
                    _forged(builder, as_of=value),
                    SENTINEL_TEXT,
                )
            )
        rows.append(
            (
                f"{relay_id}-foreign-schema",
                path,
                dict(CANARY_FOREIGN_SCHEMA),
                SENTINEL_TEXT,
            )
        )
    return tuple(rows)


#: (id, path, broken content, sentinel that must never surface).
BROKEN_RELAYS = (
    ("attention", "/api/v1/today/attention", _attention_content(), SENTINEL_INT),
    ("markets", "/api/v1/markets/overview", _markets_content(), -SENTINEL_INT),
    ("analysis", "/api/v1/analysis/SYNAA", _analysis_content(), SENTINEL_INT),
    ("option_chain", "/api/v1/options/SYNAA/chain", _option_chain_content(), SENTINEL_INT),
    ("opportunities", "/api/v1/opportunities", _opportunities_content(), SENTINEL_TEXT),
    ("performance", "/api/v1/performance/1", _performance_content(), SENTINEL_INT),
    *_p1g_rows(),
)

_RELAY_CASES = [
    pytest.param(path, content, sentinel, id=case_id)
    for case_id, path, content, sentinel in BROKEN_RELAYS
]


def _client(content: Any) -> TestClient:
    app = create_app()
    app.dependency_overrides[require_session] = lambda: None
    app.dependency_overrides[get_snapshot_reader] = lambda: BrokenSnapshotReader(content)
    # Horloge FIXE, alignée sur le `as_of` du faux lecteur : les relais
    # publient désormais l'âge et basculent en `stale` au-delà du budget.
    # Sans elle, ces tests deviendraient rouges tout seuls avec le temps, ce
    # qui masquerait la vraie question qu'ils posent : le contenu MALFORMÉ
    # est-il refusé, et le contenu honnête encore servi ?
    app.dependency_overrides[get_clock] = lambda: (lambda: AS_OF_DATETIME)
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


# ---------------------------------------------------------------------------
# P1-G — the refusals above must not be vacuous
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("path", "builder"),
    [
        pytest.param("/api/v1/performance/1", _valid_performance_content, id="performance"),
        pytest.param(
            "/api/v1/follow-up/queue", _valid_review_queue_content, id="follow_up_queue"
        ),
    ],
)
def test_the_honest_shape_of_each_relayed_snapshot_is_still_served(
    path: str, builder: Any
) -> None:
    """A shape check that refused everything would prove nothing.

    The two contents forged above are the WORKER's own published shape with a
    single field replaced, so the unforged shape must still reach ``200`` with
    ``state = "ok"`` and be relayed verbatim.
    """
    content = builder()
    response = _client(content).get(path)

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "ok"
    assert body["content"] == content


# ---------------------------------------------------------------------------
# P2-H — ``AiGroundingError`` sans handler : 500 en texte brut avec fuite.
#
# ``POST /api/v1/ai/explain`` laissait remonter ``AiGroundingError`` jusqu'au
# handler par défaut : réponse ``500 "Internal Server Error"`` sans code typé,
# et le message de ``validate_claims`` embarquait ``claim.text[:80]`` — un
# fragment de contenu STOCKÉ dans la trace serveur.
# ---------------------------------------------------------------------------

#: Une porte BLOCK dont l'identifiant n'est pas un jeton canonique ET dont le
#: code de raison déclenche la détection de langage interdit : la
#: contradiction anonyme est refusée, l'invariant de complétude échoue fermé.
_UNRESTITUTABLE_ADVICE = {
    "schema_version": "vertex.portfolio-valuation/1.0",
    "as_of": AS_OF,
    "mark_population": "SYNTHETIC",
    "lot_method": "fifo/1.0",
    "advice": {
        "advice_id": "sha256:" + "d" * 64,
        "status": "BLOCKED",
        "gates": [
            {
                "gate_id": f"{SENTINEL_TEXT} with space",
                "version": "1.0.0",
                "status": "BLOCK",
                "reason_code": f"GARANTI-{SENTINEL_TEXT}",
                "message": "synthetic",
            }
        ],
    },
}

_EXPLAIN_BODY = {
    "subject": {"kind": "portfolio_valuation", "key": "1"},
    "locale": "fr",
}


def test_an_ungrounded_ai_answer_is_refused_with_a_typed_code() -> None:
    response = _client(_UNRESTITUTABLE_ADVICE).post(
        "/api/v1/ai/explain", json=_EXPLAIN_BODY
    )

    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "AI_ANSWER_INCOMPLETE"
    assert "Internal Server Error" not in response.text


def test_the_ai_refusal_never_leaks_stored_content_to_the_client() -> None:
    raw = _client(_UNRESTITUTABLE_ADVICE).post(
        "/api/v1/ai/explain", json=_EXPLAIN_BODY
    ).text

    assert SENTINEL_TEXT not in raw
    assert "Traceback" not in raw


def test_the_ai_refusal_never_leaks_stored_content_to_any_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Seuls des noms de champs et un code typé partent dans le journal."""
    with caplog.at_level(logging.DEBUG):
        response = _client(_UNRESTITUTABLE_ADVICE).post(
            "/api/v1/ai/explain", json=_EXPLAIN_BODY
        )

    assert response.status_code == 500
    traced = [record for record in caplog.records if record.name == "vertex_api.ai"]
    assert traced, "the refusal must leave a server-side trace of its own"
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
        assert SENTINEL_TEXT not in rendered, record.name
