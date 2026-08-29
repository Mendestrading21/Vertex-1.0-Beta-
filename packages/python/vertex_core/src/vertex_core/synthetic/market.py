"""Deterministic generator of clearly-synthetic daily market quotes.

Separate from :mod:`vertex_core.synthetic.generator` (news/quote attention
fixtures) so the existing envelope stream stays byte-stable. This module
feeds the LOT-13 Markets overview chain in development:

- 24 tickers spread over 6 synthetic sectors (``SYN-TECH-01`` ...);
- two trading days of daily closes as EXACT decimal strings (never floats);
- ``source`` is always ``synthetic-dev`` and ``rights`` always ``SYNTHETIC``;
- varied qualities, including a few ``PARTIAL`` and ``STALE`` envelopes;
- a configurable number of tickers deliberately missing their older close so
  the downstream snapshot builder proves its fail-closed discard path.

Determinism: pure function of ``(seed, base_time, missing_close_count)``;
identical inputs produce identical envelopes, byte for byte. No hidden
entropy, no system clock.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from types import MappingProxyType
from typing import Mapping

from vertex_core.contracts import (
    DataEnvelope,
    DelayStatus,
    EnvelopeQuality,
    canonical_json_hash,
    ensure_utc,
)
from vertex_core.synthetic.generator import SYNTHETIC_RIGHTS, SYNTHETIC_SOURCE

__all__ = [
    "SYNTHETIC_ADJUSTMENT_BASIS",
    "SYNTHETIC_BAR_COUNT",
    "SYNTHETIC_FOCUS_TICKERS",
    "SYNTHETIC_MARKET_CURRENCY",
    "SYNTHETIC_SCHEMA_DAILY_BARS",
    "SYNTHETIC_SCHEMA_DAILY_QUOTE",
    "SYNTHETIC_SECTOR_LABELS_FR",
    "SYNTHETIC_SECTOR_TICKERS",
    "SYNTHETIC_SECTORS",
    "generate_daily_bar_envelopes",
    "generate_daily_quote_envelopes",
]


SYNTHETIC_SCHEMA_DAILY_QUOTE = "synthetic-daily-quote/1.0"
"""Schema version of every generated daily-quote envelope."""

SYNTHETIC_MARKET_CURRENCY = "SYN"
"""Fictional currency code stamped on every synthetic close (never ISO real)."""

SYNTHETIC_ADJUSTMENT_BASIS = "synthetic-unadjusted"
"""Single adjustment basis of the synthetic series (both days share it)."""

SYNTHETIC_SECTORS: tuple[str, ...] = (
    "SYN-TECH",
    "SYN-ENER",
    "SYN-FINL",
    "SYN-HLTH",
    "SYN-INDU",
    "SYN-UTIL",
)
"""The 6 synthetic sector codes (identifiers, English/technical)."""

SYNTHETIC_SECTOR_LABELS_FR: Mapping[str, str] = MappingProxyType(
    {
        "SYN-TECH": "Technologie synthétique",
        "SYN-ENER": "Énergie synthétique",
        "SYN-FINL": "Finance synthétique",
        "SYN-HLTH": "Santé synthétique",
        "SYN-INDU": "Industrie synthétique",
        "SYN-UTIL": "Services publics synthétiques",
    }
)
"""Display labels (UI French) for the synthetic sectors."""

_TICKERS_PER_SECTOR = 4

SYNTHETIC_SECTOR_TICKERS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        sector: tuple(
            f"{sector}-{index:02d}" for index in range(1, _TICKERS_PER_SECTOR + 1)
        )
        for sector in SYNTHETIC_SECTORS
    }
)
"""Point-in-time synthetic universe: sector code -> its 4 tickers (24 total)."""

# Distinct price bands (in cents) per sector, for visual variety only.
_SECTOR_PRICE_BANDS_CENTS: Mapping[str, tuple[int, int]] = MappingProxyType(
    {
        "SYN-TECH": (12_000, 48_000),
        "SYN-ENER": (3_000, 12_000),
        "SYN-FINL": (5_000, 20_000),
        "SYN-HLTH": (8_000, 30_000),
        "SYN-INDU": (4_000, 16_000),
        "SYN-UTIL": (2_000, 9_000),
    }
)

_RECEIVE_LAG = timedelta(seconds=30)
_STALE_GRACE = timedelta(hours=6)
_LATEST_OFFSET = timedelta(hours=2)
_DAY_SPACING = timedelta(hours=24)
_DEGRADED_PER_QUALITY = 2  # PARTIAL x2 and STALE x2 on the latest day

SYNTHETIC_SCHEMA_DAILY_BARS = "synthetic-daily-bars/1.0"
"""Schema version of every generated daily-OHLCV-bars envelope."""

SYNTHETIC_FOCUS_TICKERS: tuple[str, ...] = (
    "SYN-ENER-01",
    "SYN-FINL-01",
    "SYN-TECH-01",
    "SYN-TECH-02",
)
"""The 4 focus tickers of the analysis/options development pages — a fixed
subset of the declared 24-ticker synthetic universe."""

SYNTHETIC_BAR_COUNT = 60
"""Number of daily OHLCV bars generated per focus ticker."""


def _cents_to_decimal_string(cents: int) -> str:
    """Exact decimal string for a price expressed in integer cents."""
    return f"{cents // 100}.{cents % 100:02d}"


def _all_tickers() -> tuple[str, ...]:
    return tuple(
        ticker for sector in SYNTHETIC_SECTORS for ticker in SYNTHETIC_SECTOR_TICKERS[sector]
    )


def _validate_inputs(seed: int, base_time: datetime, missing_close_count: int) -> datetime:
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise TypeError(f"seed: expected int, got {type(seed).__name__}")
    if not isinstance(missing_close_count, int) or isinstance(missing_close_count, bool):
        raise TypeError(
            "missing_close_count: expected int, got "
            f"{type(missing_close_count).__name__}"
        )
    total = len(_all_tickers())
    if not 0 <= missing_close_count <= total - _DEGRADED_PER_QUALITY * 2:
        raise ValueError(
            "missing_close_count: must be within "
            f"[0, {total - _DEGRADED_PER_QUALITY * 2}], got {missing_close_count}"
        )
    if not isinstance(base_time, datetime):
        raise TypeError(f"base_time: expected datetime, got {type(base_time).__name__}")
    return ensure_utc(base_time)


def _quote_payload(
    *, ticker: str, sector: str, trading_day: str, close_cents: int
) -> dict:
    return {
        "type": "daily_quote",
        "synthetic": True,
        "ticker": ticker,
        "sector": sector,
        "trading_day": trading_day,
        "close": _cents_to_decimal_string(close_cents),
        "currency": SYNTHETIC_MARKET_CURRENCY,
        "adjustment_basis": SYNTHETIC_ADJUSTMENT_BASIS,
        "note": (
            f"[SYNTHETIC] fixture daily close for {ticker}; generated data, "
            "never real market information."
        ),
    }


def generate_daily_quote_envelopes(
    *, seed: int, base_time: datetime, missing_close_count: int = 2
) -> tuple[DataEnvelope[dict], ...]:
    """Generate the deterministic two-day synthetic daily-quote envelope set.

    Pure function of its inputs (mandatory seed, aware ``base_time``). Every
    generated timestamp lies strictly before ``base_time``. Contents:

    - one envelope per (ticker, trading day), for the 24 universe tickers and
      2 consecutive synthetic trading days (~26h and ~2h before base_time);
    - ``missing_close_count`` tickers (deterministically drawn) have NO older
      close — only their latest-day envelope exists — so a downstream
      consumer must discard them instead of interpolating;
    - 2 tickers carry ``PARTIAL`` and 2 carry ``STALE`` quality on their
      latest-day envelope (drawn among tickers with both closes); everything
      else is ``VALID``;
    - the latest-day closes are guaranteed to contain at least one strictly
      positive and one strictly negative move versus the older close among
      the fully covered tickers.
    """
    base = _validate_inputs(seed, base_time, missing_close_count)
    rng = random.Random(seed)
    tickers = _all_tickers()

    missing = set(rng.sample(tickers, missing_close_count)) if missing_close_count else set()
    covered = [ticker for ticker in tickers if ticker not in missing]
    partial = set(rng.sample(covered, _DEGRADED_PER_QUALITY))
    stale_candidates = [ticker for ticker in covered if ticker not in partial]
    stale = set(rng.sample(stale_candidates, _DEGRADED_PER_QUALITY))

    sector_of = {
        ticker: sector
        for sector in SYNTHETIC_SECTORS
        for ticker in SYNTHETIC_SECTOR_TICKERS[sector]
    }

    # Deterministic per-ticker prices: older close then a basis-point move.
    older_cents: dict[str, int] = {}
    move_bp: dict[str, int] = {}
    for ticker in tickers:
        low, high = _SECTOR_PRICE_BANDS_CENTS[sector_of[ticker]]
        older_cents[ticker] = rng.randrange(low, high)
        move_bp[ticker] = rng.randrange(-300, 301)

    # Guarantee both signs among fully covered tickers (nonzero moves exist).
    if not any(move_bp[t] > 0 for t in covered):
        move_bp[covered[0]] = 125
    if not any(move_bp[t] < 0 for t in covered):
        move_bp[covered[1]] = -125

    latest_cents = {
        ticker: max(1, older_cents[ticker] * (10_000 + move_bp[ticker]) // 10_000)
        for ticker in tickers
    }

    latest_published = base - _LATEST_OFFSET
    older_published = latest_published - _DAY_SPACING

    envelopes: list[DataEnvelope[dict]] = []
    index = 0
    for ticker in tickers:
        days = (
            [(older_published, older_cents[ticker]), (latest_published, latest_cents[ticker])]
            if ticker not in missing
            else [(latest_published, latest_cents[ticker])]
        )
        for published_at, close_cents in days:
            is_latest = published_at == latest_published
            if is_latest and ticker in partial:
                quality = EnvelopeQuality.PARTIAL
            elif is_latest and ticker in stale:
                quality = EnvelopeQuality.STALE
            else:
                quality = EnvelopeQuality.VALID
            trading_day = published_at.date().isoformat()
            payload = _quote_payload(
                ticker=ticker,
                sector=sector_of[ticker],
                trading_day=trading_day,
                close_cents=close_cents,
            )
            received_at = published_at + _RECEIVE_LAG
            stale_after = (
                received_at
                if quality is EnvelopeQuality.STALE
                else received_at + _STALE_GRACE
            )
            envelopes.append(
                DataEnvelope[dict](
                    event_id=f"{SYNTHETIC_SOURCE}:{seed}:dq{index:04d}",
                    schema_version=SYNTHETIC_SCHEMA_DAILY_QUOTE,
                    source=SYNTHETIC_SOURCE,
                    source_event_id=f"syn-dq-{ticker}-{trading_day}",
                    entitlement_id=None,
                    instrument_id=ticker,
                    observed_at=published_at,
                    published_at=published_at,
                    received_at=received_at,
                    as_of=received_at,
                    stale_after=stale_after,
                    quality_status=quality,
                    delay_status=DelayStatus.UNKNOWN,
                    connection_epoch=None,
                    rights=SYNTHETIC_RIGHTS,
                    payload_hash=canonical_json_hash(payload),
                    payload=payload,
                )
            )
            index += 1
    return tuple(envelopes)


def generate_daily_bar_envelopes(
    *, seed: int, base_time: datetime, tickers: tuple[str, ...] = SYNTHETIC_FOCUS_TICKERS
) -> tuple[DataEnvelope[dict], ...]:
    """Generate one deterministic daily-OHLCV-bars envelope per focus ticker.

    SEPARATE function from :func:`generate_daily_quote_envelopes` (whose
    envelope stream stays byte-stable). Pure function of its inputs: the seed
    is mandatory, ``base_time`` must be timezone-aware and every generated
    timestamp lies strictly before it.

    Per ticker: :data:`SYNTHETIC_BAR_COUNT` consecutive synthetic trading
    days ending the day before ``base_time``, each bar carrying EXACT decimal
    strings (integer-cent arithmetic, never floats) with the invariants
    ``high >= max(open, close)``, ``low <= min(open, close)``, ``low >= 0.01``
    and a non-negative integer volume. One envelope per ticker carries the
    whole series (``source = synthetic-dev``, ``rights = SYNTHETIC``).
    """
    base = _validate_inputs(seed, base_time, 0)
    if not isinstance(tickers, tuple) or not tickers:
        raise TypeError("tickers: a non-empty tuple of ticker strings is required")
    declared = set(_all_tickers())
    unknown = [ticker for ticker in tickers if ticker not in declared]
    if unknown:
        raise ValueError(f"tickers: not in the declared synthetic universe: {unknown}")

    rng = random.Random(seed)
    sector_of = {
        ticker: sector
        for sector in SYNTHETIC_SECTORS
        for ticker in SYNTHETIC_SECTOR_TICKERS[sector]
    }
    published_at = base - _LATEST_OFFSET
    received_at = published_at + _RECEIVE_LAG
    last_day = (base - timedelta(days=1)).date()

    envelopes: list[DataEnvelope[dict]] = []
    for index, ticker in enumerate(tickers):
        low_band, high_band = _SECTOR_PRICE_BANDS_CENTS[sector_of[ticker]]
        close_cents = rng.randrange(low_band, high_band)
        bars: list[dict] = []
        for day_index in range(SYNTHETIC_BAR_COUNT):
            trading_day = last_day - timedelta(days=SYNTHETIC_BAR_COUNT - 1 - day_index)
            open_cents = close_cents
            move_bp = rng.randrange(-250, 251)
            close_cents = max(2, open_cents * (10_000 + move_bp) // 10_000)
            hi_wiggle = rng.randrange(0, max(2, open_cents // 100))
            lo_wiggle = rng.randrange(0, max(2, open_cents // 100))
            high_cents = max(open_cents, close_cents) + hi_wiggle
            low_cents = max(1, min(open_cents, close_cents) - lo_wiggle)
            bars.append(
                {
                    "trading_day": trading_day.isoformat(),
                    "open": _cents_to_decimal_string(open_cents),
                    "high": _cents_to_decimal_string(high_cents),
                    "low": _cents_to_decimal_string(low_cents),
                    "close": _cents_to_decimal_string(close_cents),
                    "volume": rng.randrange(10_000, 2_000_000),
                }
            )
        payload = {
            "type": "daily_bars",
            "synthetic": True,
            "ticker": ticker,
            "sector": sector_of[ticker],
            "currency": SYNTHETIC_MARKET_CURRENCY,
            "adjustment_basis": SYNTHETIC_ADJUSTMENT_BASIS,
            "bars": bars,
            "note": (
                f"[SYNTHETIC] fixture daily OHLCV bars for {ticker}; generated "
                "data, never real market information."
            ),
        }
        envelopes.append(
            DataEnvelope[dict](
                event_id=f"{SYNTHETIC_SOURCE}:{seed}:db{index:04d}",
                schema_version=SYNTHETIC_SCHEMA_DAILY_BARS,
                source=SYNTHETIC_SOURCE,
                source_event_id=f"syn-db-{ticker}-{last_day.isoformat()}",
                entitlement_id=None,
                instrument_id=ticker,
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
