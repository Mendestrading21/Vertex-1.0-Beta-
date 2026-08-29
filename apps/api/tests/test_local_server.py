"""Loopback-only binding: the runner refuses any non-loopback host (fail-closed)."""

import pytest

import vertex_api.local_server as local_server
from vertex_api.local_server import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    InvalidPortError,
    LoopbackHostError,
    main,
    resolve_host,
    resolve_port,
)


class TestResolveHost:
    def test_unset_binds_default_loopback(self) -> None:
        assert resolve_host(None) == DEFAULT_HOST == "127.0.0.1"

    @pytest.mark.parametrize("host", ["127.0.0.1", "localhost"])
    def test_exact_loopback_values_are_accepted(self, host: str) -> None:
        assert resolve_host(host) == host

    @pytest.mark.parametrize(
        "host",
        [
            "0.0.0.0",
            "192.168.1.10",
            "10.0.0.5",
            "example.com",
            "",
            " 127.0.0.1",
            "127.0.0.1 ",
            "LOCALHOST",
            "127.0.0.1:8000",
            "::",
        ],
    )
    def test_any_other_value_is_refused(self, host: str) -> None:
        with pytest.raises(LoopbackHostError):
            resolve_host(host)


class TestResolvePort:
    def test_unset_uses_default(self) -> None:
        assert resolve_port(None) == DEFAULT_PORT

    def test_valid_port_is_parsed(self) -> None:
        assert resolve_port("8080") == 8080

    @pytest.mark.parametrize("port", ["0", "65536", "-1", "abc", "", "80.5"])
    def test_invalid_port_is_refused(self, port: str) -> None:
        with pytest.raises(InvalidPortError):
            resolve_port(port)


class TestMain:
    def test_non_loopback_host_never_reaches_uvicorn(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[dict] = []
        monkeypatch.setattr(
            local_server.uvicorn, "run", lambda *args, **kwargs: calls.append(kwargs)
        )
        with pytest.raises(LoopbackHostError):
            main({"VERTEX_API_HOST": "0.0.0.0"})
        assert calls == []

    def test_default_environment_starts_on_loopback(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[dict] = []
        monkeypatch.setattr(
            local_server.uvicorn, "run", lambda *args, **kwargs: calls.append(kwargs)
        )
        main({})
        assert len(calls) == 1
        assert calls[0]["host"] == "127.0.0.1"
        assert calls[0]["port"] == DEFAULT_PORT
        assert calls[0]["factory"] is True
