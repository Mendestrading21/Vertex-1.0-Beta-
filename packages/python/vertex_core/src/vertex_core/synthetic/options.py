"""Deterministic generator of clearly-synthetic option-chain envelopes.

Feeds the Options page chain (page 06) in development without touching any
real market data:

- 4 underlyings drawn from the existing 24-ticker synthetic universe;
- per underlying: 2 expirations x 12 strikes x CALL/PUT, with ONE expiration
  deliberately shared by TWO distinct ``trading_class`` values — proof that
  the downstream chain separates duplicated expiration dates by trading
  class instead of merging them;
- quotes are coherent decimal strings (``bid < ask``) derived from the
  theoretical price of ``vertex_core.calculations.options.european_price``
  (the single financial-calculation authority — this module re-implements no
  pricing formula), so a sane mid sits inside the no-arbitrage interval of
  the synthetic spot;
- per underlying, exactly one quote is deliberately CROSSED (bid > ask), one
  is deliberately STALE (observed a day earlier) and one is deliberately
  ABSENT (bid and ask ``null``) — honest partial coverage for the fail-closed
  consumers;
- volume and open interest are synthetic integers explicitly labeled
  ``OI_DELAYED`` (open interest is never an intraday measure);
- ``source`` is always ``synthetic-dev`` and ``rights`` always ``SYNTHETIC``.

Determinism: pure function of ``(seed, base_time)``; identical inputs produce
identical envelopes, byte for byte. No hidden entropy, no system clock.
"""

from __future__ import annotations

import random
from collections.abc import Mapping
from datetime import datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal
from types import MappingProxyType
from typing import Any

from vertex_core.calculations.options import european_price
from vertex_core.contracts import (
    DataEnvelope,
    DelayStatus,
    EnvelopeQuality,
    canonical_json_hash,
    ensure_utc,
)
from vertex_core.synthetic.generator import SYNTHETIC_RIGHTS, SYNTHETIC_SOURCE
from vertex_core.synthetic.market import (
    SYNTHETIC_FOCUS_TICKERS,
    SYNTHETIC_MARKET_CURRENCY,
    SYNTHETIC_SECTOR_TICKERS,
)

__all__ = [
    "SYNTHETIC_OI_STATUS",
    "SYNTHETIC_OPTION_EXCHANGE",
    "SYNTHETIC_OPTION_MULTIPLIER",
    "SYNTHETIC_OPTION_SETTLEMENT",
    "SYNTHETIC_OPTION_STYLE",
    "SYNTHETIC_OPTION_UNDERLYINGS",
    "SYNTHETIC_SCHEMA_OPTION_CHAIN",
    "generate_option_chain_envelopes",
]


SYNTHETIC_SCHEMA_OPTION_CHAIN = "synthetic-option-chain/1.0"
"""Schema version of every generated option-chain-slice envelope."""

SYNTHETIC_OPTION_UNDERLYINGS: tuple[str, ...] = SYNTHETIC_FOCUS_TICKERS
"""The 4 synthetic underlyings that carry option chains: exactly the focus
tickers of the analysis page (single declaration, no drift), all members of
the existing 24-ticker universe — verified below at import time."""

_DECLARED_TICKERS = {
    ticker for tickers in SYNTHETIC_SECTOR_TICKERS.values() for ticker in tickers
}
if not set(SYNTHETIC_OPTION_UNDERLYINGS) <= _DECLARED_TICKERS:  # pragma: no cover
    raise RuntimeError(
        "SYNTHETIC_OPTION_UNDERLYINGS must be a subset of the declared "
        "synthetic ticker universe"
    )

SYNTHETIC_OPTION_EXCHANGE = "SYNTH"
"""Fictional exchange code of every synthetic option contract."""

SYNTHETIC_OPTION_MULTIPLIER = 100
"""Contract multiplier of every synthetic option contract."""

SYNTHETIC_OPTION_STYLE = "EUROPEAN"
"""Exercise style: European, matching the analytic authority used to derive
the synthetic quotes (never presented as an American contract)."""

SYNTHETIC_OPTION_SETTLEMENT = "CASH"
"""Settlement type of every synthetic option contract."""

SYNTHETIC_OI_STATUS = "OI_DELAYED"
"""Open-interest status label: synthetic OI is always presented as delayed,
never as an intraday measure."""

_RATE_TEXT = "0.02"
_DIVIDEND_YIELD_TEXT = "0.00"

# Distinct spot bands (in cents) per underlying, for visual variety only.
_SPOT_BANDS_CENTS: Mapping[str, tuple[int, int]] = MappingProxyType(
    {
        "SYN-ENER-01": (4_000, 11_000),
        "SYN-FINL-01": (6_000, 18_000),
        "SYN-TECH-01": (15_000, 40_000),
        "SYN-TECH-02": (12_000, 30_000),
    }
)

