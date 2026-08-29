"""Fail-closed authentication: without an explicit test override, every
protected route answers 401 with detail code AUTH_NOT_IMPLEMENTED."""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from vertex_api.auth import AUTH_NOT_IMPLEMENTED, require_session


def test_require_session_always_raises_401_auth_not_implemented() -> None:
    with pytest.raises(HTTPException) as exc_info:
        require_session()
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == AUTH_NOT_IMPLEMENTED


def test_advice_preview_without_override_is_401(client: TestClient) -> None:
    response = client.post("/api/v1/advice/preview", json={})
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == AUTH_NOT_IMPLEMENTED


def test_system_engine_without_override_is_401(client: TestClient) -> None:
    response = client.get("/api/v1/system/engine")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == AUTH_NOT_IMPLEMENTED


def test_auth_runs_before_body_parsing(client: TestClient) -> None:
    """A malformed body must not leak a 422: auth rejects first (fail-closed)."""
    response = client.post(
        "/api/v1/advice/preview",
        content=b"this is not json",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == AUTH_NOT_IMPLEMENTED
