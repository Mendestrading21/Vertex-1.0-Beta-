"""P1-1 / P2-1 reproducers on the REAL chain, end to end.

SYNTHETIC envelopes -> ``ingest_envelope`` -> ``WorkerRunner.drain`` ->
PostgreSQL -> the protected route with a REAL passkey session. Nothing is
stubbed and no dependency is overridden: the snapshots these tests forge are
the ones the worker really published a few milliseconds earlier.

What the fourth adversarial audit measured: the relays validated the
STRUCTURE of a persisted field (it exists, it is a string) and never its
CONTENT. Replacing the stored value of ``strike``, ``greeks.delta``,
``bars.last_close`` or ``population`` with a 5038-character string carrying
BEL and an ANSI colour escape was answered ``200`` with that value relayed
byte-for-byte. Two distinct defects: those are FINANCIAL values, which
``financial-safety.md`` requires to be decimals; and ``population`` is the
very field that separates SYNTHETIC from real.

P2-1, same wave: ``agenda[].exchange_timezone`` was checked with
``_require_str`` only, so ``Mars/Olympus`` was served ``200 state="ok"`` —
the single leak of the calendar rule "a present but unreadable value fails
closed".

Every forged value is planted through the real snapshot repository, and the
healthy content is republished afterwards, so one test never leaves a broken
snapshot behind for the next assertion.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from soft_passkey import SoftPasskey, login_passkey, register_passkey
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from vertex_core.synthetic import (
    generate_calendar_event_envelopes,
    generate_daily_bar_envelopes,
    generate_daily_quote_envelopes,
    generate_envelopes,
    generate_option_chain_envelopes,
)
from vertex_persistence.repository.outbox import enqueue_outbox
from vertex_persistence.repository.snapshots import (
    get_current_snapshot,
    publish_snapshot,
)
from vertex_persistence.repository.theses import create_thesis
from vertex_worker.handlers import DEV_SYNTHETIC_CONFIG, build_registry
from vertex_worker.ingest import ingest_envelope
from vertex_worker.runner import WorkerRunner

#: Fixed SYNTHETIC instant — no test here reads the real clock.
NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)
BASE_TIME = NOW - timedelta(minutes=5)
SEED = 434343
INSTRUMENT = "SYN-TECH-01"

#: The exact payload the audit relayed verbatim: BEL, an ANSI colour escape
#: and 5000 filler characters — 5038 in all.
HOSTILE = "ACHETEZ MAINTENANT" + "\x07" + "\x1b" + "[31m gain garanti " + "Z" * 5000

#: A value that is neither long nor escaped: it is simply not a timezone.
UNRESOLVABLE_TIMEZONE = "Mars/Olympus"


def _clock() -> datetime:
    return NOW


@pytest.fixture()
def engine(migrated_database: None, database_url: str) -> Iterator[Engine]:
    created = create_engine(database_url)
    try:
        yield created
    finally:
        created.dispose()


@pytest.fixture()
def published(engine: Engine) -> Engine:
    """Ingest the SYNTHETIC envelopes and drain the REAL worker once."""
    envelopes = (
        generate_envelopes(seed=SEED, count=60, base_time=BASE_TIME)
        + generate_daily_quote_envelopes(seed=SEED, base_time=BASE_TIME)
        + generate_daily_bar_envelopes(seed=SEED, base_time=BASE_TIME)
        + generate_option_chain_envelopes(seed=SEED, base_time=BASE_TIME)
        + generate_calendar_event_envelopes(seed=SEED, base_time=BASE_TIME)
    )
    with Session(engine) as session:
        for envelope in envelopes:
            ingest_envelope(session, envelope)
        create_thesis(
            session,
            title="[SYNTHETIC] These de reproduction P1-1",
            hypotheses="[SYNTHETIC] Hypothese de reproduction.",
            invalidation="[SYNTHETIC] Invalidee si la cloture retombe sous 90.",
            idempotency_key="p11-repro-thesis",
            now=NOW - timedelta(hours=6),
            instrument={"ticker": "SYN7"},
            review_due_at=NOW - timedelta(days=2),
        )
        enqueue_outbox(session, "review_queue.refresh", {"reason": "p11-repro"})
        session.commit()

    registry = build_registry(clock=_clock, fusion_config=DEV_SYNTHETIC_CONFIG)
    runner = WorkerRunner(
        session_factory=lambda: Session(engine),
        registry=registry,
        poll_interval_seconds=0.05,
        clock=_clock,
    )
    runner.drain(max_batches=200)
    stats = runner.stats()
    assert stats.failed == 0 and stats.dead == 0, stats
    return engine


@pytest.fixture()
def authenticated(client: TestClient, passkey: SoftPasskey) -> TestClient:
    register_passkey(client, passkey)
    assert login_passkey(client, passkey).status_code == 200
    return client


# ---------------------------------------------------------------------------
# Helpers over the REAL snapshot repository
# ---------------------------------------------------------------------------


def _content(engine: Engine, kind: str, key: str) -> tuple[dict, datetime]:
    with Session(engine) as session:
        snapshot = get_current_snapshot(session, kind=kind, key=key)
    assert snapshot is not None, f"the worker published no {kind}/{key}"
    return json.loads(json.dumps(snapshot.content)), snapshot.as_of


def _publish(engine: Engine, kind: str, key: str, content: Any, as_of: datetime) -> None:
    with Session(engine) as session:
        publish_snapshot(session, kind=kind, key=key, content=content, as_of=as_of)
        session.commit()


def _replaced(content: dict, path: tuple, value: str) -> dict:
    """A copy of ``content`` with ONE string leaf replaced.

    The path must already hold a string in the published content: a test that
    silently forged a field the worker no longer publishes would prove
    nothing.
    """
    clone = json.loads(json.dumps(content))
    node: Any = clone
    for step in path[:-1]:
        node = node[step]
    assert isinstance(node[path[-1]], str), path
    node[path[-1]] = value
    return clone


def _strings(node: Any) -> list[str]:
    """Every string leaf of a parsed response body.

    The comparison must happen on the PARSED body: BEL and ESC travel JSON
    escaped, so a value relayed verbatim never appears literally in the raw
    text of the response.
    """
    out: list[str] = []
    if isinstance(node, dict):
        for value in node.values():
            out.extend(_strings(value))
    elif isinstance(node, list):
        for value in node:
            out.extend(_strings(value))
    elif isinstance(node, str):
        out.append(node)
    return out


def _first_path(node: Any, wanted: str, path: tuple = ()) -> tuple | None:
    """First path whose LAST key is ``wanted`` and whose value is a string."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == wanted and isinstance(value, str):
                return (*path, key)
            found = _first_path(value, wanted, (*path, key))
            if found is not None:
                return found
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found = _first_path(value, wanted, (*path, index))
            if found is not None:
                return found
    return None


