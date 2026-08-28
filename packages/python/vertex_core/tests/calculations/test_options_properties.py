"""Hypothesis property tests for the options.* financial invariants.

Invariants: put-call parity, monotonicity in spot, convexity in strike,
no-arbitrage bounds, IV round trip, exact payoff linearity, American >=
European. Strategies are bounded to the validated model domain; boundary
values T=0 and vol=0 are INCLUDED deliberately (deterministic limits).
All data is SYNTHETIC; no orders of any kind are created.
"""

import math
from decimal import Decimal

import pytest
from hypothesis import assume, given, settings, strategies as st

from vertex_core.calculations.options import (
    IV_BRACKET_HI,
    IV_BRACKET_LO,
    OptionLeg,
    american_price,
    european_price,
    implied_volatility,
    no_arbitrage_bounds,
    payoff_at_expiry,
)

pytestmark = pytest.mark.property

# Bounded, well-conditioned strategy domain (inside the model domain).
spots = st.floats(min_value=10.0, max_value=500.0, allow_nan=False, allow_infinity=False)
moneyness = st.floats(min_value=0.5, max_value=2.0, allow_nan=False, allow_infinity=False)
maturities = st.floats(min_value=0.0, max_value=3.0, allow_nan=False, allow_infinity=False)
positive_maturities = st.floats(
    min_value=1.0 / 365.0, max_value=3.0, allow_nan=False, allow_infinity=False
)
vols = st.floats(min_value=0.0, max_value=1.5, allow_nan=False, allow_infinity=False)
positive_vols = st.floats(
    min_value=0.01, max_value=1.5, allow_nan=False, allow_infinity=False
)
rates = st.floats(min_value=-0.01, max_value=0.08, allow_nan=False, allow_infinity=False)
yields_ = st.floats(min_value=0.0, max_value=0.05, allow_nan=False, allow_infinity=False)
rights = st.sampled_from(["CALL", "PUT"])


@settings(deadline=None, max_examples=200)
@given(s=spots, m=moneyness, t=maturities, vol=vols, r=rates, q=yields_)
def test_put_call_parity(s, m, t, vol, r, q):
    """C - P == S e^{-qT} - K e^{-rT}, including the T=0 and vol=0 limits."""
    k = s * m
    call = european_price(s, k, t, r, q, vol, "CALL")
    put = european_price(s, k, t, r, q, vol, "PUT")
    parity = s * math.exp(-q * t) - k * math.exp(-r * t)
    assert abs((call - put) - parity) <= 1e-9 * max(1.0, s, k)


@settings(deadline=None, max_examples=200)
@given(
    s1=spots,
    bump=st.floats(min_value=0.01, max_value=100.0, allow_nan=False, allow_infinity=False),
    m=moneyness,
    t=maturities,
    vol=vols,
    r=rates,
    q=yields_,
)
def test_monotonicity_in_spot(s1, bump, m, t, vol, r, q):
    """CALL non-decreasing and PUT non-increasing in spot."""
    s2 = s1 + bump
    k = s1 * m
    tol = 1e-9 * max(1.0, s2)
    assert european_price(s2, k, t, r, q, vol, "CALL") >= european_price(
        s1, k, t, r, q, vol, "CALL"
    ) - tol
    assert european_price(s2, k, t, r, q, vol, "PUT") <= european_price(
        s1, k, t, r, q, vol, "PUT"
    ) + tol


@settings(deadline=None, max_examples=200)
@given(
    s=spots,
    k1_mult=st.floats(min_value=0.5, max_value=1.5, allow_nan=False, allow_infinity=False),
    gap=st.floats(min_value=0.5, max_value=50.0, allow_nan=False, allow_infinity=False),
    lam=st.floats(min_value=0.05, max_value=0.95, allow_nan=False, allow_infinity=False),
    t=maturities,
    vol=vols,
    r=rates,
    q=yields_,
    right=rights,
)
def test_convexity_in_strike(s, k1_mult, gap, lam, t, vol, r, q, right):
    """price(lam*K1 + (1-lam)*K3) <= lam*price(K1) + (1-lam)*price(K3)."""
    k1 = s * k1_mult
    k3 = k1 + gap
    k2 = lam * k1 + (1.0 - lam) * k3
    p1 = european_price(s, k1, t, r, q, vol, right)
    p2 = european_price(s, k2, t, r, q, vol, right)
    p3 = european_price(s, k3, t, r, q, vol, right)
    assert p2 <= lam * p1 + (1.0 - lam) * p3 + 1e-9 * max(1.0, s, k3)


