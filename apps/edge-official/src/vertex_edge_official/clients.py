"""Strict, read-only clients for the approved official-source foundation.

The adapters preserve the provider payload verbatim inside a metadata wrapper.
They do not select a financial truth, calculate a metric or resolve a conflict.
Downstream normalizers remain responsible for typed facts and point-in-time
semantics.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any
from urllib.parse import urlencode

from vertex_core.contracts import (
    DataEnvelope,
    DelayStatus,
    EnvelopeQuality,
    canonical_json_hash,
)
from vertex_edge_official.transport import (
    HttpRequest,
    HttpResponse,
    HttpTransport,
    OfficialSourceError,
    UrllibTransport,
)

__all__ = [
    "EcbDataClient",
    "FredClient",
    "OpenFigiClient",
    "OpenFigiMapping",
    "SecEdgarClient",
    "SnbDataClient",
]

_TOKEN = re.compile(r"^[A-Za-z0-9@_.-]+$")
_SERIES_ID = re.compile(r"^[A-Za-z0-9_.-]+$")
_PERIOD = re.compile(r"^[A-Za-z0-9-]+$")
_SEC_HOST = "data.sec.gov"
_FRED_HOST = "api.stlouisfed.org"
_OPENFIGI_HOST = "api.openfigi.com"
_ECB_HOST = "data-api.ecb.europa.eu"
_SNB_HOST = "data.snb.ch"


def _require_token(value: str, field: str, pattern: re.Pattern[str] = _TOKEN) -> str:
    if not value or pattern.fullmatch(value) is None:
        raise ValueError(f"{field} contains unsupported characters")
    return value


def _date_value(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _json_payload(response: HttpResponse) -> dict[str, Any] | list[Any]:
    if response.status_code != 200:
        raise OfficialSourceError(f"provider returned HTTP {response.status_code}")
    try:
        decoded = json.loads(response.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise OfficialSourceError("provider returned invalid UTF-8 JSON") from None
    if not isinstance(decoded, (dict, list)):
        raise OfficialSourceError("provider JSON root must be an object or array")
    return decoded


def _csv_payload(response: HttpResponse) -> str:
    if response.status_code != 200:
        raise OfficialSourceError(f"provider returned HTTP {response.status_code}")
    try:
        decoded = response.body.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise OfficialSourceError("provider returned invalid UTF-8 CSV") from None
    if not decoded.strip():
        raise OfficialSourceError("provider returned an empty CSV payload")
    return decoded


def _envelope(
    *,
    source: str,
    schema_version: str,
    source_event_id: str,
    rights: str,
    response: HttpResponse,
    payload: dict[str, Any],
) -> DataEnvelope[dict[str, Any]]:
    payload_hash = canonical_json_hash(payload)
    digest = payload_hash.removeprefix("sha256:")[:24]
    return DataEnvelope[dict[str, Any]](
        event_id=f"{source}:{source_event_id}:{digest}",
        schema_version=schema_version,
        source=source,
        source_event_id=source_event_id,
        entitlement_id=None,
        instrument_id=None,
        observed_at=None,
        published_at=None,
        received_at=response.received_at,
        as_of=response.received_at,
        stale_after=response.received_at + timedelta(hours=24),
        quality_status=EnvelopeQuality.VALID,
        delay_status=DelayStatus.UNKNOWN,
        connection_epoch=None,
        rights=rights,
        payload_hash=payload_hash,
        payload=payload,
    )


class SecEdgarClient:
    """SEC submissions and Company Facts; no API key, declared contact required."""

    def __init__(
        self,
        *,
        user_agent: str,
        transport: HttpTransport | None = None,
        timeout_seconds: float = 15.0,
    ) -> None:
        if len(user_agent.strip()) < 8 or not (
            "@" in user_agent or "https://" in user_agent
        ):
            raise ValueError("SEC user_agent must identify the application and a contact")
        self._user_agent = user_agent.strip()
        self._transport = transport or UrllibTransport(allowed_hosts=frozenset({_SEC_HOST}))
        self._timeout = timeout_seconds

    def submissions(self, cik: str | int) -> DataEnvelope[dict[str, Any]]:
        return self._fetch(cik, family="submissions", schema="sec.edgar.submissions/1")

    def company_facts(self, cik: str | int) -> DataEnvelope[dict[str, Any]]:
        return self._fetch(cik, family="api/xbrl/companyfacts", schema="sec.edgar.company-facts/1")

    def _fetch(
        self, cik: str | int, *, family: str, schema: str
    ) -> DataEnvelope[dict[str, Any]]:
        cik_text = str(cik).strip()
        if not cik_text.isdigit() or not 1 <= len(cik_text) <= 10:
            raise ValueError("cik must contain one to ten digits")
        padded = cik_text.zfill(10)
        response = self._transport.send(
            HttpRequest(
                method="GET",
                url=f"https://{_SEC_HOST}/{family}/CIK{padded}.json",
                headers={"Accept": "application/json", "User-Agent": self._user_agent},
                timeout_seconds=self._timeout,
            )
        )
        raw = _json_payload(response)
        payload = {"cik": padded, "family": family, "response": raw}
        return _envelope(
            source="sec_edgar",
            schema_version=schema,
            source_event_id=f"CIK{padded}:{family.replace('/', '-')}",
            rights="R1_PUBLIC_FACT:SEC_EDGAR_POLICY_2026-08-28",
            response=response,
            payload=payload,
        )


class FredClient:
    """FRED observations with explicit ALFRED real-time periods."""

    def __init__(
        self,
        *,
        api_key: str,
        transport: HttpTransport | None = None,
        timeout_seconds: float = 15.0,
    ) -> None:
        if not api_key.strip():
            raise ValueError("FRED api_key is required")
        self._api_key = api_key.strip()
        self._transport = transport or UrllibTransport(allowed_hosts=frozenset({_FRED_HOST}))
        self._timeout = timeout_seconds

    def observations(
        self,
        series_id: str,
        *,
        realtime_start: date | None = None,
        realtime_end: date | None = None,
        observation_start: date | None = None,
        observation_end: date | None = None,
    ) -> DataEnvelope[dict[str, Any]]:
        series = _require_token(series_id, "series_id", _SERIES_ID)
        params = {
            "series_id": series,
            "api_key": self._api_key,
            "file_type": "json",
        }
        optional = {
            "realtime_start": _date_value(realtime_start),
            "realtime_end": _date_value(realtime_end),
            "observation_start": _date_value(observation_start),
            "observation_end": _date_value(observation_end),
        }
        params.update({key: value for key, value in optional.items() if value is not None})
        response = self._transport.send(
            HttpRequest(
                method="GET",
                url=f"https://{_FRED_HOST}/fred/series/observations?{urlencode(params)}",
                headers={"Accept": "application/json"},
                timeout_seconds=self._timeout,
            )
        )
        raw = _json_payload(response)
        request_metadata = {"series_id": series, **optional}
        payload = {"request": request_metadata, "response": raw}
        vintage = (
            f"{optional['realtime_start'] or 'current'}:"
            f"{optional['realtime_end'] or 'current'}"
        )
        return _envelope(
            source="fred_alfred",
            schema_version="fred.alfred.observations/1",
            source_event_id=f"{series}:{vintage}",
            rights="R1_PUBLIC_FACT:FRED_SERIES_TERMS_REVIEW_REQUIRED",
            response=response,
            payload=payload,
        )


@dataclass(frozen=True, slots=True)
class OpenFigiMapping:
    id_type: str
    id_value: str
    exchange_code: str | None = None
    mic_code: str | None = None
    currency: str | None = None

    def as_payload(self) -> dict[str, str]:
        if self.exchange_code is not None and self.mic_code is not None:
            raise ValueError("exchange_code and mic_code are mutually exclusive")
        payload = {
            "idType": _require_token(self.id_type, "id_type"),
            "idValue": self.id_value.strip(),
        }
        if not payload["idValue"]:
            raise ValueError("id_value is required")
        for key, value in (
            ("exchCode", self.exchange_code),
            ("micCode", self.mic_code),
            ("currency", self.currency),
        ):
            if value is not None:
                payload[key] = _require_token(value, key)
        return payload


class OpenFigiClient:
    """Identifier mapping only; ambiguous provider results stay as returned."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        transport: HttpTransport | None = None,
        timeout_seconds: float = 15.0,
    ) -> None:
        self._api_key = api_key.strip() if api_key and api_key.strip() else None
        self._transport = transport or UrllibTransport(
            allowed_hosts=frozenset({_OPENFIGI_HOST})
        )
        self._timeout = timeout_seconds

    def map(self, mappings: list[OpenFigiMapping]) -> DataEnvelope[dict[str, Any]]:
        if not 1 <= len(mappings) <= 10:
            raise ValueError("one to ten OpenFIGI mappings are required per bounded request")
        request_payload = [mapping.as_payload() for mapping in mappings]
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self._api_key is not None:
            headers["X-OPENFIGI-APIKEY"] = self._api_key
        response = self._transport.send(
            HttpRequest(
                method="POST",
                url=f"https://{_OPENFIGI_HOST}/v3/mapping",
                headers=headers,
                body=json.dumps(request_payload, separators=(",", ":")).encode("utf-8"),
                timeout_seconds=self._timeout,
            )
        )
        raw = _json_payload(response)
        payload = {"request": request_payload, "response": raw}
        return _envelope(
            source="openfigi",
            schema_version="openfigi.mapping/1",
            source_event_id=canonical_json_hash(request_payload).removeprefix("sha256:")[:32],
            rights="R0_REFERENCE:OPENFIGI_TERMS_REVIEW_REQUIRED",
            response=response,
            payload=payload,
        )


