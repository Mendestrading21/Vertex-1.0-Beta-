"""GET /api/v1/health: public liveness, no sensitive data, no auth required."""

from fastapi.testclient import TestClient

from vertex_core.version import ENGINE_VERSION


def test_health_is_public_and_reports_liveness(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "alive", "engine_version": ENGINE_VERSION}


def test_health_carries_no_extra_field(client: TestClient) -> None:
    body = client.get("/api/v1/health").json()
    assert set(body) == {"status", "engine_version"}
