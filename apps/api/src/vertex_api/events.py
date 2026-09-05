"""Signal-only Server-Sent Events stream over snapshot head versions.

``GET /api/v1/events/stream`` never carries business data: each ``snapshot``
event is exactly ``{"resource": "<kind>/<key>", "version": <int>}`` — a
signal that the head of a watched snapshot moved, upon which the client
refetches through the REST endpoints. Periodic ``ping`` events (empty JSON
object) keep the connection alive.

Implementation: the head pointer of every watched snapshot is POLLED in the
database (interval injectable, 1s by default; the blocking read runs in the
threadpool, never on the event loop). A detected change is COALESCED for a
short window (50ms by default) and re-read, so a burst of publications emits
one event carrying the latest version instead of one event per version.

The baseline at connect is silent: the stream emits an initial ``ping`` and
then only CHANGES — a client learns the current state through REST, not
through this channel.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass

from starlette.concurrency import run_in_threadpool

from vertex_api.snapshot_reader import SnapshotReader

__all__ = [
    "WATCHED_SNAPSHOTS",
    "WATCHED_SNAPSHOT_KINDS",
    "StreamSettings",
    "format_sse_event",
    "get_stream_settings",
    "snapshot_event_stream",
]

WATCHED_SNAPSHOTS: tuple[tuple[str, str], ...] = (
    ("attention", "global"),
    ("calendar", "global"),
    ("capabilities", "global"),
    ("markets_overview", "global"),
    ("opportunities", "global"),
    # LOT S4: the worker publishes the risk matrix under this single fixed
    # key (``vertex_worker.risk``); relayed by ``GET /api/v1/risk/matrix``.
    ("risk_matrix", "global"),
)
"""(kind, key) heads whose version changes are signalled on the stream."""

WATCHED_SNAPSHOT_KINDS: tuple[str, ...] = (
    "analysis",
    "option_chain",
    "performance",
    "portfolio_valuation",
    "review_queue",
    "sec_fundamentals",
)
"""Kinds watched BY PREFIX: every published key of these kinds is signalled
as ``<kind>/<key>`` (e.g. ``option_chain/SYN-TECH-01``,
``portfolio_valuation/1``, ``performance/1``, ``review_queue/global``).

Documented semantics choice: rather than hard-coding the current list of
synthetic underlyings, the stream polls the head table for ALL keys of a
watched kind (``SnapshotReader.heads_for_kind``) — ``option_chain/*``. A new
underlying published by the worker therefore starts signalling without any
API change; a key never published emits nothing (absence stays silent, it is
never invented). A key appearing for the first time during a connection is
signalled as a change."""


@dataclass(frozen=True)
class StreamSettings:
    """Injectable timing of the stream (tests use short deterministic values)."""

    poll_interval_seconds: float = 1.0
    coalesce_seconds: float = 0.05
    ping_interval_seconds: float = 15.0

    def __post_init__(self) -> None:
        for name in ("poll_interval_seconds", "coalesce_seconds", "ping_interval_seconds"):
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or value <= 0:
                raise ValueError(f"{name}: strictly positive number required")


def get_stream_settings() -> StreamSettings:
    """FastAPI dependency: production timings (tests override with short ones)."""
    return StreamSettings()


def format_sse_event(event: str, data: dict[str, object]) -> str:
    """One SSE frame: named event, single canonical JSON data line."""
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n"


def _resource_name(kind: str, key: str) -> str:
    return f"{kind}/{key}"


async def _poll_versions(reader: SnapshotReader) -> dict[str, int | None]:
    versions: dict[str, int | None] = {}
    for kind, key in WATCHED_SNAPSHOTS:
        versions[_resource_name(kind, key)] = await run_in_threadpool(
            reader.head_version, kind=kind, key=key
        )
    for kind in WATCHED_SNAPSHOT_KINDS:
        heads = await run_in_threadpool(reader.heads_for_kind, kind=kind)
        for key in sorted(heads):
            versions[_resource_name(kind, key)] = heads[key]
    return versions


async def snapshot_event_stream(
    reader: SnapshotReader, settings: StreamSettings
) -> AsyncIterator[str]:
    """Yield SSE frames forever; the caller (client disconnect) ends the loop.

    Deterministic contract: only ``ping`` frames and ``snapshot`` frames of
    the exact shape ``{"resource": ..., "version": ...}`` are ever emitted —
    no snapshot content, no market data, no business field crosses this
    stream.
    """
    last = await _poll_versions(reader)
    yield format_sse_event("ping", {})
    last_ping = time.monotonic()

    while True:
        await asyncio.sleep(settings.poll_interval_seconds)
        current = await _poll_versions(reader)
        changed = [
            resource
            for resource, version in current.items()
            if version is not None and version != last.get(resource)
        ]
        if changed:
            # Coalescence: let an in-flight burst land, then re-read once so
            # a single event carries the latest version per resource.
            await asyncio.sleep(settings.coalesce_seconds)
            current = await _poll_versions(reader)
            for resource in sorted(changed):
                version = current.get(resource)
                if version is not None and version != last.get(resource):
                    yield format_sse_event(
                        "snapshot", {"resource": resource, "version": version}
                    )
        last = current
        now = time.monotonic()
        if now - last_ping >= settings.ping_interval_seconds:
            yield format_sse_event("ping", {})
            last_ping = now