class EcbDataClient:
    """ECB Data API CSV retrieval; series selection remains caller-owned."""

    def __init__(
        self, *, transport: HttpTransport | None = None, timeout_seconds: float = 15.0
    ) -> None:
        self._transport = transport or UrllibTransport(allowed_hosts=frozenset({_ECB_HOST}))
        self._timeout = timeout_seconds

    def data(
        self,
        flow_ref: str,
        series_key: str,
        *,
        start_period: str | None = None,
        end_period: str | None = None,
    ) -> DataEnvelope[dict[str, Any]]:
        flow = _require_token(flow_ref, "flow_ref")
        key = _require_token(series_key, "series_key")
        params = {"format": "csvdata"}
        for name, value in (("startPeriod", start_period), ("endPeriod", end_period)):
            if value is not None:
                params[name] = _require_token(value, name, _PERIOD)
        response = self._transport.send(
            HttpRequest(
                method="GET",
                url=f"https://{_ECB_HOST}/service/data/{flow}/{key}?{urlencode(params)}",
                headers={"Accept": "text/csv"},
                timeout_seconds=self._timeout,
            )
        )
        payload = {
            "request": {"flow_ref": flow, "series_key": key, **params},
            "csv": _csv_payload(response),
        }
        return _envelope(
            source="ecb_data_portal",
            schema_version="ecb.data.csv/1",
            source_event_id=f"{flow}:{key}:{start_period or 'first'}:{end_period or 'latest'}",
            rights="R1_PUBLIC_FACT:ECB_DATA_TERMS_REVIEW_REQUIRED",
            response=response,
            payload=payload,
        )


