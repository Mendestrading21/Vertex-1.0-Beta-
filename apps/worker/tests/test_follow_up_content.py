"""Unit tests of the review queue content builder (SYNTHETIC fakes only).

Pure-builder tests: no database, no clock reads, no network. The real chain
(API write -> outbox -> worker -> snapshot -> GET) is exercised in
``apps/api/tests_integration/test_follow_up_api_e2e.py``.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta

from vertex_persistence.repository.theses import (
    ProjectedThesis,
    ThesisRecord,
    ThesisState,
)
from vertex_worker.follow_up import (
    REASON_NEW_INFORMATION,
    build_review_queue_content,
    due_sort_key,
)
from vertex_worker.handlers import (
    CONTENT_SCHEMA_PREFIXES,
    DEV_SYNTHETIC_CONFIG,
    ObservationRecord,
)

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)
TICKER = "SYN-TECH-01"


def make_projected(
    thesis_id: int,
    *,
    ticker: str | None = None,
    review_due_at: datetime | None = None,
    base_due: datetime | None = None,
    is_due: bool = False,
    last_recorded_at: datetime | None = None,
    last_reviewed_at: datetime | None = None,
    created_at: datetime | None = None,
    status: str = "ACTIVE",
) -> ProjectedThesis:
    created = created_at if created_at is not None else NOW - timedelta(days=10)
    return ProjectedThesis(
        thesis=ThesisRecord(
            id=thesis_id,
            portfolio_id=None,
            instrument={"ticker": ticker} if ticker is not None else None,
            title=f"SYNTHETIC thesis {thesis_id}",
            hypotheses="[SYNTHETIC] hypotheses text",
            invalidation="[SYNTHETIC] what would prove it wrong",
            horizon=None,
            review_due_at=base_due,
            created_at=created,
        ),
        state=ThesisState(
            status=status,
            review_due_at=review_due_at,
            is_due=is_due,
            snooze_until=None,
            last_reviewed_at=last_reviewed_at,
            last_action="CREATED",
            last_recorded_at=(
                last_recorded_at if last_recorded_at is not None else created
            ),
            revision_count=1,
        ),
    )


def make_record(
    event_id: str,
    *,
    title: str,
    entities: list[str] | None = None,
    received_at: datetime,
) -> ObservationRecord:
    return ObservationRecord(
        event_id=event_id,
        source="synthetic-dev",
        source_event_id=f"native-{event_id}",
        instrument_ref=None,
        published_at=received_at - timedelta(minutes=1),
        received_at=received_at,
        as_of=received_at,
        quality_status="VALID",
        rights="SYNTHETIC",
        schema_version="synthetic-news/1.0",
        payload={"title": title, "entities": entities or []},
    )


# -- documented lexicographic ordering of the due queue ----------------------


def test_due_queue_lexicographic_ordering() -> None:
    """Order: effective due asc, base due asc, last_recorded asc, id asc."""
    oldest_due = NOW - timedelta(days=5)
    newer_due = NOW - timedelta(days=1)
    due = [
        # Same effective due as thesis 2 but base deadline closer -> before 2.
        make_projected(
            3,
            review_due_at=newer_due,
            base_due=newer_due,
            is_due=True,
            last_recorded_at=NOW - timedelta(days=2),
        ),
        # Most overdue -> always first, whatever the other keys say.
        make_projected(
            5,
            review_due_at=oldest_due,
            base_due=oldest_due,
            is_due=True,
            last_recorded_at=NOW - timedelta(hours=1),
        ),
        make_projected(
            2,
            review_due_at=newer_due,
            base_due=newer_due + timedelta(days=3),
            is_due=True,
            last_recorded_at=NOW - timedelta(days=9),
        ),
        # Ties with 4 on every temporal key -> thesis id decides.
        make_projected(
            7,
            review_due_at=newer_due,
            base_due=newer_due + timedelta(days=3),
            is_due=True,
            last_recorded_at=NOW - timedelta(days=9),
        ),
    ]
    content = build_review_queue_content(due, due, [], now=NOW, config=DEV_SYNTHETIC_CONFIG)
    assert [entry["thesis_id"] for entry in content["due"]] == [5, 3, 2, 7]
    assert [entry["rank"] for entry in content["due"]] == [1, 2, 3, 4]
    # Overdue durations are explicit and non-negative.
    assert content["due"][0]["overdue_seconds"] == 5 * 86400
    # The ordering contract is published with the content.
    assert content["ordering"]["method"] == "lexicographic"
    assert len(content["ordering"]["keys"]) == 4


def test_due_sort_key_is_deterministic_under_shuffle() -> None:
    entries = [
        make_projected(i, review_due_at=NOW - timedelta(days=i), is_due=True)
        for i in range(1, 6)
    ]
    forward = sorted(entries, key=due_sort_key)
    backward = sorted(entries, key=due_sort_key)
    assert [e.thesis.id for e in forward] == [e.thesis.id for e in backward]


# -- has_new_information: flag + reason, never a thesis write ----------------


def test_new_information_raises_urgency_without_touching_the_thesis() -> None:
    reviewed_at = NOW - timedelta(days=2)
    thesis = make_projected(
        1,
        ticker=TICKER,
        review_due_at=NOW - timedelta(days=1),
        is_due=True,
        last_reviewed_at=reviewed_at,
    )
    fresh = make_record(
        "evt-new",
        title="[SYNTHETIC] fresh news about the ticker",
        entities=[TICKER],
        received_at=NOW - timedelta(hours=1),  # AFTER the last review
    )
    before_thesis = dataclasses.asdict(thesis.thesis)
    before_state = dataclasses.asdict(thesis.state)

    content = build_review_queue_content(
        [thesis], [thesis], [fresh], now=NOW, config=DEV_SYNTHETIC_CONFIG
    )

    entry = content["theses"][0]
    assert entry["has_new_information"] is True
    reasons = entry["urgency_reasons"]
    assert len(reasons) == 1
    assert reasons[0]["code"] == REASON_NEW_INFORMATION
    assert reasons[0]["reference_instant"] == reviewed_at.isoformat()
    # The due entry carries the raised urgency too.
    assert content["due"][0]["has_new_information"] is True

    # The thesis itself was NEVER modified: the builder consumed frozen
    # projections and the snapshot relays them unchanged (revision_count,
    # due instant and state all identical to the input projection).
    assert dataclasses.asdict(thesis.thesis) == before_thesis
    assert dataclasses.asdict(thesis.state) == before_state
    assert entry["state"]["revision_count"] == 1
    assert entry["state"]["review_due_at"] == before_state["review_due_at"].isoformat()


def test_information_older_than_last_review_is_context_not_urgency() -> None:
    thesis = make_projected(
        1,
        ticker=TICKER,
        review_due_at=NOW - timedelta(days=1),
        is_due=True,
        last_reviewed_at=NOW - timedelta(hours=2),
    )
    stale_info = make_record(
        "evt-old",
        title="[SYNTHETIC] already-reviewed news",
        entities=[TICKER],
        received_at=NOW - timedelta(days=1),  # BEFORE the last review
    )
    content = build_review_queue_content(
        [thesis], [thesis], [stale_info], now=NOW, config=DEV_SYNTHETIC_CONFIG
    )
    entry = content["theses"][0]
    # The cluster is still attached as CONTEXT with provenance...
    assert len(entry["information_context"]["clusters"]) == 1
    provenance = entry["information_context"]["clusters"][0]["provenance"]
    assert provenance["member_event_ids"] == ["evt-old"]
    assert provenance["sources"] == ["synthetic-dev"]
    assert provenance["rights"] == ["SYNTHETIC"]
    # ...but it raises no urgency.
    assert entry["has_new_information"] is False
    assert entry["urgency_reasons"] == []


def test_thesis_without_instrument_gets_no_information_context() -> None:
    thesis = make_projected(1, ticker=None)
    record = make_record(
        "evt-any", title="[SYNTHETIC] news", entities=[TICKER], received_at=NOW
    )
    content = build_review_queue_content(
        [thesis], [], [record], now=NOW, config=DEV_SYNTHETIC_CONFIG
    )
    entry = content["theses"][0]
    assert entry["instrument_ticker"] is None
    assert entry["information_context"]["clusters"] == []
    assert entry["has_new_information"] is False


# -- populations are labeled separately, never aggregated --------------------


def test_populations_stay_separate_labels() -> None:
    thesis = make_projected(1, ticker=TICKER)
    record = make_record(
        "evt-1", title="[SYNTHETIC] news", entities=[TICKER], received_at=NOW
    )
    content = build_review_queue_content(
        [thesis], [], [record], now=NOW, config=DEV_SYNTHETIC_CONFIG
    )
    populations = content["populations"]
    # Two SIDE-BY-SIDE labels; no single merged population field exists.
    assert populations == {
        "theses": "USER_DECLARED",
        "information_context": "SYNTHETIC",
    }
    assert "population" not in content
    # With no observation at all the context population is honestly EMPTY.
    empty = build_review_queue_content(
        [thesis], [], [], now=NOW, config=DEV_SYNTHETIC_CONFIG
    )
    assert empty["populations"]["information_context"] == "EMPTY"
    assert empty["populations"]["theses"] == "USER_DECLARED"


def test_builder_is_deterministic_and_counts_coverage() -> None:
    theses = [
        make_projected(1, ticker=TICKER, review_due_at=NOW - timedelta(days=1), is_due=True),
        make_projected(2),
    ]
    records = [
        make_record("evt-b", title="[SYNTHETIC] b", entities=[TICKER], received_at=NOW),
        make_record(
            "evt-a", title="[SYNTHETIC] a", entities=[TICKER], received_at=NOW - timedelta(hours=1)
        ),
    ]
    first = build_review_queue_content(
        theses, [theses[0]], records, now=NOW, config=DEV_SYNTHETIC_CONFIG
    )
    second = build_review_queue_content(
        list(reversed(theses)),
        [theses[0]],
        list(reversed(records)),
        now=NOW,
        config=DEV_SYNTHETIC_CONFIG,
    )
    assert first == second
    coverage = first["coverage"]
    assert coverage["theses_total"] == 2
    assert coverage["due_count"] == 1
    assert coverage["theses_with_instrument"] == 1
    assert coverage["observations_considered"] == 2
    assert coverage["content_observations"] == 2


def test_coverage_publishes_the_declared_content_families() -> None:
    """La couverture dit quelles familles la fenêtre a regardées (S0)."""
    content = build_review_queue_content([], [], [], now=NOW, config=DEV_SYNTHETIC_CONFIG)
    assert content["coverage"]["content_schema_prefixes"] == list(CONTENT_SCHEMA_PREFIXES)
    assert content["coverage"]["observations_considered"] == 0
