"""Pydantic validation of the ``vertex.tradingview.alert.v1`` contract.

Local mirror of the Cloudflare Worker validation
(``apps/ingress-tradingview/worker/src/contract.js``): SAME required fields,
patterns, enums and bounds as ``contracts/json-schema/tradingview-alert-v1.schema.json``.
The local side never trusts the Worker: everything is re-validated here.

Ingress policy overlay (stricter than schema v1, never looser):

- ``sent_at`` / ``bar_time`` must be ISO-8601 with an EXPLICIT timezone
  (a naive timestamp is ambiguous -> rejected, fail-closed);
- ``values.nonce`` is REQUIRED: schema v1 has no top-level ``nonce`` field and
  forbids additional properties, so the nonce travels inside ``values``
  (a string map the schema allows). The canonical deduplication key is
  ``alert_id + ":" + nonce`` (``event_id``);
- ``bar_time`` must not follow ``sent_at`` by more than
  ``MAX_BAR_TIME_AHEAD``: a bar cannot close after the alert reporting it.
  Without that bound ``bar_time`` is the one alert timestamp with no bound at
  all, and it is persisted verbatim into the trigger record.

The transported ``price`` is TradingView CONTEXT ONLY. It is never a market
observation, never an authoritative price, and no financial computation is
derived from it anywhere in this package.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from enum import Enum, unique
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
    model_validator,
)

__all__ = [
    "MAX_BAR_TIME_AHEAD",
    "MAX_PAYLOAD_BYTES",
    "MAX_VALUES_PROPERTIES",
    "SCHEMA_ID",
    "AlertRejected",
    "TradingViewAlertV1",
    "TradingViewSignal",
    "ensure_sent_at_in_window",
    "parse_alert",
]

SCHEMA_ID = "vertex.tradingview.alert.v1"
MAX_PAYLOAD_BYTES = 16 * 1024
MAX_VALUES_PROPERTIES = 40
NONCE_KEY = "nonce"

#: Tolerated skew when TradingView stamps ``bar_time`` and ``sent_at`` from its
#: own clocks. Beyond it, a bar claiming to close AFTER the alert that reports
#: it is incoherent evidence and is refused (fail-closed). The past side stays
#: unbounded on purpose: a monthly bar legitimately opened long before.
MAX_BAR_TIME_AHEAD = timedelta(seconds=60)

_SCRIPT_VERSION_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}\.[0-9]+$")
_PRICE_RE = re.compile(r"^-?[0-9]+(?:\.[0-9]+)?$")
_NONCE_RE = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
# ISO-8601 with mandatory explicit timezone (Z or +hh:mm / -hh:mm) — identical
# to the Worker regex.
_TIMESTAMP_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,9})?(?:Z|[+-][0-9]{2}:[0-9]{2})$"
)


class AlertRejected(ValueError):
    """Fail-closed rejection of a payload, carrying an auditable reason code.

    ``reason_code`` never contains payload content and is safe to log/audit.
    """

    def __init__(self, reason_code: str, detail: str = "") -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}" if detail else reason_code)


@unique
class TradingViewSignal(str, Enum):
    """Signal enum, verbatim from the JSON Schema (non-authoritative triggers)."""

    SETUP = "SETUP"
    BREAKOUT = "BREAKOUT"
    BREAKDOWN = "BREAKDOWN"
    REGIME_CHANGE = "REGIME_CHANGE"
    EVENT = "EVENT"
    FUNDAMENTAL_UPDATE = "FUNDAMENTAL_UPDATE"
    HEARTBEAT = "HEARTBEAT"


def _parse_wire_timestamp(value: Any) -> Any:
    """Parse a wire timestamp string into an aware UTC datetime (fail-closed).

    Only strings matching the strict ISO-8601-with-timezone regex are accepted;
    anything else (naive strings, datetimes, numbers) is rejected so that the
    local validation stays byte-for-byte aligned with the Worker.
    """
    if not isinstance(value, str):
        raise ValueError("wire timestamp must be a string")
    if len(value) > 64 or not _TIMESTAMP_RE.match(value):
        raise ValueError("timestamp must be ISO-8601 with an explicit timezone")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        raise ValueError("naive timestamp rejected")
    return parsed.astimezone(UTC)


WireUtcTimestamp = Annotated[datetime, BeforeValidator(_parse_wire_timestamp)]


def _parse_signal(value: Any) -> Any:
    """Map the wire string onto the enum (strict mode does not coerce)."""
    if isinstance(value, TradingViewSignal):
        return value
    if isinstance(value, str):
        try:
            return TradingViewSignal(value)
        except ValueError:
            raise ValueError(
                "signal must be one of " + ", ".join(s.value for s in TradingViewSignal)
            ) from None
    raise ValueError("signal must be a string")


WireSignal = Annotated[TradingViewSignal, BeforeValidator(_parse_signal)]

_ScalarValue = str | int | float | bool | None


class TradingViewAlertV1(BaseModel):
    """One validated ``vertex.tradingview.alert.v1`` payload.

    Strict, frozen, ``extra='forbid'`` — unknown fields, coercible types and
    non-finite numbers are rejected. The ``schema`` wire field maps to
    ``schema_id`` (``schema`` shadows a BaseModel attribute).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True, populate_by_name=False)

    schema_id: str = Field(alias="schema")
    alert_id: Annotated[str, StringConstraints(min_length=1, max_length=120)]
    script_version: str
    sent_at: WireUtcTimestamp
    bar_time: WireUtcTimestamp
    exchange: Annotated[str, StringConstraints(min_length=1, max_length=32)]
    ticker: Annotated[str, StringConstraints(min_length=1, max_length=48)]
    interval: Annotated[str, StringConstraints(min_length=1, max_length=16)]
    signal: WireSignal
    price: str | None = None
    values: Mapping[str, _ScalarValue] | None = None

    @field_validator("schema_id")
    @classmethod
    def _check_schema_const(cls, value: str) -> str:
        if value != SCHEMA_ID:
            raise ValueError(f"schema must be the constant {SCHEMA_ID!r}")
        return value

    @field_validator("script_version")
    @classmethod
    def _check_script_version(cls, value: str) -> str:
        if not _SCRIPT_VERSION_RE.match(value):
            raise ValueError("script_version must match YYYY-MM-DD.N")
        return value

    @field_validator("price")
    @classmethod
    def _check_price(cls, value: str | None) -> str | None:
        if value is not None and not _PRICE_RE.match(value):
            raise ValueError("price must match ^-?[0-9]+(\\.[0-9]+)?$ or be null")
        return value

    @field_validator("values")
    @classmethod
    def _check_values(
        cls, value: Mapping[str, _ScalarValue] | None
    ) -> Mapping[str, _ScalarValue] | None:
        if value is None:
            return None
        if len(value) > MAX_VALUES_PROPERTIES:
            raise ValueError(f"values must carry at most {MAX_VALUES_PROPERTIES} properties")
        for key, item in value.items():
            if not key:
                raise ValueError("values keys must be non-empty strings")
            if isinstance(item, float) and not math.isfinite(item):
                raise ValueError("non-finite numbers are rejected in values")
        return dict(value)

    @model_validator(mode="after")
    def _check_nonce_policy(self) -> TradingViewAlertV1:
        # Ingress policy: values.nonce required (see module docstring).
        if self.values is None or NONCE_KEY not in self.values:
            raise ValueError("missing_nonce: values.nonce is required by the ingress policy")
        nonce = self.values[NONCE_KEY]
        if not isinstance(nonce, str) or not _NONCE_RE.match(nonce):
            raise ValueError("invalid_nonce: values.nonce must match ^[A-Za-z0-9._-]{8,64}$")
        return self

    @model_validator(mode="after")
    def _check_bar_time_coherence(self) -> TradingViewAlertV1:
        # Ingress policy: a bar cannot close after the alert reporting it.
        if self.bar_time - self.sent_at > MAX_BAR_TIME_AHEAD:
            raise ValueError(
                "bar_time_after_sent_at: bar_time must not follow sent_at by more "
                f"than {int(MAX_BAR_TIME_AHEAD.total_seconds())}s"
            )
        return self

    @property
    def nonce(self) -> str:
        """Deduplication nonce (validated ``values.nonce``)."""
        # narrowing mypy, garde réelle au-dessus
        assert self.values is not None  # guaranteed by _check_nonce_policy  # noqa: S101
        nonce = self.values[NONCE_KEY]
        assert isinstance(nonce, str)  # noqa: S101 (narrowing mypy, garde réelle au-dessus)
        return nonce

    @property
    def event_id(self) -> str:
        """Canonical idempotency key: ``alert_id + ':' + nonce``."""
        return f"{self.alert_id}:{self.nonce}"

    def price_context(self) -> Mapping[str, Any]:
        """The transported price as explicitly NON-authoritative context.

        The alert is never a price proof: any revalidation requires a fresh
        IBKR observation (see ``orchestrator``).
        """
        return {
            "value": self.price,
            "authoritative": False,
            "source": "tradingview_alert",
            "note": "context only; never a market observation",
        }


