"""``redact_error`` / ``format_last_error``: nothing payload-like survives.

All fixture strings are SYNTHETIC — no real secret, DSN or market payload.
"""

from __future__ import annotations

import pytest

from vertex_persistence.errors import ValidationFailedError
from vertex_persistence.redaction import REDACTED, format_last_error, redact_error


def test_plain_technical_message_passes_through() -> None:
    assert redact_error("connection refused by peer") == "connection refused by peer"


def test_quoted_values_are_redacted() -> None:
    out = redact_error("duplicate key value 'evt-42' violates \"uq_synthetic\"")
    assert "evt-42" not in out
    assert "uq_synthetic" not in out
    assert REDACTED in out


def test_key_value_pairs_are_redacted() -> None:
    out = redact_error("password=SYNTH cookie=SYNTH account=SYNTH-123")
    assert "SYNTH" not in out
    assert out.count(REDACTED) == 3
    assert out.startswith("password=")  # the key survives, its value never


def test_long_digit_runs_are_redacted() -> None:
    out = redact_error("failed for id 1234567890 after 3 tries")
    assert "1234567890" not in out
    assert " 3 " in out  # short technical counters stay readable


def test_sql_statement_and_parameters_tail_is_cut() -> None:
    message = (
        "(errors.UniqueViolation) boom "
        "[SQL: INSERT INTO observations (payload) VALUES (%(payload)s)] "
        "[parameters: {'payload': 'SYNTH-PARAM'}]"
    )
    out = redact_error(message)
    assert "INSERT INTO" not in out
    assert "SYNTH-PARAM" not in out
    assert out.startswith("(errors.UniqueViolation) boom")


def test_message_truncated_to_200_chars() -> None:
    assert len(redact_error("x" * 1000)) <= 200


def test_non_string_message_rejected() -> None:
    with pytest.raises(ValidationFailedError):
        redact_error(None)  # type: ignore[arg-type]


def test_format_last_error_shape_is_code_type_message() -> None:
    assert format_last_error("HANDLER_ERROR", ValueError("boom")) == (
        "HANDLER_ERROR:ValueError: boom"
    )


def test_format_last_error_without_message_is_code_type_only() -> None:
    assert format_last_error("HANDLER_ERROR", ValueError()) == "HANDLER_ERROR:ValueError"


def test_format_last_error_redacts_the_exception_message() -> None:
    error = format_last_error("HANDLER_ERROR", RuntimeError("token='SYNTH' account=SYNTH-1"))
    assert error.startswith("HANDLER_ERROR:RuntimeError")
    assert "SYNTH" not in error


def test_format_last_error_rejects_non_canonical_code() -> None:
    for bad_code in ("", "lower_case", "HAS SPACE", "X" * 65, "INJ'ECT", "1LEADING"):
        with pytest.raises(ValidationFailedError):
            format_last_error(bad_code, ValueError("x"))


def test_format_last_error_rejects_a_free_string_instead_of_exception() -> None:
    with pytest.raises(ValidationFailedError):
        format_last_error("HANDLER_ERROR", "free-form diagnostic")  # type: ignore[arg-type]
