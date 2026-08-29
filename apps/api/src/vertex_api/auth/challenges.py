"""Server-side WebAuthn challenge store (in-memory, per process, bounded).

Documented design choice (LOT-09): challenges live in a bounded in-memory
store rather than a database table because

- a challenge is ephemeral by contract (120 s TTL, single use) and never a
  durable fact worth persisting;
- the Vertex One API is a single local process on loopback (ADR-009) — there
  is no second process that would need to share the store;
- losing the store on restart fails CLOSED: the pending ceremony's verify
  step simply gets a generic 401 and the client restarts the ceremony.

Properties enforced here:

- single use: ``consume`` pops the entry — a replayed ``flow_id`` finds
  nothing;
- purpose binding: a registration challenge can never satisfy a login
  verify and vice versa;
- TTL 120 s on an injected monotonic clock (testable without real time);
- bounded memory: at most ``max_entries`` pending challenges — when full,
  the oldest entry is evicted (fail-closed for that older ceremony).
"""

from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Literal, Optional

__all__ = ["CHALLENGE_TTL_SECONDS", "ChallengePurpose", "ChallengeStore"]

CHALLENGE_TTL_SECONDS = 120.0

ChallengePurpose = Literal["register", "login"]

_CHALLENGE_BYTES = 32
_FLOW_ID_BYTES = 16


@dataclass(frozen=True)
class _Entry:
    purpose: ChallengePurpose
    challenge: bytes
    expires_at_monotonic: float


@dataclass
class ChallengeStore:
    """Thread-safe bounded store of pending WebAuthn challenges."""

    ttl_seconds: float = CHALLENGE_TTL_SECONDS
    max_entries: int = 64
    clock: Callable[[], float] = time.monotonic
    _entries: dict[str, _Entry] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def issue(self, purpose: ChallengePurpose) -> tuple[str, bytes]:
        """Create and remember a fresh challenge; returns ``(flow_id, challenge)``."""
        flow_id = secrets.token_urlsafe(_FLOW_ID_BYTES)
        challenge = secrets.token_bytes(_CHALLENGE_BYTES)
        now = self.clock()
        with self._lock:
            self._evict_expired(now)
            while len(self._entries) >= self.max_entries:
                oldest = min(
                    self._entries, key=lambda key: self._entries[key].expires_at_monotonic
                )
                del self._entries[oldest]
            self._entries[flow_id] = _Entry(
                purpose=purpose,
                challenge=challenge,
                expires_at_monotonic=now + self.ttl_seconds,
            )
        return flow_id, challenge

    def consume(self, flow_id: str, purpose: ChallengePurpose) -> Optional[bytes]:
        """Pop the challenge for ``flow_id`` — single use, purpose-bound, TTL.

        Returns ``None`` (fail-closed) when the flow id is unknown, already
        consumed, expired, or was issued for the other purpose. A purpose
        mismatch still consumes the entry, so a mismatched probe cannot keep
        the challenge alive for a second try.
        """
        now = self.clock()
        with self._lock:
            self._evict_expired(now)
            entry = self._entries.pop(flow_id, None)
        if entry is None:
            return None
        if entry.purpose != purpose:
            return None
        return entry.challenge

    def _evict_expired(self, now: float) -> None:
        expired = [
            key for key, entry in self._entries.items() if entry.expires_at_monotonic <= now
        ]
        for key in expired:
            del self._entries[key]
