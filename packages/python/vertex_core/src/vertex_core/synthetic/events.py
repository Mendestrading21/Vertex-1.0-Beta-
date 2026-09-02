"""Deterministic generator of clearly-synthetic calendar-event envelopes.

Feeds the Calendar page chain (page 02) in development without touching any
real market data:

- EARNINGS events for the focus tickers: some stay ``ESTIMATED``; the others
  are ``CONFIRMED`` through a DATED REVISION whose entry preserves the
  previous status and the previous event instant (estimated and confirmed
  are never the same label, and the old value is never erased);
- DIVIDEND events (ex-date facts) for a subset of the focus tickers;
- OPTION_EXPIRATION events DERIVED from the existing synthetic option-chain
  generator (:func:`vertex_core.synthetic.options.generate_option_chain_envelopes`):
  the expiration dates are read from the generated chains themselves, so the
  calendar can never drift from the chains (single declaration, no second
  authority);
- 3 global MACRO events (no ticker).

Every event carries a STABLE ``event_id`` (derived from category, ticker and
date — replaying the generator yields the same ids), the canonical status
``ESTIMATED`` or ``CONFIRMED``, its instant BOTH as aware UTC
(``event_time_utc``) and in the declared exchange timezone
(``event_time_local`` + ``exchange_timezone``, IANA), ``source =
synthetic-dev``, ``rights = SYNTHETIC`` and a ``revisions`` list where every
entry keeps the previous value.

Determinism: pure function of ``(seed, base_time)``; identical inputs produce
identical envelopes, byte for byte. No hidden entropy, no system clock.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from vertex_core.contracts import (
    DataEnvelope,
    DelayStatus,
    EnvelopeQuality,
    canonical_json_hash,
    ensure_utc,
)
from vertex_core.synthetic.generator import (
    SYNTHETIC_RIGHTS,
    SYNTHETIC_SOURCE,
    SYNTHETIC_TITLE_PREFIX,
)
from vertex_core.synthetic.market import SYNTHETIC_FOCUS_TICKERS
from vertex_core.synthetic.options import generate_option_chain_envelopes

__all__ = [
    "EVENT_CATEGORY_DIVIDEND",
    "EVENT_CATEGORY_EARNINGS",
    "EVENT_CATEGORY_MACRO",
    "EVENT_CATEGORY_OPTION_EXPIRATION",
    "EVENT_SCOPE_GLOBAL",
    "EVENT_SCOPE_TICKER",
    "EVENT_STATUS_CONFIRMED",
    "EVENT_STATUS_ESTIMATED",
    "SYNTHETIC_EXCHANGE_TIMEZONE",
    "SYNTHETIC_MACRO_EVENT_COUNT",
    "SYNTHETIC_SCHEMA_CALENDAR_EVENT",
    "generate_calendar_event_envelopes",
]


SYNTHETIC_SCHEMA_CALENDAR_EVENT = "synthetic-calendar-event/1.0"
"""Schema version of every generated calendar-event envelope."""

SYNTHETIC_EXCHANGE_TIMEZONE = "Europe/Zurich"
"""Declared IANA timezone of the fictional SYNTH exchange. The timezone label
travels with every event so downstream consumers can prove they conserve it —
it is a fixture attribute, never real market metadata."""

EVENT_STATUS_ESTIMATED = "ESTIMATED"
EVENT_STATUS_CONFIRMED = "CONFIRMED"
"""The two canonical, always-distinct date statuses of a calendar event."""

EVENT_CATEGORY_EARNINGS = "EARNINGS"
EVENT_CATEGORY_DIVIDEND = "DIVIDEND"
EVENT_CATEGORY_OPTION_EXPIRATION = "OPTION_EXPIRATION"
EVENT_CATEGORY_MACRO = "MACRO"

EVENT_SCOPE_TICKER = "TICKER"
EVENT_SCOPE_GLOBAL = "GLOBAL"

SYNTHETIC_MACRO_EVENT_COUNT = 3
"""Number of generated global macro events."""

_LOCAL_EVENT_TIME = time(hour=17, minute=30)
"""Fixed local wall-clock instant of every synthetic event (exchange tz)."""

_PUBLISH_OFFSET = timedelta(hours=2)
_RECEIVE_LAG = timedelta(seconds=30)
_STALE_GRACE = timedelta(hours=6)
_REVISION_AGE = timedelta(hours=26)

_MACRO_TITLES = (
    "Fictional central bank policy decision",
    "Fictional inflation figures release",
    "Fictional employment report",
)
_MACRO_DAY_OFFSETS = (5, 10, 20)
_MACRO_STATUSES = (
    EVENT_STATUS_CONFIRMED,
    EVENT_STATUS_CONFIRMED,
    EVENT_STATUS_ESTIMATED,
)

_DIVIDEND_TICKER_COUNT = 2
_DIVIDEND_DAY_OFFSETS = (14, 21)
_DIVIDEND_AMOUNT_TEXTS = ("0.35", "0.60")
_EARNINGS_FIRST_OFFSET_DAYS = 7
_EARNINGS_SPACING_DAYS = 3


def _validate_inputs(seed: int, base_time: datetime) -> datetime:
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise TypeError(f"seed: expected int, got {type(seed).__name__}")
    if not isinstance(base_time, datetime):
        raise TypeError(f"base_time: expected datetime, got {type(base_time).__name__}")
    return ensure_utc(base_time)


def _local_instant(day: date, tz: ZoneInfo) -> datetime:
    """Aware instant at the fixed local wall-clock time of ``day`` (a date)."""
    return datetime.combine(day, _LOCAL_EVENT_TIME, tzinfo=tz)


def _time_fields(instant_local: datetime) -> dict[str, str]:
    """Both representations of one instant: UTC and the exchange timezone."""
    return {
        "event_time_utc": instant_local.astimezone(ZoneInfo("UTC")).isoformat(),
        "event_time_local": instant_local.isoformat(),
        "exchange_timezone": SYNTHETIC_EXCHANGE_TIMEZONE,
    }


def _event_payload(
    *,
    stable_id: str,
    category: str,
    status: str,
    title: str,
    ticker: str | None,
    instant_local: datetime,
    revisions: list[dict[str, Any]],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": "calendar_event",
        "synthetic": True,
        "event_id": stable_id,
        "category": category,
        "status": status,
        "title": SYNTHETIC_TITLE_PREFIX + title,
        "ticker": ticker,
        "scope": EVENT_SCOPE_TICKER if ticker is not None else EVENT_SCOPE_GLOBAL,
        **_time_fields(instant_local),
        "revisions": revisions,
        "note": (
            "[SYNTHETIC] fixture calendar event; generated data, never real market information."
        ),
    }
    if extra:
        payload.update(extra)
    return payload


def _chain_expirations(*, seed: int, base_time: datetime) -> list[tuple[str, str]]:
    """Unique (underlying, expiration ISO date) pairs of the generated chains.

    Read from the option-chain generator's own output so the calendar and the
    chains share ONE declaration of the expiration dates.
    """
    pairs: set[tuple[str, str]] = set()
    for envelope in generate_option_chain_envelopes(seed=seed, base_time=base_time):
        payload = envelope.payload
        pairs.add((payload["underlying"], payload["expiration"]))
    return sorted(pairs)


def generate_calendar_event_envelopes(
    *, seed: int, base_time: datetime
) -> tuple[DataEnvelope[dict[str, Any]], ...]:
    """Generate the deterministic synthetic calendar-event envelope set.

    Pure function of ``(seed, base_time)``. Per focus ticker one EARNINGS
    event — even-indexed tickers are ``CONFIRMED`` through a dated revision
    that preserves the previous ``ESTIMATED`` instant, odd-indexed tickers
    stay ``ESTIMATED`` —, DIVIDEND events for the first
    :data:`_DIVIDEND_TICKER_COUNT` tickers, one OPTION_EXPIRATION event per
    (underlying, expiration) pair actually present in the generated chains,
    and :data:`SYNTHETIC_MACRO_EVENT_COUNT` global MACRO events. Every
    envelope timestamp lies strictly before ``base_time``; the event instants
    themselves lie after it (upcoming agenda).
    """
    base = _validate_inputs(seed, base_time)
    tz = ZoneInfo(SYNTHETIC_EXCHANGE_TIMEZONE)

    published_at = base - _PUBLISH_OFFSET
    received_at = published_at + _RECEIVE_LAG
    revised_at = base - _REVISION_AGE

    entries: list[tuple[str, dict[str, Any]]] = []  # (stable_id, payload)

    # -- earnings (estimated, or confirmed through a dated revision) ---------
    for index, ticker in enumerate(SYNTHETIC_FOCUS_TICKERS):
        estimated_day = (
            base + timedelta(days=_EARNINGS_FIRST_OFFSET_DAYS + _EARNINGS_SPACING_DAYS * index)
        ).date()
        estimated_local = _local_instant(estimated_day, tz)
        stable_id = f"syn-ev-earnings-{ticker}"
        if index % 2 == 0:
            confirmed_local = _local_instant(estimated_day + timedelta(days=1), tz)
            revisions = [
                {
                    "revised_at": revised_at.isoformat(),
                    "previous_status": EVENT_STATUS_ESTIMATED,
                    "previous_event_time_utc": estimated_local.astimezone(
                        ZoneInfo("UTC")
                    ).isoformat(),
                    "reason": "synthetic confirmation of the estimated date",
                }
            ]
            payload = _event_payload(
                stable_id=stable_id,
                category=EVENT_CATEGORY_EARNINGS,
                status=EVENT_STATUS_CONFIRMED,
                title=f"Fictional quarterly results of {ticker}",
                ticker=ticker,
                instant_local=confirmed_local,
                revisions=revisions,
            )
        else:
            payload = _event_payload(
                stable_id=stable_id,
                category=EVENT_CATEGORY_EARNINGS,
                status=EVENT_STATUS_ESTIMATED,
                title=f"Fictional quarterly results of {ticker}",
                ticker=ticker,
                instant_local=estimated_local,
                revisions=[],
            )
        entries.append((stable_id, payload))

    # -- dividends (confirmed ex-date facts) ---------------------------------
    for index, ticker in enumerate(SYNTHETIC_FOCUS_TICKERS[:_DIVIDEND_TICKER_COUNT]):
        ex_day = (base + timedelta(days=_DIVIDEND_DAY_OFFSETS[index])).date()
        stable_id = f"syn-ev-dividend-{ticker}-{ex_day.isoformat()}"
        payload = _event_payload(
            stable_id=stable_id,
            category=EVENT_CATEGORY_DIVIDEND,
            status=EVENT_STATUS_CONFIRMED,
            title=f"Fictional ex-dividend date of {ticker}",
            ticker=ticker,
            instant_local=_local_instant(ex_day, tz),
            revisions=[],
            extra={
                "amount": _DIVIDEND_AMOUNT_TEXTS[index],
                "currency": "SYN",
            },
        )
        entries.append((stable_id, payload))

    # -- option expirations derived from the existing chains -----------------
    for underlying, expiration in _chain_expirations(seed=seed, base_time=base):
        stable_id = f"syn-ev-expiry-{underlying}-{expiration}"
        payload = _event_payload(
            stable_id=stable_id,
            category=EVENT_CATEGORY_OPTION_EXPIRATION,
            status=EVENT_STATUS_CONFIRMED,
            title=f"Fictional option expiration of {underlying} ({expiration})",
            ticker=underlying,
            instant_local=_local_instant(datetime.fromisoformat(expiration).date(), tz),
            revisions=[],
            extra={"expiration": expiration},
        )
        entries.append((stable_id, payload))

    # -- global macro events -------------------------------------------------
    for index in range(SYNTHETIC_MACRO_EVENT_COUNT):
        day = (base + timedelta(days=_MACRO_DAY_OFFSETS[index])).date()
        stable_id = f"syn-ev-macro-{index + 1:02d}"
        payload = _event_payload(
            stable_id=stable_id,
            category=EVENT_CATEGORY_MACRO,
            status=_MACRO_STATUSES[index],
            title=_MACRO_TITLES[index],
            ticker=None,
            instant_local=_local_instant(day, tz),
            revisions=[],
        )
        entries.append((stable_id, payload))

    envelopes: list[DataEnvelope[dict[str, Any]]] = []
    for index, (stable_id, payload) in enumerate(entries):
        envelopes.append(
            DataEnvelope[dict[str, Any]](
                event_id=f"{SYNTHETIC_SOURCE}:{seed}:ev{index:04d}",
                schema_version=SYNTHETIC_SCHEMA_CALENDAR_EVENT,
                source=SYNTHETIC_SOURCE,
                source_event_id=stable_id,
                entitlement_id=None,
                instrument_id=payload["ticker"],
                observed_at=published_at,
                published_at=published_at,
                received_at=received_at,
                as_of=received_at,
                stale_after=received_at + _STALE_GRACE,
                quality_status=EnvelopeQuality.VALID,
                delay_status=DelayStatus.UNKNOWN,
                connection_epoch=None,
                rights=SYNTHETIC_RIGHTS,
                payload_hash=canonical_json_hash(payload),
                payload=payload,
            )
        )
    return tuple(envelopes)
