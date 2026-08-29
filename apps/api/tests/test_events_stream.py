"""GET /api/v1/events/stream: signal-only SSE over snapshot head versions.

The stream may carry ONLY two frame kinds: ``ping`` (empty JSON object) and
``snapshot`` (exactly ``{"resource": ..., "version": ...}``). No business
field ever crosses this channel. Timings are short and injected — the tests
read a bounded number of events and close cleanly, never relying on the
production 1s/15s intervals.
"""

from __future__ import annotations

import asyncio
import json
import socket
import threading
import time
from typing import Iterator, Optional

import httpx
import pytest
import uvicorn
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snapshot_fakes import synthetic_session
from vertex_api.auth import AUTH_REQUIRED, require_session
from vertex_api.events import (
    StreamSettings,
    format_sse_event,
    get_stream_settings,
    snapshot_event_stream,
)
from vertex_api.snapshot_reader import get_snapshot_reader

FAST = StreamSettings(
    poll_interval_seconds=0.005, coalesce_seconds=0.005, ping_interval_seconds=0.02
)


class ScriptedHeadReader:
    """SYNTHETIC reader: head versions are mutated by the test itself."""

    def __init__(self) -> None:
        self.versions: dict[tuple[str, str], Optional[int]] = {
            ("attention", "global"): None,
            ("capabilities", "global"): None,
            ("markets_overview", "global"): None,
        }
        self.polls = 0

    def current(self, *, kind: str, key: str):  # pragma: no cover - not used here
        raise AssertionError("the stream must never load snapshot content")

    def head_version(self, *, kind: str, key: str) -> Optional[int]:
        self.polls += 1
        return self.versions[(kind, key)]

    def heads_for_kind(self, *, kind: str) -> dict[str, int]:
        return {
            key: version
            for (head_kind, key), version in self.versions.items()
            if head_kind == kind and version is not None
        }

    def ping(self) -> bool:  # pragma: no cover - not used here
        return True


def parse_frames(raw: str) -> list[tuple[str, dict]]:
    """Split concatenated SSE frames into (event, data) pairs."""
    frames: list[tuple[str, dict]] = []
    for block in raw.split("\n\n"):
        if not block.strip():
            continue
        lines = block.split("\n")
        assert lines[0].startswith("event: ")
        assert lines[1].startswith("data: ")
        frames.append((lines[0][len("event: "):], json.loads(lines[1][len("data: "):])))
    return frames


async def collect_events(
    reader: ScriptedHeadReader,
    *,
    bump_to: int,
    stop_after_snapshot_events: int,
    timeout: float = 5.0,
) -> list[tuple[str, dict]]:
    """Drive the generator: after the first ping, bump a head and read on."""

    async def run() -> list[tuple[str, dict]]:
        frames: list[tuple[str, dict]] = []
        snapshot_events = 0
        stream = snapshot_event_stream(reader, FAST)
        async for frame in stream:
            frames.extend(parse_frames(frame))
            event = frames[-1][0]
            if event == "ping" and reader.versions[("attention", "global")] is None:
                # Baseline observed; publish versions 1..bump_to in one burst.
                reader.versions[("attention", "global")] = bump_to
            if event == "snapshot":
                snapshot_events += 1
                if snapshot_events >= stop_after_snapshot_events:
                    break
        await stream.aclose()
        return frames

    return await asyncio.wait_for(run(), timeout=timeout)


def test_without_session_is_generic_401(client: TestClient) -> None:
    response = client.get("/api/v1/events/stream")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == AUTH_REQUIRED


def test_burst_is_coalesced_into_one_signal_with_latest_version() -> None:
    reader = ScriptedHeadReader()
    frames = asyncio.run(
        collect_events(reader, bump_to=3, stop_after_snapshot_events=1)
    )
    snapshot_frames = [data for event, data in frames if event == "snapshot"]
    # One coalesced signal for the whole burst, carrying the LATEST version.
    assert snapshot_frames == [{"resource": "attention/global", "version": 3}]


def test_stream_is_signal_only_no_business_field() -> None:
    reader = ScriptedHeadReader()
    frames = asyncio.run(
        collect_events(reader, bump_to=2, stop_after_snapshot_events=1)
    )
    assert frames, "at least the initial ping must be emitted"
    for event, data in frames:
        assert event in {"ping", "snapshot"}
        if event == "ping":
            assert data == {}
        else:
            assert set(data) == {"resource", "version"}
            assert isinstance(data["version"], int)
            assert data["resource"] in {"attention/global", "capabilities/global"}


