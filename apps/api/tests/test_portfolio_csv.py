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


# ---------------------------------------------------------------------------
# P1-4 — la magnitude d'un décimal déclaré est BORNÉE avant tout rendu
# ---------------------------------------------------------------------------
#
# `_parse_decimal` n'exigeait que `is_finite()`. Or `Decimal('1E+99999999')`
# EST fini : le seul plafond restant était la mémoire de la machine, et
# `_decimal_text` (`format(value, "f")`) matérialisait l'exposant en chiffres.
# Une requête de 26 Kio (500 lignes, sous le budget de 256 Kio) sortait ainsi
# 95 Mio de réponse — amplification x3566 mesurée.
#
# Trois vecteurs distincts produisent le même effet ; les bornes doivent les
# fermer tous les trois, pas seulement le premier :
#   1. exposant positif géant   `1E+200000`          -> 200 001 caractères
#   2. exposant négatif géant   `1E-200000`          -> 200 002 caractères
#   3. coefficient géant        `1.<200000 zéros>1`  -> 200 003 caractères
#
# Aucune assertion ci-dessous ne regarde la VALEUR refusée : le code d'erreur
# nomme le CHAMP, `ImportRowError.row_number` nomme la LIGNE.

CSV_HEADER = "kind,ticker,quantity,price,amount,currency,fees,effective_at,note"

# Vecteurs COURTS : le texte tient en dix caractères, seule la magnitude
# explose. Ils traversent `csv.reader` sans encombre et doivent donc obtenir
# un refus par LIGNE et par CHAMP.
COMPACT_AMPLIFYING_DECIMALS = [
    pytest.param("1E+200000", id="huge-positive-exponent"),
    pytest.param("-1E+200000", id="huge-negative-value"),
    pytest.param("1E-200000", id="huge-negative-exponent"),
    pytest.param("9E+99999999", id="near-decimal-limit"),
]

# Vecteurs LONGS : la magnitude est écrite en toutes lettres. Ils atteignent
# `validate_import_fields` par l'ÉCHO du confirm (champs JSON, pas de cellule
# CSV) ; par le CSV ils butent d'abord sur la limite de champ du lecteur.
LITERAL_AMPLIFYING_DECIMALS = [
    pytest.param("1." + "0" * 200000 + "1", id="huge-coefficient"),
    pytest.param("0." + "0" * 200000, id="huge-scale-zero"),
    pytest.param("1" * 200000, id="huge-integer-literal"),
]


