from __future__ import annotations

import pytest

from vertex_edge_official import HttpRequest, OfficialSourceError, UrllibTransport


def test_transport_rejects_non_https_and_non_allowlisted_hosts_before_network() -> None:
    transport = UrllibTransport(allowed_hosts=frozenset({"data.sec.gov"}))
    for url in (
        "http://data.sec.gov/submissions/CIK0000000001.json",
        "https://example.invalid/submissions/CIK0000000001.json",
    ):
        with pytest.raises(OfficialSourceError, match="allowlist"):
            transport.send(HttpRequest("GET", url, {}))


def test_transport_rejects_unbounded_configuration() -> None:
    with pytest.raises(ValueError, match="allowed_hosts"):
        UrllibTransport(allowed_hosts=frozenset())
    with pytest.raises(ValueError, match="positive"):
        UrllibTransport(allowed_hosts=frozenset({"data.sec.gov"}), max_body_bytes=0)