def test_pings_keep_flowing_without_any_change() -> None:
    reader = ScriptedHeadReader()

    async def read_pings() -> list[tuple[str, dict]]:
        frames: list[tuple[str, dict]] = []
        stream = snapshot_event_stream(reader, FAST)
        async for frame in stream:
            frames.extend(parse_frames(frame))
            if len(frames) >= 3:
                break
        await stream.aclose()
        return frames

    frames = asyncio.run(asyncio.wait_for(read_pings(), timeout=5.0))
    assert [event for event, _ in frames] == ["ping", "ping", "ping"]


def test_option_chain_keys_are_watched_by_kind_prefix() -> None:
    """``option_chain/*``: a key that APPEARS while streaming is signalled.

    Documented semantics: the stream watches the whole ``option_chain`` kind
    (every published key), so a brand-new underlying — never listed anywhere
    in the API — starts signalling as soon as the worker publishes its head.
    """
    reader = ScriptedHeadReader()

    async def run() -> list[tuple[str, dict]]:
        frames: list[tuple[str, dict]] = []
        stream = snapshot_event_stream(reader, FAST)
        async for frame in stream:
            frames.extend(parse_frames(frame))
            event = frames[-1][0]
            if event == "ping" and ("option_chain", "SYN-TECH-01") not in reader.versions:
                reader.versions[("option_chain", "SYN-TECH-01")] = 5
            if event == "snapshot":
                break
        await stream.aclose()
        return frames

    frames = asyncio.run(asyncio.wait_for(run(), timeout=5.0))
    snapshot_frames = [data for event, data in frames if event == "snapshot"]
    assert snapshot_frames == [
        {"resource": "option_chain/SYN-TECH-01", "version": 5}
    ]


def test_format_sse_event_is_canonical() -> None:
    frame = format_sse_event("snapshot", {"version": 2, "resource": "attention/global"})
    assert frame == 'event: snapshot\ndata: {"resource":"attention/global","version":2}\n\n'


@pytest.fixture()
def stream_state() -> ScriptedHeadReader:
    return ScriptedHeadReader()


def _free_loopback_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@pytest.fixture()
def stream_server_url(app: FastAPI, stream_state: ScriptedHeadReader) -> Iterator[str]:
    """Real loopback HTTP server for TRUE progressive streaming.

    The in-process test transports (Starlette TestClient, httpx
    ASGITransport) buffer the whole response body, which an endless SSE
    stream never provides — so this one test drives uvicorn on an ephemeral
    127.0.0.1 port (loopback only, never a public bind) with the SAME
    dependency overrides and short injected timings.
    """
    app.dependency_overrides[require_session] = synthetic_session
    app.dependency_overrides[get_snapshot_reader] = lambda: stream_state
    app.dependency_overrides[get_stream_settings] = lambda: FAST
    port = _free_loopback_port()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10.0
    while not server.started:
        if time.monotonic() > deadline or not thread.is_alive():
            raise RuntimeError("loopback SSE test server failed to start")
        time.sleep(0.01)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=10.0)
    app.dependency_overrides.clear()


def test_http_stream_reads_events_then_closes_cleanly(
    stream_server_url: str, stream_state: ScriptedHeadReader
) -> None:
    """httpx streaming client: a few frames are read, then the client closes."""
    stream_state.versions[("capabilities", "global")] = 1

    events: list[tuple[str, str]] = []
    timeout = httpx.Timeout(5.0, read=5.0)
    with httpx.Client(timeout=timeout) as http_client:
        with http_client.stream(
            "GET", f"{stream_server_url}/api/v1/events/stream"
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            current_event = None
            for line in response.iter_lines():
                if line.startswith("event: "):
                    current_event = line[len("event: "):]
                elif line.startswith("data: ") and current_event is not None:
                    events.append((current_event, line[len("data: "):]))
                    if current_event == "ping":
                        # Baseline seen: move one watched head.
                        stream_state.versions[("attention", "global")] = 7
                    if current_event == "snapshot":
                        break
            # Closing the response context aborts the endless stream cleanly.

    assert events[0][0] == "ping"
    snapshot_payloads = [json.loads(data) for event, data in events if event == "snapshot"]
    assert snapshot_payloads == [{"resource": "attention/global", "version": 7}]
