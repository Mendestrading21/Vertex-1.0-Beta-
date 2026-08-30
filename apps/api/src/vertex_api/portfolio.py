"""Manual portfolio journal of the API: DTOs, CSV codec and database gateway.

ACCOUNTING JOURNAL SEMANTICS (docs/03-domain/PORTFOLIO_MANUAL.md): every
route here RECORDS a past fact the user already executed OUTSIDE Vertex —
"enregistrer un achat/vente déjà exécuté hors Vertex". Nothing creates,
previews, transmits, modifies or cancels an order; no broker account,
position, P&L or execution API exists anywhere in this module. The manual
ledger is the ONLY source of positions.

Rules implemented here:

- the default portfolio ``main`` is created on first use (documented
  get-or-create; base currency ``USD`` because the only synthetic mark
  universe is quoted in USD). No other portfolio management exists yet;
- corrections are COMPENSATING rows only (``compensate_ledger_event``); a
  second compensation of the same event is a clean 409 conflict;
- every accepted ledger write enqueues ``portfolio.valuation.refresh`` IN THE
  SAME TRANSACTION (outbox atomicity, ADR-006) so the worker revalues the
  portfolio; the topic string is re-declared here because the API never
  imports worker code;
- CSV import is PREVIEW (typed rows, per-row errors, potential duplicates
  against the ledger — never a write) then CONFIRM (only rows echoed back
  with their integrity hash; the confirm REPLAYS the full validation and
  recomputes each hash — an altered echo is rejected fail-closed). Confirmed
  rows are recorded with source ``IMPORT_CONFIRMED``;
- CSV cells starting with ``=``, ``+``, ``-`` or ``@`` are neutralized with a
  leading apostrophe on export (spreadsheet formula injection); the import
  parser strips ONE leading apostrophe per cell so a Vertex export
  round-trips. Import input is bounded: 256 KiB and 500 data rows.

All money, prices, quantities and fees travel as exact decimal STRINGS on
the wire and as ``Decimal`` in Python — never floats.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import (
    Annotated,
    Any,
    Iterable,
    Literal,
    Mapping,
    Optional,
    Protocol,
    Sequence,
)

from fastapi import FastAPI
from pydantic import Field, StringConstraints, model_validator
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from vertex_api.auth.db import open_db_session
from vertex_api.snapshot_views import checked_relayed_content
from vertex_core.contracts.types import (
    ContractModel,
    CurrencyCode,
    FrozenStrMapping,
    NonEmptyStr,
    PositiveInt,
    UtcDatetime,
)
from vertex_persistence.enums import (
    LEDGER_EVENT_KINDS,
    LedgerEventKind,
    PositionLotSource,
)
from vertex_persistence.models import LedgerTransaction, Portfolio
from vertex_persistence.repository.ledger import (
    create_portfolio,
    list_position_lots,
    record_ledger_event,
    compensate_ledger_event,
)
from vertex_persistence.repository.outbox import enqueue_outbox
from vertex_persistence.repository.snapshots import CurrentSnapshot, get_current_snapshot

__all__ = [
    "DEFAULT_BASE_CURRENCY",
    "DEFAULT_PORTFOLIO_NAME",
    "EXPORT_SCHEMA_VERSION",
    "IMPORT_COLUMNS",
    "MAX_DECIMAL_MAGNITUDE_EXPONENT",
    "MAX_DECIMAL_SCALE",
    "MAX_IMPORT_BYTES",
    "MAX_IMPORT_ROWS",
    "SNAPSHOT_KIND_PORTFOLIO_VALUATION",
    "TOPIC_PERFORMANCE_REFRESH",
    "TOPIC_PORTFOLIO_VALUATION_REFRESH",
    "CompensateTransactionRequest",
    "CompensateTransactionResponse",
    "CsvImportPreviewRequest",
    "DbPortfolioGateway",
    "ImportConfirmRequest",
    "ImportConfirmResponse",
    "ImportPreviewResponse",
    "ImportRowDuplicate",
    "ImportRowEcho",
    "ImportRowError",
    "InstrumentRefInput",
    "LedgerEntryView",
    "LedgerTransactionEntry",
    "PortfolioGateway",
    "PortfolioInfo",
    "PortfolioLotEntry",
    "PortfolioOverview",
    "PortfolioResponse",
    "PortfolioValuationView",
    "RecordTransactionRequest",
    "RecordTransactionResponse",
    "ValidatedImportRow",
    "build_portfolio_response",
    "decimal_magnitude_is_recordable",
    "detect_potential_duplicates",
    "import_row_hash",
    "neutralize_csv_cell",
    "parse_import_csv",
    "render_export_csv",
    "validate_import_fields",
]

DEFAULT_PORTFOLIO_NAME = "main"
DEFAULT_BASE_CURRENCY = "USD"
"""Documented get-or-create default: the single local user's portfolio is
named ``main`` and based in USD (the currency of the synthetic mark
universe). Created on the first portfolio request, never implicitly more."""

TOPIC_PORTFOLIO_VALUATION_REFRESH = "portfolio.valuation.refresh"
"""Outbox topic OWNED by the worker (``vertex_worker.portfolio``); the string
is re-declared here because the API enqueues jobs but never imports worker
code (module boundary)."""

TOPIC_PERFORMANCE_REFRESH = "performance.refresh"
"""Outbox topic OWNED by the worker (``vertex_worker.performance``), enqueued
alongside every valuation refresh: a new declared ledger fact changes the
daily performance series exactly like it changes the valuation."""

OUTBOX_NOTIFY_CHANNEL = "vertex_outbox"
"""Best-effort wake-up channel (signal only; the outbox table is the queue)."""

SNAPSHOT_KIND_PORTFOLIO_VALUATION = "portfolio_valuation"
"""Snapshot kind published by the worker; the key is the portfolio id."""

EXPORT_SCHEMA_VERSION = "vertex.portfolio-ledger-export/1.0"
"""Version stamp written as the first line of every ledger export."""

MAX_IMPORT_BYTES = 256 * 1024
MAX_IMPORT_ROWS = 500

MAX_DECIMAL_MAGNITUDE_EXPONENT = 24
"""Magnitude ceiling of every DECLARED decimal: ``|value| < 10**24``.