class SnbDataClient:
    """SNB Data Portal cube CSV retrieval; no scraping and no UI automation."""

    def __init__(
        self, *, transport: HttpTransport | None = None, timeout_seconds: float = 15.0
    ) -> None:
        self._transport = transport or UrllibTransport(allowed_hosts=frozenset({_SNB_HOST}))
        self._timeout = timeout_seconds

    def cube(self, cube_id: str, *, language: str = "en") -> DataEnvelope[dict[str, Any]]:
        cube = _require_token(cube_id, "cube_id")
        if language not in {"de", "en", "fr", "it"}:
            raise ValueError("language must be one of de, en, fr or it")
        response = self._transport.send(
            HttpRequest(
                method="GET",
                url=f"https://{_SNB_HOST}/api/cube/{cube}/data/csv/{language}",
                headers={"Accept": "text/csv"},
                timeout_seconds=self._timeout,
            )
        )
        payload = {
            "request": {"cube_id": cube, "language": language},
            "csv": _csv_payload(response),
        }
        return _envelope(
            source="snb_data_portal",
            schema_version="snb.cube.csv/1",
            source_event_id=f"{cube}:{language}",
            rights="R1_PUBLIC_FACT:SNB_DATA_TERMS_REVIEW_REQUIRED",
            response=response,
            payload=payload,
        )
