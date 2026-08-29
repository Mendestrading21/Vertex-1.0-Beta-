"""POST /api/v1/simulations/preview: vertex_core-only orchestration.

Everything here is SYNTHETIC: declared legs and assumptions with explicit
decimal strings. The expected figures come from the documented catalogue
formulas (bull call debit: max loss D, max gain W*M - D, breakeven K1 + D/M)
so the route's relayed vertex_core results are checked against the
specification, never against a re-implementation.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient


def leg(
    right: str,
    quantity: int,
    *,
    strike: str | None = None,
    premium: str = "1.00",
    multiplier: int = 100,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "right": right,
        "quantity": quantity,
        "premium": premium,
        "multiplier": multiplier,
    }
    if strike is not None:
        body["strike"] = strike
    return body


def bull_call_payload() -> dict[str, Any]:
    """BULL_CALL_DEBIT: long CALL K1=100 @5, short CALL K2=110 @2, M=100.

    Per-unit debit d=3, W=10; with fees 1.00: total D&fees = 301.
    """
    return {
        "legs": [
            leg("CALL", 1, strike="100", premium="5.00"),
            leg("CALL", -1, strike="110", premium="2.00"),
        ],
        "assumptions": {
            "spot": "100.00",
            "volatility": "0.25",
            "rate": "0.02",
            "dividend_yield": "0.00",
            "fees": "1.00",
            "spot_grid": ["80.00", "100.00", "120.00"],
            "time_grid_years": ["0.08", "0"],
        },
    }


def post(client: TestClient, payload: dict[str, Any]):
    return client.post("/api/v1/simulations/preview", json=payload)


def test_requires_a_session_401(client: TestClient) -> None:
    assert post(client, bull_call_payload()).status_code == 401


def test_bull_call_debit_preview_matches_the_specification(
    authenticated_client: TestClient,
) -> None:
    response = post(authenticated_client, bull_call_payload())
    assert response.status_code == 200
    body = response.json()

    assert body["value_nature"] == "THEORETICAL"
    assert body["defined_risk"]["is_defined_risk"] is True
    assert body["defined_risk"]["reason_code"] == "DEFINED_RISK"
    assert "BULL_CALL_DEBIT" in body["defined_risk"]["detail"]

    # Evaluation grid = declared spots + strikes + the zero tail, sorted
    # (the strike 100 and the declared spot 100.00 are one point).
    points = {p["spot"]: p["pnl"] for p in body["payoff_points"]}
    assert list(points) == ["0", "80.00", "100.00", "110", "120.00"]
    # Max loss D (fees included) on the whole downside; capped gain W*M - D.
    assert points["0"] == "-301.00"
    assert points["80.00"] == "-301.00"
    assert points["110"] == "699.00"
    assert points["120.00"] == "699.00"

    # Breakeven K1 + D/M = 103.01, certified with an exact zero residual.
    (breakeven,) = body["breakevens"]
    assert breakeven["spot"] == "103.01"
    assert breakeven["payoff_at_spot"] == "0.00"
    assert breakeven["bracket_low"] == "100.00"
    assert breakeven["bracket_high"] == "110"

    assert body["max_gain_on_grid"]["pnl"] == "699.00"
    assert body["max_loss_on_grid"]["pnl"] == "-301.00"

    # Scenario grid: 1 scenario x 2 times x 3 spots of decimal strings.
    grid = body["scenario_grid"]
    assert len(grid) == 1
    assert len(grid[0]) == 2
    assert all(len(row) == 3 for row in grid[0])
    assert all(isinstance(cell, str) for row in grid[0] for cell in row)
    assert body["scenario_spot_grid"] == ["80.00", "100.00", "120.00"]

    # CalculationRecord lineage for BOTH authoritative calculations.
    for name in ("payoff", "scenario_grid"):
        calc = body["calculations"][name]
        assert calc["calculation_id"] == f"options.{name if name != 'payoff' else 'payoff'}"
        assert calc["input_hash"].startswith("sha256:")
        assert calc["result_hash"].startswith("sha256:")
        assert calc["status"] == "OK"

    # Assumptions echoed verbatim; warnings present; nothing persisted.
    assert body["assumptions"]["fees"] == "1.00"
    assert body["assumptions"]["spot"] == "100.00"
    assert any("THEORETICAL" in warning for warning in body["warnings"])


def test_all_long_straddle_is_accepted(authenticated_client: TestClient) -> None:
    payload = bull_call_payload()
    payload["legs"] = [
        leg("CALL", 1, strike="100", premium="4.00"),
        leg("PUT", 1, strike="100", premium="3.50"),
    ]
    response = post(authenticated_client, payload)
    assert response.status_code == 200
    body = response.json()
    assert body["defined_risk"]["reason_code"] == "DEFINED_RISK"
    assert "LONG_STRADDLE" in body["defined_risk"]["detail"]
    assert len(body["breakevens"]) == 2  # one on each side of the strike


def test_naked_short_call_is_422_with_the_verifiers_exact_reason(
    authenticated_client: TestClient,
) -> None:
    payload = bull_call_payload()
    payload["legs"] = [leg("CALL", -1, strike="110", premium="2.00")]
    response = post(authenticated_client, payload)
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "UNCOVERED_SHORT_UPSIDE_TAIL"
    assert "unbounded loss" in detail["message"]


def test_short_outside_the_closed_catalog_is_422(
    authenticated_client: TestClient,
) -> None:
    payload = bull_call_payload()
    payload["legs"] = [
        leg("CALL", 2, strike="100", premium="5.00"),
        leg("CALL", 1, strike="105", premium="3.00"),
        leg("CALL", -1, strike="110", premium="2.00"),
    ]
    response = post(authenticated_client, payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "OUTSIDE_CLOSED_CATALOG"


def test_debit_at_or_above_width_is_422(authenticated_client: TestClient) -> None:
    payload = bull_call_payload()
    payload["legs"] = [
        leg("CALL", 1, strike="100", premium="15.00"),  # d = 13 >= W = 10
        leg("CALL", -1, strike="110", premium="2.00"),
    ]
    response = post(authenticated_client, payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "VERTICAL_DEBIT_NOT_BELOW_WIDTH"


def test_oversized_spot_grid_is_422(authenticated_client: TestClient) -> None:
    payload = bull_call_payload()
    payload["assumptions"]["spot_grid"] = [
        f"{100 + i}.00" for i in range(42)  # 42 > the 41-point bound
    ]
    assert post(authenticated_client, payload).status_code == 422


def test_oversized_time_grid_is_422(authenticated_client: TestClient) -> None:
    payload = bull_call_payload()
    payload["assumptions"]["time_grid_years"] = [f"0.0{i}" for i in range(1, 10)]
    assert post(authenticated_client, payload).status_code == 422


def test_out_of_domain_spot_is_a_typed_422(authenticated_client: TestClient) -> None:
    payload = bull_call_payload()
    payload["assumptions"]["spot_grid"] = ["10000000000000"]  # 1e13 > 1e12
    response = post(authenticated_client, payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"].endswith("out_of_domain")


def test_out_of_domain_premium_is_a_typed_422(
    authenticated_client: TestClient,
) -> None:
    payload = bull_call_payload()
    payload["legs"] = [leg("CALL", 1, strike="100", premium="10000000000000")]
    response = post(authenticated_client, payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "leg_premium_out_of_domain"


def test_out_of_domain_volatility_is_a_typed_422(
    authenticated_client: TestClient,
) -> None:
    payload = bull_call_payload()
    payload["assumptions"]["volatility"] = "11"  # > 10, the validated domain
    response = post(authenticated_client, payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "volatility_out_of_domain"


@pytest.mark.parametrize(
    "bad_leg",
    [
        leg("CALL", 0, strike="100"),  # zero quantity
        leg("STOCK", 1, strike="100"),  # a STOCK leg must not carry a strike
        leg("CALL", 1),  # a CALL leg requires a strike
        leg("CALL", 1, strike="-5"),  # non-positive strike
    ],
)
def test_invalid_legs_are_rejected_by_the_wire_contract(
    authenticated_client: TestClient, bad_leg: dict[str, Any]
) -> None:
    payload = bull_call_payload()
    payload["legs"] = [bad_leg]
    assert post(authenticated_client, payload).status_code == 422


def test_nothing_is_persisted_by_a_preview(authenticated_client: TestClient) -> None:
    # Two identical previews: pure computation, no snapshot, no id, no state.
    first = post(authenticated_client, bull_call_payload())
    second = post(authenticated_client, bull_call_payload())
    assert first.status_code == second.status_code == 200
    first_body = first.json()
    second_body = second.json()
    assert first_body["payoff_points"] == second_body["payoff_points"]
    assert first_body["calculations"]["payoff"]["input_hash"] == (
        second_body["calculations"]["payoff"]["input_hash"]
    )
    assert "simulation_id" not in first_body
