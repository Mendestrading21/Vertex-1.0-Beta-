"""decision.risk_reward — exact financial risk:reward ratio for a long directional scenario.

Implements the calculation registry entry ``decision.risk_reward``
(``docs/03-domain/calculations/CALCULATION_REGISTRY.yaml``):

- inputs: entry, stop, target, multiplier, costs (plus the currency and
  horizon coherence flags established upstream);
- output unit: ratio (a pure financial ratio — NEVER a 0-100 score);
- gates: ``ordered_levels``, ``positive_risk``, ``same_currency``;
- invariants: ``finite``, ``costs_reduce_reward``.

Formula (DECISION_ENGINE.md, long directional scenario with entry E,
stop S < E, target T > E, integer contract multiplier M >= 1 and
non-negative total costs C, all in one single currency):

    risk   = (E - S) * M + C
    reward = (T - E) * M - C
    ratio  = reward / risk

All money inputs are ``Decimal`` (boundary policy); arithmetic stays in
``Decimal`` end to end, so the result is exact up to the default context
precision of 28 significant digits (division only). ``reward`` may be zero or
negative when costs absorb the gross reward — that is honest information, not
an error; the ratio is then <= 0.

Fail-closed:

- a wrong *type* raises :class:`RiskRewardInputError` (typed exception);
- a wrong *value* (missing, non-finite, unordered levels, currency mismatch,
  undefined horizon, non-positive risk) returns ``status=INVALID`` with a
  machine-readable ``reason`` and ``ratio``/``risk``/``reward`` all ``None``
  — no partial figure is ever presented for an invalid computation, and a
  missing input is never replaced by zero.

Deterministic: pure function of its arguments, no randomness, no clock,
no network. An options structure must use its own payoff function; it never
reuses this linear formula.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import model_validator

from vertex_core.contracts.enums import CalculationStatus
from vertex_core.contracts.types import ContractModel, FiniteDecimal, NonEmptyStr

__all__ = [
    "RiskRewardInputError",
    "RiskRewardResult",
    "risk_reward",
]

_RESULT_STATUSES = frozenset({CalculationStatus.OK, CalculationStatus.INVALID})


class RiskRewardInputError(TypeError):
    """Typed error for a wrongly *typed* risk:reward input (fail-closed).

    Value-level problems (unordered levels, currency mismatch, missing input,
    non-finite Decimal, non-positive risk) do not raise: they return an
    explicit ``INVALID`` result instead.
    """


class RiskRewardResult(ContractModel):
    """Outcome of the ``decision.risk_reward`` calculation.

    ``status`` is ``OK`` or ``INVALID`` (never ``NOT_IMPLEMENTED`` here).
    On ``OK``: ``ratio``, ``risk`` and ``reward`` are finite Decimals with
    ``risk > 0`` and ``reason`` is ``None``. On ``INVALID``: ``ratio``,
    ``risk`` and ``reward`` are all ``None`` and ``reason`` names the first
    violated rule — an invalid computation never exposes partial figures.
    The ratio is a financial ratio (reward per unit of risk), never a score.
    """

    status: CalculationStatus
    ratio: FiniteDecimal | None = None
    risk: FiniteDecimal | None = None
    reward: FiniteDecimal | None = None
    reason: NonEmptyStr | None = None

    @model_validator(mode="after")
    def _check_shape(self) -> RiskRewardResult:
        if self.status not in _RESULT_STATUSES:
            raise ValueError("risk_reward status must be OK or INVALID")
        if self.status is CalculationStatus.OK:
            if self.ratio is None or self.risk is None or self.reward is None:
                raise ValueError("an OK risk_reward result requires ratio, risk and reward")
            if self.reason is not None:
                raise ValueError("an OK risk_reward result carries no reason")
            if self.risk <= 0:
                raise ValueError("an OK risk_reward result requires risk > 0")
        else:
            if self.ratio is not None or self.risk is not None or self.reward is not None:
                raise ValueError("an INVALID risk_reward result must not expose partial figures")
            if self.reason is None:
                raise ValueError("an INVALID risk_reward result requires a reason")
        return self


def _invalid(reason: str) -> RiskRewardResult:
    return RiskRewardResult(status=CalculationStatus.INVALID, reason=reason)


def _check_decimal_type(name: str, value: object) -> None:
    if not isinstance(value, Decimal):
        raise RiskRewardInputError(
            f"{name} must be a Decimal (boundary policy), got {type(value).__name__}"
        )


def _check_bool_type(name: str, value: object) -> None:
    if not isinstance(value, bool):
        raise RiskRewardInputError(f"{name} must be a bool, got {type(value).__name__}")


def risk_reward(
    entry: Decimal | None,
    stop: Decimal | None,
    target: Decimal | None,
    multiplier: int | None,
    costs: Decimal | None,
    currency_match: bool | None,
    horizon_defined: bool | None,
) -> RiskRewardResult:
    """Exact risk:reward ratio of a long directional scenario (registry ``decision.risk_reward``).

    Validation order is fixed and documented (the first violated rule names
    the ``reason``):

    1.  ``MISSING_INPUT``       — any argument is ``None`` (absence stays
        absence; it is never converted to zero);
    2.  wrong types raise :class:`RiskRewardInputError` (float money values
        are rejected: the boundary is ``Decimal``);
    3.  ``NON_FINITE_INPUT``    — NaN or infinity in entry/stop/target/costs;
    4.  ``INVALID_MULTIPLIER``  — contract multiplier < 1;
    5.  ``NEGATIVE_COSTS``      — costs < 0;
    6.  ``NON_POSITIVE_PRICE``  — entry, stop or target <= 0;
    7.  ``CURRENCY_MISMATCH``   — the three levels and costs are not proven to
        share one currency (registry gate ``same_currency``);
    8.  ``HORIZON_UNDEFINED``   — the scenario horizon is not defined;
    9.  ``STOP_NOT_BELOW_ENTRY``  — stop >= entry (registry gate ``ordered_levels``);
    10. ``TARGET_NOT_ABOVE_ENTRY`` — target <= entry (registry gate ``ordered_levels``);
    11. ``NON_POSITIVE_RISK``   — computed risk <= 0 (registry gate
        ``positive_risk``; unreachable once 4/5/9 hold, kept as a final
        independent guard — a ratio is never produced when risk <= 0).

    Invariants (tested): the result is finite (``finite``), and increasing
    costs strictly decreases reward and ratio while increasing risk
    (``costs_reduce_reward``).
    """
    if (
        entry is None
        or stop is None
        or target is None
        or multiplier is None
        or costs is None
        or currency_match is None
        or horizon_defined is None
    ):
        return _invalid("MISSING_INPUT")

    _check_decimal_type("entry", entry)
    _check_decimal_type("stop", stop)
    _check_decimal_type("target", target)
    _check_decimal_type("costs", costs)
    if isinstance(multiplier, bool) or not isinstance(multiplier, int):
        raise RiskRewardInputError(
            f"multiplier must be an int, got {type(multiplier).__name__}"
        )
    _check_bool_type("currency_match", currency_match)
    _check_bool_type("horizon_defined", horizon_defined)

    if not (entry.is_finite() and stop.is_finite() and target.is_finite() and costs.is_finite()):
        return _invalid("NON_FINITE_INPUT")
    if multiplier < 1:
        return _invalid("INVALID_MULTIPLIER")
    if costs < 0:
        return _invalid("NEGATIVE_COSTS")
    if entry <= 0 or stop <= 0 or target <= 0:
        return _invalid("NON_POSITIVE_PRICE")
    if not currency_match:
        return _invalid("CURRENCY_MISMATCH")
    if not horizon_defined:
        return _invalid("HORIZON_UNDEFINED")
    if stop >= entry:
        return _invalid("STOP_NOT_BELOW_ENTRY")
    if target <= entry:
        return _invalid("TARGET_NOT_ABOVE_ENTRY")

    multiplier_dec = Decimal(multiplier)
    risk = (entry - stop) * multiplier_dec + costs
    reward = (target - entry) * multiplier_dec - costs
    if risk <= 0:
        return _invalid("NON_POSITIVE_RISK")

    ratio = reward / risk
    return RiskRewardResult(
        status=CalculationStatus.OK,
        ratio=ratio,
        risk=risk,
        reward=reward,
    )
