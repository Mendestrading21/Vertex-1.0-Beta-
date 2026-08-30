"""Simulation preview: wire DTOs and the vertex_core-only orchestration.

``POST /api/v1/simulations/preview`` evaluates one manually declared
structure against explicit assumptions. EVERY financial figure comes from
``vertex_core.calculations.options`` — the single calculation authority:

- structure certification: :func:`defined_risk_check` runs on EVERY request;
  a structure containing a short quantity that the strict closed catalogue
  does not certify is rejected 422 with the verifier's EXACT reason code
  (e.g. ``OUTSIDE_CLOSED_CATALOG``) — a short leg only exists inside a
  certified ``DEFINED_RISK`` structure;
- expiry P&L: :func:`payoff_at_expiry` (exact ``Decimal``) on the evaluation
  grid = declared spot grid, extended with every leg strike and the
  zero-spot bankruptcy tail (the breakpoints of the piecewise-linear payoff);
- before-expiry grid: :func:`scenario_grid` (single declared-volatility
  scenario) on the declared spot x time grid, bounded by the wire contract
  (max 41 spot points x 8 time points);
- breakevens: the payoff is piecewise linear between two adjacent evaluation
  points with no strike inbetween (strikes ARE evaluation points), so each
  sign change pins one crossing. The crossing point is solved exactly from
  the two authoritative payoff values and then CERTIFIED by re-evaluating
  ``payoff_at_expiry`` at the reported spot — the published residual is the
  authority's own figure (non-zero only through decimal quantization of the
  crossing spot). The API never prices anything itself;
- extremes: max gain / max loss OVER THE EVALUATION GRID, explicitly labeled
  as on-grid figures (a warning says gains beyond the grid are not
  asserted); the certified defined-risk verdict travels alongside.

The result is labeled ``value_nature = "THEORETICAL"``; both calculations
keep their ``CalculationRecord`` lineage. NOTHING is persisted — a preview
is a pure computation on declared inputs; it neither creates nor implies any
transaction.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, localcontext
from typing import Any, Literal

from pydantic import Field

from vertex_core.calculations.options import (
    OptionLeg,
    defined_risk_check,
    payoff_at_expiry,
    scenario_grid,
)
from vertex_core.contracts import CalculationRecord, make_calculation_record
from vertex_core.contracts.types import (
    ContractModel,
    FiniteDecimal,
    FrozenStrMapping,
    NonEmptyStr,
    NonNegativeDecimal,
    PositiveDecimal,
)
from vertex_core.version import ENGINE_VERSION

__all__ = [
    "MAX_SIMULATION_LEGS",
    "MAX_SPOT_POINTS",
    "MAX_TIME_POINTS",
    "SimulationAssumptions",
    "SimulationBreakeven",
    "SimulationExtreme",
    "SimulationPayoffPoint",
    "SimulationPreviewRequest",
    "SimulationPreviewResponse",
    "SimulationRejectedError",
    "run_simulation_preview",
]

MAX_SIMULATION_LEGS = 8
"""Wire bound on the number of declared legs."""

MAX_SPOT_POINTS = 41
"""Wire bound of the declared spot grid (HP-06: light preview only)."""

MAX_TIME_POINTS = 8
"""Wire bound of the declared time grid (HP-06: light preview only)."""

_CODE_SHA = f"module:vertex_core.calculations.options@{ENGINE_VERSION}"
_BREAKEVEN_QUANTUM = Decimal("0.00000001")


class SimulationRejectedError(Exception):
    """Typed rejection carrying the verifier's exact machine-readable code."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


class SimulationAssumptions(ContractModel):
    """Declared assumptions of one preview (decimal strings on the wire).

    ``spot`` is the declared underlying reference of the snapshot the user
    composed against (echoed back); ``volatility`` is the single annualized
    decimal volatility applied to every option leg of the scenario grid
    (``0.25`` = 25%/yr); ``rate`` / ``dividend_yield`` are continuously
    compounded annualized decimals; ``fees`` groups the positive declared
    costs of the expiry payoff. The grids are BOUNDED by the wire contract.
    """

    spot: PositiveDecimal
    volatility: NonNegativeDecimal
    rate: FiniteDecimal
    dividend_yield: FiniteDecimal
    fees: NonNegativeDecimal = Decimal("0")
    spot_grid: tuple[PositiveDecimal, ...] = Field(
        min_length=1, max_length=MAX_SPOT_POINTS
    )
    time_grid_years: tuple[NonNegativeDecimal, ...] = Field(
        min_length=1, max_length=MAX_TIME_POINTS
    )


class SimulationPreviewRequest(ContractModel):
    """One declared structure plus its assumptions.

    Legs ARE the engine's own :class:`OptionLeg` contract (strict: signed
    non-zero quantity, strike required on CALL/PUT and forbidden on STOCK,
    non-negative decimal premium, positive integer multiplier) — the wire
    never redefines the calculation contract.
    """

    legs: tuple[OptionLeg, ...] = Field(min_length=1, max_length=MAX_SIMULATION_LEGS)
    assumptions: SimulationAssumptions


