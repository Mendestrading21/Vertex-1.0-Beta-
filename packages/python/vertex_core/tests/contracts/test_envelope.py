"""DataEnvelope: temporal invariants, strictness, generic payload typing."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from vertex_core.contracts import (
    DataEnvelope,
    DelayStatus,
    EnvelopeQuality,
    Money,
    canonical_json_hash,
)

RECEIVED_AT = datetime(2026, 3, 2, 15, 0, tzinfo=timezone.utc)
PAYLOAD = {"last": Decimal("187.25")}


def make_envelope(**overrides):
    kwargs = dict(
        event_id="evt-0001",
        schema_version="1.0.0",
        source="ibkr.market_data",
        received_at=RECEIVED_AT,
        as_of=RECEIVED_AT,
        stale_after=RECEIVED_AT + timedelta(seconds=30),
        quality_status=EnvelopeQuality.VALID,
        delay_status=DelayStatus.DELAYED,
        rights="display-only",
        payload_hash=canonical_json_hash(PAYLOAD),
        payload=PAYLOAD,
    )
    kwargs.update(overrides)
    return DataEnvelope(**kwargs)


class TestDataEnvelope:
    def test_valid_construction_with_absent_optionals(self):
        env = make_envelope()
        # Absent metadata stays None; it is never fabricated.
        assert env.observed_at is None
        assert env.published_at is None
        assert env.connection_epoch is None

    def test_naive_received_at_rejected(self):
        with pytest.raises(ValidationError, match="naive datetime"):
            make_envelope(received_at=datetime(2026, 3, 2, 15, 0))

    def test_naive_as_of_rejected(self):
        with pytest.raises(ValidationError, match="naive datetime"):
            make_envelope(as_of=datetime(2026, 3, 2, 15, 0))

    def test_naive_observed_at_rejected(self):
        with pytest.raises(ValidationError, match="naive datetime"):
            make_envelope(observed_at=datetime(2026, 3, 2, 14, 59))

    def test_observed_after_received_rejected(self):
        with pytest.raises(ValidationError, match="observed_at"):
            make_envelope(observed_at=RECEIVED_AT + timedelta(seconds=1))

    def test_observed_equal_to_received_accepted(self):
        assert make_envelope(observed_at=RECEIVED_AT).observed_at == RECEIVED_AT

    def test_observed_before_received_accepted(self):
        env = make_envelope(observed_at=RECEIVED_AT - timedelta(seconds=3))
        assert env.observed_at < env.received_at

    def test_malformed_payload_hash_rejected(self):
        for bad in ("deadbeef", "sha256:XYZ", "md5:" + "0" * 64):
            with pytest.raises(ValidationError):
                make_envelope(payload_hash=bad)

    def test_frozen(self):
        env = make_envelope()
        with pytest.raises(ValidationError):
            env.quality_status = EnvelopeQuality.STALE

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            make_envelope(account_value=Decimal("1"))

    def test_quality_and_delay_are_canonical_enums(self):
        env = make_envelope(
            quality_status=EnvelopeQuality.INSUFFICIENT_DATA,
            delay_status=DelayStatus.DELAYED_FROZEN,
        )
        assert env.quality_status is EnvelopeQuality.INSUFFICIENT_DATA
        assert env.delay_status is DelayStatus.DELAYED_FROZEN

    def test_generic_parametrization_with_model_payload(self):
        money = Money(amount=Decimal("42.10"), currency="USD")
        env = DataEnvelope[Money](
            event_id="evt-0002",
            schema_version="1.0.0",
            source="manual.declaration",
            received_at=RECEIVED_AT,
            as_of=RECEIVED_AT,
            stale_after=RECEIVED_AT + timedelta(minutes=5),
            quality_status=EnvelopeQuality.VALID,
            delay_status=DelayStatus.UNKNOWN,
            rights="internal",
            payload_hash=canonical_json_hash(money),
            payload=money,
        )
        assert isinstance(env.payload, Money)
        assert env.payload.amount == Decimal("42.10")

    def test_generic_payload_is_validated(self):
        with pytest.raises(ValidationError):
            DataEnvelope[Money](
                event_id="evt-0003",
                schema_version="1.0.0",
                source="manual.declaration",
                received_at=RECEIVED_AT,
                as_of=RECEIVED_AT,
                stale_after=RECEIVED_AT + timedelta(minutes=5),
                quality_status=EnvelopeQuality.VALID,
                delay_status=DelayStatus.UNKNOWN,
                rights="internal",
                payload_hash=canonical_json_hash({"amount": "x"}),
                payload={"amount": "not-a-decimal", "currency": "USD"},
            )