def _row(**overrides: str) -> str:
    cells = {
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
    cells.update(overrides)
    return ",".join(cells[column] for column in CSV_HEADER.split(","))


DECIMAL_FIELDS = [
    ("amount", "AMOUNT_OUT_OF_RANGE"),
    ("quantity", "QUANTITY_OUT_OF_RANGE"),
    ("price", "PRICE_OUT_OF_RANGE"),
    ("fees", "FEES_OUT_OF_RANGE"),
]


@pytest.mark.parametrize("raw", COMPACT_AMPLIFYING_DECIMALS)
@pytest.mark.parametrize("field, expected_code", DECIMAL_FIELDS)
def test_an_out_of_range_magnitude_is_a_typed_row_error(
    field: str, expected_code: str, raw: str
) -> None:
    """Refus TYPÉ, nommant la ligne et le champ — jamais la valeur."""
    valid, invalid = parse_import_csv(f"{CSV_HEADER}\n{_row(**{field: raw})}", now=NOW)
    assert valid == []
    assert len(invalid) == 1
    assert invalid[0].row_number == 1
    assert expected_code in invalid[0].errors


@pytest.mark.parametrize("raw", LITERAL_AMPLIFYING_DECIMALS)
@pytest.mark.parametrize("field, expected_code", DECIMAL_FIELDS)
def test_a_literal_out_of_range_magnitude_is_a_typed_field_error(
    field: str, expected_code: str, raw: str
) -> None:
    """Même refus par la voie que l'écho du confirm emprunte réellement.

    `validate_import_fields` reçoit des champs JSON, jamais des cellules CSV :
    un littéral de 200 000 chiffres l'atteint sans passer par le lecteur.
    """
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
    fields[field] = raw
    row, errors = validate_import_fields(fields, row_number=7, now=NOW)
    assert row is None
    assert expected_code in errors
    assert len(repr(errors)) < 512  # le refus lui-même reste borné


@pytest.mark.parametrize("raw", COMPACT_AMPLIFYING_DECIMALS)
def test_a_refused_row_never_materializes_its_magnitude(raw: str) -> None:
    """Le refus doit rester borné : rien n'est rendu en `format(…, "f")`."""
    valid, invalid = parse_import_csv(f"{CSV_HEADER}\n{_row(amount=raw)}", now=NOW)
    assert valid == []
    rendered = repr([entry.model_dump() for entry in invalid])
    assert len(rendered) < 512


def test_the_preview_of_the_full_row_budget_stays_bounded() -> None:
    """Le vecteur exact de l'audit : 500 lignes (le maximum) x `1E+200000`."""
    body = "\n".join([_row(amount="1E+200000")] * MAX_IMPORT_ROWS)
    csv_text = f"{CSV_HEADER}\n{body}"
    valid, invalid = parse_import_csv(csv_text, now=NOW)
    assert valid == []
    assert len(invalid) == MAX_IMPORT_ROWS
    rendered = repr([entry.model_dump() for entry in invalid])
    # Sortie proportionnée à l'entrée, plus jamais à l'exposant déclaré.
    assert len(rendered) < len(csv_text)


# -- anti-vacuité : le portefeuille est la SEULE vérité de l'utilisateur -----
#
# Une borne n'est défendable que si elle laisse passer toute saisie légitime.
# Ces valeurs doivent rester ACCEPTÉES.


@pytest.mark.parametrize(
    "field, raw",
    [
        # Le plus gros nominal monétaire jamais émis légitimement
        # (pengő hongrois 1946, ~1E+20) reste 4 décades sous le plafond.
        ("amount", "100000000000000000000"),
        ("amount", "-99999999999999999999999.99"),
        ("amount", "12.5"),
        ("amount", "0"),
        # Portefeuille libellé dans une devise faible (IDR, VND) :
        # dix milliards d'unités, courant.
        ("amount", "-10000000000.00"),
        # Fraction de titre au grain le plus fin d'un courtier (1E-8).
        ("quantity", "0.00000001"),
        ("quantity", "1000000"),
        # Prix en centièmes de pip.
        ("price", "0.000001"),
        ("price", "0"),
        ("price", "123456.7890"),
        ("fees", "0.0001"),
        # Artefact d'export tableur (float rendu sur 17 chiffres) : accepté.
        ("price", "10.000000000000001"),
        ("quantity", "3.0000000000000000"),
    ],
)
def test_a_legitimate_declaration_is_still_recorded(field: str, raw: str) -> None:
    valid, invalid = parse_import_csv(f"{CSV_HEADER}\n{_row(**{field: raw})}", now=NOW)
    assert invalid == [], invalid
    assert len(valid) == 1
    assert getattr(valid[0], field) == Decimal(raw)


@pytest.mark.parametrize(
    "raw, accepted",
    [
        ("9.99999999999999999999999E+23", True),   # juste sous 10^24
        ("1E+24", False),                          # le plafond, exclu
        ("1E-18", True),                           # grain le plus fin admis
        ("1E-19", False),                          # au-delà du grain admis
    ],
)
def test_the_bound_itself_is_exact(raw: str, accepted: bool) -> None:
    valid, invalid = parse_import_csv(f"{CSV_HEADER}\n{_row(amount=raw)}", now=NOW)
    assert (invalid == []) is accepted
    assert (len(valid) == 1) is accepted


# ---------------------------------------------------------------------------
# Même classe que P1-5, trouvée en fermant P1-4 : un 500 NON TYPÉ de plus
# ---------------------------------------------------------------------------
#
# Les vecteurs d'amplification ci-dessus tiennent dans une cellule de 200 000
# caractères — sous le budget de 256 Kio. Or `csv.reader` refuse une cellule
# au-delà de 131 072 caractères en levant `_csv.Error`, qui n'est PAS un
# `CsvImportError` : il traversait `parse_import_csv` et atteignait le
# gestionnaire par défaut, exactement comme `DataError`. Refus typé désormais.


@pytest.mark.parametrize(
    "csv_text",
    [
        pytest.param(
            CSV_HEADER + "\n" + _row(note="x" * 200000), id="cell-over-field-limit"
        ),
    ],
)
def test_unreadable_csv_is_a_typed_whole_input_refusal(csv_text: str) -> None:
    with pytest.raises(CsvImportError) as exc:
        parse_import_csv(csv_text, now=NOW)
    assert exc.value.code in {"CSV_MALFORMED", "CSV_HEADER_INVALID"}
