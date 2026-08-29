"""Simulation preview against REAL passkey authentication and REAL CSRF.

No dependency override anywhere: the WebAuthn session cookie and the CSRF
double-submit header are the real fail-closed path of the mutation route.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from soft_passkey import SoftPasskey, login_passkey, register_passkey

CSRF_HEADER = "X-Vertex-CSRF"
CSRF_COOKIE = "vertex_csrf"

PAYLOAD = {
    "legs": [
        {
            "right": "CALL",
            "quantity": 1,
            "strike": "100",
            "premium": "5.00",
            "multiplier": 100,
        },
        {
            "right": "CALL",
            "quantity": -1,
            "strike": "110",
            "premium": "2.00",
            "multiplier": 100,
        },
    ],
    "assumptions": {
        "spot": "100.00",
        "volatility": "0.25",
        "rate": "0.02",
        "dividend_yield": "0.00",
        "fees": "1.00",
        "spot_grid": ["90.00", "100.00", "110.00"],
        "time_grid_years": ["0.08", "0"],
    },
}


@pytest.fixture()
def authenticated(client: TestClient, passkey: SoftPasskey) -> TestClient:
    register_passkey(client, passkey)
    assert login_passkey(client, passkey).status_code == 200
    return client


def test_without_session_is_generic_401(client: TestClient) -> None:
    response = client.post("/api/v1/simulations/preview", json=PAYLOAD)
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTH_REQUIRED"


def test_csrf_is_required_on_the_mutation(authenticated: TestClient) -> None:
    # A real session WITHOUT the CSRF double-submit header: generic 401.
    response = authenticated.post("/api/v1/simulations/preview", json=PAYLOAD)
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTH_REQUIRED"

    # A forged header value fails the double submit the same way.
    forged = authenticated.post(
        "/api/v1/simulations/preview",
        json=PAYLOAD,
        headers={CSRF_HEADER: "forged"},
    )
    assert forged.status_code == 401


def test_preview_succeeds_with_session_and_csrf(authenticated: TestClient) -> None:
    csrf_token = authenticated.cookies.get(CSRF_COOKIE)
    assert csrf_token
    response = authenticated.post(
        "/api/v1/simulations/preview",
        json=PAYLOAD,
        headers={CSRF_HEADER: csrf_token},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["value_nature"] == "THEORETICAL"
    assert body["defined_risk"]["reason_code"] == "DEFINED_RISK"
    assert body["breakevens"][0]["spot"] == "103.01"
    assert body["calculations"]["payoff"]["input_hash"].startswith("sha256:")

    # The rejection path keeps its exact machine-readable reason end to end.
    naked = dict(PAYLOAD, legs=[PAYLOAD["legs"][1]])
    rejected = authenticated.post(
        "/api/v1/simulations/preview",
        json=naked,
        headers={CSRF_HEADER: csrf_token},
    )
    assert rejected.status_code == 422
    assert rejected.json()["detail"]["code"] == "UNCOVERED_SHORT_UPSIDE_TAIL"