class SimulationPayoffPoint(ContractModel):
    """Exact expiry P&L at one evaluated terminal spot (decimal strings)."""

    spot: NonEmptyStr
    pnl: NonEmptyStr


class SimulationBreakeven(ContractModel):
    """One certified expiry breakeven.

    ``payoff_at_spot`` is the authority's own re-evaluation of
    ``options.payoff`` at the reported spot (exact ``Decimal``; non-zero only
    through decimal quantization of the crossing point). ``bracket_low`` /
    ``bracket_high`` are the two authoritative evaluation points whose sign
    change pinned the crossing.
    """

    spot: NonEmptyStr
    payoff_at_spot: NonEmptyStr
    bracket_low: NonEmptyStr
    bracket_high: NonEmptyStr


class SimulationExtreme(ContractModel):
    """Best/worst expiry P&L over the evaluation grid, with its spot."""

    pnl: NonEmptyStr
    at_spot: NonEmptyStr


class SimulationPreviewResponse(ContractModel):
    """The full preview result (nothing persisted, nothing transactional)."""

    value_nature: Literal["THEORETICAL"]
    defined_risk: FrozenStrMapping
    payoff_points: tuple[SimulationPayoffPoint, ...]
    breakevens: tuple[SimulationBreakeven, ...]
    max_gain_on_grid: SimulationExtreme
    max_loss_on_grid: SimulationExtreme
    scenario_spot_grid: tuple[NonEmptyStr, ...]
    scenario_time_grid_years: tuple[NonEmptyStr, ...]
    scenario_grid: tuple[tuple[tuple[NonEmptyStr, ...], ...], ...]
    calculations: FrozenStrMapping
    assumptions: FrozenStrMapping
    warnings: tuple[str, ...]


def _calculation_meta(record: CalculationRecord) -> dict[str, Any]:
    """Lineage subset returned to the client: version + hashes, no blob."""
    return {
        "calculation_id": record.calculation_id,
        "engine_version": record.engine_version,
        "method": record.method,
        "input_hash": record.input_hash,
        "result_hash": record.result_hash,
        "status": record.status.value,
        "assumptions": list(record.assumptions),
    }


def _dec(value: Decimal) -> str:
    return format(value, "f")


def _num_string(value: float) -> str:
    return format(Decimal(repr(value)), "f")


def _evaluation_grid(request: SimulationPreviewRequest) -> tuple[Decimal, ...]:
    """Declared spot grid, extended with every strike and the zero tail.

    Strikes are the breakpoints of the piecewise-linear expiry payoff:
    with them (and 0) in the grid, the payoff is exactly linear between any
    two adjacent evaluation points, so on-grid extremes sit at true local
    extremes of the evaluated domain and each sign change pins one crossing.
    """
    points = {Decimal(0)}
    points.update(request.assumptions.spot_grid)
    for leg in request.legs:
        if leg.strike is not None:
            points.add(leg.strike)
    return tuple(sorted(points))


def _breakevens(
    legs: tuple[OptionLeg, ...],
    grid: tuple[Decimal, ...],
    payoffs: tuple[Decimal, ...],
    fees: Decimal,
) -> tuple[list[SimulationBreakeven], bool]:
    """Certified zero crossings of the expiry payoff on the evaluation grid.

    The crossing between two adjacent authoritative points is solved with
    exact ``Decimal`` arithmetic, quantized, then RE-EVALUATED through
    ``payoff_at_expiry`` — the reported residual is the authority's own
    value at the reported spot, never an API-side price.
    """
    breakevens: list[SimulationBreakeven] = []
    quantized_any = False
    candidates: list[tuple[Decimal, Decimal, Decimal]] = []
    for (a, pa), (b, pb) in zip(
        zip(grid, payoffs, strict=True), zip(grid[1:], payoffs[1:], strict=True), strict=False
    ):
        if pa == 0:
            candidates.append((a, a, a))
        elif (pa < 0 < pb) or (pb < 0 < pa):
            with localcontext() as ctx:
                ctx.prec = 60
                crossing = a + pa * (b - a) / (pa - pb)
            quantized = crossing.quantize(_BREAKEVEN_QUANTUM)
            if quantized != crossing:
                quantized_any = True
            else:
                quantized = crossing  # exact: keep the un-padded form
            candidates.append((quantized, a, b))
    if payoffs and payoffs[-1] == 0:
        candidates.append((grid[-1], grid[-1], grid[-1]))
    for spot, low, high in candidates:
        residual = payoff_at_expiry(legs, (spot,), fees)[0]
        breakevens.append(
            SimulationBreakeven(
                spot=_dec(spot),
                payoff_at_spot=_dec(residual),
                bracket_low=_dec(low),
                bracket_high=_dec(high),
            )
        )
    return breakevens, quantized_any