Why a ceiling exists at all. ``Decimal`` accepts any exponent the machine can
hold, and ``Decimal("1E+99999999")`` is perfectly ``is_finite()``; the only
remaining limit was the memory of the machine, and ``_decimal_text`` renders
the exponent as digits. 500 declared rows (the row budget) carrying
``1E+200000`` fitted in 26 KiB — well under ``MAX_IMPORT_BYTES`` — and produced
95 MiB of response. A byte budget on the INPUT bounds nothing when a single
cell can expand by five orders of magnitude, so the magnitude itself is
bounded, before anything is formatted.

Why 10**24, and why that refusal is defendable. The manual journal is the
user's ONLY source of truth: Vertex must not decide for them what is "too
much". The ceiling is therefore placed where no declaration can honestly
reach, whatever the currency:

- ~10**20 is the largest nominal figure ever issued in a real currency
  (the 10**20 pengő note, Hungary 1946) — four decades of headroom;
- ~10**14 USD is the world's entire broad money supply — ten decades;
- ~10**11 USD is the largest personal fortune ever recorded — thirteen
  decades.

A figure above 10**24 is not a declaration, it is a typing or paste accident,
and recording it corrupts every valuation and performance series downstream.
"""

MAX_DECIMAL_SCALE = 18
"""Granularity floor of every DECLARED decimal: at most 18 decimal places.

The mirror of the ceiling — ``1E-200000`` renders to 200 002 characters just
like ``1E+200000`` — and it also bounds the coefficient: with the ceiling
above, a value written in full carries at most 24 + 18 digits, so
``format(value, "f")`` never exceeds 44 characters.

