"""Unit tests of the pure CSV codec of the portfolio journal (SYNTHETIC data).

Covers the formula-injection guard, the export/import cell round-trip, the
size and row budgets, per-row validation and the integrity hash contract.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from portfolio_fakes import make_entry
from vertex_api.portfolio import (
    EXPORT_SCHEMA_VERSION,
    MAX_IMPORT_ROWS,
    CsvImportError,
    import_row_hash,
    neutralize_csv_cell,
    parse_import_csv,
    render_export_csv,
    validate_import_fields,
)

NOW = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("=SUM(A1)", "'=SUM(A1)"),
        ("+1234", "'+1234"),
        ("-100.5", "'-100.5"),
        ("@cmd", "'@cmd"),
        ("plain text", "plain text"),
        ("", ""),
        ("SYN-A", "SYN-A"),
    ],
)
def test_formula_prefixes_are_neutralized(raw: str, expected: str) -> None:
    assert neutralize_csv_cell(raw) == expected


def test_export_then_import_round_trips_cells() -> None:
    entries = [
        make_entry(1, note="=HYPERLINK(evil)"),
        make_entry(2, kind="WITHDRAWAL", ticker=None, quantity=None, price=None, amount="-250.75"),
    ]
    exported = render_export_csv(entries)
    assert exported.startswith(f"# {EXPORT_SCHEMA_VERSION}\n")

    # The import parser maps columns by name, skips the version stamp and
    # strips the neutralizing apostrophe: a Vertex export re-imports as-is.
    valid, invalid = parse_import_csv(exported, now=NOW)
    assert invalid == []
    assert len(valid) == 2
    assert valid[0].amount == Decimal("-1000")
    assert valid[0].note == "=HYPERLINK(evil)"
    assert valid[1].kind == "WITHDRAWAL"
    assert valid[1].amount == Decimal("-250.75")


def test_import_size_budget_is_enforced() -> None:
    with pytest.raises(CsvImportError) as exc:
        parse_import_csv("x" * (256 * 1024 + 1), now=NOW)
    assert exc.value.code == "CSV_TOO_LARGE"


def test_import_row_budget_is_enforced() -> None:
    header = "kind,ticker,quantity,price,amount,currency,fees,effective_at,note"
    body = "\n".join(
        ["DIVIDEND,,,,1,SYN,0,2026-08-20T10:00:00+00:00,"] * (MAX_IMPORT_ROWS + 1)
    )
    with pytest.raises(CsvImportError) as exc:
        parse_import_csv(f"{header}\n{body}", now=NOW)
    assert exc.value.code == "CSV_TOO_MANY_ROWS"


def test_per_row_errors_are_reported_with_codes() -> None:
    header = "kind,ticker,quantity,price,amount,currency,fees,effective_at,note"
    rows = "\n".join(
        [
            header,
            "SELL_RECORDED,SYN-A,5,101,505,SYN,0,2026-08-20T10:00:00+00:00,ok",
            "NOPE,SYN-A,5,101,505,SYN,0,2026-08-20T10:00:00+00:00,bad kind",
            "BUY_RECORDED,SYN-A,5,101,-505,syn,0,2026-08-20T10:00:00+00:00,bad currency",
            "BUY_RECORDED,SYN-A,5,101,-505,SYN,0,2026-08-20T10:00:00,naive time",
            "BUY_RECORDED,SYN-A,5,101,-505,SYN,0,2099-01-01T00:00:00+00:00,future",
            "BUY_RECORDED,SYN-A,5,101,-505,SYN,-1,2026-08-20T10:00:00+00:00,neg fees",
            "too,few",
        ]
    )
    valid, invalid = parse_import_csv(rows, now=NOW)
    assert [row.row_number for row in valid] == [1]
    errors = {entry.row_number: entry.errors for entry in invalid}
    assert errors[2] == ("UNKNOWN_KIND",)
    assert errors[3] == ("INVALID_CURRENCY",)
    assert errors[4] == ("INVALID_EFFECTIVE_AT",)
    assert errors[5] == ("EFFECTIVE_AT_IN_FUTURE",)
    assert errors[6] == ("INVALID_FEES",)
    assert errors[7] == ("WRONG_COLUMN_COUNT",)


def test_row_hash_is_deterministic_and_field_sensitive() -> None:
    fields = {
        "kind": "BUY_RECORDED",
        "ticker": "SYN-A",
        "quantity": "10",
        "price": "100",
        "amount": "-1000",
        "currency": "SYN",
        "fees": "0",
        "effective_at": "2026-08-20T10:00:00+00:00",
        "note": "",
    }
    first = import_row_hash(fields)
    assert first == import_row_hash(dict(fields))
    assert first.startswith("sha256:")
    altered = dict(fields, amount="-1000.01")
    assert import_row_hash(altered) != first


def test_validate_import_fields_replays_identically() -> None:
    fields = {
        "kind": "BUY_RECORDED",
        "ticker": "SYN-A",
        "quantity": "10",
        "price": "100",
        "amount": "-1000",
        "currency": "SYN",
        "fees": "0",
        "effective_at": "2026-08-20T10:00:00+00:00",
        "note": "n",
    }
    row1, errors1 = validate_import_fields(fields, row_number=1, now=NOW)
    row2, errors2 = validate_import_fields(fields, row_number=1, now=NOW)
    assert errors1 == errors2 == []
    assert row1 is not None and row2 is not None
    assert row1.row_hash == row2.row_hash
    assert row1.canonical_fields == row2.canonical_fields
