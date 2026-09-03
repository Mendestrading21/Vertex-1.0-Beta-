"""Market statistics and indicator calculations (registry ids ``market.*``).

Pure, deterministic functions implementing the ``market.*`` entries of
``docs/03-domain/calculations/CALCULATION_REGISTRY.yaml``:

- ``market.simple_return``       -> :func:`simple_return`
- ``market.log_return``          -> :func:`log_return`
- ``market.realized_volatility`` -> :func:`realized_volatility`
- ``market.atr``                 -> :func:`atr`
- ``market.rebased_series``      -> :func:`rebase_series`
- ``market.relative_strength``   -> :func:`relative_strength`
- ``market.breadth``             -> :func:`breadth`
- ``market.sma``                 -> :func:`simple_moving_average`
- ``market.ema``                 -> :func:`exponential_moving_average`
- ``market.bollinger_bands``     -> :func:`bollinger_bands`
- ``market.rsi``                 -> :func:`relative_strength_index`
- ``market.macd``                -> :func:`macd`

Numeric policy (UNITS_TIME_AND_PRECISION):

- Boundary inputs may be ``int``, ``float`` or ``Decimal``; ``Decimal`` values
  are converted explicitly to ``float64`` before computation. ``bool`` is
  rejected (it is not a number at this boundary).
- The numerical core is ``float64``. Documented tolerances:
  results are reproducible bit-for-bit for identical inputs (determinism), and
  algebraic identities (return composition, annualization) hold within
  ``FLOAT64_REL_TOL`` relative / ``FLOAT64_ABS_TOL`` absolute error.
- ``NaN``, infinities and non-numeric sentinels are rejected fail-closed with
  :class:`CalculationInputError`; negative zero is normalized to ``0.0``.
- A computation whose result would not be finite (float64 overflow or
  underflow to an unusable value) raises :class:`CalculationInputError`
  instead of returning ``inf``/``NaN`` — never a silent fallback.
- Absent data is never substituted: there are no default values for prices,
  returns, counts or thresholds.

No randomness is used anywhere in this module.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from itertools import pairwise
from typing import NamedTuple

from vertex_core.contracts.types import ContractModel, PositiveDecimal, UtcDatetime

__all__ = [
    "FLOAT64_ABS_TOL",
    "FLOAT64_REL_TOL",
    "BollingerBands",
    "CalculationInputError",
    "MacdSeries",
    "NumberLike",
    "OhlcBar",
    "atr",
    "bollinger_bands",
    "breadth",
    "exponential_moving_average",
    "log_return",
    "macd",
    "realized_volatility",
    "rebase_series",
    "relative_strength",
    "relative_strength_index",
    "simple_moving_average",
    "simple_return",
]

FLOAT64_REL_TOL = 1e-9
"""Documented relative tolerance for float64 algebraic identities."""

FLOAT64_ABS_TOL = 1e-12
"""Documented absolute tolerance for float64 comparisons near zero."""

NumberLike = int | float | Decimal
"""Accepted numeric boundary types; converted explicitly to float64 inside."""


class CalculationInputError(ValueError):
    """Typed, fail-closed gate violation for a ``market.*`` calculation.

    ``reason`` is a stable machine-readable code naming the violated gate
    (e.g. ``"non_positive_price"``, ``"adjustment_basis_mismatch"``,
    ``"minimum_sample"``); ``detail`` is the human-readable explanation.
    No calculation in this module ever substitutes a default value for an
    invalid input — it raises this exception instead.
    """

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


class OhlcBar(ContractModel):
    """One OHLC bar at the contract boundary (strict, frozen, Decimal prices).

    Prices are strictly positive finite ``Decimal`` values and the timestamp
    is timezone-aware UTC. Cross-field OHLC coherence (``high >= low``,
    ``high >= max(open, close)``, ``low <= min(open, close)``) is deliberately
    NOT enforced here: it is the ``ordered_complete_bars`` gate of
    :func:`atr`, which rejects an incoherent bar with a typed
    :class:`CalculationInputError` so the violation is observable and
    reportable rather than silently unconstructible.
    """

    timestamp: UtcDatetime
    open: PositiveDecimal
    high: PositiveDecimal
    low: PositiveDecimal
    close: PositiveDecimal


def _to_float(value: object, name: str) -> float:
    """Convert a boundary number to finite float64; reject everything else.

    Rejects ``bool``, non-numeric types, ``NaN``, infinities, and any value
    whose float64 conversion is not finite (overflow). Negative zero is
    normalized to ``0.0``.
    """
    if isinstance(value, bool):
        raise CalculationInputError(
            "invalid_type", f"{name} must be int, float or Decimal, got bool"
        )
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise CalculationInputError(
                "non_finite_input", f"{name} is a non-finite Decimal ({value})"
            )
        result = float(value)
    elif isinstance(value, int):
        try:
            result = float(value)
        except OverflowError:
            raise CalculationInputError(
                "non_finite_input", f"{name} is too large for float64"
            ) from None
    elif isinstance(value, float):
        result = value
    else:
        raise CalculationInputError(
            "invalid_type",
            f"{name} must be int, float or Decimal, got {type(value).__name__}",
        )
    if not math.isfinite(result):
        raise CalculationInputError(
            "non_finite_input", f"{name} is not finite in float64 ({result!r})"
        )
    # Normalize negative zero so sign sentinels never propagate.
    return 0.0 if result == 0.0 else result


def _require_positive_price(value: object, name: str) -> float:
    price = _to_float(value, name)
    if price <= 0.0:
        raise CalculationInputError(
            "non_positive_price", f"{name} must be strictly positive, got {price!r}"
        )
    return price


def _require_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CalculationInputError(
            "invalid_type", f"{name} must be int, got {type(value).__name__}"
        )
    return value


def _require_sequence(value: object, name: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, (list, tuple)):
        raise CalculationInputError(
            "invalid_type", f"{name} must be a list or tuple, got {type(value).__name__}"
        )
    return value


def _require_adjustment_basis(value: object, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise CalculationInputError(
            "invalid_adjustment_basis", f"{name} must be a non-empty string"
        )
    return value


def _check_same_adjustment_basis(basis_t0: object, basis_t1: object) -> None:
    b0 = _require_adjustment_basis(basis_t0, "adjustment_basis_t0")
    b1 = _require_adjustment_basis(basis_t1, "adjustment_basis_t1")
    if b0 != b1:
        raise CalculationInputError(
            "adjustment_basis_mismatch",
            f"prices are on different adjustment bases ({b0!r} vs {b1!r}); "
            "returns across bases are meaningless",
        )


def _finite_result(value: float, calculation_id: str) -> float:
    if not math.isfinite(value):
        raise CalculationInputError(
            "non_finite_result",
            f"{calculation_id} produced a non-finite float64 result ({value!r})",
        )
    return 0.0 if value == 0.0 else value


def simple_return(
    price_t0: NumberLike,
    price_t1: NumberLike,
    *,
    adjustment_basis_t0: str,
    adjustment_basis_t1: str,
) -> float:
    """``market.simple_return`` — simple (arithmetic) return ``p1 / p0 - 1``.

    Gates (each violation raises :class:`CalculationInputError`):

    - ``positive_prices``: both prices strictly positive and finite;
    - ``same_adjustment_basis``: both adjustment-basis labels are required,
      non-empty, and must compare equal (e.g. ``"split_adjusted"``); mixing
      bases silently is forbidden.

    Composition (documented invariant, within ``FLOAT64_REL_TOL``):
    ``(1 + r(p0, p1)) * (1 + r(p1, p2)) == 1 + r(p0, p2)``.

    Returns a finite float64 ratio (dimensionless, per registry ``ratio``).
    """
    _check_same_adjustment_basis(adjustment_basis_t0, adjustment_basis_t1)
    p0 = _require_positive_price(price_t0, "price_t0")
    p1 = _require_positive_price(price_t1, "price_t1")
    return _finite_result(p1 / p0 - 1.0, "market.simple_return")


def log_return(
    price_t0: NumberLike,
    price_t1: NumberLike,
    *,
    adjustment_basis_t0: str,
    adjustment_basis_t1: str,
) -> float:
    """``market.log_return`` — logarithmic return ``ln(p1) - ln(p0)``.

    Gates:

    - ``strictly_positive_prices``: both prices strictly positive and finite;
    - ``same_adjustment_basis``: enforced identically to
      :func:`simple_return` (a fail-closed superset of the registry gate —
      a log return across two different adjustment bases is just as
      meaningless as a simple one).

    Computed as ``log(p1) - log(p0)`` (never ``log(p1 / p0)``) so the ratio
    cannot overflow float64. Additive composition holds within
    ``FLOAT64_REL_TOL``, and ``log_return == log1p(simple_return)`` within
    documented tolerance. Returns a finite float64 log-ratio.
    """
    _check_same_adjustment_basis(adjustment_basis_t0, adjustment_basis_t1)
    p0 = _require_positive_price(price_t0, "price_t0")
    p1 = _require_positive_price(price_t1, "price_t1")
    return _finite_result(math.log(p1) - math.log(p0), "market.log_return")


def realized_volatility(
    returns: Sequence[NumberLike],
    periods_per_year: NumberLike,
) -> float:
    """``market.realized_volatility`` — annualized sample volatility.

    Method: unbiased sample standard deviation (``ddof=1``) of the provided
    per-period returns, annualized by ``sqrt(periods_per_year)``
    (independent-increments scaling — a documented assumption). The caller
    states the sampling regularity by providing ``periods_per_year``
    consistent with the return series (e.g. 252 for daily bars).

    Gates:

    - ``minimum_sample``: at least 2 returns, otherwise the sample standard
      deviation does not exist — the input is INVALID and rejected;
    - every return must be a finite number (``NaN``/inf rejected);
    - ``periods_per_year`` must be strictly positive and finite.

    Invariants: result is non-negative and finite (an overflowing series
    raises :class:`CalculationInputError` rather than returning ``inf``).
    Returns an annualized decimal ratio as float64 (e.g. ``0.24`` = 24%/yr).
    """
    seq = _require_sequence(returns, "returns")
    n = len(seq)
    if n < 2:
        raise CalculationInputError(
            "minimum_sample",
            f"realized volatility requires at least 2 returns, got {n}",
        )
    ppy = _to_float(periods_per_year, "periods_per_year")
    if ppy <= 0.0:
        raise CalculationInputError(
            "invalid_annualization",
            f"periods_per_year must be strictly positive, got {ppy!r}",
        )
    values = [_to_float(r, f"returns[{i}]") for i, r in enumerate(seq)]
    mean = math.fsum(values) / n
    if not math.isfinite(mean):
        raise CalculationInputError(
            "non_finite_result",
            "market.realized_volatility mean overflowed float64",
        )
    squared = []
    for value in values:
        deviation = value - mean
        squared.append(deviation * deviation)
    variance = math.fsum(squared) / (n - 1)
    annualized_variance = variance * ppy
    if not math.isfinite(annualized_variance):
        raise CalculationInputError(
            "non_finite_result",
            "market.realized_volatility variance overflowed float64",
        )
    return _finite_result(math.sqrt(annualized_variance), "market.realized_volatility")


def _check_bar_complete(bar: OhlcBar, index: int) -> None:
    # Exact Decimal comparisons — no float rounding at the gate.
    if bar.high < bar.low:
        raise CalculationInputError(
            "incomplete_bar",
            f"bars[{index}] has high < low ({bar.high} < {bar.low})",
        )
    if bar.high < bar.open or bar.high < bar.close:
        raise CalculationInputError(
            "incomplete_bar",
            f"bars[{index}] has high below open or close",
        )
    if bar.low > bar.open or bar.low > bar.close:
        raise CalculationInputError(
            "incomplete_bar",
            f"bars[{index}] has low above open or close",
        )


def atr(bars: Sequence[OhlcBar], lookback: int) -> float:
    """``market.atr`` — Average True Range over the last ``lookback`` bars.

    Method: Wilder true range
    ``TR_i = max(high_i - low_i, |high_i - close_{i-1}|, |low_i - close_{i-1}|)``
    averaged with a simple arithmetic mean over the last ``lookback`` true
    ranges (NOT Wilder's recursive exponential smoothing — documented choice,
    deterministic and warm-up free).

    Gate ``ordered_complete_bars`` (any violation raises
    :class:`CalculationInputError`):

    - ``bars`` is a list/tuple of :class:`OhlcBar` only;
    - ``lookback >= 1`` and ``len(bars) >= lookback + 1`` (each true range
      needs the previous close — fewer bars is INVALID, never padded);
    - timestamps strictly increasing (duplicates and disorder rejected);
    - every bar coherent: ``high >= low``, ``high >= max(open, close)``,
      ``low <= min(open, close)``.

    Invariant: result is non-negative and finite, in price units of the bars
    (unit/currency ownership stays with the caller's instrument identity).
    """
    seq = _require_sequence(bars, "bars")
    typed_bars: list[OhlcBar] = []
    for i, bar in enumerate(seq):
        if not isinstance(bar, OhlcBar):
            raise CalculationInputError(
                "invalid_type",
                f"bars[{i}] must be OhlcBar, got {type(bar).__name__}",
            )
        typed_bars.append(bar)
    lb = _require_int(lookback, "lookback")
    if lb < 1:
        raise CalculationInputError("invalid_lookback", f"lookback must be >= 1, got {lb}")
    if len(typed_bars) < lb + 1:
        raise CalculationInputError(
            "minimum_sample",
            f"ATR with lookback {lb} requires at least {lb + 1} bars, got {len(typed_bars)}",
        )
    previous_ts: datetime | None = None
    for i, bar in enumerate(typed_bars):
        if previous_ts is not None and bar.timestamp <= previous_ts:
            raise CalculationInputError(
                "unordered_bars",
                f"bars[{i}] timestamp {bar.timestamp.isoformat()} does not "
                f"strictly follow bars[{i - 1}]",
            )
        previous_ts = bar.timestamp
        _check_bar_complete(bar, i)
    true_ranges = []
    start = len(typed_bars) - lb
    for i in range(start, len(typed_bars)):
        bar = typed_bars[i]
        prev = typed_bars[i - 1]
        high = _to_float(bar.high, f"bars[{i}].high")
        low = _to_float(bar.low, f"bars[{i}].low")
        prev_close = _to_float(prev.close, f"bars[{i - 1}].close")
        true_ranges.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    result = _finite_result(math.fsum(true_ranges) / lb, "market.atr")
    if result < 0.0:  # defensive: TR terms are non-negative by construction
        raise CalculationInputError("non_finite_result", "market.atr produced a negative range")
    return result


def rebase_series(
    prices: Sequence[NumberLike],
    *,
    adjustment_bases: Sequence[str],
    base_value: NumberLike = 100.0,
) -> tuple[float, ...]:
    """``market.rebased_series`` — série ramenée à une base commune.

    Chaque point vaut ``base_value * p_i / p_0`` : la série devient
    dimensionnelle-libre et directement comparable à une autre série rebasée,
    SANS qu'aucun rendement ne soit calculé par le consommateur.

    Gates (chaque violation lève :class:`CalculationInputError`) :

    - ``non_empty_series`` : au moins un prix. Une série vide n'a pas de base,
      et rendre un tuple vide laisserait le consommateur inventer la sienne ;
    - ``aligned_bases`` : autant d'étiquettes d'ajustement que de prix. Une
      étiquette manquante ne peut pas être devinée ;
    - ``positive_prices`` : chaque prix fini et strictement positif ;
    - ``same_adjustment_basis`` : toutes les étiquettes égales. Comparer un
      cours ajusté des dividendes à un cours qui ne l'est pas affiche un écart
      FAUX, et rien à l'écran ne le signalerait ;
    - ``positive_base_value`` : base finie et strictement positive.

    Invariant documenté : ``resultat[0] == float(base_value)`` exactement — le
    premier point n'est jamais approché, il EST la base.

    Rapport à :func:`simple_return` (invariant vérifié par test) :
    ``resultat[i] / base_value - 1 == simple_return(p_0, p_i)`` à
    ``FLOAT64_REL_TOL`` près.
    """
    if not prices:
        raise CalculationInputError(
            "empty_series",
            "market.rebased_series: une série sans point n'a pas de base, "
            "et en inventer une reviendrait à fabriquer une donnée",
        )
    if len(adjustment_bases) != len(prices):
        raise CalculationInputError(
            "misaligned_adjustment_bases",
            f"market.rebased_series: {len(prices)} prix pour "
            f"{len(adjustment_bases)} étiquettes d'ajustement ; une étiquette "
            "manquante ne se devine pas",
        )

    # `_check_same_adjustment_basis` lève sur toute divergence : comparer un
    # cours ajusté des dividendes à un cours qui ne l'est pas afficherait un
    # écart FAUX, que rien à l'écran ne signalerait.
    reference = adjustment_bases[0]
    for basis in adjustment_bases:
        _check_same_adjustment_basis(reference, basis)

    base = _require_positive_price(base_value, "base_value")
    p0 = _require_positive_price(prices[0], "prices[0]")
    rebased = [base]
    for index, price in enumerate(prices[1:], start=1):
        valeur = _require_positive_price(price, f"prices[{index}]")
        rebased.append(_finite_result(base * valeur / p0, "market.rebased_series"))
    return tuple(rebased)


def relative_strength(
    asset_returns: Sequence[NumberLike],
    benchmark_returns: Sequence[NumberLike],
    horizon: int,
) -> float:
    """``market.relative_strength`` — compounded asset vs benchmark ratio.

    Method: over the last ``horizon`` aligned periods,
    ``RS = prod(1 + r_asset) / prod(1 + r_benchmark)``. ``RS > 1`` means the
    asset outperformed the benchmark over the horizon. Inputs are per-period
    SIMPLE returns (not log returns).

    Gates:

    - ``aligned_calendars``: both series are lists/tuples of the exact same
      length — the caller must have aligned the calendars beforehand;
      mismatched lengths are rejected, never truncated;
    - ``horizon >= 1`` and ``horizon <= len(series)`` (INVALID otherwise);
    - every return finite and strictly greater than ``-1`` (a simple return
      of ``-100%`` or below cannot come from positive prices and would make
      compounding degenerate).

    Invariant: result is a finite, strictly positive float64 ratio; float64
    overflow/underflow of the compounded factors raises
    :class:`CalculationInputError` instead of returning ``inf`` or ``0/0``.
    """
    asset_seq = _require_sequence(asset_returns, "asset_returns")
    bench_seq = _require_sequence(benchmark_returns, "benchmark_returns")
    if len(asset_seq) != len(bench_seq):
        raise CalculationInputError(
            "misaligned_calendars",
            f"asset_returns has {len(asset_seq)} entries but benchmark_returns "
            f"has {len(bench_seq)}; series must be aligned on the same calendar",
        )
    h = _require_int(horizon, "horizon")
    if h < 1:
        raise CalculationInputError("invalid_horizon", f"horizon must be >= 1, got {h}")
    if h > len(asset_seq):
        raise CalculationInputError(
            "minimum_sample",
            f"horizon {h} exceeds the {len(asset_seq)} aligned periods available",
        )

    def _compound(seq: Sequence[object], name: str) -> float:
        growth = 1.0
        for offset in range(len(seq) - h, len(seq)):
            value = _to_float(seq[offset], f"{name}[{offset}]")
            factor = 1.0 + value
            if factor <= 0.0:
                raise CalculationInputError(
                    "invalid_return",
                    f"{name}[{offset}] = {value!r} implies a non-positive price "
                    "factor; simple returns must be > -1",
                )
            growth *= factor
            if not math.isfinite(growth):
                raise CalculationInputError(
                    "non_finite_result",
                    f"market.relative_strength {name} compounding overflowed float64",
                )
        return growth

    asset_growth = _compound(asset_seq, "asset_returns")
    bench_growth = _compound(bench_seq, "benchmark_returns")
    if bench_growth <= 0.0:  # float64 underflow of a positive product
        raise CalculationInputError(
            "non_finite_result",
            "market.relative_strength benchmark compounding underflowed float64",
        )
    result = _finite_result(asset_growth / bench_growth, "market.relative_strength")
    if result <= 0.0:
        raise CalculationInputError(
            "non_finite_result",
            "market.relative_strength ratio underflowed float64",
        )
    return result


def breadth(
    above_count: int,
    universe_size: int,
    *,
    covered_count: int,
    coverage_threshold: NumberLike,
) -> float:
    """``market.breadth`` — participation ratio of a point-in-time universe.

    Method and range (documented registry decision): this implementation
    returns the PARTICIPATION ratio ``above_count / covered_count`` in
    ``[0, 1]`` — the share of covered universe members above the reference
    (e.g. above their moving average). The registry invariant
    ``between_minus_one_and_one`` is therefore satisfied; the signed
    advancers-minus-decliners variant in ``[-1, 1]`` is a distinct
    calculation and is NOT what this function computes.

    Semantics of the counts (no defaults, all explicit):

    - ``universe_size``: full point-in-time universe (``>= 1``);
    - ``covered_count``: members with usable data for the measure
      (``0 <= covered_count <= universe_size``);
    - ``above_count``: covered members above the reference
      (``0 <= above_count <= covered_count``).

    Gate ``coverage_threshold``: ``covered_count / universe_size`` must reach
    ``coverage_threshold`` (in ``(0, 1]``, caller-provided, no default) or
    the breadth is INVALID and rejected — a ratio computed on a sliver of the
    universe is never silently presented as universe breadth.
    """
    above = _require_int(above_count, "above_count")
    universe = _require_int(universe_size, "universe_size")
    covered = _require_int(covered_count, "covered_count")
    if universe < 1:
        raise CalculationInputError(
            "invalid_universe", f"universe_size must be >= 1, got {universe}"
        )
    if covered < 0 or covered > universe:
        raise CalculationInputError(
            "invalid_coverage",
            f"covered_count must be within [0, universe_size], got {covered} "
            f"for universe {universe}",
        )
    if above < 0 or above > covered:
        raise CalculationInputError(
            "invalid_count",
            f"above_count must be within [0, covered_count], got {above} for coverage {covered}",
        )
    threshold = _to_float(coverage_threshold, "coverage_threshold")
    if threshold <= 0.0 or threshold > 1.0:
        raise CalculationInputError(
            "invalid_threshold",
            f"coverage_threshold must be in (0, 1], got {threshold!r}",
        )
    coverage = covered / universe
    if coverage < threshold:
        raise CalculationInputError(
            "coverage_below_threshold",
            f"coverage {coverage:.6f} ({covered}/{universe}) is below the "
            f"required threshold {threshold:.6f}",
        )
    # threshold > 0 and coverage >= threshold imply covered >= 1 here.
    return _finite_result(above / covered, "market.breadth")


# ---------------------------------------------------------------------------
# Overlays et oscillateurs — market.sma, market.ema, market.bollinger_bands,
# market.rsi, market.macd
#
# Convention commune, déclarée une fois : une série rend UNE valeur par
# fenêtre COMPLÈTE, alignée sur le dernier prix de la fenêtre. Aucun
# remplissage en tête, aucune fenêtre partielle : une série plus courte que
# la fenêtre est INVALIDE (``minimum_sample``), jamais moyennée « sur ce
# qu'on a ». Les prix passent la même frontière que :func:`rebase_series` :
# finis, strictement positifs, et sur UNE seule base d'ajustement — ces
# fonctions ne reçoivent que des nombres, l'appelant garantit la base.
# ---------------------------------------------------------------------------


def _require_window(value: object, name: str, *, minimum: int = 1) -> int:
    window = _require_int(value, name)
    if window < minimum:
        raise CalculationInputError("invalid_window", f"{name} must be >= {minimum}, got {window}")
    return window


def _require_price_series(prices: object, *, minimum: int, calculation_id: str) -> list[float]:
    seq = _require_sequence(prices, "prices")
    if len(seq) < minimum:
        raise CalculationInputError(
            "minimum_sample",
            f"{calculation_id} requires at least {minimum} prices, got {len(seq)}",
        )
    return [_require_positive_price(price, f"prices[{index}]") for index, price in enumerate(seq)]


def _mean(values: Sequence[float], calculation_id: str) -> float:
    """Moyenne arithmétique : somme exactement arrondie puis UNE division."""
    try:
        total = math.fsum(values)
    except OverflowError:
        raise CalculationInputError(
            "non_finite_result", f"{calculation_id} sum overflowed float64"
        ) from None
    return _finite_result(total / len(values), calculation_id)


def _sma_core(values: Sequence[float], window: int, calculation_id: str) -> tuple[float, ...]:
    return tuple(
        _mean(values[start : start + window], calculation_id)
        for start in range(len(values) - window + 1)
    )


def simple_moving_average(prices: Sequence[NumberLike], window: int) -> tuple[float, ...]:
    """``market.sma`` — moyenne mobile simple sur fenêtres complètes.

    Méthode : ``SMA_t = (1 / window) * sum(p_{t-window+1..t})`` — somme
    exactement arrondie (``math.fsum``) puis une division. Un point par
    fenêtre COMPLÈTE, aligné sur le dernier prix de la fenêtre :
    ``len(résultat) == len(prices) - window + 1``.

    Portes (chaque violation lève :class:`CalculationInputError`) :

    - ``prices`` est une liste ou un tuple (``invalid_type``) ;
    - ``window`` est un entier ``>= 1`` (``invalid_type`` / ``invalid_window``) ;
    - ``len(prices) >= window`` (``minimum_sample``) — une série plus courte
      n'est jamais moyennée sur ce qu'on a ;
    - chaque prix fini et strictement positif (``non_finite_input`` /
      ``non_positive_price`` / ``invalid_type``).

    Invariants : chaque point est fini et compris entre le minimum et le
    maximum de sa fenêtre (à un arrondi float64 près) ; ``window == 1`` rend
    les prix eux-mêmes, exactement. Unité : celle des prix.
    """
    _require_sequence(prices, "prices")
    w = _require_window(window, "window")
    values = _require_price_series(prices, minimum=w, calculation_id="market.sma")
    return _sma_core(values, w, "market.sma")


def _ema_core(values: Sequence[float], window: int, calculation_id: str) -> tuple[float, ...]:
    """Amorce = moyenne arithmétique des ``window`` premières valeurs, puis
    ``y_t = alpha * x_t + (1 - alpha) * y_{t-1}`` avec ``alpha = 2 / (window + 1)``.
    Aucune contrainte de signe : la ligne de signal du MACD passe ici aussi."""
    alpha = 2.0 / (window + 1.0)
    decay = 1.0 - alpha
    current = _mean(values[:window], calculation_id)
    points = [current]
    for value in values[window:]:
        current = _finite_result(alpha * value + decay * current, calculation_id)
        points.append(current)
    return tuple(points)


def exponential_moving_average(prices: Sequence[NumberLike], window: int) -> tuple[float, ...]:
    """``market.ema`` — moyenne mobile exponentielle amorcée par la moyenne.

    Méthode : amorce ``EMA_window = moyenne arithmétique des window premiers
    prix``, puis ``EMA_t = alpha * p_t + (1 - alpha) * EMA_{t-1}`` avec
    ``alpha = 2 / (window + 1)``. La convention d'amorce est DÉCLARÉE : une
    bibliothèque qui amorce sur le premier prix seul publierait d'autres
    valeurs pour la même fenêtre. Un point par fenêtre complète :
    ``len(résultat) == len(prices) - window + 1``.

    Portes : identiques à :func:`simple_moving_average` (``invalid_type``,
    ``invalid_window``, ``minimum_sample``, ``non_finite_input``,
    ``non_positive_price``).

    Invariants : chaque point est une combinaison convexe des prix vus
    jusque-là, donc compris dans leur intervalle (à un arrondi float64 près) ;
    ``window == 1`` (``alpha == 1``) rend les prix eux-mêmes, exactement.
    """
    _require_sequence(prices, "prices")
    w = _require_window(window, "window")
    values = _require_price_series(prices, minimum=w, calculation_id="market.ema")
    return _ema_core(values, w, "market.ema")


class BollingerBands(NamedTuple):
    """``market.bollinger_bands`` — trois bandes alignées sur le dernier prix.

    ``middle`` EST ``simple_moving_average(prices, window)`` (égalité exacte,
    vérifiée par test) ; ``upper`` et ``lower`` s'en écartent de ``num_std``
    écarts-types de POPULATION (ddof = 0) de la fenêtre.
    """

    lower: tuple[float, ...]
    middle: tuple[float, ...]
    upper: tuple[float, ...]


def bollinger_bands(
    prices: Sequence[NumberLike], window: int, *, num_std: NumberLike
) -> BollingerBands:
    """``market.bollinger_bands`` — médiane SMA et bandes à ``num_std`` écarts-types.

    Méthode : ``middle = SMA(window)`` (le MÊME calcul que ``market.sma``,
    égalité exacte) ; ``sigma`` = écart-type de POPULATION (ddof = 0) de la
    fenêtre, convention déclarée — la convention usuelle des bandes, qui
    diffère du ddof = 1 de ``market.realized_volatility`` ;
    ``upper = middle + num_std * sigma`` et ``lower = middle - num_std * sigma``.

    Portes :

    - ``window >= 2`` (``invalid_window``) : un seul prix n'a pas de
      dispersion, la bande n'existe pas ;
    - ``num_std`` fini et strictement positif (``invalid_type`` /
      ``non_finite_input`` / ``invalid_num_std``) ;
    - ``len(prices) >= window`` (``minimum_sample``) ; prix finis et
      strictement positifs.

    Invariants : ``lower <= middle <= upper`` point à point, bandes
    symétriques autour de la médiane à un ulp près, trois séries de même
    longueur ``len(prices) - window + 1``.
    """
    _require_sequence(prices, "prices")
    w = _require_window(window, "window", minimum=2)
    k = _to_float(num_std, "num_std")
    if k <= 0.0:
        raise CalculationInputError(
            "invalid_num_std", f"num_std must be strictly positive, got {k!r}"
        )
    values = _require_price_series(prices, minimum=w, calculation_id="market.bollinger_bands")
    middle = _sma_core(values, w, "market.bollinger_bands")
    upper: list[float] = []
    lower: list[float] = []
    for start, mean in enumerate(middle):
        block = values[start : start + w]
        variance = _mean([(value - mean) ** 2 for value in block], "market.bollinger_bands")
        half_width = _finite_result(k * math.sqrt(variance), "market.bollinger_bands")
        upper.append(_finite_result(mean + half_width, "market.bollinger_bands"))
        lower.append(_finite_result(mean - half_width, "market.bollinger_bands"))
    return BollingerBands(lower=tuple(lower), middle=middle, upper=tuple(upper))


def relative_strength_index(prices: Sequence[NumberLike], window: int) -> tuple[float, ...]:
    """``market.rsi`` — indice de force relative de Wilder.

    Méthode : variations ``d_t = p_t - p_{t-1}`` ; gain ``max(d_t, 0)``,
    perte ``max(-d_t, 0)`` ; gain moyen ``AG`` et perte moyenne ``AL``
    amorcés par la moyenne arithmétique des ``window`` premières variations,
    puis lissage de Wilder ``AG_t = (AG_{t-1} * (window - 1) + gain_t) / window``
    (idem ``AL``) ; ``RSI_t = 100 * AG_t / (AG_t + AL_t)``. Un point par
    variation au-delà de la fenêtre : ``len(résultat) == len(prices) - window``.

    Portes :

    - ``window >= 1`` (``invalid_window``) ; ``len(prices) >= window + 1``
      (``minimum_sample``) ; prix finis et strictement positifs ;
    - ``flat_series`` : ``AG_t + AL_t == 0`` en un point publié — fenêtre
      d'amorce sans aucune variation, ou (fenêtre 1, sans mémoire) un pas
      plat. Le rapport n'existe pas ; publier 0, 50 ou 100 serait une valeur
      inventée, la série entière est refusée.

    Invariant : chaque point est fini et compris dans ``[0, 100]`` ; une
    série strictement croissante vaut exactement ``100.0`` (``AL == 0``), une
    série strictement décroissante exactement ``0.0``.
    """
    _require_sequence(prices, "prices")
    w = _require_window(window, "window")
    values = _require_price_series(prices, minimum=w + 1, calculation_id="market.rsi")
    gains: list[float] = []
    losses: list[float] = []
    for previous, current in pairwise(values):
        delta = current - previous
        gains.append(delta if delta > 0.0 else 0.0)
        losses.append(-delta if delta < 0.0 else 0.0)

    def _point(average_gain: float, average_loss: float, last_index: int) -> float:
        total = average_gain + average_loss
        if total <= 0.0:
            raise CalculationInputError(
                "flat_series",
                "market.rsi: no price variation over the smoothing window ending at "
                f"prices[{last_index}]; the gain/loss ratio does not exist and no "
                "conventional value is substituted",
            )
        return _finite_result(100.0 * (average_gain / total), "market.rsi")

    average_gain = _mean(gains[:w], "market.rsi")
    average_loss = _mean(losses[:w], "market.rsi")
    points = [_point(average_gain, average_loss, w)]
    for offset in range(w, len(gains)):
        average_gain = (average_gain * (w - 1) + gains[offset]) / w
        average_loss = (average_loss * (w - 1) + losses[offset]) / w
        points.append(_point(average_gain, average_loss, offset + 1))
    return tuple(points)


class MacdSeries(NamedTuple):
    """``market.macd`` — ligne MACD, ligne de signal et histogramme.

    ``macd`` compte ``len(prices) - slow + 1`` points ; ``signal`` et
    ``histogram`` en comptent ``signal - 1`` de moins, alignés sur la fin.
    """

    macd: tuple[float, ...]
    signal: tuple[float, ...]
    histogram: tuple[float, ...]


def macd(prices: Sequence[NumberLike], *, fast: int, slow: int, signal: int) -> MacdSeries:
    """``market.macd`` — convergence/divergence de moyennes mobiles.

    Méthode : ``MACD_t = EMA_fast(p)_t - EMA_slow(p)_t`` sur les points où
    les DEUX moyennes existent (``len(prices) - slow + 1`` points) ; ligne de
    signal ``EMA_signal(MACD)`` ; ``histogram = MACD - signal`` sur les points
    où le signal existe (``len(prices) - slow - signal + 2`` points). Les
    moyennes sont celles de ``market.ema`` (amorce = moyenne arithmétique),
    la ligne de signal est amorcée de la même façon sur la ligne MACD.

    Portes :

    - ``fast``, ``slow``, ``signal`` entiers ``>= 1`` (``invalid_type`` /
      ``invalid_window``) ;
    - ``fast < slow`` strictement (``unordered_windows``) ;
    - ``len(prices) >= slow + signal - 1`` (``minimum_sample``) : au moins un
      point de signal ; prix finis et strictement positifs.

    Invariant : toutes les valeurs sont finies ; une série constante donne
    une ligne MACD nulle (à l'arrondi float64 près). Unité : celle des prix.
    """
    _require_sequence(prices, "prices")
    f = _require_window(fast, "fast")
    s = _require_window(slow, "slow")
    g = _require_window(signal, "signal")
    if f >= s:
        raise CalculationInputError(
            "unordered_windows",
            f"fast window {f} must be strictly shorter than slow window {s}",
        )
    values = _require_price_series(prices, minimum=s + g - 1, calculation_id="market.macd")
    fast_ema = _ema_core(values, f, "market.macd")
    slow_ema = _ema_core(values, s, "market.macd")
    offset = s - f
    line = tuple(
        _finite_result(fast_ema[index + offset] - slow_ema[index], "market.macd")
        for index in range(len(slow_ema))
    )
    signal_line = _ema_core(line, g, "market.macd")
    tail = line[len(line) - len(signal_line) :]
    histogram = tuple(
        _finite_result(value - smoothed, "market.macd")
        for value, smoothed in zip(tail, signal_line, strict=True)
    )
    return MacdSeries(macd=line, signal=signal_line, histogram=histogram)
