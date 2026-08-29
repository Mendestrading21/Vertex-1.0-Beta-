"""Unit tests of the deterministic outbox retry backoff."""

from __future__ import annotations

import pytest

from vertex_persistence.backoff import (
    DEFAULT_BASE_SECONDS,
    DEFAULT_CAP_SECONDS,
    DEFAULT_MAX_ATTEMPTS,
    compute_backoff_seconds,
)
from vertex_persistence.errors import ValidationFailedError


def test_default_schedule_is_exponential() -> None:
    assert [compute_backoff_seconds(n) for n in range(1, 8)] == [5, 10, 20, 40, 80, 160, 320]


def test_default_constants() -> None:
    assert DEFAULT_MAX_ATTEMPTS == 8
    assert DEFAULT_BASE_SECONDS == 5
    assert DEFAULT_CAP_SECONDS == 3600


def test_cap_is_applied() -> None:
    assert compute_backoff_seconds(11) == 3600  # 5 * 2**10 = 5120 > cap
    assert compute_backoff_seconds(100) == 3600  # no overflow on huge attempts
    assert compute_backoff_seconds(3, base_seconds=10, factor=10, cap_seconds=50) == 50


def test_custom_parameters() -> None:
    assert compute_backoff_seconds(1, base_seconds=2, factor=3, cap_seconds=100) == 2
    assert compute_backoff_seconds(2, base_seconds=2, factor=3, cap_seconds=100) == 6
    assert compute_backoff_seconds(4, base_seconds=2, factor=3, cap_seconds=100) == 54
    assert compute_backoff_seconds(5, base_seconds=2, factor=3, cap_seconds=100) == 100


def test_factor_one_is_constant_delay() -> None:
    assert compute_backoff_seconds(7, base_seconds=9, factor=1, cap_seconds=100) == 9


def test_deterministic_no_jitter() -> None:
    assert len({compute_backoff_seconds(4) for _ in range(50)}) == 1


@pytest.mark.parametrize("attempts", [0, -1, -100])
def test_non_positive_attempts_rejected(attempts: int) -> None:
    with pytest.raises(ValidationFailedError):
        compute_backoff_seconds(attempts)


@pytest.mark.parametrize("attempts", [1.0, "1", None, True])
def test_non_int_attempts_rejected(attempts: object) -> None:
    with pytest.raises(ValidationFailedError):
        compute_backoff_seconds(attempts)  # type: ignore[arg-type]


def test_invalid_parameters_rejected() -> None:
    with pytest.raises(ValidationFailedError):
        compute_backoff_seconds(1, base_seconds=0)
    with pytest.raises(ValidationFailedError):
        compute_backoff_seconds(1, factor=0)
    with pytest.raises(ValidationFailedError):
        compute_backoff_seconds(1, cap_seconds=4)  # cap below base
    with pytest.raises(ValidationFailedError):
        compute_backoff_seconds(1, base_seconds=2.5)  # type: ignore[arg-type]
