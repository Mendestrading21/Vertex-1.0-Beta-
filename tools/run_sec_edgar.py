#!/usr/bin/env python3
"""Fetch, normalize and optionally persist one SEC EDGAR issuer snapshot.

The command is one-shot and read-only toward the provider.  Persistence is
explicit (``--persist``), append-only and uses Vertex's normal ingestion path.
Neither credentials, raw payloads nor a database URL are printed.

Usage::

    export VERTEX_SEC_USER_AGENT='Vertex research contact@example.com'
    python tools/run_sec_edgar.py --cik 320193 --instrument AAPL

    export VERTEX_DATABASE_URL='postgresql+psycopg://...'
    python tools/run_sec_edgar.py --cik 320193 --instrument AAPL --persist
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

REPO_ROOT = Path(__file__).resolve().parents[1]
for _package in (
    "packages/python/vertex_core/src",
    "packages/python/vertex_persistence/src",
    "apps/edge-official/src",
    "apps/worker/src",
):
    _path = str(REPO_ROOT / _package)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from vertex_edge_official import (  # noqa: E402
    OfficialSourceConfig,
    OfficialSourceError,
    SecEdgarClient,
    normalize_sec_edgar,
)
from vertex_persistence.dsn import database_name  # noqa: E402
from vertex_worker.ingest import ingest_envelope  # noqa: E402

__all__ = ["main"]

_EXAMPLE_MARKERS = ("CHANGE_ME", "change_me", "example", "placeholder")
_TEST_DATABASE_MARKERS = ("_test", "test_", "vertex_test", "vertex_e2e")


def _refuse(message: str) -> NoReturn:
    print(json.dumps({"status": "ERROR", "reason": message}, sort_keys=True), file=sys.stderr)
    raise SystemExit(2)


def _database_url() -> str:
    url = os.environ.get("VERTEX_DATABASE_URL", "").strip()
    if not url:
        _refuse("VERTEX_DATABASE_URL is required with --persist")
    if any(marker in url for marker in _EXAMPLE_MARKERS):
        _refuse("VERTEX_DATABASE_URL contains an example value")
    name = database_name(url)
    if any(marker in name for marker in _TEST_DATABASE_MARKERS):
        if os.environ.get("VERTEX_ALLOW_TEST_DB") != "1":
            _refuse("test-like database requires VERTEX_ALLOW_TEST_DB=1")
    return url


def _arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cik", required=True, help="SEC CIK, one to ten digits")
    parser.add_argument(
        "--instrument",
        required=True,
        help="explicit Vertex instrument mapping (for example AAPL)",
    )
    parser.add_argument(
        "--persist",
        action="store_true",
        help="persist normalized observations to VERTEX_DATABASE_URL",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _arguments(argv)
        config = OfficialSourceConfig.from_environ(os.environ)
        if config.sec_user_agent is None:
            _refuse("VERTEX_SEC_USER_AGENT is required and must contain a real contact")
        client = SecEdgarClient(
            user_agent=config.sec_user_agent,
            timeout_seconds=config.timeout_seconds,
        )
        submissions = client.submissions(args.cik)
        company_facts = client.company_facts(args.cik)
        normalized = normalize_sec_edgar(
            submissions,
            company_facts,
            instrument_ref=args.instrument,
        )

        inserted = 0
        duplicates = 0
        if args.persist:
            engine = create_engine(_database_url(), pool_pre_ping=True)
            try:
                with Session(engine) as session:
                    # Raw API bodies stay in memory only: the rights policy
                    # limits them to 24 h and Vertex has no raw-retention
                    # reaper yet. Normalized facts carry both raw event ids
                    # and hashes, so lineage survives without a hidden mirror.
                    for envelope in normalized:
                        result = ingest_envelope(session, envelope)
                        if result.inserted:
                            inserted += 1
                        else:
                            duplicates += 1
                    session.commit()
            finally:
                engine.dispose()

        print(
            json.dumps(
                {
                    "status": "AVAILABLE",
                    "source": "sec_edgar",
                    "cik": str(args.cik).zfill(10),
                    "instrument": args.instrument,
                    "raw_observations": 2,
                    "normalized_observations": len(normalized),
                    "persisted": bool(args.persist),
                    "inserted": inserted if args.persist else None,
                    "duplicates": duplicates if args.persist else None,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    except OfficialSourceError as exc:
        print(
            json.dumps({"status": "ERROR", "reason": str(exc)}, sort_keys=True),
            file=sys.stderr,
        )
        return 2
    except ValueError as exc:
        print(
            json.dumps({"status": "ERROR", "reason": str(exc)}, sort_keys=True),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