def run_simulation_preview(
    request: SimulationPreviewRequest, *, now: datetime
) -> SimulationPreviewResponse:
    """Run one preview through the calculation authority (synchronous, pure).

    Raises :class:`SimulationRejectedError` when the defined-risk verifier
    refuses the structure, and lets the authority's typed
    ``OptionInputError`` propagate for any domain violation — the route maps
    both to a 422 with the exact machine-readable reason. Runs no I/O and
    persists nothing; the route executes it in the threadpool (HP-06).
    """
    legs = request.legs
    assumptions = request.assumptions

    # 1) Mandatory certification: a short quantity exists only inside a
    #    certified DEFINED_RISK structure (strict closed catalogue).
    verdict = defined_risk_check(legs)
    if not verdict.is_defined_risk:
        raise SimulationRejectedError(verdict.reason_code, verdict.detail)

    # 2) Exact expiry payoff on the strike-extended evaluation grid.
    evaluation_grid = _evaluation_grid(request)
    payoffs = payoff_at_expiry(legs, evaluation_grid, assumptions.fees)
    payoff_record = make_calculation_record(
        calculation_id="options.payoff",
        calculation_type="options",
        code_sha=_CODE_SHA,
        method="exact Decimal expiry P&L per terminal spot (sum of legs - fees)",
        inputs={
            "legs": [leg.model_dump() for leg in legs],
            "terminal_spot_grid": list(evaluation_grid),
            "fees": assumptions.fees,
        },
        result=list(payoffs),
        started_at=now,
        completed_at=now,
        assumptions=(
            "evaluation grid = declared spot grid + leg strikes + zero tail",
            "declared fees grouped at expiry",
        ),
    )

    # 3) Breakevens certified by the authority itself.
    breakevens, quantized_any = _breakevens(
        legs, evaluation_grid, payoffs, assumptions.fees
    )

    # 4) On-grid extremes (explicitly labeled; never a global claim).
    indexed = list(zip(evaluation_grid, payoffs, strict=True))
    max_spot, max_pnl = max(indexed, key=lambda pair: (pair[1], -pair[0]))
    min_spot, min_pnl = min(indexed, key=lambda pair: (pair[1], -pair[0]))

    # 5) Before-expiry scenario grid on the declared bounded grids.
    iv_scenario = tuple(
        None if leg.right == "STOCK" else assumptions.volatility for leg in legs
    )
    grid = scenario_grid(
        legs,
        assumptions.spot_grid,
        assumptions.time_grid_years,
        (iv_scenario,),
        assumptions.rate,
        assumptions.dividend_yield,
    )
    scenario_record = make_calculation_record(
        calculation_id="options.scenario_grid",
        calculation_type="options",
        code_sha=_CODE_SHA,
        method="BSM repricing grid, declared single-volatility scenario",
        inputs={
            "legs": [leg.model_dump() for leg in legs],
            "spot_grid": list(assumptions.spot_grid),
            "time_grid_years": list(assumptions.time_grid_years),
            "iv_scenarios": [
                [None if vol is None else vol for vol in iv_scenario]
            ],
            "rate": assumptions.rate,
            "dividend_yield": assumptions.dividend_yield,
        },
        result=grid,
        started_at=now,
        completed_at=now,
        assumptions=(
            "single scenario: declared volatility applied to every option leg",
            "P&L before declared costs (scenario_grid contract)",
        ),
    )

    warnings = [
        "THEORETICAL values from declared assumptions; never quotes, never "
        "executable prices, no order capability exists",
        "extremes are evaluated on the declared grid extended with the leg "
        "strikes and the zero-spot tail; gains beyond the evaluated domain "
        "are not asserted",
    ]
    if quantized_any:
        warnings.append(
            "breakeven spots are quantized to 1e-8; the published "
            "payoff_at_spot residual is options.payoff re-evaluated at the "
            "reported spot"
        )

    return SimulationPreviewResponse(
        value_nature="THEORETICAL",
        defined_risk={
            "is_defined_risk": verdict.is_defined_risk,
            "reason_code": verdict.reason_code,
            "detail": verdict.detail,
        },
        payoff_points=tuple(
            SimulationPayoffPoint(spot=_dec(spot), pnl=_dec(pnl))
            for spot, pnl in indexed
        ),
        breakevens=tuple(breakevens),
        max_gain_on_grid=SimulationExtreme(pnl=_dec(max_pnl), at_spot=_dec(max_spot)),
        max_loss_on_grid=SimulationExtreme(pnl=_dec(min_pnl), at_spot=_dec(min_spot)),
        scenario_spot_grid=tuple(_dec(spot) for spot in assumptions.spot_grid),
        scenario_time_grid_years=tuple(
            _dec(point) for point in assumptions.time_grid_years
        ),
        scenario_grid=tuple(
            tuple(tuple(_num_string(cell) for cell in row) for row in scenario)
            for scenario in grid
        ),
        calculations={
            "payoff": _calculation_meta(payoff_record),
            "scenario_grid": _calculation_meta(scenario_record),
        },
        assumptions=request.assumptions.model_dump(mode="json"),
        warnings=tuple(warnings),
    )