def parse_alert(raw: bytes | bytearray | str | Mapping[str, Any]) -> TradingViewAlertV1:
    """Parse and strictly validate one alert payload (fail-closed).

    Accepts raw bytes/str (size-checked against 16 KiB, strict UTF-8, strict
    JSON) or an already-decoded mapping. Raises :class:`AlertRejected` with an
    auditable ``reason_code`` on any violation; never returns a partial model.
    """
    if isinstance(raw, (bytes, bytearray, str)):
        encoded = raw.encode("utf-8") if isinstance(raw, str) else bytes(raw)
        if len(encoded) > MAX_PAYLOAD_BYTES:
            raise AlertRejected("oversize_payload", f"{len(encoded)} bytes > {MAX_PAYLOAD_BYTES}")
        if len(encoded) == 0:
            raise AlertRejected("empty_payload")
        try:
            decoded = json.loads(encoded.decode("utf-8"))
        except UnicodeDecodeError as exc:
            raise AlertRejected("invalid_encoding", str(exc)) from exc
        except json.JSONDecodeError as exc:
            raise AlertRejected("invalid_json", exc.msg) from exc
    elif isinstance(raw, Mapping):
        decoded = dict(raw)
        # A decoded mapping (e.g. extracted from a queue envelope) must obey
        # the SAME 16 KiB bound as the wire payload: re-serialize compactly
        # and measure (fail-closed on unserializable input).
        try:
            reencoded = json.dumps(decoded, separators=(",", ":"), ensure_ascii=False)
        except (TypeError, ValueError):
            reencoded = None  # let strict model validation name the offending field
        if reencoded is not None and len(reencoded.encode("utf-8")) > MAX_PAYLOAD_BYTES:
            raise AlertRejected("oversize_payload", f"> {MAX_PAYLOAD_BYTES} bytes re-encoded")
    else:
        raise AlertRejected("unsupported_input_type", type(raw).__name__)

    if not isinstance(decoded, dict):
        raise AlertRejected("not_an_object", type(decoded).__name__)

    try:
        return TradingViewAlertV1.model_validate(decoded)
    except ValidationError as exc:
        # Auditable summary: field paths and error types only, never raw values.
        summary = "; ".join(
            f"{'.'.join(str(loc) for loc in err['loc']) or '<root>'}:{err['type']}"
            for err in exc.errors(include_input=False, include_url=False)
        )
        raise AlertRejected("contract_violation", summary) from exc


def ensure_sent_at_in_window(
    alert: TradingViewAlertV1,
    *,
    reference: datetime,
    window: timedelta,
) -> None:
    """Reject alerts whose ``sent_at`` lies outside ``reference +/- window``.

    ``reference`` is the ingress receipt time (``received_at`` stamped at the
    first Vertex boundary), NOT the wall clock at replay time: a queue drained
    after a long local outage must still route old messages (they later expire
    on the HP-02 deadline instead of being re-qualified).

    Raises :class:`AlertRejected` (``sent_at_too_old`` / ``sent_at_in_future``).
    """
    if reference.tzinfo is None or reference.tzinfo.utcoffset(reference) is None:
        raise AlertRejected("naive_reference_clock", "reference must be timezone-aware UTC")
    delta = reference - alert.sent_at
    if delta > window:
        raise AlertRejected(
            "sent_at_too_old", f"sent_at is {delta.total_seconds():.0f}s before reference"
        )
    if -delta > window:
        raise AlertRejected(
            "sent_at_in_future", f"sent_at is {(-delta).total_seconds():.0f}s after reference"
        )