_STRIKE_COUNT = 12
_NEAR_EXPIRY_DAYS = 28
_FAR_EXPIRY_DAYS = 56
_RECEIVE_LAG = timedelta(seconds=30)
_QUOTE_AGE_FRESH = timedelta(minutes=30)
_QUOTE_AGE_STALE = timedelta(hours=24)
_STALE_GRACE = timedelta(hours=6)
_CENTS = Decimal("0.01")

# Deterministic in-slice positions of the degraded quotes (first slice of
# each underlying only): contract order is (strike asc, CALL then PUT).
_CROSSED_INDEX = 2  # second strike, CALL
_STALE_INDEX = 5  # third strike, PUT
_MISSING_INDEX = 9  # fifth strike, PUT

_CON_ID_BASE = 900_000_000


def _validate_inputs(seed: int, base_time: datetime) -> datetime:
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise TypeError(f"seed: expected int, got {type(seed).__name__}")
    if not isinstance(base_time, datetime):
        raise TypeError(
            f"base_time: expected datetime, got {type(base_time).__name__}"
        )
    return ensure_utc(base_time)


def _cents_text(cents: int) -> str:
    return f"{cents // 100}.{cents % 100:02d}"


def _quantize_cents(value: Decimal) -> Decimal:
    return value.quantize(_CENTS, rounding=ROUND_HALF_EVEN)


def _smile_volatility(base_vol: float, spot_cents: int, strike_cents: int) -> float:
    """Deterministic synthetic smile: base vol plus a quadratic moneyness bump.

    Descriptive fixture shape only — this is an INPUT of the theoretical
    pricer, not a financial calculation of its own.
    """
    moneyness = strike_cents / spot_cents
    return base_vol + 0.35 * (moneyness - 1.0) ** 2


def _theoretical_mid(
    *,
    spot_cents: int,
    strike_cents: int,
    maturity_years: float,
    volatility: float,
    right: str,
) -> Decimal:
    """Theoretical mid from the single pricing authority, quantized to cents."""
    price = european_price(
        Decimal(_cents_text(spot_cents)),
        Decimal(_cents_text(strike_cents)),
        maturity_years,
        Decimal(_RATE_TEXT),
        Decimal(_DIVIDEND_YIELD_TEXT),
        volatility,
        right,
    )
    return _quantize_cents(Decimal(repr(price)))


