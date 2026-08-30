"""Contract tests for vertex.tradingview.alert.v1 (Pydantic mirror)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from conftest import make_alert_payload

from vertex_ingress_tv.schema import (
    MAX_PAYLOAD_BYTES,
    AlertRejected,
    TradingViewAlertV1,
    TradingViewSignal,
    ensure_sent_at_in_window,
    parse_alert,
)

T_REF = datetime(2026, 8, 29, 12, 0, 0, tzinfo=UTC)
WINDOW = timedelta(seconds=300)


def reject(payload, expected_reason: str) -> AlertRejected:
    with pytest.raises(AlertRejected) as exc_info:
        parse_alert(payload)
    assert exc_info.value.reason_code == expected_reason, exc_info.value.detail
    return exc_info.value


class TestValidAlert:
    def test_valid_payload_parses(self) -> None:
        alert = parse_alert(make_alert_payload())
        assert alert.schema_id == "vertex.tradingview.alert.v1"
        assert alert.alert_id == "syn-market-regime-v1"
        assert alert.signal is TradingViewSignal.REGIME_CHANGE
        assert alert.sent_at == datetime(2026, 8, 29, 11, 59, 30, tzinfo=UTC)
        assert alert.sent_at.tzinfo is not None  # aware, always

    def test_valid_payload_parses_from_bytes_and_str(self) -> None:
        raw = json.dumps(make_alert_payload())
        assert parse_alert(raw).event_id == "syn-market-regime-v1:1787999700000"
        assert parse_alert(raw.encode()).event_id == "syn-market-regime-v1:1787999700000"

    def test_event_id_is_alert_id_plus_nonce(self) -> None:
        alert = parse_alert(make_alert_payload())
        assert alert.nonce == "1787999700000"
        assert alert.event_id == "syn-market-regime-v1:1787999700000"

    def test_offset_timestamps_normalize_to_utc(self) -> None:
        alert = parse_alert(make_alert_payload(sent_at="2026-08-29T13:59:30+02:00"))
        assert alert.sent_at == datetime(2026, 8, 29, 11, 59, 30, tzinfo=UTC)

    def test_null_and_absent_price_are_distinct_from_zero(self) -> None:
        assert parse_alert(make_alert_payload(price=None)).price is None
        payload = make_alert_payload()
        del payload["price"]
        assert parse_alert(payload).price is None

    def test_price_context_is_never_authoritative(self) -> None:
        context = parse_alert(make_alert_payload()).price_context()
        assert context["authoritative"] is False
        assert context["source"] == "tradingview_alert"
        assert context["value"] == "123.45"


class TestRejections:
    def test_oversize_payload_rejected(self) -> None:
        payload = make_alert_payload(
            values={"nonce": "1787999700000", "pad": "x" * (MAX_PAYLOAD_BYTES + 100)}
        )
        reject(json.dumps(payload), "oversize_payload")

    def test_payload_at_exactly_16k_boundary(self) -> None:
        def padded(pad_len: int) -> str:
            return json.dumps(
                make_alert_payload(values={"nonce": "1787999700000", "pad": "x" * pad_len})
            )

        overhead = len(padded(0).encode())
        one_over = MAX_PAYLOAD_BYTES - overhead + 1
        assert len(padded(one_over).encode()) == MAX_PAYLOAD_BYTES + 1
        reject(padded(one_over), "oversize_payload")
        # Exactly 16 KiB stays accepted (boundary is inclusive).
        assert len(padded(one_over - 1).encode()) == MAX_PAYLOAD_BYTES
        assert parse_alert(padded(one_over - 1)).nonce == "1787999700000"

    def test_empty_and_invalid_json_rejected(self) -> None:
        reject(b"", "empty_payload")
        reject(b"{not json", "invalid_json")
        reject(b"\xff\xfe", "invalid_encoding")

    def test_non_object_json_rejected(self) -> None:
        reject(b"[1, 2]", "not_an_object")
        reject(b'"alert"', "not_an_object")

    def test_unknown_field_rejected(self) -> None:
        reject(make_alert_payload(surprise="x"), "contract_violation")

    @pytest.mark.parametrize(
        "missing",
        [
            "schema",
            "alert_id",
            "script_version",
            "sent_at",
            "bar_time",
            "exchange",
            "ticker",
            "interval",
            "signal",
        ],
    )
    def test_each_required_field_missing_rejected(self, missing: str) -> None:
        payload = make_alert_payload()
        del payload[missing]
        reject(payload, "contract_violation")

    def test_wrong_schema_constant_rejected(self) -> None:
        reject(make_alert_payload(schema="vertex.tradingview.alert.v2"), "contract_violation")

    @pytest.mark.parametrize("bad", ["v1", "2026-08-29", "26-08-29.1", "2026-08-29.1x"])
    def test_bad_script_version_rejected(self, bad: str) -> None:
        reject(make_alert_payload(script_version=bad), "contract_violation")

    @pytest.mark.parametrize(
        "bad", ["2026-08-29T11:59:30", "2026-08-29 11:59:30Z", "not-a-date", "", 1756465170]
    )
    def test_naive_or_malformed_timestamps_rejected(self, bad) -> None:
        reject(make_alert_payload(sent_at=bad), "contract_violation")
        reject(make_alert_payload(bar_time=bad), "contract_violation")

    def test_unknown_signal_rejected(self) -> None:
        reject(make_alert_payload(signal="BUY_NOW"), "contract_violation")

    @pytest.mark.parametrize("bad", ["", "12.", ".5", "1,5", "1e3", "NaN", 123.45])
    def test_bad_price_rejected(self, bad) -> None:
        reject(make_alert_payload(price=bad), "contract_violation")

    def test_values_nesting_and_bounds_rejected(self) -> None:
        reject(
            make_alert_payload(values={"nonce": "1787999700000", "nested": {}}),
            "contract_violation",
        )
        reject(
            make_alert_payload(values={"nonce": "1787999700000", "arr": [1]}),
            "contract_violation",
        )
        too_many = {"nonce": "1787999700000"}
        too_many.update({f"k{i}": i for i in range(40)})
        reject(make_alert_payload(values=too_many), "contract_violation")

    def test_non_finite_number_in_values_rejected(self) -> None:
        # JSON cannot carry NaN, but a mapping input could (fail-closed anyway).
        reject(
            make_alert_payload(values={"nonce": "1787999700000", "bad": float("nan")}),
            "contract_violation",
        )

    def test_missing_or_invalid_nonce_rejected(self) -> None:
        payload = make_alert_payload()
        del payload["values"]
        reject(payload, "contract_violation")
        reject(make_alert_payload(values={"volume": "1"}), "contract_violation")
        reject(make_alert_payload(values={"nonce": "short"}), "contract_violation")
        reject(make_alert_payload(values={"nonce": 1787999700000}), "contract_violation")

    def test_rejection_detail_never_contains_payload_values(self) -> None:
        exc = reject(make_alert_payload(price="99999.99999x"), "contract_violation")
        assert "99999.99999" not in exc.detail
        assert "price" in exc.detail  # field path only


class TestBarTimeIsBoundedBySentAt:
    """A bar cannot close after the alert that reports it (policy overlay).

    ``bar_time`` is the only alert timestamp with no bound at all: it is
    persisted verbatim into the trigger record and read downstream. An alert
    claiming a bar in 2126 must not become a stored fact.
    """

    def test_bar_time_far_after_sent_at_is_rejected(self) -> None:
        reject(
            make_alert_payload(sent_at="2026-08-29T11:59:30Z", bar_time="2126-08-29T11:55:00Z"),
            "contract_violation",
        )

    def test_bar_time_before_sent_at_is_accepted(self) -> None:
        # A weekly bar opened long before the alert fired stays valid.
        alert = parse_alert(
            make_alert_payload(sent_at="2026-08-29T11:59:30Z", bar_time="2026-08-24T00:00:00Z")
        )
        assert alert.bar_time < alert.sent_at

    def test_small_provider_skew_is_tolerated(self) -> None:
        # TradingView stamps bar_time and sent_at from its own clocks.
        alert = parse_alert(
            make_alert_payload(sent_at="2026-08-29T11:59:30Z", bar_time="2026-08-29T11:59:31Z")
        )
        assert alert.bar_time > alert.sent_at


class TestSentAtWindow:
    def _alert(self, sent_at: str) -> TradingViewAlertV1:
        return parse_alert(make_alert_payload(sent_at=sent_at))

    def test_within_window_accepted(self) -> None:
        ensure_sent_at_in_window(
            self._alert("2026-08-29T11:59:30Z"), reference=T_REF, window=WINDOW
        )

    def test_exactly_at_window_edge_accepted(self) -> None:
        ensure_sent_at_in_window(
            self._alert("2026-08-29T11:55:00Z"), reference=T_REF, window=WINDOW
        )

    def test_too_old_rejected(self) -> None:
        with pytest.raises(AlertRejected) as exc_info:
            ensure_sent_at_in_window(
                self._alert("2026-08-29T11:54:59Z"), reference=T_REF, window=WINDOW
            )
        assert exc_info.value.reason_code == "sent_at_too_old"

    def test_future_rejected(self) -> None:
        with pytest.raises(AlertRejected) as exc_info:
            ensure_sent_at_in_window(
                self._alert("2026-08-29T12:05:01Z"), reference=T_REF, window=WINDOW
            )
        assert exc_info.value.reason_code == "sent_at_in_future"

    def test_naive_reference_clock_rejected(self) -> None:
        with pytest.raises(AlertRejected) as exc_info:
            ensure_sent_at_in_window(
                self._alert("2026-08-29T11:59:30Z"),
                reference=datetime(2026, 8, 29, 12, 0, 0),  # noqa: DTZ001 (naïf délibéré : rejet vérifié)
                window=WINDOW,
            )
        assert exc_info.value.reason_code == "naive_reference_clock"