18 decimal places is the finest granularity any financial system uses (the
attounit/wei), ten decades finer than the finest brokerage fractional-share
grain (10**-8) and fourteen finer than the finest currency minor unit
(10**-4). Trailing zeros are counted as declared, so a spreadsheet export
rendering a float over 17 significant digits still passes.
"""

IMPORT_COLUMNS: tuple[str, ...] = (
    "kind",
    "ticker",
    "quantity",
    "price",
    "amount",
    "currency",
    "fees",
    "effective_at",
    "note",
)

EXPORT_COLUMNS: tuple[str, ...] = (
    "id",
    "kind",
    "ticker",
    "quantity",
    "price",
    "amount",
    "currency",
    "fees",
    "effective_at",
    "recorded_at",
    "source",
    "note",
    "compensates",
)

_POSITION_KINDS = frozenset(
    {LedgerEventKind.BUY_RECORDED.value, LedgerEventKind.SELL_RECORDED.value}
)

_TICKER_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"
_CURRENCY_PATTERN = r"^[A-Z]{3}$"

TickerStr = Annotated[str, StringConstraints(pattern=_TICKER_PATTERN)]
NoteStr = Annotated[str, StringConstraints(min_length=1, max_length=500)]

# Machine-readable error codes (stable tokens).
ERROR_ALREADY_COMPENSATED = "ALREADY_COMPENSATED"
ERROR_UNKNOWN_TRANSACTION = "UNKNOWN_TRANSACTION"
ERROR_EFFECTIVE_AT_IN_FUTURE = "EFFECTIVE_AT_IN_FUTURE"
ERROR_CSV_TOO_LARGE = "CSV_TOO_LARGE"
ERROR_CSV_TOO_MANY_ROWS = "CSV_TOO_MANY_ROWS"
ERROR_CSV_HEADER_INVALID = "CSV_HEADER_INVALID"
ERROR_CSV_MALFORMED = "CSV_MALFORMED"
ERROR_ECHO_HASH_MISMATCH = "ECHO_HASH_MISMATCH"
ERROR_IMPORT_ROW_INVALID = "IMPORT_ROW_INVALID"

ROW_ERROR_WRONG_COLUMN_COUNT = "WRONG_COLUMN_COUNT"
ROW_ERROR_UNKNOWN_KIND = "UNKNOWN_KIND"
ROW_ERROR_INVALID_TICKER = "INVALID_TICKER"
ROW_ERROR_MISSING_TICKER = "MISSING_TICKER"
ROW_ERROR_MISSING_QUANTITY = "MISSING_QUANTITY"
ROW_ERROR_INVALID_QUANTITY = "INVALID_QUANTITY"
ROW_ERROR_MISSING_PRICE = "MISSING_PRICE"
ROW_ERROR_INVALID_PRICE = "INVALID_PRICE"
ROW_ERROR_INVALID_AMOUNT = "INVALID_AMOUNT"
ROW_ERROR_INVALID_CURRENCY = "INVALID_CURRENCY"
ROW_ERROR_INVALID_FEES = "INVALID_FEES"
ROW_ERROR_INVALID_EFFECTIVE_AT = "INVALID_EFFECTIVE_AT"
ROW_ERROR_EFFECTIVE_AT_IN_FUTURE = "EFFECTIVE_AT_IN_FUTURE"
ROW_ERROR_NOTE_TOO_LONG = "NOTE_TOO_LONG"
ROW_ERROR_QUANTITY_OUT_OF_RANGE = "QUANTITY_OUT_OF_RANGE"
ROW_ERROR_PRICE_OUT_OF_RANGE = "PRICE_OUT_OF_RANGE"
ROW_ERROR_AMOUNT_OUT_OF_RANGE = "AMOUNT_OUT_OF_RANGE"
ROW_ERROR_FEES_OUT_OF_RANGE = "FEES_OUT_OF_RANGE"
"""Out-of-range magnitudes get their OWN codes, distinct from the malformed
``INVALID_*`` ones: the row parses, its magnitude is what is refused. Each
code names the FIELD and ``ImportRowError.row_number`` names the ROW — the
refused value itself never travels back."""


# ---------------------------------------------------------------------------
# Wire DTOs — requests
# ---------------------------------------------------------------------------


class InstrumentRefInput(ContractModel):
    """Canonical instrument reference of a recorded position fact.

    ``ticker`` only for now: the synthetic universe identifies instruments by
    plain ticker. Extending the identity (options, con_id, trading class) is a
    contract change, never an implicit field.
    """

    ticker: TickerStr


class RecordTransactionRequest(ContractModel):
    """One past fact to append to the accounting journal.

    This RECORDS a transaction the user already executed outside Vertex; it
    is never an instruction. ``amount`` is the signed cash impact declared by
    the user (exact decimal string on the wire); ``effective_at`` must not be
    in the future (a fact that has not happened yet cannot be recorded).
    """

    kind: LedgerEventKind
    instrument: Optional[InstrumentRefInput] = None
    quantity: Optional[Decimal] = None
    price: Optional[Decimal] = None
    amount: Decimal
    currency: CurrencyCode
    fees: Decimal = Decimal("0")
    effective_at: UtcDatetime
    note: Optional[NoteStr] = None

    @model_validator(mode="after")
    def _check_shape(self) -> "RecordTransactionRequest":
        for label, value in (
            ("quantity", self.quantity),
            ("price", self.price),
            ("amount", self.amount),
            ("fees", self.fees),
        ):
            if value is None:
                continue
            if not value.is_finite():
                raise ValueError(f"{label}: non-finite decimal rejected")
            # ``is_finite()`` alone bounded nothing: ``1E+200000`` IS finite,
            # and one such field reached the ledger INSERT, where PostgreSQL
            # refused it with a DataError whose text quoted the whole row.
            # The magnitude window is the same one the CSV codec applies —
            # see ``decimal_magnitude_is_recordable``. The message names the
            # FIELD and the WINDOW, never the refused value.
            if not decimal_magnitude_is_recordable(value):
                raise ValueError(
                    f"{label}: {label.upper()}_OUT_OF_RANGE — a declared "
                    f"decimal must be below 1E+{MAX_DECIMAL_MAGNITUDE_EXPONENT} "
                    f"in magnitude with at most {MAX_DECIMAL_SCALE} decimal "
                    "places"
                )
        if self.fees < 0:
            raise ValueError("fees: negative fees rejected")
        if self.quantity is not None and self.quantity <= 0:
            raise ValueError(
                "quantity: strictly positive quantity required "
                "(the direction is carried by the kind)"
            )
        if self.price is not None and self.price < 0:
            raise ValueError("price: negative price rejected")
        if self.kind.value in _POSITION_KINDS:
            if self.instrument is None:
                raise ValueError("instrument: required for a recorded position fact")
            if self.quantity is None:
                raise ValueError("quantity: required for a recorded position fact")
            if self.price is None:
                raise ValueError("price: required for a recorded position fact")
        return self


class CompensateTransactionRequest(ContractModel):
    """Correction by compensation: the mandatory reason of the new row."""

    note: NoteStr


class CsvImportPreviewRequest(ContractModel):
    """Raw CSV text to preview. Nothing is written by the preview."""

    csv: str


class ImportRowEcho(ContractModel):
    """One VALIDATED import row echoed with its integrity hash.

    The confirm endpoint replays the validation on these fields and
    recomputes ``row_hash``; any divergence rejects the whole request.
    Optional fields are empty strings in the canonical hashed form.
    """

    row_number: PositiveInt
    kind: NonEmptyStr
    ticker: str
    quantity: str
    price: str
    amount: NonEmptyStr
    currency: NonEmptyStr
    fees: NonEmptyStr
    effective_at: NonEmptyStr
    note: str
    row_hash: NonEmptyStr


class ImportRowError(ContractModel):
    """One rejected import row with its machine-readable error codes."""

    row_number: PositiveInt
    errors: tuple[NonEmptyStr, ...] = Field(min_length=1)


class ImportRowDuplicate(ContractModel):
    """One valid row that matches already-recorded ledger transactions."""

    row_number: PositiveInt
    matching_transaction_ids: tuple[PositiveInt, ...] = Field(min_length=1)


class ImportPreviewResponse(ContractModel):
    """Typed preview of one CSV import — NO write happened."""

    rows_total: Annotated[int, Field(ge=0)]
    rows_valid: tuple[ImportRowEcho, ...]
    rows_invalid: tuple[ImportRowError, ...]
    potential_duplicates: tuple[ImportRowDuplicate, ...]
    max_rows: PositiveInt
    max_bytes: PositiveInt


class ImportConfirmRequest(ContractModel):
    """The rows to record: the preview echo, unmodified, hash included."""

    rows: tuple[ImportRowEcho, ...] = Field(min_length=1, max_length=MAX_IMPORT_ROWS)


class ImportConfirmResponse(ContractModel):
    """Receipt of one confirmed import (source ``IMPORT_CONFIRMED``)."""

    recorded_transaction_ids: tuple[PositiveInt, ...]
    source: Literal["IMPORT_CONFIRMED"]
    refresh_enqueued: bool


class RecordTransactionResponse(ContractModel):
    """Receipt of one recorded journal fact."""

    transaction_id: PositiveInt
    refresh_enqueued: bool


class CompensateTransactionResponse(ContractModel):
    """Receipt of one compensating row (the original stays untouched)."""

    compensation_id: PositiveInt
    compensates: PositiveInt
    refresh_enqueued: bool


# ---------------------------------------------------------------------------
# Wire DTOs — portfolio overview response
# ---------------------------------------------------------------------------


class PortfolioInfo(ContractModel):
    """The user-declared portfolio identity (never a broker account)."""

    id: PositiveInt
    name: NonEmptyStr
    base_currency: CurrencyCode


class LedgerTransactionEntry(ContractModel):
    """One journal row, verbatim (decimal strings, UTC instants)."""

    id: PositiveInt
    kind: NonEmptyStr
    instrument: Optional[FrozenStrMapping]
    quantity: Optional[NonEmptyStr]
    price: Optional[NonEmptyStr]
    amount: NonEmptyStr
    currency: CurrencyCode
    fees: NonEmptyStr
    effective_at: UtcDatetime
    recorded_at: UtcDatetime
    source: NonEmptyStr
    note: Optional[NonEmptyStr]
    compensates: Optional[PositiveInt]
    compensated_by: Optional[PositiveInt]


class PortfolioLotEntry(ContractModel):
    """One user-declared position lot, verbatim from the repository."""

    id: PositiveInt
    instrument: FrozenStrMapping
    quantity: NonEmptyStr
    unit_cost: NonEmptyStr
    currency: CurrencyCode
    opened_at: UtcDatetime
    source: NonEmptyStr
    note: Optional[NonEmptyStr]


class PortfolioValuationView(ContractModel):
    """The last published valuation snapshot — or an honest empty state.

    ``state = "empty"`` means the worker never published a valuation for this
    portfolio: nothing is invented, ``reason`` says why. ``state = "ok"``
    relays the persisted snapshot content VERBATIM (``mark_population``
    ``SYNTHETIC`` shown as-is); the API computes no P&L, weight or total.
    """

    state: Literal["ok", "empty"]
    snapshot_version: Optional[PositiveInt]
    as_of: Optional[UtcDatetime]
    content: Optional[FrozenStrMapping]
    reason: Optional[NonEmptyStr]


class PortfolioResponse(ContractModel):
    """The manual portfolio: journal, declared lots, last valuation."""

    portfolio: PortfolioInfo
    transactions: tuple[LedgerTransactionEntry, ...]
    lots: tuple[PortfolioLotEntry, ...]
    valuation: PortfolioValuationView


# ---------------------------------------------------------------------------
# Internal views (gateway output; ORM-free so unit tests use plain fakes)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LedgerEntryView:
    """ORM-free view of one persisted ledger transaction."""

    id: int
    kind: str
    instrument: Optional[Mapping[str, Any]]
    quantity: Optional[Decimal]
    price: Optional[Decimal]
    amount: Decimal
    currency: str
    fees: Decimal
    effective_at: datetime
    recorded_at: datetime
    source: str
    note: Optional[str]
    compensates: Optional[int]


@dataclass(frozen=True)
class LotView:
    """ORM-free view of one user-declared position lot."""

    id: int
    instrument: Mapping[str, Any]
    quantity: Decimal
    unit_cost: Decimal
    currency: str
    opened_at: datetime
    source: str
    note: Optional[str]


@dataclass(frozen=True)
class PortfolioOverview:
    """Everything the GET route needs, loaded in one gateway call."""

    portfolio_id: int
    name: str
    base_currency: str
    transactions: tuple[LedgerEntryView, ...]
    lots: tuple[LotView, ...]
    valuation: Optional[CurrentSnapshot]


@dataclass(frozen=True)
class ValidatedImportRow:
    """One import row after full validation (typed values + canonical texts)."""

    row_number: int
    kind: str
    ticker: Optional[str]
    quantity: Optional[Decimal]
    price: Optional[Decimal]
    amount: Decimal
    currency: str
    fees: Decimal
    effective_at: datetime
    note: Optional[str]
    canonical_fields: Mapping[str, str]
    row_hash: str


# ---------------------------------------------------------------------------
# CSV codec (pure)
# ---------------------------------------------------------------------------


def neutralize_csv_cell(value: str) -> str:
    """Neutralize spreadsheet formula injection: ``=``, ``+``, ``-``, ``@``.

    A cell starting with one of those characters gets a leading apostrophe
    (the standard spreadsheet text guard); the CSV writer then quotes it. The
    import parser strips exactly one leading apostrophe, so a Vertex export
    re-imports losslessly.
    """
    if value and value[0] in ("=", "+", "-", "@"):
        return "'" + value
    return value


def _denormalize_csv_cell(value: str) -> str:
    """Reverse of :func:`neutralize_csv_cell`: strip ONE leading apostrophe."""
    if value.startswith("'"):
        return value[1:]
    return value


def decimal_magnitude_is_recordable(value: Decimal) -> bool:
    """Is this declared decimal within the recordable magnitude window?

    The SINGLE truth of the bound, applied by the journal DTO
    (:class:`RecordTransactionRequest`) and by the CSV codec alike, so no
    write path can reach ``_decimal_text`` with an unbounded exponent.

    Accepts a finite value whose magnitude is below
    ``10**MAX_DECIMAL_MAGNITUDE_EXPONENT`` and whose declared granularity is
    no finer than ``10**-MAX_DECIMAL_SCALE``. ``Decimal.adjusted()`` is the
    base-10 exponent of the leading digit and ``as_tuple().exponent`` the
    declared scale: both are read from the coefficient WITHOUT expanding it,
    which is the whole point — the check must cost nothing on the very input
    it refuses.
    """
    if not value.is_finite():
        return False
    exponent = value.as_tuple().exponent
    if not isinstance(exponent, int) or exponent < -MAX_DECIMAL_SCALE:
        return False
    return value.adjusted() < MAX_DECIMAL_MAGNITUDE_EXPONENT


def _decimal_text(value: Decimal) -> str:
    """Render an ALREADY BOUNDED decimal in full positional notation.

    Every caller must have passed :func:`decimal_magnitude_is_recordable`
    first: ``format(value, "f")`` materializes the exponent as digits, so it
    is the amplification primitive this module bounds upstream.
    """
    return format(value, "f")


def import_row_hash(fields: Mapping[str, str]) -> str:
    """Integrity hash of one canonical import row (order-independent JSON).

    The hash covers exactly the canonical field texts; the confirm endpoint
    recomputes it after replaying the validation, so an echo altered in any
    field — or a hash altered to match nothing — is rejected.
    """
    canonical = json.dumps(
        {key: fields[key] for key in sorted(fields)},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_import_fields(
    fields: Mapping[str, str], *, row_number: int, now: datetime
) -> tuple[Optional[ValidatedImportRow], list[str]]:
    """Validate ONE import row fail-closed; return (row, []) or (None, errors).

    The same function runs at preview AND at confirm — the confirm never
    trusts the echo, it replays this validation and recomputes the hash.
    """
    errors: list[str] = []
    kind = fields.get("kind", "").strip()
    ticker = fields.get("ticker", "").strip()
    quantity_text = fields.get("quantity", "").strip()
    price_text = fields.get("price", "").strip()
    amount_text = fields.get("amount", "").strip()
    currency = fields.get("currency", "").strip()
    fees_text = fields.get("fees", "").strip()
    effective_text = fields.get("effective_at", "").strip()
    note = fields.get("note", "").strip()

    if kind not in LEDGER_EVENT_KINDS:
        errors.append(ROW_ERROR_UNKNOWN_KIND)

    parsed_ticker: Optional[str] = None
    if ticker:
        if re.match(_TICKER_PATTERN, ticker):
            parsed_ticker = ticker
        else:
            errors.append(ROW_ERROR_INVALID_TICKER)

    def _parse_decimal(
        invalid_error: str, range_error: str, raw: str
    ) -> Optional[Decimal]:
        """Parse one declared decimal, MAGNITUDE BOUND INCLUDED.

        ``Decimal(raw)`` itself is cheap whatever the exponent (the exponent
        stays an ``int``); what is not cheap is ``_decimal_text``. The bound
        is therefore applied here, before the value can reach the canonical
        rendering, and it yields its OWN code so the user can tell a
        malformed cell from an out-of-range one.
        """
        try:
            value = Decimal(raw)
        except (InvalidOperation, ValueError):
            errors.append(invalid_error)
            return None
        if not value.is_finite():
            errors.append(invalid_error)
            return None
        if not decimal_magnitude_is_recordable(value):
            errors.append(range_error)
            return None
        return value

    quantity: Optional[Decimal] = None
    if quantity_text:
        quantity = _parse_decimal(
            ROW_ERROR_INVALID_QUANTITY, ROW_ERROR_QUANTITY_OUT_OF_RANGE, quantity_text
        )
        if quantity is not None and quantity <= 0:
            errors.append(ROW_ERROR_INVALID_QUANTITY)
            quantity = None

    price: Optional[Decimal] = None
    if price_text:
        price = _parse_decimal(
            ROW_ERROR_INVALID_PRICE, ROW_ERROR_PRICE_OUT_OF_RANGE, price_text
        )
        if price is not None and price < 0:
            errors.append(ROW_ERROR_INVALID_PRICE)
            price = None

    amount: Optional[Decimal] = None
    if amount_text:
        amount = _parse_decimal(
            ROW_ERROR_INVALID_AMOUNT, ROW_ERROR_AMOUNT_OUT_OF_RANGE, amount_text
        )
    else:
        errors.append(ROW_ERROR_INVALID_AMOUNT)

    if not re.match(_CURRENCY_PATTERN, currency):
        errors.append(ROW_ERROR_INVALID_CURRENCY)

    fees: Optional[Decimal] = None
    if fees_text:
        fees = _parse_decimal(
            ROW_ERROR_INVALID_FEES, ROW_ERROR_FEES_OUT_OF_RANGE, fees_text
        )
        if fees is not None and fees < 0:
            errors.append(ROW_ERROR_INVALID_FEES)
            fees = None
    else:
        fees = Decimal("0")

    effective_at: Optional[datetime] = None
    try:
        parsed = datetime.fromisoformat(effective_text) if effective_text else None
    except ValueError:
        parsed = None
    if parsed is None or parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        errors.append(ROW_ERROR_INVALID_EFFECTIVE_AT)
    else:
        effective_at = parsed.astimezone(timezone.utc)
        if effective_at > now:
            errors.append(ROW_ERROR_EFFECTIVE_AT_IN_FUTURE)
            effective_at = None

    if len(note) > 500:
        errors.append(ROW_ERROR_NOTE_TOO_LONG)

    if kind in _POSITION_KINDS:
        if parsed_ticker is None and ROW_ERROR_INVALID_TICKER not in errors:
            errors.append(ROW_ERROR_MISSING_TICKER)
        if not quantity_text:
            errors.append(ROW_ERROR_MISSING_QUANTITY)
        if not price_text:
            errors.append(ROW_ERROR_MISSING_PRICE)

    if errors:
        return None, sorted(set(errors))

    assert amount is not None and fees is not None and effective_at is not None
    canonical_fields = {
        "kind": kind,
        "ticker": parsed_ticker or "",
        "quantity": _decimal_text(quantity) if quantity is not None else "",
        "price": _decimal_text(price) if price is not None else "",
        "amount": _decimal_text(amount),
        "currency": currency,
        "fees": _decimal_text(fees),
        "effective_at": effective_at.isoformat(),
        "note": note,
    }
    return (
        ValidatedImportRow(
            row_number=row_number,
            kind=kind,
            ticker=parsed_ticker,
            quantity=quantity,
            price=price,
            amount=amount,
            currency=currency,
            fees=fees,
            effective_at=effective_at,
            note=note or None,
            canonical_fields=canonical_fields,
            row_hash=import_row_hash(canonical_fields),
        ),
        [],
    )


class CsvImportError(ValueError):
    """Whole-input CSV rejection (size, row budget, header) with a code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def parse_import_csv(
    csv_text: str, *, now: datetime
) -> tuple[list[ValidatedImportRow], list[ImportRowError]]:
    """Parse and validate one CSV import fail-closed (NO write, pure).

    Global limits raise :class:`CsvImportError`; per-row problems become
    :class:`ImportRowError` entries. Comment lines starting with ``#`` (the
    export's version stamp) are skipped. Row numbers count DATA rows from 1.
    """
    if len(csv_text.encode("utf-8")) > MAX_IMPORT_BYTES:
        raise CsvImportError(
            ERROR_CSV_TOO_LARGE, f"csv input exceeds {MAX_IMPORT_BYTES} bytes"
        )
    lines = [
        line
        for line in csv_text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not lines:
        raise CsvImportError(ERROR_CSV_HEADER_INVALID, "csv input carries no header row")
    reader = csv.reader(io.StringIO("\n".join(lines)))
    try:
        rows = list(reader)
    except csv.Error as exc:
        # The stdlib reader fails on its own terms — a cell above its
        # 131 072-character field limit, an unterminated quote, an embedded
        # NUL. All three fit under MAX_IMPORT_BYTES, so all three were
        # reachable, and none of them is a ``CsvImportError``: they escaped
        # this function and reached the DEFAULT exception handler as an
        # UNTYPED 500, exactly like the database errors of P1-5. Malformed
        # input is a client fault and gets a typed whole-input refusal; the
        # stdlib message is dropped rather than relayed, since it is the one
        # thing here that could quote a fragment of the submitted file.
        raise CsvImportError(
            ERROR_CSV_MALFORMED, "csv input is not readable as delimited text"
        ) from exc
    header = [cell.strip() for cell in rows[0]] if rows else []
    # Every required column must be present by NAME (any order); unknown
    # columns — e.g. the export's id/recorded_at/source/compensates — are
    # ignored, so a Vertex ledger export re-imports directly.
    missing = [column for column in IMPORT_COLUMNS if column not in header]
    if missing or len(header) != len(set(header)):
        raise CsvImportError(
            ERROR_CSV_HEADER_INVALID,
            f"csv header must carry each of: {','.join(IMPORT_COLUMNS)} (once)",
        )
    column_index = {column: header.index(column) for column in IMPORT_COLUMNS}
    data_rows = rows[1:]
    if len(data_rows) > MAX_IMPORT_ROWS:
        raise CsvImportError(
            ERROR_CSV_TOO_MANY_ROWS, f"csv input exceeds {MAX_IMPORT_ROWS} data rows"
        )
    valid: list[ValidatedImportRow] = []
    invalid: list[ImportRowError] = []
    for index, raw_cells in enumerate(data_rows, start=1):
        if len(raw_cells) != len(header):
            invalid.append(
                ImportRowError(row_number=index, errors=(ROW_ERROR_WRONG_COLUMN_COUNT,))
            )
            continue
        fields = {
            column: _denormalize_csv_cell(raw_cells[column_index[column]].strip())
            for column in IMPORT_COLUMNS
        }
        row, errors = validate_import_fields(fields, row_number=index, now=now)
        if row is None:
            invalid.append(ImportRowError(row_number=index, errors=tuple(errors)))
        else:
            valid.append(row)
    return valid, invalid


def _duplicate_key_of_entry(entry: LedgerEntryView) -> tuple[str, ...]:
    ticker = ""
    if isinstance(entry.instrument, Mapping):
        raw = entry.instrument.get("ticker")
        if isinstance(raw, str):
            ticker = raw
    return (
        entry.kind,
        ticker,
        _decimal_text(entry.quantity) if entry.quantity is not None else "",
        _decimal_text(entry.price) if entry.price is not None else "",
        _decimal_text(entry.amount),
        entry.currency,
        entry.effective_at.astimezone(timezone.utc).isoformat(),
    )


def _duplicate_key_of_row(row: ValidatedImportRow) -> tuple[str, ...]:
    return (
        row.kind,
        row.ticker or "",
        _decimal_text(row.quantity) if row.quantity is not None else "",
        _decimal_text(row.price) if row.price is not None else "",
        _decimal_text(row.amount),
        row.currency,
        row.effective_at.isoformat(),
    )


def detect_potential_duplicates(
    rows: Sequence[ValidatedImportRow], ledger: Sequence[LedgerEntryView]
) -> list[ImportRowDuplicate]:
    """Flag valid rows matching already-recorded facts (kind, instrument,
    quantity, price, amount, currency and effective instant all equal).

    A flag is INFORMATION, never a block: recording the same fact twice can
    be legitimate — the user decides which rows reach the confirm call.
    """
    by_key: dict[tuple[str, ...], list[int]] = {}
    for entry in ledger:
        by_key.setdefault(_duplicate_key_of_entry(entry), []).append(entry.id)
    duplicates: list[ImportRowDuplicate] = []
    for row in rows:
        matches = by_key.get(_duplicate_key_of_row(row))
        if matches:
            duplicates.append(
                ImportRowDuplicate(
                    row_number=row.row_number,
                    matching_transaction_ids=tuple(sorted(matches)),
                )
            )
    return duplicates


def render_export_csv(entries: Iterable[LedgerEntryView]) -> str:
    """Render the journal as CSV: version stamp line, header, ledger rows.

    Nothing but the ledger is exported. Every cell goes through the formula
    neutralization guard.
    """
    buffer = io.StringIO()
    buffer.write(f"# {EXPORT_SCHEMA_VERSION}\n")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(EXPORT_COLUMNS)
    for entry in entries:
        ticker = ""
        if isinstance(entry.instrument, Mapping):
            raw = entry.instrument.get("ticker")
            if isinstance(raw, str):
                ticker = raw
        cells = [
            str(entry.id),
            entry.kind,
            ticker,
            _decimal_text(entry.quantity) if entry.quantity is not None else "",
            _decimal_text(entry.price) if entry.price is not None else "",
            _decimal_text(entry.amount),
            entry.currency,
            _decimal_text(entry.fees),
            entry.effective_at.astimezone(timezone.utc).isoformat(),
            entry.recorded_at.astimezone(timezone.utc).isoformat(),
            entry.source,
            entry.note or "",
            str(entry.compensates) if entry.compensates is not None else "",
        ]
        writer.writerow([neutralize_csv_cell(cell) for cell in cells])
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Gateway (protocol + real database implementation)
# ---------------------------------------------------------------------------


class PortfolioGateway(Protocol):
    """Narrow write/read boundary of the portfolio routes.

    Injected through a FastAPI dependency so unit tests substitute
    deterministic fakes; the real implementation writes ONLY through the
    existing ``vertex_persistence.repository.ledger`` functions and enqueues
    the valuation refresh in the same transaction.
    """

    def overview(self) -> PortfolioOverview:
        """Journal + declared lots + last valuation of the ``main`` portfolio."""
        ...

    def record_transaction(
        self,
        *,
        kind: str,
        instrument: Optional[Mapping[str, Any]],
        quantity: Optional[Decimal],
        price: Optional[Decimal],
        amount: Decimal,
        currency: str,
        fees: Decimal,
        effective_at: datetime,
        note: Optional[str],
        now: datetime,
    ) -> int:
        """Append one journal fact + enqueue the refresh, one transaction."""
        ...

    def compensate_transaction(self, *, event_id: int, note: str, now: datetime) -> int:
        """Append the compensating row + enqueue the refresh, one transaction."""
        ...

    def record_import(
        self, rows: Sequence[ValidatedImportRow], *, now: datetime
    ) -> list[int]:
        """Append every confirmed row (source IMPORT_CONFIRMED) + one refresh."""
        ...


class DbPortfolioGateway:
    """Real gateway over the application's engine (one session per call)."""

    def __init__(self, app: FastAPI) -> None:
        self._app = app

    # -- portfolio -----------------------------------------------------------

    def _get_or_create_main(self, session: Session) -> Portfolio:
        """Get-or-create the single ``main`` portfolio (documented default).

        The concurrent-first-creation race is closed by the unique name
        constraint: the loser rolls back its savepoint and re-reads the
        winner's row — never a duplicate, never an error surfaced to the user.
        """
        row = session.execute(
            select(Portfolio).where(Portfolio.name == DEFAULT_PORTFOLIO_NAME)
        ).scalar_one_or_none()
        if row is not None:
            return row
        try:
            with session.begin_nested():
                create_portfolio(
                    session,
                    name=DEFAULT_PORTFOLIO_NAME,
                    base_currency=DEFAULT_BASE_CURRENCY,
                )
        except IntegrityError:
            pass  # concurrent creation won; re-read below
        created = session.execute(
            select(Portfolio).where(Portfolio.name == DEFAULT_PORTFOLIO_NAME)
        ).scalar_one_or_none()
        if created is None:  # pragma: no cover - defensive
            raise RuntimeError("portfolio get-or-create failed to converge")
        return created

    @staticmethod
    def _entry_view(row: LedgerTransaction) -> LedgerEntryView:
        return LedgerEntryView(
            id=row.id,
            kind=row.kind,
            instrument=row.instrument,
            quantity=row.quantity,
            price=row.price,
            amount=row.amount,
            currency=row.currency,
            fees=row.fees,
            effective_at=row.effective_at,
            recorded_at=row.recorded_at,
            source=row.source,
            note=row.note,
            compensates=row.compensates,
        )

    def overview(self) -> PortfolioOverview:
        with open_db_session(self._app) as session:
            portfolio = self._get_or_create_main(session)
            rows = (
                session.execute(
                    select(LedgerTransaction)
                    .where(LedgerTransaction.portfolio_id == portfolio.id)
                    .order_by(LedgerTransaction.effective_at, LedgerTransaction.id)
                )
                .scalars()
                .all()
            )
            lots = list_position_lots(session, portfolio.id)
            valuation = get_current_snapshot(
                session,
                kind=SNAPSHOT_KIND_PORTFOLIO_VALUATION,
                key=str(portfolio.id),
            )
            overview = PortfolioOverview(
                portfolio_id=portfolio.id,
                name=portfolio.name,
                base_currency=portfolio.base_currency,
                transactions=tuple(self._entry_view(row) for row in rows),
                lots=tuple(
                    LotView(
                        id=lot.id,
                        instrument=lot.instrument,
                        quantity=lot.quantity,
                        unit_cost=lot.unit_cost,
                        currency=lot.currency,
                        opened_at=lot.opened_at,
                        source=lot.source,
                        note=lot.note,
                    )
                    for lot in lots
                ),
                valuation=valuation,
            )
            # The get-or-create write (first use only) must survive the call.
            session.commit()
            return overview

    # -- writes (each: ledger write + refresh enqueue, ONE transaction) ------

    def _enqueue_refresh(self, session: Session, portfolio_id: int) -> None:
        enqueue_outbox(
            session,
            TOPIC_PORTFOLIO_VALUATION_REFRESH,
            {"portfolio_id": portfolio_id},
        )
        # Same transaction, same trigger: a new declared fact changes the
        # daily performance series exactly like it changes the valuation.
        enqueue_outbox(
            session,
            TOPIC_PERFORMANCE_REFRESH,
            {"portfolio_id": portfolio_id},
        )
        # Wake-up signal only, delivered on commit; polling remains the
        # delivery guarantee (ADR-006: NOTIFY is never the queue).
        session.execute(
            text("SELECT pg_notify(:channel, :topic)"),
            {
                "channel": OUTBOX_NOTIFY_CHANNEL,
                "topic": TOPIC_PORTFOLIO_VALUATION_REFRESH,
            },
        )

    def record_transaction(
        self,
        *,
        kind: str,
        instrument: Optional[Mapping[str, Any]],
        quantity: Optional[Decimal],
        price: Optional[Decimal],
        amount: Decimal,
        currency: str,
        fees: Decimal,
        effective_at: datetime,
        note: Optional[str],
        now: datetime,
    ) -> int:
        with open_db_session(self._app) as session:
            portfolio = self._get_or_create_main(session)
            event_id = record_ledger_event(
                session,
                portfolio_id=portfolio.id,
                kind=kind,
                amount=amount,
                currency=currency,
                fees=fees,
                effective_at=effective_at,
                recorded_at=now,
                instrument=dict(instrument) if instrument is not None else None,
                quantity=quantity,
                price=price,
                source=PositionLotSource.MANUAL.value,
                note=note,
            )
            self._enqueue_refresh(session, portfolio.id)
            session.commit()
            return event_id

    def compensate_transaction(self, *, event_id: int, note: str, now: datetime) -> int:
        with open_db_session(self._app) as session:
            portfolio = self._get_or_create_main(session)
            compensation_id = compensate_ledger_event(
                session, event_id=event_id, note=note, recorded_at=now
            )
            self._enqueue_refresh(session, portfolio.id)
            session.commit()
            return compensation_id

    def record_import(
        self, rows: Sequence[ValidatedImportRow], *, now: datetime
    ) -> list[int]:
        with open_db_session(self._app) as session:
            portfolio = self._get_or_create_main(session)
            recorded: list[int] = []
            for row in rows:
                recorded.append(
                    record_ledger_event(
                        session,
                        portfolio_id=portfolio.id,
                        kind=row.kind,
                        amount=row.amount,
                        currency=row.currency,
                        fees=row.fees,
                        effective_at=row.effective_at,
                        recorded_at=now,
                        instrument=(
                            {"ticker": row.ticker} if row.ticker is not None else None
                        ),
                        quantity=row.quantity,
                        price=row.price,
                        source=PositionLotSource.IMPORT_CONFIRMED.value,
                        note=row.note,
                    )
                )
            self._enqueue_refresh(session, portfolio.id)
            session.commit()
            return recorded


# ---------------------------------------------------------------------------
# Response builders (pure presentation, no computation)
# ---------------------------------------------------------------------------


def _optional_decimal_str(value: Optional[Decimal]) -> Optional[str]:
    return None if value is None else _decimal_text(value)


def build_portfolio_response(overview: PortfolioOverview) -> PortfolioResponse:
    """Render the journal + lots + last valuation, presentation only.

    ``compensated_by`` is a ledger RELATION (which row corrects which), read
    from the rows themselves; no financial figure is derived here. Absence of
    a published valuation is a NORMAL state relayed honestly.
    """
    compensated_by: dict[int, int] = {}
    for entry in overview.transactions:
        if entry.compensates is not None:
            compensated_by[entry.compensates] = entry.id

    if overview.valuation is None:
        valuation = PortfolioValuationView(
            state="empty",
            snapshot_version=None,
            as_of=None,
            content=None,
            reason="no valuation snapshot published",
        )
    else:
        valuation = PortfolioValuationView(
            state="ok",
            snapshot_version=overview.valuation.version,
            as_of=overview.valuation.as_of,
            # Le contenu de valorisation était relayé sans AUCUNE validation :
            # 100 % de ses champs chaîne passaient verbatim, valeurs monétaires
            # et étiquette `population` comprises. Il subit désormais le même
            # contrat de classe que les autres relais.
            #
            # 6e audit — le contrat de classe ne suffisait pas ici. La nature
            # que `vertex_worker.portfolio` publie n'est pas `population` mais
            # `mark_population` (MARK_POPULATION_SYNTHETIC) : le garde de
            # vocabulaire fermé et de contradiction interne, posé sur la clé
            # LITTÉRALE `population`, la laissait passer en texte libre. Une
            # valorisation réétiquetée `mark_population = "REAL"` alors que ses
            # marks portent toujours `rights = SYNTHETIC` remontait jusqu'au
            # bandeau « DONNÉES RÉELLES » de `PortfolioPage`. `checked_relayed_
            # content` traite désormais la nature comme une CLASSE de champs
            # (voir `snapshot_views.NATURE_LEAF_KEYS`) ; ce relais échoue donc
            # fermé sur cette charge au lieu de la servir.
            content=dict(checked_relayed_content(overview.valuation.content)),
            reason=None,
        )

    return PortfolioResponse(
        portfolio=PortfolioInfo(
            id=overview.portfolio_id,
            name=overview.name,
            base_currency=overview.base_currency,
        ),
        transactions=tuple(
            LedgerTransactionEntry(
                id=entry.id,
                kind=entry.kind,
                instrument=(
                    dict(entry.instrument) if entry.instrument is not None else None
                ),
                quantity=_optional_decimal_str(entry.quantity),
                price=_optional_decimal_str(entry.price),
                amount=_decimal_text(entry.amount),
                currency=entry.currency,
                fees=_decimal_text(entry.fees),
                effective_at=entry.effective_at,
                recorded_at=entry.recorded_at,
                source=entry.source,
                note=entry.note,
                compensates=entry.compensates,
                compensated_by=compensated_by.get(entry.id),
            )
            for entry in overview.transactions
        ),
        lots=tuple(
            PortfolioLotEntry(
                id=lot.id,
                instrument=dict(lot.instrument),
                quantity=_decimal_text(lot.quantity),
                unit_cost=_decimal_text(lot.unit_cost),
                currency=lot.currency,
                opened_at=lot.opened_at,
                source=lot.source,
                note=lot.note,
            )
            for lot in overview.lots
        ),
        valuation=valuation,
    )
