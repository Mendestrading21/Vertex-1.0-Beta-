from __future__ import annotations

import json
from datetime import UTC, date, datetime

import pytest

from vertex_edge_official import (
    EcbDataClient,
    FredClient,
    HttpRequest,
    HttpResponse,
    OfficialSourceError,
    OpenFigiClient,
    OpenFigiMapping,
    SecEdgarClient,
    SnbDataClient,
)

NOW = datetime(2026, 9, 1, 12, tzinfo=UTC)


class FakeTransport:
    def __init__(self, body: bytes = b'{"ok":true}', status_code: int = 200) -> None:
        self.body = body
        self.status_code = status_code
        self.requests: list[HttpRequest] = []

    def send(self, request: HttpRequest) -> HttpResponse:
        self.requests.append(request)
        return HttpResponse(self.status_code, {}, self.body, NOW)


def test_sec_requires_contact_and_pads_cik_without_authentication() -> None:
    with pytest.raises(ValueError, match="contact"):
        SecEdgarClient(user_agent="Vertex")

    transport = FakeTransport()
    envelope = SecEdgarClient(
        user_agent="Vertex One dev@example.invalid", transport=transport
    ).submissions(320193)

    request = transport.requests[0]
    assert request.url == "https://data.sec.gov/submissions/CIK0000320193.json"
    assert request.headers["User-Agent"] == "Vertex One dev@example.invalid"
    assert "Authorization" not in request.headers
    assert envelope.schema_version == "sec.edgar.submissions/1"
    assert envelope.source == "sec_edgar"
    assert envelope.payload["cik"] == "0000320193"
    assert envelope.observed_at is None


def test_sec_company_facts_uses_the_documented_endpoint() -> None:
    transport = FakeTransport()
    envelope = SecEdgarClient(
        user_agent="Vertex One https://example.invalid/contact", transport=transport
    ).company_facts("1045810")
    assert transport.requests[0].url.endswith(
        "/api/xbrl/companyfacts/CIK0001045810.json"
    )
    assert envelope.schema_version == "sec.edgar.company-facts/1"


def test_fred_keeps_vintage_dates_and_never_puts_key_in_payload() -> None:
    transport = FakeTransport(b'{"observations":[]}')
    envelope = FredClient(api_key="synthetic-key", transport=transport).observations(
        "GDP",
        realtime_start=date(2020, 1, 1),
        realtime_end=date(2020, 12, 31),
    )
    request = transport.requests[0]
    assert "api_key=synthetic-key" in request.url
    assert "synthetic-key" not in json.dumps(envelope.payload)
    assert envelope.payload["request"]["realtime_start"] == "2020-01-01"
    assert envelope.payload["request"]["realtime_end"] == "2020-12-31"
    assert envelope.schema_version == "fred.alfred.observations/1"


def test_openfigi_is_bounded_and_does_not_resolve_ambiguity() -> None:
    body = b'[{"data":[{"figi":"SYN-A"},{"figi":"SYN-B"}]}]'
    transport = FakeTransport(body)
    envelope = OpenFigiClient(api_key="synthetic-key", transport=transport).map(
        [OpenFigiMapping(id_type="TICKER", id_value="SYN", exchange_code="US")]
    )
    request = transport.requests[0]
    assert request.headers["X-OPENFIGI-APIKEY"] == "synthetic-key"
    assert len(envelope.payload["response"][0]["data"]) == 2
    with pytest.raises(ValueError, match="one to ten"):
        OpenFigiClient(transport=transport).map([])


def test_openfigi_rejects_conflicting_exchange_selectors() -> None:
    mapping = OpenFigiMapping(
        id_type="TICKER", id_value="SYN", exchange_code="US", mic_code="XNAS"
    )
    with pytest.raises(ValueError, match="mutually exclusive"):
        mapping.as_payload()


def test_ecb_and_snb_only_build_official_csv_endpoints() -> None:
    ecb_transport = FakeTransport(b"KEY,OBS_VALUE\nSYN,1\n")
    ecb = EcbDataClient(transport=ecb_transport).data(
        "EXR", "D.USD.EUR.SP00.A", start_period="2026-01-01"
    )
    assert ecb_transport.requests[0].url.startswith(
        "https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?"
    )
    assert ecb.payload["csv"].startswith("KEY")

    snb_transport = FakeTransport(b"Date;Value\n2026-01;1\n")
    snb = SnbDataClient(transport=snb_transport).cube("snbmonagglech", language="fr")
    assert snb_transport.requests[0].url == (
        "https://data.snb.ch/api/cube/snbmonagglech/data/csv/fr"
    )
    assert snb.schema_version == "snb.cube.csv/1"


def test_invalid_or_empty_provider_payloads_fail_closed() -> None:
    with pytest.raises(OfficialSourceError, match="invalid UTF-8 JSON"):
        FredClient(api_key="synthetic", transport=FakeTransport(b"not-json")).observations(
            "GDP"
        )
    with pytest.raises(OfficialSourceError, match="empty CSV"):
        SnbDataClient(transport=FakeTransport(b"   ")).cube("synthetic")
    with pytest.raises(OfficialSourceError, match="HTTP 429"):
        OpenFigiClient(transport=FakeTransport(status_code=429)).map(
            [OpenFigiMapping(id_type="TICKER", id_value="SYN")]
        )
