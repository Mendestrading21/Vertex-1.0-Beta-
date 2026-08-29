"""Typed errors of the worker package (fail-closed, canonical error codes)."""

from __future__ import annotations

import re

__all__ = [
    "WorkerError",
    "HandlerError",
    "UnregisteredTopicError",
    "GENERIC_HANDLER_CODE",
]

_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")

GENERIC_HANDLER_CODE = "HANDLER_EXCEPTION"
"""Outbox error code recorded for handler exceptions without their own code."""


class WorkerError(Exception):
    """Base class of every typed error raised by ``vertex_worker``."""


class HandlerError(WorkerError):
    """A handler failed with a canonical error code.

    ``code`` is the uppercase machine token recorded (redacted) in
    ``outbox.last_error`` by ``fail_outbox``. A non-canonical code is
    rejected at construction time — fail-closed, never at failure time.
    """

    def __init__(self, message: str, *, code: str) -> None:
        if not isinstance(code, str) or not _CODE_RE.match(code):
            raise ValueError(
                "code: expected a canonical uppercase error code "
                f"(pattern {_CODE_RE.pattern}), got {code!r}"
            )
        super().__init__(message)
        self.code = code


class UnregisteredTopicError(HandlerError):
    """A claimed message carries a topic no handler is registered for.

    Defensive: the runner only claims registered topics, so reaching this
    error means the registry and the claim filter diverged — the message is
    failed with an explicit code instead of being silently dropped.
    """

    def __init__(self, topic: str) -> None:
        super().__init__(
            f"no handler registered for topic {topic!r}", code="UNREGISTERED_TOPIC"
        )
