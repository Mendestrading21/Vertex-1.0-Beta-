"""Deterministic exponential backoff for outbox retries.

Pure function, no clock, no randomness: single-host deployment (ADR-006) does
not need jitter to avoid thundering herds, and determinism keeps the retry
schedule testable. Delays are whole seconds:

``delay(attempts) = min(cap_seconds, base_seconds * factor ** (attempts - 1))``

with the defaults 5 s, 10 s, 20 s, 40 s, 80 s, 160 s, 320 s for attempts 1..7;
attempt 8 (``DEFAULT_MAX_ATTEMPTS``) marks the message ``DEAD`` instead of
scheduling another retry.
"""

from __future__ import annotations

from vertex_persistence.errors import ValidationFailedError

__all__ = [
    "DEFAULT_BASE_SECONDS",
    "DEFAULT_CAP_SECONDS",
    "DEFAULT_FACTOR",
    "DEFAULT_MAX_ATTEMPTS",
    "compute_backoff_seconds",
]

DEFAULT_MAX_ATTEMPTS = 8
DEFAULT_BASE_SECONDS = 5
DEFAULT_FACTOR = 2
DEFAULT_CAP_SECONDS = 3600


def compute_backoff_seconds(
    attempts: int,
    *,
    base_seconds: int = DEFAULT_BASE_SECONDS,
    factor: int = DEFAULT_FACTOR,
    cap_seconds: int = DEFAULT_CAP_SECONDS,
) -> int:
    """Return the retry delay in seconds after ``attempts`` failed attempts.

    ``attempts`` counts completed failed attempts and must be >= 1. All
    parameters are strictly validated; invalid input raises
    :class:`ValidationFailedError` (fail-closed, no clamping of bad input).
    """
    for label, value in (
        ("attempts", attempts),
        ("base_seconds", base_seconds),
        ("factor", factor),
        ("cap_seconds", cap_seconds),
    ):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValidationFailedError(f"{label} must be an int, got {type(value).__name__}")
    if attempts < 1:
        raise ValidationFailedError(f"attempts must be >= 1, got {attempts}")
    if base_seconds < 1:
        raise ValidationFailedError(f"base_seconds must be >= 1, got {base_seconds}")
    if factor < 1:
        raise ValidationFailedError(f"factor must be >= 1, got {factor}")
    if cap_seconds < base_seconds:
        raise ValidationFailedError(
            f"cap_seconds ({cap_seconds}) must be >= base_seconds ({base_seconds})"
        )
    # Avoid huge intermediate powers: once the delay reaches the cap it stays there.
    delay = base_seconds
    for _ in range(attempts - 1):
        delay *= factor
        if delay >= cap_seconds:
            return cap_seconds
    return min(delay, cap_seconds)