@settings(deadline=None, max_examples=200)
@given(s=spots, m=moneyness, t=maturities, vol=vols, r=rates, q=yields_, right=rights)
def test_price_respects_no_arbitrage_bounds(s, m, t, vol, r, q, right):
    k = s * m
    price = european_price(s, k, t, r, q, vol, right)
    lower, upper = no_arbitrage_bounds(s, k, t, r, q, right)
    tol = 1e-9 * max(1.0, s, k)
    assert lower - tol <= price <= upper + tol


@settings(deadline=None, max_examples=200)
@given(
    s=spots, m=moneyness, t=positive_maturities, vol=positive_vols, r=rates,
    q=yields_, right=rights,
)
def test_iv_round_trip_within_relative_tolerance(s, m, t, vol, r, q, right):
    """price -> implied_volatility -> price within 1e-7 relative."""
    k = s * m
    price = european_price(s, k, t, r, q, vol, right)
    lower, upper = no_arbitrage_bounds(s, k, t, r, q, right)
    # Only well-posed inversions: price strictly inside bounds and inside the
    # verified bracket, and not vanishingly small (ill-conditioned vega).
    assume(lower < price < upper)
    assume(price >= 1e-6 * s)
    assume(
        european_price(s, k, t, r, q, IV_BRACKET_LO, right)
        < price
        < european_price(s, k, t, r, q, IV_BRACKET_HI, right)
    )
    iv = implied_volatility(price, s, k, t, r, q, right, "MID")
    reprice = european_price(s, k, t, r, q, iv, right)
    assert abs(reprice - price) <= 1e-7 * price
    # Volatility recovery is only asserted where the inversion is
    # well-conditioned (enough optionality above the lower bound; deep ITM
    # prices are flat in vol at float64 resolution and only the price round
    # trip is meaningful there).
    if price - lower >= 1e-4 * max(1.0, s):
        assert abs(iv - vol) <= 1e-4


quantities = st.integers(min_value=-3, max_value=3).filter(lambda q: q != 0)
strike_decimals = st.sampled_from(
    [Decimal("80"), Decimal("95.50"), Decimal("100"), Decimal("112.25"), Decimal("130")]
)
premium_decimals = st.sampled_from(
    [Decimal("0.55"), Decimal("2"), Decimal("4.10"), Decimal("7.35")]
)
leg_strategy = st.builds(
    lambda qty, right, strike, premium: OptionLeg(
        quantity=qty, right=right, strike=strike, premium=premium, multiplier=100
    ),
    qty=quantities,
    right=st.sampled_from(["CALL", "PUT"]),
    strike=strike_decimals,
    premium=premium_decimals,
)
spot_grid_strategy = st.lists(
    st.sampled_from(
        [Decimal("0"), Decimal("80"), Decimal("95.50"), Decimal("100"),
         Decimal("112.25"), Decimal("130"), Decimal("250")]
    ),
    min_size=1,
    max_size=5,
)


@settings(deadline=None, max_examples=100)
@given(legs=st.lists(leg_strategy, min_size=2, max_size=4), grid=spot_grid_strategy)
def test_payoff_leg_sum_linearity_exact(legs, grid):
    """Combined payoff equals the exact Decimal sum of single-leg payoffs."""
    combined = payoff_at_expiry(legs, grid, Decimal("0"))
    per_leg = [payoff_at_expiry([leg], grid, Decimal("0")) for leg in legs]
    for i in range(len(grid)):
        assert combined[i] == sum(p[i] for p in per_leg)


@settings(deadline=None, max_examples=25)
@given(
    s=st.floats(min_value=50.0, max_value=200.0, allow_nan=False, allow_infinity=False),
    m=st.floats(min_value=0.7, max_value=1.4, allow_nan=False, allow_infinity=False),
    days=st.integers(min_value=30, max_value=730),
    vol=st.floats(min_value=0.1, max_value=0.8, allow_nan=False, allow_infinity=False),
    r=st.floats(min_value=-0.01, max_value=0.08, allow_nan=False, allow_infinity=False),
    q=st.floats(min_value=0.0, max_value=0.05, allow_nan=False, allow_infinity=False),
    right=rights,
)
def test_american_not_below_european(s, m, days, vol, r, q, right):
    """American >= European minus the documented CRR lattice tolerance.

    The CRR-800 discretization error oscillates with an amplitude well
    below 1e-3 of spot on this domain; the tolerance is that documented
    lattice error, not model slack.
    """
    t = days / 365.0  # exact on the engine's ACT/365F date grid
    k = s * m
    am = american_price(s, k, t, r, q, vol, right, steps=800)
    eu = european_price(s, k, t, r, q, vol, right)
    assert am >= eu - 1e-3 * s