# (relay kind, snapshot key, route, the field names the audit named)
_CASES = [
    (
        "option_chain",
        INSTRUMENT,
        f"/api/v1/options/{INSTRUMENT}/chain",
        ("strike", "delta", "bid", "value", "population"),
    ),
    (
        "analysis",
        INSTRUMENT,
        f"/api/v1/analysis/{INSTRUMENT}",
        ("last_close", "close", "population"),
    ),
    (
        "opportunities",
        "global",
        "/api/v1/opportunities",
        ("ticker", "detail", "population"),
    ),
    (
        "review_queue",
        "global",
        "/api/v1/follow-up/queue",
        ("title", "hypotheses", "theses"),
    ),
    (
        "attention",
        "global",
        "/api/v1/today/attention",
        ("title", "item_id", "population"),
    ),
    (
        "calendar",
        "global",
        "/api/v1/calendar",
        ("title", "exchange_timezone", "population"),
    ),
    (
        "markets_overview",
        "global",
        "/api/v1/markets/overview",
        ("last_close", "return_1d", "population"),
    ),
]


@pytest.mark.parametrize("kind,key,route,fields", _CASES)
def test_a_hostile_value_is_refused_on_every_relayed_field(
    published: Engine,
    authenticated: TestClient,
    kind: str,
    key: str,
    route: str,
    fields: tuple[str, ...],
) -> None:
    """Every named field: 500 typed, and the stored value never served.

    The audit served each of these 200 with the hostile value reproduced
    verbatim. The healthy snapshot is republished between two forgeries, so
    each assertion measures its OWN field.
    """
    healthy, as_of = _content(published, kind, key)
    baseline = authenticated.get(route)
    assert baseline.status_code == 200, baseline.text

    for name in fields:
        path = _first_path(healthy, name)
        assert path is not None, f"{kind}/{key}: no published string field {name!r}"
        _publish(published, kind, key, _replaced(healthy, path, HOSTILE), as_of)

        response = authenticated.get(route)
        assert response.status_code == 500, (name, path, response.status_code)
        assert response.json() == {
            "code": "SNAPSHOT_CONTENT_INVALID",
            "detail": (
                "a published snapshot cannot be served: its stored content "
                "does not match the published schema"
            ),
        }
        assert HOSTILE not in _strings(response.json())
        assert "ACHETEZ" not in response.text

        _publish(published, kind, key, healthy, as_of)
        assert authenticated.get(route).status_code == 200


