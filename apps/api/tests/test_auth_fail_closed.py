"""Fail-closed authentication: without a valid session, every protected route
answers the same generic 401 with detail code AUTH_REQUIRED — whatever the
cause (no cookie, forged cookie, or even a server without a database)."""

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from vertex_api.auth import AUTH_REQUIRED, SESSION_COOKIE_NAME, require_session


def _bare_request(app: FastAPI, headers: list[tuple[bytes, bytes]]) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/advice/preview",
            "headers": headers,
            "query_string": b"",
            "app": app,
        }
    )


def test_require_session_without_cookie_raises_generic_401(app: FastAPI) -> None:
    with pytest.raises(HTTPException) as exc_info:
        require_session(_bare_request(app, headers=[]))
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == {
        "code": AUTH_REQUIRED,
        "message": "authentication required",
    }


def test_require_session_with_forged_cookie_and_no_database_is_generic_401(
    app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A cookie that cannot be checked (no database configured) fails closed
    with the SAME generic 401 — no configuration detail leaks."""
    monkeypatch.delenv("VERTEX_DATABASE_URL", raising=False)
    cookie = f"{SESSION_COOKIE_NAME}=forged-token".encode()
    with pytest.raises(HTTPException) as exc_info:
        require_session(_bare_request(app, headers=[(b"cookie", cookie)]))
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == {
        "code": AUTH_REQUIRED,
        "message": "authentication required",
    }


def test_advice_preview_without_session_is_401(client: TestClient) -> None:
    response = client.post("/api/v1/advice/preview", json={})
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == AUTH_REQUIRED


def test_system_engine_without_session_is_401(client: TestClient) -> None:
    response = client.get("/api/v1/system/engine")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == AUTH_REQUIRED


def test_auth_runs_before_body_parsing(client: TestClient) -> None:
    """A malformed body must not leak a 422: auth rejects first (fail-closed)."""
    response = client.post(
        "/api/v1/advice/preview",
        content=b"this is not json",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == AUTH_REQUIRED


def test_401_reveals_no_cause_detail(client: TestClient) -> None:
    """The 401 body is exactly the generic shape — no cause, no state."""
    response = client.get("/api/v1/system/engine")
    assert response.json() == {
        "detail": {"code": AUTH_REQUIRED, "message": "authentication required"}
    }
    assert response.headers["WWW-Authenticate"] == "Session"