def generate_option_chain_envelopes(
    *, seed: int, base_time: datetime
) -> tuple[DataEnvelope[dict[str, Any]], ...]:
    """Generate the deterministic synthetic option-chain envelope set.

    Pure function of ``(seed, base_time)``. One envelope per
    ``(underlying, expiration, trading_class)`` chain slice — three slices
    per underlying: the near expiration under the standard trading class AND
    under the ``<underlying>W`` class (same date, two identities), plus the
    far expiration under the standard class. Twelve envelopes in total, each
    carrying its 24 contracts (12 strikes x CALL/PUT) with full identity and
    decimal-string quotes. The first slice of each underlying carries the
    three deliberately degraded quotes (crossed, stale, missing) and is
    honestly labeled ``PARTIAL``.
    """
    base = _validate_inputs(seed, base_time)
    rng = random.Random(seed)  # noqa: S311 (données SYNTHETIC, aucun usage cryptographique)

    near_expiry = (base + timedelta(days=_NEAR_EXPIRY_DAYS)).date()
    far_expiry = (base + timedelta(days=_FAR_EXPIRY_DAYS)).date()

    fresh_observed = base - _QUOTE_AGE_FRESH
    stale_observed = base - _QUOTE_AGE_STALE
    received_at = fresh_observed + _RECEIVE_LAG

    envelopes: list[DataEnvelope[dict[str, Any]]] = []
    con_id = _CON_ID_BASE
    envelope_index = 0

    for underlying in SYNTHETIC_OPTION_UNDERLYINGS:
        low, high = _SPOT_BANDS_CENTS[underlying]
        spot_cents = rng.randrange(low, high)
        base_vol = 0.18 + rng.randrange(0, 16) / 100.0  # 0.18 .. 0.33

        step_cents = max(100, (spot_cents // 20) // 100 * 100)
        center_cents = max(step_cents, round(spot_cents / step_cents) * step_cents)
        strikes_cents = [
            center_cents + (i - _STRIKE_COUNT // 2 + 1) * step_cents
            for i in range(_STRIKE_COUNT)
        ]
        if strikes_cents[0] <= 0:  # pragma: no cover - bands prevent this
            raise RuntimeError("synthetic strike grid produced a non-positive strike")

        # (expiration, trading_class, vol shift) — the near expiration exists
        # under TWO distinct trading classes with distinct synthetic surfaces.
        slices = (
            (near_expiry, underlying, 0.0),
            (near_expiry, f"{underlying}W", 0.03),
            (far_expiry, underlying, 0.02),
        )

        for slice_number, (expiry, trading_class, vol_shift) in enumerate(slices):
            degraded_slice = slice_number == 0
            maturity_years = (expiry - base.date()).days / 365.0
            contracts: list[dict[str, Any]] = []
            contract_index = 0
            for strike_cents in strikes_cents:
                for right in ("CALL", "PUT"):
                    volatility = (
                        _smile_volatility(base_vol, spot_cents, strike_cents)
                        + vol_shift
                    )
                    mid = _theoretical_mid(
                        spot_cents=spot_cents,
                        strike_cents=strike_cents,
                        maturity_years=maturity_years,
                        volatility=volatility,
                        right=right,
                    )
                    half_spread = max(
                        Decimal("0.02"), _quantize_cents(mid * Decimal("0.02"))
                    )
                    bid = _quantize_cents(mid - half_spread)
                    ask = _quantize_cents(mid + half_spread)
                    if bid < _CENTS:
                        bid = _CENTS
                        if ask <= bid:
                            ask = bid + Decimal("0.02")

                    bid_text: str | None = format(bid, "f")
                    ask_text: str | None = format(ask, "f")
                    observed_at = fresh_observed
                    if degraded_slice and contract_index == _CROSSED_INDEX:
                        bid_text, ask_text = ask_text, bid_text  # crossed
                    elif degraded_slice and contract_index == _STALE_INDEX:
                        observed_at = stale_observed
                    elif degraded_slice and contract_index == _MISSING_INDEX:
                        bid_text = None
                        ask_text = None

                    con_id += 1
                    contracts.append(
                        {
                            "con_id": con_id,
                            "strike": _cents_text(strike_cents),
                            "right": right,
                            "bid": bid_text,
                            "ask": ask_text,
                            "bid_size": rng.randrange(1, 50) if bid_text else None,
                            "ask_size": rng.randrange(1, 50) if ask_text else None,
                            "volume": rng.randrange(0, 5_000),
                            "open_interest": rng.randrange(0, 20_000),
                            "open_interest_status": SYNTHETIC_OI_STATUS,
                            "observed_at": observed_at.isoformat(),
                        }
                    )
                    contract_index += 1

            payload = {
                "type": "option_chain_slice",
                "synthetic": True,
                "underlying": underlying,
                "underlying_spot": _cents_text(spot_cents),
                "currency": SYNTHETIC_MARKET_CURRENCY,
                "expiration": expiry.isoformat(),
                "trading_class": trading_class,
                "exchange": SYNTHETIC_OPTION_EXCHANGE,
                "style": SYNTHETIC_OPTION_STYLE,
                "settlement": SYNTHETIC_OPTION_SETTLEMENT,
                "multiplier": SYNTHETIC_OPTION_MULTIPLIER,
                "rate": _RATE_TEXT,
                "dividend_yield": _DIVIDEND_YIELD_TEXT,
                "contracts": contracts,
                "note": (
                    f"[SYNTHETIC] fixture option chain slice for {underlying}; "
                    "generated data, never real market information."
                ),
            }
            quality = (
                EnvelopeQuality.PARTIAL if degraded_slice else EnvelopeQuality.VALID
            )
            envelopes.append(
                DataEnvelope[dict[str, Any]](
                    event_id=f"{SYNTHETIC_SOURCE}:{seed}:oc{envelope_index:04d}",
                    schema_version=SYNTHETIC_SCHEMA_OPTION_CHAIN,
                    source=SYNTHETIC_SOURCE,
                    source_event_id=(
                        f"syn-oc-{underlying}-{expiry.isoformat()}-{trading_class}"
                    ),
                    entitlement_id=None,
                    instrument_id=underlying,
                    observed_at=fresh_observed,
                    published_at=fresh_observed,
                    received_at=received_at,
                    as_of=received_at,
                    stale_after=received_at + _STALE_GRACE,
                    quality_status=quality,
                    delay_status=DelayStatus.UNKNOWN,
                    connection_epoch=None,
                    rights=SYNTHETIC_RIGHTS,
                    payload_hash=canonical_json_hash(payload),
                    payload=payload,
                )
            )
            envelope_index += 1

    return tuple(envelopes)