def test_the_four_fields_named_by_the_audit_fail_closed(
    published: Engine, authenticated: TestClient
) -> None:
    """The reproduction cited in the audit report, path by path.

    ``option_chain.expirations[0].contracts[0].strike`` (stored ``204.00``),
    the same contract's ``greeks.delta`` (stored ``0.997...``),
    ``analysis.bars.last_close`` (stored ``239.66``) and
    ``analysis.population`` (stored ``SYNTHETIC``).
    """
    chain, chain_as_of = _content(published, "option_chain", INSTRUMENT)
    contracts = chain["expirations"][0]["contracts"]
    assert isinstance(contracts[0]["strike"], str)
    greeks_index = next(
        index
        for index, entry in enumerate(contracts)
        if isinstance(entry["greeks"].get("delta"), str)
    )

    chain_route = f"/api/v1/options/{INSTRUMENT}/chain"
    for path in (
        ("expirations", 0, "contracts", 0, "strike"),
        ("expirations", 0, "contracts", greeks_index, "greeks", "delta"),
    ):
        _publish(
            published,
            "option_chain",
            INSTRUMENT,
            _replaced(chain, path, HOSTILE),
            chain_as_of,
        )
        assert authenticated.get(chain_route).status_code == 500, path
    _publish(published, "option_chain", INSTRUMENT, chain, chain_as_of)
    assert authenticated.get(chain_route).status_code == 200

    dossier, dossier_as_of = _content(published, "analysis", INSTRUMENT)
    analysis_route = f"/api/v1/analysis/{INSTRUMENT}"
    assert dossier["population"] == "SYNTHETIC"
    for path in (("bars", "last_close"), ("population",)):
        _publish(
            published,
            "analysis",
            INSTRUMENT,
            _replaced(dossier, path, HOSTILE),
            dossier_as_of,
        )
        assert authenticated.get(analysis_route).status_code == 500, path
    _publish(published, "analysis", INSTRUMENT, dossier, dossier_as_of)
    assert authenticated.get(analysis_route).status_code == 200


#: Undeclared nature labels: plausible, short, control free — and refused.
_UNDECLARED_NATURES = ("REEL", "PRODUCTION", "LIVE", "real", "SYNTHETIC ", "IBKR")

#: Values a naive check — or ``Decimal`` itself — accepts, and which the
#: relay would then publish AS A PRICE.
_NOT_A_PRICE = ("204,00", " 204.00", "1e3", "0x10", "２０４.００", "NaN", "-204.00")


