"""Observations: idempotent insert, append-only trigger, fail-closed inputs.

All fixture data is SYNTHETIC (source="SYNTHETIC_TEST") — no real market data.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from vertex_persistence.errors import EnumValidationError, JsonEncodingError, ValidationFailedError
from vertex_persistence.models import Observation
from vertex_persistence.repository import insert_observation

UTC = timezone.utc
T0 = datetime(2026, 8, 28, 12, 0, 0, tzinfo=UTC)


def _insert(session: Session, event_id: str = "evt-1", **overrides: Any) -> bool:
    values: dict[str, Any] = dict(
        event_id=event_id,
        schema_version="1.0.0",
        source="SYNTHETIC_TEST",
        received_at=T0,
        as_of=T0,
        stale_after=T0 + timedelta(minutes=5),
        quality_status="VALID",
        delay_status="LIVE",
        rights="DELAYED_ENTITLED",
        payload={"symbol": "SYN", "last": Decimal("101.25"), "bid": None},
    )
    values.update(overrides)
    return insert_observation(session, **values)


def test_same_event_id_inserted_once(db_session: Session) -> None:
    assert _insert(db_session, "evt-dup") is True
    db_session.commit()
    assert _insert(db_session, "evt-dup") is False  # idempotent: second write is a no-op
    db_session.commit()
    count = db_session.execute(
        select(func.count()).select_from(Observation).where(Observation.event_id == "evt-dup")
    ).scalar_one()
    assert count == 1


def test_duplicate_never_overwrites_original(db_session: Session) -> None:
    _insert(db_session, "evt-keep", payload={"v": 1})
    db_session.commit()
    assert _insert(db_session, "evt-keep", payload={"v": 2}) is False
    db_session.commit()
    row = db_session.execute(
        select(Observation).where(Observation.event_id == "evt-keep")
    ).scalar_one()
    assert row.payload == {"v": 1}


def test_update_forbidden_by_trigger(db_session: Session) -> None:
    _insert(db_session)
    db_session.commit()
    with pytest.raises(DBAPIError, match="append-only"):
        db_session.execute(text("UPDATE observations SET source = 'tampered'"))
    db_session.rollback()


def test_delete_forbidden_by_trigger(db_session: Session) -> None:
    _insert(db_session)
    db_session.commit()
    with pytest.raises(DBAPIError, match="append-only"):
        db_session.execute(text("DELETE FROM observations"))
    db_session.rollback()
    assert db_session.execute(select(func.count()).select_from(Observation)).scalar_one() == 1


def test_payload_stores_decimal_as_exact_string(db_session: Session) -> None:
    _insert(db_session, "evt-decimal", payload={"last": Decimal("0.10"), "size": 0})
    db_session.commit()
    row = db_session.execute(
        select(Observation).where(Observation.event_id == "evt-decimal")
    ).scalar_one()
    assert row.payload["last"] == "0.10"  # exact string, not a float
    assert row.payload["size"] == 0
    assert row.payload_hash.startswith("sha256:")


def test_absent_value_stays_null_not_zero(db_session: Session) -> None:
    _insert(db_session, "evt-absent", payload={"bid": None})
    db_session.commit()
    row = db_session.execute(
        select(Observation).where(Observation.event_id == "evt-absent")
    ).scalar_one()
    assert row.payload["bid"] is None
    assert row.observed_at is None  # optional timestamp not defaulted


def test_naive_datetime_rejected(db_session: Session) -> None:
    with pytest.raises(ValidationFailedError, match="naive"):
        _insert(db_session, as_of=datetime(2026, 8, 28, 12, 0, 0))


def test_non_canonical_quality_status_rejected(db_session: Session) -> None:
    with pytest.raises(EnumValidationError):
        _insert(db_session, quality_status="GOODISH")
    with pytest.raises(EnumValidationError):
        _insert(db_session, delay_status="REALTIME")


def test_nan_payload_rejected(db_session: Session) -> None:
    with pytest.raises(JsonEncodingError):
        _insert(db_session, payload={"last": float("nan")})


def test_check_constraint_blocks_raw_non_canonical_status(db_session: Session) -> None:
    """Even raw SQL cannot store a non-canonical status (CHECK constraint)."""
    with pytest.raises(DBAPIError, match="ck_observations_quality_status_canonical"):
        db_session.execute(
            text(
                "INSERT INTO observations (event_id, schema_version, source, received_at,"
                " as_of, stale_after, quality_status, delay_status, rights, payload,"
                " payload_hash) VALUES ('evt-raw', '1', 'SYNTHETIC_TEST', now(), now(),"
                " now(), 'BOGUS', 'LIVE', 'X', '{}'::jsonb, 'sha256:0')"
            )
        )
    db_session.rollback()
