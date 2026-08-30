"""Calendar chain integration test (real PostgreSQL, real migrations).

Synthetic calendar-event envelopes -> ``ingest_envelope`` (which enqueues an
ADDITIONAL ``calendar.ingested`` message per newly written event) -> bounded
worker run -> published ``calendar/global`` snapshot read back through the
repository.

What this proves end to end, on real rows:

- a REVISION (same stable ``event_id``, later envelope) that moves an event
  from ``ESTIMATED`` to ``CONFIRMED`` replaces the displayed event WITHOUT
  erasing the previous value: the old instant stays readable in
  ``revisions[]`` and is a DIFFERENT instant/label from the confirmed one;
- the agenda is chronologically sorted;
- the importance is reproducible: two identical drains produce the same
  content and publish-if-changed keeps the same version and content hash;
- the crossing with a MANUAL ledger position and a user thesis really
  appears in ``event_context`` and really moves the importance rank.

Every fixture is SYNTHETIC and deterministic (fixed seed, fixed clock).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select

from vertex_core.contracts import (
    DataEnvelope,
    DelayStatus,
    EnvelopeQuality,
    canonical_json_hash,
)
from vertex_core.synthetic import (
    EVENT_CATEGORY_DIVIDEND,
    EVENT_CATEGORY_EARNINGS,
    EVENT_CATEGORY_MACRO,
    EVENT_CATEGORY_OPTION_EXPIRATION,
    EVENT_STATUS_CONFIRMED,
    EVENT_STATUS_ESTIMATED,
    SYNTHETIC_EXCHANGE_TIMEZONE,
    SYNTHETIC_MARKET_CURRENCY,
    SYNTHETIC_RIGHTS,
    SYNTHETIC_SCHEMA_CALENDAR_EVENT,
    SYNTHETIC_SOURCE,
    generate_calendar_event_envelopes,
)
from vertex_persistence.enums import OutboxStatus
from vertex_persistence.models import OutboxMessage
from vertex_persistence.repository.ledger import create_portfolio, record_ledger_event
from vertex_persistence.repository.outbox import enqueue_outbox
from vertex_persistence.repository.snapshots import get_current_snapshot
from vertex_persistence.repository.theses import create_thesis
from vertex_worker.calendar import (
    IMPORTANCE_RULE_RANKS,
    IMPORTANCE_RULE_VERSION,
    SNAPSHOT_KEY_GLOBAL,
    SNAPSHOT_KIND_CALENDAR,
    TOPIC_CALENDAR_INGESTED,
)
from vertex_worker.handlers import DEV_SYNTHETIC_CONFIG, build_registry
from vertex_worker.ingest import ingest_envelope
from vertex_worker.runner import WorkerRunner

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)
BASE_TIME = NOW - timedelta(minutes=30)
SEED = 20260825

POSITION_TICKER = "SYN-ENER-01"  # manual ledger position, earnings event
THESIS_TICKER = "SYN-TECH-01"  # declared user thesis, earnings event
PLAIN_TICKER = "SYN-TECH-02"  # neither: watchlist earnings only
REVISED_TICKER = "SYN-FINL-01"  # ESTIMATED earnings, revised below
REVISED_STABLE_ID = f"syn-ev-earnings-{REVISED_TICKER}"

OPENED_AT = NOW - timedelta(days=2)


class MutableClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def make_runner(session_factory, clock) -> WorkerRunner:
    registry = build_registry(clock=clock, fusion_config=DEV_SYNTHETIC_CONFIG)
    assert TOPIC_CALENDAR_INGESTED in registry.topics
    return WorkerRunner(
        session_factory=session_factory,
        registry=registry,
        poll_interval_seconds=0.05,
        clock=clock,
    )


def _drain_clean(runner: WorkerRunner, session_factory) -> None:
    runner.drain(max_batches=60)
    stats = runner.stats()
    assert stats.failed == 0 and stats.dead == 0 and stats.lease_lost == 0
    with session_factory() as session:
        remaining = session.execute(
            select(func.count())
            .select_from(OutboxMessage)
            .where(OutboxMessage.status != OutboxStatus.DONE.value)
        ).scalar_one()
    assert remaining == 0


def _confirmation_envelope(
    original: DataEnvelope[dict], *, event_id: str, as_of: datetime
) -> DataEnvelope[dict]:
    """A SYNTHETIC revision of one estimated event: same stable id, CONFIRMED.

    The confirmed instant is one day after the estimated one and the previous
    ESTIMATED value is carried in ``revisions[]`` — exactly the shape the
    generator emits for an already-confirmed event, here produced as a LATER
    envelope so the supersession path itself is exercised.
    """
    previous = dict(original.payload)
    assert previous["status"] == EVENT_STATUS_ESTIMATED
    previous_utc = datetime.fromisoformat(previous["event_time_utc"])
    previous_local = datetime.fromisoformat(previous["event_time_local"])
    payload: dict[str, Any] = {
        **previous,
        "status": EVENT_STATUS_CONFIRMED,
        "event_time_utc": (previous_utc + timedelta(days=1)).isoformat(),
        "event_time_local": (previous_local + timedelta(days=1)).isoformat(),
        "revisions": [
            {
                "revised_at": as_of.isoformat(),
                "previous_status": EVENT_STATUS_ESTIMATED,
                "previous_event_time_utc": previous["event_time_utc"],
                "reason": "synthetic confirmation of the estimated date",
            }
        ],
    }
    return DataEnvelope[dict](
        event_id=event_id,
        schema_version=SYNTHETIC_SCHEMA_CALENDAR_EVENT,
        source=SYNTHETIC_SOURCE,
        source_event_id=payload["event_id"],
        entitlement_id=None,
        instrument_id=payload["ticker"],
        observed_at=as_of,
        published_at=as_of,
        received_at=as_of,
        as_of=as_of,
        stale_after=as_of + timedelta(hours=6),
        quality_status=EnvelopeQuality.VALID,
        delay_status=DelayStatus.UNKNOWN,
        connection_epoch=None,
        rights=SYNTHETIC_RIGHTS,
        payload_hash=canonical_json_hash(payload),
        payload=payload,
    )


def _seed_manual_context(session_factory) -> tuple[int, int]:
    """One MANUAL ledger position and one declared user thesis (real repos)."""
    with session_factory() as session:
        portfolio_id = create_portfolio(session, name="main", base_currency="USD")
        record_ledger_event(
            session,
            portfolio_id=portfolio_id,
            kind="BUY_RECORDED",
            amount=Decimal("-1000"),
            currency=SYNTHETIC_MARKET_CURRENCY,
            fees=Decimal("0"),
            effective_at=OPENED_AT,
            recorded_at=OPENED_AT,
            instrument={"ticker": POSITION_TICKER},
            quantity=Decimal("10"),
            price=Decimal("100"),
            note="SYNTHETIC test fact recorded after an execution outside Vertex",
        )
        created = create_thesis(
            session,
            title="SYNTHETIC thesis on the fictional tech name",
            hypotheses="synthetic hypothesis, no real market claim",
            invalidation="synthetic falsifier: the fictional level breaks",
            idempotency_key="syn-thesis-calendar-chain-01",
            now=OPENED_AT,
            instrument={"ticker": THESIS_TICKER},
        )
        session.commit()
        return portfolio_id, created.thesis_id


def test_calendar_chain_end_to_end(session_factory) -> None:
    portfolio_id, thesis_id = _seed_manual_context(session_factory)

    envelopes = generate_calendar_event_envelopes(seed=SEED, base_time=BASE_TIME)
    assert len(envelopes) == 17
    original_estimated = next(
        envelope
        for envelope in envelopes
        if envelope.payload["event_id"] == REVISED_STABLE_ID
    )
    assert original_estimated.payload["status"] == EVENT_STATUS_ESTIMATED
    estimated_instant = original_estimated.payload["event_time_utc"]

    # A LATER envelope of the SAME stable id confirms the estimated date.
    revision = _confirmation_envelope(
        original_estimated,
        event_id=f"{SYNTHETIC_SOURCE}:{SEED}:ev-revision-0001",
        as_of=original_estimated.as_of + timedelta(minutes=10),
    )
    confirmed_instant = revision.payload["event_time_utc"]
    assert confirmed_instant != estimated_instant

    with session_factory() as session:
        inserted = sum(
            1
            for envelope in (*envelopes, revision)
            if ingest_envelope(session, envelope).inserted
        )
        session.commit()
    assert inserted == len(envelopes) + 1 == 18

    with session_factory() as session:
        calendar_jobs = session.execute(
            select(func.count())
            .select_from(OutboxMessage)
            .where(OutboxMessage.topic == TOPIC_CALENDAR_INGESTED)
        ).scalar_one()
    assert calendar_jobs == inserted  # one calendar job per inserted event

    clock = MutableClock(NOW)
    runner = make_runner(session_factory, clock)
    _drain_clean(runner, session_factory)

    with session_factory() as session:
        snapshot = get_current_snapshot(
            session, kind=SNAPSHOT_KIND_CALENDAR, key=SNAPSHOT_KEY_GLOBAL
        )
    assert snapshot is not None
    content = snapshot.content

    assert content["schema_version"] == "vertex.calendar/1.0"
    assert content["population"] == "SYNTHETIC"
    assert content["as_of"] == NOW.isoformat()
    assert content["importance_rule"] == {
        "version": IMPORTANCE_RULE_VERSION,
        "ranks": [dict(entry) for entry in IMPORTANCE_RULE_RANKS],
    }

    agenda = content["agenda"]
    by_stable_id = {entry["event_id"]: entry for entry in agenda}
    assert len(by_stable_id) == len(agenda) == 17  # the revision REPLACED one

    coverage = content["coverage"]
    assert coverage["observations_considered"] == 18
    assert coverage["events_displayed"] == 17
    assert coverage["events_superseded"] == 1
    assert coverage["rejected_records"] == []

    # -- 1. the revision keeps the previous value readable ------------------
    revised = by_stable_id[REVISED_STABLE_ID]
    assert revised["status"] == EVENT_STATUS_CONFIRMED
    assert revised["event_time_utc"] == confirmed_instant
    assert revised["revised"] is True
    assert len(revised["revisions"]) == 1
    kept = revised["revisions"][0]
    # The OLD value is still readable, and it is NOT the confirmed one.
    assert kept["previous_status"] == EVENT_STATUS_ESTIMATED
    assert kept["previous_event_time_utc"] == estimated_instant
    assert kept["previous_status"] != revised["status"]
    assert kept["previous_event_time_utc"] != revised["event_time_utc"]
    # The superseded envelope itself is untouched in the observation table.
    assert revised["source_event_id"] == revision.event_id

    # An event that never moved keeps an EMPTY revision list and its label.
    untouched = by_stable_id[f"syn-ev-earnings-{PLAIN_TICKER}"]
    assert untouched["revisions"] == []
    assert untouched["revised"] is False
    assert untouched["status"] in (EVENT_STATUS_ESTIMATED, EVENT_STATUS_CONFIRMED)

    # Both labels coexist in the published agenda and stay distinct.
    assert content["statuses"][EVENT_STATUS_ESTIMATED] >= 1
    assert content["statuses"][EVENT_STATUS_CONFIRMED] >= 1
    assert (
        content["statuses"][EVENT_STATUS_ESTIMATED]
        + content["statuses"][EVENT_STATUS_CONFIRMED]
        == len(agenda)
    )
    assert sum(content["categories"].values()) == len(agenda)
    assert set(content["categories"]) == {
        EVENT_CATEGORY_EARNINGS,
        EVENT_CATEGORY_DIVIDEND,
        EVENT_CATEGORY_OPTION_EXPIRATION,
        EVENT_CATEGORY_MACRO,
    }

    # -- 2. the agenda is chronologically sorted ----------------------------
    instants = [entry["event_time_utc"] for entry in agenda]
    assert instants == sorted(instants)
    parsed = [datetime.fromisoformat(value) for value in instants]
    assert parsed == sorted(parsed)
    assert all(instant > NOW for instant in parsed)  # upcoming agenda only
    # Timezone conservation: both representations and the IANA label travel.
    for entry in agenda:
        assert entry["exchange_timezone"] == SYNTHETIC_EXCHANGE_TIMEZONE
        assert datetime.fromisoformat(
            entry["event_time_local"]
        ) == datetime.fromisoformat(entry["event_time_utc"])

    # -- 3. the manual position and the thesis really cross the agenda ------
    position_event = by_stable_id[f"syn-ev-earnings-{POSITION_TICKER}"]
    assert position_event["event_context"]["positions"] == [
        {"portfolio_id": portfolio_id}
    ]
    assert position_event["event_context"]["theses"] == []
    assert position_event["importance"] == {
        "rank": 2,
        "code": "EARNINGS_POSITION_OR_THESIS",
        "rule_version": IMPORTANCE_RULE_VERSION,
    }

    thesis_event = by_stable_id[f"syn-ev-earnings-{THESIS_TICKER}"]
    assert thesis_event["event_context"]["positions"] == []
    assert thesis_event["event_context"]["theses"] == [
        {
            "thesis_id": thesis_id,
            "title": "SYNTHETIC thesis on the fictional tech name",
            "status": "ACTIVE",
        }
    ]
    assert thesis_event["importance"]["code"] == "EARNINGS_POSITION_OR_THESIS"
    assert {
        "rel": "thesis",
        "resource": f"theses/{thesis_id}",
    } in thesis_event["event_context"]["links"]

    # A ticker with neither position nor thesis stays a watchlist earning.
    plain_event = by_stable_id[f"syn-ev-earnings-{PLAIN_TICKER}"]
    assert plain_event["event_context"]["positions"] == []
    assert plain_event["event_context"]["theses"] == []
    assert plain_event["importance"] == {
        "rank": 3,
        "code": "EARNINGS_WATCHLIST",
        "rule_version": IMPORTANCE_RULE_VERSION,
    }

    # Every rank published comes from the versioned rule, never an invention.
    declared = {entry["code"]: entry["rank"] for entry in IMPORTANCE_RULE_RANKS}
    for entry in agenda:
        importance = entry["importance"]
        assert importance["rule_version"] == IMPORTANCE_RULE_VERSION
        assert declared[importance["code"]] == importance["rank"]
    macro = [e for e in agenda if e["category"] == EVENT_CATEGORY_MACRO]
    assert macro and all(e["importance"]["code"] == "MACRO_GLOBAL" for e in macro)
    assert all(e["event_context"]["positions"] == [] for e in macro)

    # -- 4. reproducible importance: identical drain republishes nothing ----
    first_version, first_hash = snapshot.version, snapshot.content_hash
    with session_factory() as session:
        enqueue_outbox(
            session,
            TOPIC_CALENDAR_INGESTED,
            {
                "event_id": "replay",
                "source": SYNTHETIC_SOURCE,
                "schema_version": SYNTHETIC_SCHEMA_CALENDAR_EVENT,
            },
        )
        session.commit()
    replay_runner = make_runner(session_factory, clock)
    assert replay_runner.drain(max_batches=5) == 1

    with session_factory() as session:
        replayed = get_current_snapshot(
            session, kind=SNAPSHOT_KIND_CALENDAR, key=SNAPSHOT_KEY_GLOBAL
        )
    assert replayed is not None
    assert replayed.version == first_version
    assert replayed.content_hash == first_hash
    assert replayed.content == content

    # -- 5. later clock: a new version, IDENTICAL agenda and importances ----
    clock.now = NOW + timedelta(minutes=5)
    with session_factory() as session:
        enqueue_outbox(
            session,
            TOPIC_CALENDAR_INGESTED,
            {
                "event_id": "tick",
                "source": SYNTHETIC_SOURCE,
                "schema_version": SYNTHETIC_SCHEMA_CALENDAR_EVENT,
            },
        )
        session.commit()
    later_runner = make_runner(session_factory, clock)
    assert later_runner.drain(max_batches=5) == 1
    with session_factory() as session:
        later = get_current_snapshot(
            session, kind=SNAPSHOT_KIND_CALENDAR, key=SNAPSHOT_KEY_GLOBAL
        )
    assert later is not None
    assert later.version == first_version + 1
    assert later.content["as_of"] == clock.now.isoformat()
    assert later.content["agenda"] == agenda  # only the clock moved
