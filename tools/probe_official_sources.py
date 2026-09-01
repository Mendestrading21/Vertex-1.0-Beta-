#!/usr/bin/env python3
"""Probe one official source without logging credentials or raw provider data.

With no ``--live`` flag, this command only validates local configuration. Live
mode needs one explicitly selected source and its bounded reference query. The
output contains envelope metadata, never the response payload.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from vertex_core.contracts import DataEnvelope
from vertex_edge_official import (
    EcbDataClient,
    FredClient,
    OfficialSourceConfig,
    OfficialSourceError,
    OpenFigiClient,
    OpenFigiMapping,
    SecEdgarClient,
    SnbDataClient,
)


@dataclass(frozen=True, slots=True)
class Arguments:
    live: bool
    source: str | None
    cik: str | None
    series_id: str | None
    realtime_start: date | None
    realtime_end: date | None
    id_type: str | None
    id_value: str | None
    exchange_code: str | None
    flow_ref: str | None
    series_key: str | None
    start_period: str | None
    end_period: str | None
    cube_id: str | None
    language: str


def _date(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD") from None


def parse_args(argv: Sequence[str] | None = None) -> Arguments:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="perform the bounded network probe")
    parser.add_argument(
        "--source",
        choices=("sec-submissions", "sec-company-facts", "fred", "openfigi", "ecb", "snb"),
    )
    parser.add_argument("--cik")
    parser.add_argument("--series-id")
    parser.add_argument("--realtime-start", type=_date)
    parser.add_argument("--realtime-end", type=_date)
    parser.add_argument("--id-type")
    parser.add_argument("--id-value")
    parser.add_argument("--exchange-code")
    parser.add_argument("--flow-ref")
    parser.add_argument("--series-key")
    parser.add_argument("--start-period")
    parser.add_argument("--end-period")
    parser.add_argument("--cube-id")
    parser.add_argument("--language", choices=("de", "en", "fr", "it"), default="en")
    namespace = parser.parse_args(argv)
    return Arguments(**vars(namespace))


def _required(value: str | None, flag: str) -> str:
    if value is None or not value.strip():
        raise ValueError(f"{flag} is required for this source")
    return value.strip()


def _receipt(envelope: DataEnvelope[Any]) -> dict[str, Any]:
    return {
        "status": "AVAILABLE",
        "source": envelope.source,
        "schema_version": envelope.schema_version,
        "source_event_id": envelope.source_event_id,
        "received_at": envelope.received_at.isoformat(),
        "stale_after": envelope.stale_after.isoformat(),
        "quality_status": envelope.quality_status.value,
        "delay_status": envelope.delay_status.value,
        "rights": envelope.rights,
        "payload_hash": envelope.payload_hash,
    }


def run_live(args: Arguments, config: OfficialSourceConfig) -> dict[str, Any]:
    timeout = config.timeout_seconds
    if args.source in {"sec-submissions", "sec-company-facts"}:
        if config.sec_user_agent is None:
            raise ValueError("VERTEX_SEC_USER_AGENT is required")
        client = SecEdgarClient(user_agent=config.sec_user_agent, timeout_seconds=timeout)
        cik = _required(args.cik, "--cik")
        envelope = (
            client.submissions(cik)
            if args.source == "sec-submissions"
            else client.company_facts(cik)
        )
        return _receipt(envelope)
    if args.source == "fred":
        if config.fred_api_key is None:
            raise ValueError("VERTEX_FRED_API_KEY is required")
        envelope = FredClient(
            api_key=config.fred_api_key, timeout_seconds=timeout
        ).observations(
            _required(args.series_id, "--series-id"),
            realtime_start=args.realtime_start,
            realtime_end=args.realtime_end,
        )
        return _receipt(envelope)
    if args.source == "openfigi":
        mapping = OpenFigiMapping(
            id_type=_required(args.id_type, "--id-type"),
            id_value=_required(args.id_value, "--id-value"),
            exchange_code=args.exchange_code,
        )
        return _receipt(
            OpenFigiClient(
                api_key=config.openfigi_api_key, timeout_seconds=timeout
            ).map([mapping])
        )
    if args.source == "ecb":
        return _receipt(
            EcbDataClient(timeout_seconds=timeout).data(
                _required(args.flow_ref, "--flow-ref"),
                _required(args.series_key, "--series-key"),
                start_period=args.start_period,
                end_period=args.end_period,
            )
        )
    if args.source == "snb":
        return _receipt(
            SnbDataClient(timeout_seconds=timeout).cube(
                _required(args.cube_id, "--cube-id"), language=args.language
            )
        )
    raise ValueError("--source is required with --live")


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        config = OfficialSourceConfig.from_environ(os.environ)
        result = run_live(args, config) if args.live else config.capability_summary()
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (OfficialSourceError, ValueError) as exc:
        print(
            json.dumps(
                {"status": "ERROR", "reason": str(exc)},
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
