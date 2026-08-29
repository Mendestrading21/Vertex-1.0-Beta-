"""E2E worker process: the REAL WorkerRunner polling the test database.

Started by e2e/global.setup.ts alongside uvicorn so that ledger writes and
thesis revisions made THROUGH THE UI during the tests are actually processed
(valuation, performance and review-queue snapshots republished, then signaled
over SSE). Nothing is reimplemented: this is the production registry and
runner on a short poll interval. The DSN comes exclusively from
``VERTEX_TEST_DATABASE_URL`` (environment only, never a file).
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from vertex_worker.handlers import DEV_SYNTHETIC_CONFIG, build_registry
from vertex_worker.runner import WorkerRunner


def main() -> int:
    url = os.environ.get("VERTEX_TEST_DATABASE_URL")
    if not url:
        print("VERTEX_TEST_DATABASE_URL is not set. Aborting.", file=sys.stderr)
        return 2

    def clock() -> datetime:
        return datetime.now(timezone.utc)

    engine = create_engine(url)
    try:
        runner = WorkerRunner(
            session_factory=lambda: Session(engine),
            registry=build_registry(clock=clock, fusion_config=DEV_SYNTHETIC_CONFIG),
            poll_interval_seconds=0.2,
            clock=clock,
        )
        print("e2e worker: polling started", flush=True)
        runner.run()  # runs until SIGTERM (teardown) stops the process
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