def test_population_may_not_claim_a_nature_nobody_declares(
    published: Engine, authenticated: TestClient
) -> None:
    """``population`` separates SYNTHETIC from real: a plausible but
    undeclared label is refused, not displayed as a nature.

    One seeded chain for the whole vocabulary: the exhaustive matrix lives in
    ``apps/api/tests/test_relay_value_contracts.py``; what is proven HERE is
    that the closed vocabulary holds on the really published dossier.
    """
    dossier, as_of = _content(published, "analysis", INSTRUMENT)
    assert dossier["population"] == "SYNTHETIC"
    route = f"/api/v1/analysis/{INSTRUMENT}"
    for forged in _UNDECLARED_NATURES:
        _publish(
            published,
            "analysis",
            INSTRUMENT,
            _replaced(dossier, ("population",), forged),
            as_of,
        )
        response = authenticated.get(route)
        assert response.status_code == 500, forged
        assert response.json()["code"] == "SNAPSHOT_CONTENT_INVALID"
    _publish(published, "analysis", INSTRUMENT, dossier, as_of)
    assert authenticated.get(route).status_code == 200


def test_a_strike_that_is_not_a_decimal_is_refused(
    published: Engine, authenticated: TestClient
) -> None:
    """Not the audit's payload: a strike must be a DECIMAL, not free text."""
    chain, as_of = _content(published, "option_chain", INSTRUMENT)
    path = ("expirations", 0, "contracts", 0, "strike")
    route = f"/api/v1/options/{INSTRUMENT}/chain"
    for forged in _NOT_A_PRICE:
        _publish(
            published,
            "option_chain",
            INSTRUMENT,
            _replaced(chain, path, forged),
            as_of,
        )
        response = authenticated.get(route)
        assert response.status_code == 500, forged
        assert response.json()["code"] == "SNAPSHOT_CONTENT_INVALID"
    _publish(published, "option_chain", INSTRUMENT, chain, as_of)
    assert authenticated.get(route).status_code == 200


def test_an_unresolvable_exchange_timezone_fails_closed(
    published: Engine, authenticated: TestClient
) -> None:
    """P2-1: ``Mars/Olympus`` was served 200 ``state="ok"``.

    Every local instant published beside it — ``event_time_local``, the
    revision history — is stated in that zone, so a zone nothing resolves
    makes them unverifiable.
    """
    agenda, as_of = _content(published, "calendar", "global")
    assert agenda["agenda"], "the worker published an empty agenda"
    assert agenda["agenda"][0]["exchange_timezone"] == "Europe/Zurich"

    healthy = authenticated.get("/api/v1/calendar")
    assert healthy.status_code == 200
    assert healthy.json()["state"] in ("ok", "degraded", "stale")

    _publish(
        published,
        "calendar",
        "global",
        _replaced(
            agenda, ("agenda", 0, "exchange_timezone"), UNRESOLVABLE_TIMEZONE
        ),
        as_of,
    )
    response = authenticated.get("/api/v1/calendar")
    assert response.status_code == 500
    assert response.json()["code"] == "SNAPSHOT_CONTENT_INVALID"
    assert UNRESOLVABLE_TIMEZONE not in response.text


def test_a_refusal_carries_the_field_name_and_never_the_stored_value(
    published: Engine, authenticated: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    """The promise is verified on the LOG, not asserted in a docstring."""
    chain, as_of = _content(published, "option_chain", INSTRUMENT)
    path = ("expirations", 0, "contracts", 0, "strike")
    _publish(
        published, "option_chain", INSTRUMENT, _replaced(chain, path, HOSTILE), as_of
    )

    with caplog.at_level(logging.DEBUG):
        response = authenticated.get(f"/api/v1/options/{INSTRUMENT}/chain")
    assert response.status_code == 500

    records = "\n".join(record.getMessage() for record in caplog.records)
    assert "expirations[0].contracts[0].strike" in records
    assert HOSTILE not in records
    assert "ACHETEZ" not in records
    assert "\x1b" not in records and "\x07" not in records
    assert "ZZZZZ" not in records
