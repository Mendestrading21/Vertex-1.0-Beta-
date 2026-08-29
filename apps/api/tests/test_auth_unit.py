"""Unit tests of the auth building blocks: challenge store, config, and the
fail-closed behavior of the ceremony routes when no state can back them.

Everything here is SYNTHETIC, deterministic and database-free (an injected
monotonic clock replaces real time). The full ceremony against PostgreSQL
lives in ``apps/api/tests_integration``.
"""

import pytest
from fastapi.testclient import TestClient

from vertex_api.auth import AUTH_REQUIRED, AuthConfigError, ChallengeStore, load_auth_config


class FakeClock:
    def __init__(self) -> None:
        self.value = 1000.0

    def __call__(self) -> float:
        return self.value


class TestChallengeStore:
    def test_issue_and_consume_single_use(self) -> None:
        store = ChallengeStore(clock=FakeClock())
        flow_id, challenge = store.issue("register")
        assert len(challenge) == 32
        assert store.consume(flow_id, "register") == challenge
        # Single use: a replay finds nothing.
        assert store.consume(flow_id, "register") is None

    def test_purpose_binding_consumes_and_rejects(self) -> None:
        store = ChallengeStore(clock=FakeClock())
        flow_id, _ = store.issue("register")
        assert store.consume(flow_id, "login") is None
        # The mismatched probe consumed the entry: no second chance.
        assert store.consume(flow_id, "register") is None

    def test_ttl_expires_after_120_seconds(self) -> None:
        clock = FakeClock()
        store = ChallengeStore(clock=clock)
        flow_id, _ = store.issue("login")
        clock.value += 120.0
        assert store.consume(flow_id, "login") is None

    def test_challenge_survives_just_under_ttl(self) -> None:
        clock = FakeClock()
        store = ChallengeStore(clock=clock)
        flow_id, challenge = store.issue("login")
        clock.value += 119.0
        assert store.consume(flow_id, "login") == challenge

    def test_bounded_store_evicts_oldest(self) -> None:
        clock = FakeClock()
        store = ChallengeStore(clock=clock, max_entries=2)
        first, _ = store.issue("login")
        clock.value += 1.0
        second, _ = store.issue("login")
        clock.value += 1.0
        third, _ = store.issue("login")
        assert store.consume(first, "login") is None  # evicted
        assert store.consume(second, "login") is not None
        assert store.consume(third, "login") is not None

    def test_unknown_flow_id_is_none(self) -> None:
        store = ChallengeStore(clock=FakeClock())
        assert store.consume("never-issued", "login") is None


class TestAuthConfig:
    def test_defaults_are_strict_loopback(self) -> None:
        config = load_auth_config({})
        assert config.rp_id == "localhost"
        assert config.expected_origins == ("http://127.0.0.1", "http://localhost")
        assert config.cookie_secure is True
        assert config.session_ttl.total_seconds() == 8 * 3600

    def test_dev_ports_extend_origins_explicitly(self) -> None:
        config = load_auth_config({"VERTEX_AUTH_DEV_ORIGIN_PORTS": "5173, 8000"})
        assert config.expected_origins == (
            "http://127.0.0.1",
            "http://localhost",
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:8000",
            "http://localhost:8000",
        )

    @pytest.mark.parametrize("raw", ["abc", "0", "65536", "-1", "80;81"])
    def test_invalid_port_list_fails_closed(self, raw: str) -> None:
        with pytest.raises(AuthConfigError):
            load_auth_config({"VERTEX_AUTH_DEV_ORIGIN_PORTS": raw})

    def test_insecure_cookie_needs_explicit_dev_opt_out(self) -> None:
        assert load_auth_config({}).cookie_secure is True
        assert (
            load_auth_config({"VERTEX_AUTH_COOKIE_INSECURE_DEV": "1"}).cookie_secure is False
        )
        # Any other value keeps the fail-closed default.
        assert (
            load_auth_config({"VERTEX_AUTH_COOKIE_INSECURE_DEV": "true"}).cookie_secure
            is True
        )


class TestCeremonyRoutesFailClosed:
    """Without a database, every ceremony route answers the generic 401."""

    @pytest.fixture(autouse=True)
    def _no_database(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("VERTEX_DATABASE_URL", raising=False)

    def test_register_options_without_database_is_401(self, client: TestClient) -> None:
        response = client.post("/api/v1/auth/register/options")
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == AUTH_REQUIRED

    def test_login_options_without_database_is_401(self, client: TestClient) -> None:
        response = client.post("/api/v1/auth/login/options")
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == AUTH_REQUIRED

    def test_register_verify_with_unknown_flow_is_401(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/auth/register/verify",
            json={"flow_id": "never-issued", "label": "synthetic", "credential": {}},
        )
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == AUTH_REQUIRED

    def test_login_verify_with_unknown_flow_is_401(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/auth/login/verify",
            json={"flow_id": "never-issued", "credential": {}},
        )
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == AUTH_REQUIRED

    def test_logout_without_session_is_401(self, client: TestClient) -> None:
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == AUTH_REQUIRED

    def test_ceremony_401_carries_no_cause_detail(self, client: TestClient) -> None:
        bodies = {
            client.post("/api/v1/auth/register/options").text,
            client.post("/api/v1/auth/login/options").text,
            client.post("/api/v1/auth/logout").text,
        }
        # Whatever the internal cause, the wire body is identical.
        assert len(bodies) == 1
