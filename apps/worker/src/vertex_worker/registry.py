"""Topic-to-handler registry of the outbox worker.

One handler per topic, registered explicitly — an unknown topic is never
claimed and a duplicate registration is refused (fail-closed, no silent
override of an authority).
"""

from __future__ import annotations

from typing import Callable, Dict, Optional

from sqlalchemy.orm import Session

from vertex_persistence.repository.outbox import ClaimedOutboxMessage

__all__ = ["Handler", "HandlerRegistry"]


Handler = Callable[[Session, ClaimedOutboxMessage], None]
"""A topic handler: runs inside the ack transaction; raising fails the message."""


class HandlerRegistry:
    """Explicit, immutable-by-convention mapping of outbox topics to handlers."""

    def __init__(self) -> None:
        self._handlers: Dict[str, Handler] = {}

    def register(self, topic: str, handler: Handler) -> None:
        """Register ``handler`` for ``topic``; duplicates are refused."""
        if not isinstance(topic, str) or not topic.strip():
            raise ValueError("topic: non-empty string required")
        if not callable(handler):
            raise TypeError(f"handler: expected callable, got {type(handler).__name__}")
        if topic in self._handlers:
            raise ValueError(f"topic {topic!r} already has a registered handler")
        self._handlers[topic] = handler

    @property
    def topics(self) -> tuple[str, ...]:
        """Registered topics in deterministic (sorted) order."""
        return tuple(sorted(self._handlers))

    def get(self, topic: str) -> Optional[Handler]:
        """Return the handler for ``topic``, or ``None`` when unregistered."""
        return self._handlers.get(topic)
