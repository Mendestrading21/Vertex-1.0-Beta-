"""End-to-end passkey authentication against the real API and PostgreSQL.

The whole chain is real: WebAuthn ceremonies (synthetic ES256 authenticator),
py_webauthn verification, credential/session storage by the persistence
repository, session cookie + CSRF double submit, and the protected advice
route answering 200 only behind a REAL session — no dependency override
anywhere in this module.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
from soft_passkey import SoftPasskey, login_passkey, register_passkey
from sqlalchemy import create_engine, text

CSRF_HEADER = "X-Vertex-CSRF"
SESSION_COOKIE = "vertex_session"
CSRF_COOKIE = "vertex_csrf"


def build_all_pass_payload() -> dict[str, Any]:
    """SYNTHETIC advice inputs that make all ten gates PASS (QUALIFIED)."""
    return {
        "instrument_id": "SYNTH:NASDAQ:STK:USD",
        "as_of": "2026-08-01T12:00:00Z",
        "valid_until": "2026-08-01T13:00:00Z",
        "input_snapshot_id": "synthetic-snapshot-1",
        "horizon": "1d",
        "direction": "NEUTRAL",
        "risk_summary": "synthetic risk summary for tests",
        "evidence_ids": ["synthetic-evidence-1"],
        "scenario_ids": ["synthetic-scenario-1"],
        "explanation_facts": ["synthetic explanation fact"],
        "instrument": {"identity_status": "RESOLVED", "resolved_with_conid": True},
        "entitlements": {"capability_status": "AVAILABLE"},
        "snapshot": {"quality": "GOOD", "fresh": True},
        "session_event": {"session_known": True, "event_calendar_known": True},
        "liquidity": {
            "asset_class": "STOCK",
            "observed_liquidity": "1000000.50",
            "required_minimum": "500000",
            "observation_delayed": False,
        },
        "calculations": {"calculation_statuses": {"synthetic_calculation": "OK"}},
        "portfolio_risk": {
            "risk_required": True,
            "portfolio_risk_available": True,
            "declarations_current": True,
        },
        "probability": {"probability_used": False},
        "contradictions": {
            "unresolved_critical_count": 0,
            "explicit_contradiction_count": 0,
        },
        "constraints": {"constraints_version": "v1", "constraints_current": True},
    }


class TestFullCycle:
    def test_bootstrap_register_login_access_and_logout(
        self, client: TestClient, passkey: SoftPasskey
    ) -> None:
        # Nothing is reachable before authentication.
        assert client.get("/api/v1/system/engine").status_code == 401

        # Bootstrap: the very first registration is free (no credential yet).
        register_passkey(client, passkey)

        # Real login: session and CSRF cookies are issued.
        login_response = login_passkey(client, passkey)
        assert login_response.status_code == 200, login_response.text
        body = login_response.json()
        assert body["authenticated"] is True
        assert body["expires_at"].endswith("Z")
        assert client.cookies.get(SESSION_COOKIE)
        csrf_token = client.cookies.get(CSRF_COOKIE)
        assert csrf_token

        # A GET behind the real session succeeds without CSRF.
        engine_response = client.get("/api/v1/system/engine")
        assert engine_response.status_code == 200

        # A mutation requires the CSRF double-submit header.
        payload = build_all_pass_payload()
        no_header = client.post("/api/v1/advice/preview", json=payload)
        assert no_header.status_code == 401
        wrong_header = client.post(
            "/api/v1/advice/preview", json=payload, headers={CSRF_HEADER: "forged"}
        )
        assert wrong_header.status_code == 401
        with_header = client.post(
            "/api/v1/advice/preview", json=payload, headers={CSRF_HEADER: csrf_token}
        )
        assert with_header.status_code == 200, with_header.text
        assert with_header.json()["status"] == "QUALIFIED"

        # Logout revokes server-side and clears the cookies.
        logout_response = client.post(
            "/api/v1/auth/logout", headers={CSRF_HEADER: csrf_token}
        )
        assert logout_response.status_code == 200
        assert logout_response.json() == {"logged_out": True}
        assert client.get("/api/v1/system/engine").status_code == 401

    def test_forged_session_cookie_is_rejected(self, client: TestClient) -> None:
        client.cookies.set(SESSION_COOKIE, "forged-token-never-issued")
        response = client.get("/api/v1/system/engine")
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "AUTH_REQUIRED"


class TestRegistrationGate:
    def test_second_registration_requires_a_real_session(
        self, client: TestClient, passkey: SoftPasskey
    ) -> None:
        register_passkey(client, passkey)

        # Without a session, the registration window is closed forever.
        assert client.post("/api/v1/auth/register/options").status_code == 401

        # With a real session (and CSRF), a second passkey can be added.
        assert login_passkey(client, passkey).status_code == 200
        client.headers[CSRF_HEADER] = client.cookies.get(CSRF_COOKIE)
        register_passkey(client, SoftPasskey(), label="second synthetic passkey")

    def test_register_verify_flow_id_is_single_use(
        self, client: TestClient, passkey: SoftPasskey
    ) -> None:
        options_response = client.post("/api/v1/auth/register/options")
        assert options_response.status_code == 200
        body = options_response.json()
        credential = passkey.create(body["options"])
        request_body = {
            "flow_id": body["flow_id"],
            "label": "synthetic passkey",
            "credential": credential,
        }
        assert client.post("/api/v1/auth/register/verify", json=request_body).status_code == 200
        # Replay of the same flow (even with the same valid credential): 401.
        replay = client.post("/api/v1/auth/register/verify", json=request_body)
        assert replay.status_code == 401


class TestLoginRejections:
    def test_login_from_unlisted_origin_is_rejected(
        self, client: TestClient, passkey: SoftPasskey
    ) -> None:
        register_passkey(client, passkey)
        passkey.origin = "http://evil.example"
        response = login_passkey(client, passkey)
        assert response.status_code == 401
        assert not client.cookies.get(SESSION_COOKIE)

    def test_login_with_unknown_credential_is_rejected(
        self, client: TestClient, passkey: SoftPasskey
    ) -> None:
        register_passkey(client, passkey)
        stranger = SoftPasskey()
        stranger.credential_id = passkey.credential_id  # right id, wrong key
        response = login_passkey(client, stranger)
        assert response.status_code == 401

    def test_login_options_without_any_credential_is_401(
        self, client: TestClient
    ) -> None:
        assert client.post("/api/v1/auth/login/options").status_code == 401


class TestCloneDetection:
    def test_sign_count_regression_revokes_credential_and_sessions(
        self, client: TestClient, passkey: SoftPasskey
    ) -> None:
        register_passkey(client, passkey)
        assert login_passkey(client, passkey).status_code == 200  # counter -> 1
        assert client.get("/api/v1/system/engine").status_code == 200

        # A clone replays an already-used counter value: login fails closed...
        clone_response = login_passkey(client, passkey, sign_count=1)
        assert clone_response.status_code == 401

        # ...the pre-existing session is revoked with the credential...
        assert client.get("/api/v1/system/engine").status_code == 401

        # ...and the credential is dead: no login ceremony can even start.
        assert client.post("/api/v1/auth/login/options").status_code == 401


class TestStorageAndCookies:
    def test_issued_tokens_never_stored_in_clear(
        self, client: TestClient, passkey: SoftPasskey, database_url: str
    ) -> None:
        register_passkey(client, passkey)
        assert login_passkey(client, passkey).status_code == 200
        session_token = client.cookies.get(SESSION_COOKIE)
        csrf_token = client.cookies.get(CSRF_COOKIE)
        assert session_token and csrf_token

        engine = create_engine(database_url)
        try:
            with engine.connect() as connection:
                rows = connection.execute(
                    text("SELECT session_id_hash, csrf_token_hash FROM auth_sessions")
                ).all()
        finally:
            engine.dispose()
        assert len(rows) == 1
        for stored_value in rows[0]:
            assert stored_value.startswith("sha256:")
            assert session_token not in stored_value
            assert csrf_token not in stored_value

    def test_default_cookie_attributes_are_hardened(
        self, secure_client: TestClient, passkey: SoftPasskey
    ) -> None:
        """Default config: Secure, HttpOnly (session only), SameSite=strict, 8 h."""
        register_passkey(secure_client, passkey)
        options_body = secure_client.post("/api/v1/auth/login/options").json()
        response = secure_client.post(
            "/api/v1/auth/login/verify",
            json={
                "flow_id": options_body["flow_id"],
                "credential": passkey.get(options_body["options"]),
            },
        )
        assert response.status_code == 200
        cookie_headers = response.headers.get_list("set-cookie")
        session_header = next(h for h in cookie_headers if h.startswith(f"{SESSION_COOKIE}="))
        csrf_header = next(h for h in cookie_headers if h.startswith(f"{CSRF_COOKIE}="))
        for header in (session_header, csrf_header):
            assert "Secure" in header
            assert "SameSite=strict" in header
            assert "Max-Age=28800" in header
            assert "Path=/" in header
        assert "HttpOnly" in session_header
        assert "HttpOnly" not in csrf_header  # readable for the double submit
