"""Pure builders of the snapshot-backed responses (no I/O, no computation).

These functions translate persisted snapshot content and the declared
capability manifest into the wire DTOs of ``vertex_api.schemas``. They are
presentation only:

- the attention response relays the worker's published items verbatim
  (population, coverage, provenance) and answers an HONEST empty state when
  no snapshot was ever published — never a 500, never invented items;
- the capabilities response crosses the full manifest with what was REALLY
  probed: a capability without any persisted probe is ``ERROR`` with reason
  ``NEVER_TESTED`` (fail-closed), a probe whose status is not a canonical
  ``SourceCapabilityStatus`` is ``ERROR`` with reason ``INVALID_STATUS``,
  and conflicting field statuses inside the winning probe collapse to
  ``ERROR`` with reason ``CONFLICTING_FIELD_STATUSES``.

No price, Greek, score, probability or verdict is ever computed here.

FAIL-CLOSED SHAPE CHECK (P1-7). Every builder validates the persisted content
against what the WIRE CONTRACT really constrains — not merely "a string is a
string": a non-empty string where the DTO requires one, ``>= 0`` or ``> 0``
where the DTO constrains the sign, string keys where the DTO expects a
``FrozenStrMapping``. The refusal is therefore always a
:class:`SnapshotContentError` naming its field, never a raw pydantic
``ValidationError`` — whose message quotes ``input_value``, i.e. THE STORED
VALUE, and would carry a fragment of the persisted payload into the server
log (``.claude/rules/security.md``).
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from functools import lru_cache
from typing import Any, Callable, Mapping, Optional, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from vertex_core.contracts.enums import (
    DelayStatus,
    Direction,
    EnvelopeQuality,
    ExerciseStyle,
    IdentityStatus,
    OptionRight,
    SettlementType,
    SnapshotQuality,
    SourceCapabilityStatus,
)
from vertex_persistence.repository.snapshots import CurrentSnapshot

from vertex_api.capability_manifest import CapabilityDeclaration, CapabilityManifest
from vertex_api.schemas import (
    AnalysisResponse,
    AttentionItem,
    AttentionSnapshotResponse,
    CapabilityStatusEntry,
    DbHealth,
    MarketsBreadth,
    MarketsCoverage,
    MarketsDiscardedTicker,
    MarketsOverviewResponse,
    MarketsRejectedRecord,
    MarketsSector,
    MarketsTicker,
    OptionChainContract,
    OptionChainExpiration,
    OptionChainResponse,
    SnapshotHealth,
    SystemCapabilitiesResponse,
    SystemHealth,
    WorkerHealth,
)

__all__ = [
    "DATA_STATE_LABELS",
    "DELAY_STATUS_LABELS",
    "MAX_RELAYED_CODE_LENGTH",
    "MAX_RELAYED_DEPTH",
    "MAX_RELAYED_TEXT_LENGTH",
    "MAX_RELAYED_USER_TEXT_LENGTH",
    "POPULATION_LABELS",
    "VALUE_NATURE_LABELS",
    "REASON_CONFLICTING_FIELD_STATUSES",
    "REASON_INVALID_STATUS",
    "REASON_NEVER_TESTED",
    "REASON_NO_SNAPSHOT_PUBLISHED",
    "SnapshotContentError",
    "build_analysis_response",
    "build_attention_response",
    "build_capabilities_response",
    "build_markets_overview_response",
    "build_option_chain_response",
    "build_system_health",
    "checked_relayed_content",
]

REASON_NO_SNAPSHOT_PUBLISHED = "no snapshot published"
REASON_NEVER_TESTED = "NEVER_TESTED"
REASON_INVALID_STATUS = "INVALID_STATUS"
REASON_CONFLICTING_FIELD_STATUSES = "CONFLICTING_FIELD_STATUSES"

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


class SnapshotContentError(ValueError):
    """Persisted snapshot content does not match its published schema.

    ``field`` is the DOTTED PATH of the offending field inside the persisted
    content (``items[3].title``, ``coverage.lookback_seconds``...). It is the
    only part of this exception that may be logged: the message itself is a
    developer/test aid and may quote a stored value, whereas a log record may
    never carry a fragment of the persisted payload
    (``.claude/rules/security.md``). ``field`` stays ``None`` when the caller
    could not name one — the handler then logs an explicit ``unknown``.
    """

    def __init__(self, message: str, *, field: Optional[str] = None) -> None:
        super().__init__(message)
        self.field = field


def _parse_utc(value: Any, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise SnapshotContentError(f"{field}: ISO-8601 string required", field=field)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise SnapshotContentError(
            f"{field}: invalid ISO-8601 datetime", field=field
        ) from exc
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        raise SnapshotContentError(f"{field}: naive datetime rejected", field=field)
    return parsed.astimezone(timezone.utc)


def _parse_utc_or_none(value: Any) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        return None
    return parsed.astimezone(timezone.utc)


def _require_mapping(value: Any, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SnapshotContentError(f"{field}: mapping required", field=field)
    return value


def _require_list(value: Any, *, field: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise SnapshotContentError(f"{field}: list required", field=field)
    return value


def _wire_mapping(value: Any, *, field: str) -> dict[str, Any]:
    """A mapping relayed as-is into a ``FrozenStrMapping`` wire field.

    The wire contract is ``Mapping[str, Any]`` in STRICT mode: a persisted
    mapping carrying a non-string key would be refused by pydantic itself,
    and the resulting ``ValidationError`` quotes that key — a stored value —
    in its message. The check therefore happens HERE, so the refusal stays a
    :class:`SnapshotContentError` naming the field only.
    """
    mapping = _require_mapping(value, field=field)
    for key in mapping:
        if not isinstance(key, str):
            raise SnapshotContentError(
                f"{field}: string keys required", field=field
            )
    return dict(mapping)


def _str_tuple(value: Any, *, field: str) -> tuple[str, ...]:
    items = _require_list(value, field=field)
    result: list[str] = []
    for entry in items:
        if not isinstance(entry, str) or not entry:
            raise SnapshotContentError(
                f"{field}: non-empty strings required", field=field
            )
        result.append(entry)
    return tuple(result)


# ---------------------------------------------------------------------------
# Form contracts of every RELAYED value (P1-1)
# ---------------------------------------------------------------------------
#
# "Verbatim relay" is not "arbitrary relay". The checks above answer the
# question "is this field a string?"; they never answered "is this string a
# PRICE, a NATURE LABEL or a sentence?". A snapshot whose ``strike`` held an
# ANSI escape sequence followed by five thousand filler characters was
# therefore served 200, with that value reproduced verbatim on the wire.
#
# The frontier that ADMITS a source-controlled value is the worker
# (``vertex_worker.analysis``: ``_price_or_none``, ``_currency_or_none``,
# ``_trading_day_or_none``, ``_basis_code_or_none``). The relay is the LAST
# frontier before a human reads the value, and it re-states the SAME kind of
# contract on what it publishes — deny-by-default, never a repair:
#
# - a FINANCIAL value (money, strike, premium, quote, Greek, IV, weight,
#   ratio, percentage) must be a plain decimal string, as
#   ``financial-safety.md`` requires. No exponent, no underscore, no Unicode
#   digit, no surrounding whitespace — everything ``Decimal`` would silently
#   accept and the relay would then publish as a price;
# - a NATURE LABEL (``population``, ``value_nature``, ``data_state``,
#   ``delay_status``) belongs to a CLOSED vocabulary. These are the fields
#   that keep real, delayed, theoretical, simulated and demonstration apart:
#   left free, they let synthetic content claim to be something else;
# - a CANONICAL enumerated value (``right``, ``style``, ``settlement``,
#   ``direction``, ``quality``, ``identity_status``) is READ from
#   ``vertex_core.contracts.enums`` — the single vocabulary authority — and
#   never redefined here;
# - a TECHNICAL CODE (identity, event id, gate id, engine version, content
#   hash, currency, calendar day, instant, IANA timezone) must match its
#   declared shape;
# - a PROSE field (title, label, reason, message, note, user statement) has
#   no vocabulary to impose, so the contract is the only one that HOLDS for
#   free text: a length bound and the refusal of control characters — the
#   escapes a terminal, a log viewer or a browser would interpret instead of
#   displaying.
#
# Deny-by-default applies to the LEAF KEY NAME: a key this map does not know
# falls back to the PROSE contract, which is still bounded and control-free.
# A field added upstream is therefore relayed under a real constraint before
# this map learns about it — it is simply not YET constrained as a decimal or
# as a closed label, which is what the lot report quantifies as residual.
#
# Refusals stay :class:`SnapshotContentError` naming the FIELD PATH only —
# never the stored value, neither in the response body nor in a log record.

MAX_RELAYED_CODE_LENGTH = 128
"""Technical codes: identities, versions, hashes, event ids."""

MAX_RELAYED_TEXT_LENGTH = 512
"""Prose the SYSTEM writes: titles, reasons, methods, conclusions."""

MAX_RELAYED_USER_TEXT_LENGTH = 5000
"""Prose the USER writes (thesis statement and falsifier).

Same bound as the write contract (``vertex_api.follow_up.NonBlankText``): the
relay must be able to serve back exactly what the API accepted, never less.
"""

MAX_RELAYED_INSTANT_LENGTH = 64
MAX_RELAYED_DEPTH = 32
"""Nesting bound of a relayed content (a persisted payload is data, not a
recursion budget)."""

_CONTROL_CHARS = re.compile(
    "[\x00-\x1f\x7f-\x9f\u061c\u200b-\u200f\u2028\u2029"
    "\u202a-\u202e\u2066-\u2069\ufeff]"
)
"""C0/C1 controls, DEL, zero-width characters, bidirectional overrides and
the Unicode line/paragraph separators. None of them is content: they are what
turns a relayed string into terminal escapes, invisible text, or text a
reader sees in an order it was not written in."""

_CONTROL_CHARS_ALLOWING_LAYOUT = re.compile(
    "[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u061c"
    "\u200b-\u200f\u2028\u2029\u202a-\u202e\u2066-\u2069\ufeff]"
)
"""Same set MINUS tab, newline and carriage return: a user-written statement
may be laid out over several lines, and the relay must serve back exactly
what the write contract accepted."""

_UNSIGNED_DECIMAL_RE = re.compile(r"^(?:0|[1-9][0-9]{0,17})(?:\.[0-9]{1,30})?$")
"""Plain non-negative decimal string, ASCII digits only.

Same intent as ``vertex_worker.analysis._PRICE_RE``, widened on the FRACTION
only: the engines publish float64 results at full precision through
``format(Decimal(repr(value)), "f")``.
"""

_SIGNED_DECIMAL_RE = re.compile(r"^-?(?:0|[1-9][0-9]{0,17})(?:\.[0-9]{1,30})?$")
"""Same shape with an optional minus: a Greek, a rate or a P&L is signed."""

_PERCENT_DECIMAL_RE = re.compile(r"^[+-]?(?:0|[1-9][0-9]{0,17})(?:\.[0-9]{1,30})?$")
"""Same shape with an EXPLICIT sign allowed: published percentages carry one
(``+1.74``) so the direction reads without a recomputation."""

_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
"""ISO-4217 alphabetic code — identical to the worker's admission rule."""

_TRADING_DAY_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
"""Strict ISO calendar day (the value must ALSO be a real date)."""

_CODE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@/+-]{0,127}$")
"""Technical code: identity, version, hash, event id, resource path."""

_UPPER_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
"""Uppercase status/reason token."""

_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
"""Canonical hash reference, the SAME shape as
``vertex_core.contracts.types.Sha256Ref`` (the contract type the calculation
record itself declares). Read from that authority, never widened here."""

_UNIT_RE = re.compile(r"^[A-Za-z0-9%$€£¥][A-Za-z0-9%$€£¥/_.-]{0,15}$")
"""Display unit (``%``, ``return_ratio``)."""

_MAPPING_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@/+-]{0,127}$")
"""A key of a relayed mapping travels to the wire exactly like a value."""

POPULATION_LABELS: frozenset[str] = frozenset(
    {
        "REAL",
        "DELAYED",
        "THEORETICAL",
        "SIMULATED",
        "SYNTHETIC",
        "DEMO",
        "USER_DECLARED",
        "SYNTHETIC_MARKS_REAL_LEDGER",
        "EMPTY",
    }
)
"""CLOSED vocabulary of the field that separates real from everything else.

``population`` is what a reader uses to know whether what is displayed is an
observation, a delayed observation, a theoretical value, a simulation, a
demonstration or a user declaration. Left free, it lets synthetic content
present itself as something else — exactly what ``financial-safety.md``
forbids (real, delayed, theoretical, simulated and demonstration never share
a status). Adding a member is an explicit, reviewed contract change, never
an accident of a persisted payload.
"""

VALUE_NATURE_LABELS: frozenset[str] = frozenset({"THEORETICAL"})
"""CLOSED vocabulary of ``value_nature``.

``THEORETICAL`` is the ONLY nature the workers declare today
(``vertex_worker.options.VALUE_NATURE_THEORETICAL``). The relay closes the
set on what really exists instead of reserving room for natures no producer
publishes.
"""

DATA_STATE_LABELS: frozenset[str] = frozenset({"ok", "partial", "stale"})
"""CLOSED vocabulary of the markets ``data_state``."""

DELAY_STATUS_LABELS: frozenset[str] = frozenset(
    member.value for member in DelayStatus
)
"""CLOSED vocabulary of ``delay_status``, READ from ``vertex_core``."""

_QUALITY_LABELS: frozenset[str] = frozenset(
    member.value for member in EnvelopeQuality
) | frozenset(member.value for member in SnapshotQuality)
"""Both canonical quality namespaces, read from ``vertex_core``. They never
convert into one another (ADR-014); the relay only refuses a label that
belongs to neither."""

_OPTION_RIGHT_LABELS = frozenset(member.value for member in OptionRight)
_EXERCISE_STYLE_LABELS = frozenset(member.value for member in ExerciseStyle)
_SETTLEMENT_LABELS = frozenset(member.value for member in SettlementType)
_DIRECTION_LABELS = frozenset(member.value for member in Direction)
_IDENTITY_STATUS_LABELS = frozenset(member.value for member in IdentityStatus)


def _reject_control_chars(
    value: str, *, field: str, allow_layout: bool = False
) -> None:
    pattern = _CONTROL_CHARS_ALLOWING_LAYOUT if allow_layout else _CONTROL_CHARS
    if pattern.search(value):
        raise SnapshotContentError(
            f"{field}: control characters are not relayable content", field=field
        )


def _bounded(value: str, *, field: str, limit: int) -> None:
    if len(value) > limit:
        raise SnapshotContentError(
            f"{field}: relayed string longer than the {limit}-character budget "
            "of its field class",
            field=field,
        )


def _relayed_text(value: str, *, field: str) -> None:
    """Prose the SYSTEM writes: no vocabulary, but a bound and no escapes."""
    _bounded(value, field=field, limit=MAX_RELAYED_TEXT_LENGTH)
    _reject_control_chars(value, field=field)


def _relayed_user_text(value: str, *, field: str) -> None:
    """Prose the USER wrote: same contract, line layout preserved."""
    _bounded(value, field=field, limit=MAX_RELAYED_USER_TEXT_LENGTH)
    _reject_control_chars(value, field=field, allow_layout=True)


def _relayed_code(value: str, *, field: str) -> None:
    if not _CODE_RE.fullmatch(value):
        raise SnapshotContentError(
            f"{field}: technical code shape required", field=field
        )


def _relayed_upper_code(value: str, *, field: str) -> None:
    if not _UPPER_CODE_RE.fullmatch(value):
        raise SnapshotContentError(
            f"{field}: uppercase status token required", field=field
        )


def _relayed_hash(value: str, *, field: str) -> None:
    if not _HASH_RE.fullmatch(value):
        raise SnapshotContentError(
            f"{field}: namespaced content hash required", field=field
        )


def _relayed_unit(value: str, *, field: str) -> None:
    if not _UNIT_RE.fullmatch(value):
        raise SnapshotContentError(
            f"{field}: display unit shape required", field=field
        )


def _relayed_decimal(value: str, *, field: str) -> None:
    if not _UNSIGNED_DECIMAL_RE.fullmatch(value):
        raise SnapshotContentError(
            f"{field}: plain non-negative decimal string required", field=field
        )


def _relayed_signed_decimal(value: str, *, field: str) -> None:
    if not _SIGNED_DECIMAL_RE.fullmatch(value):
        raise SnapshotContentError(
            f"{field}: plain signed decimal string required", field=field
        )


def _relayed_percent(value: str, *, field: str) -> None:
    if not _PERCENT_DECIMAL_RE.fullmatch(value):
        raise SnapshotContentError(
            f"{field}: plain signed decimal percentage required", field=field
        )


def _relayed_currency(value: str, *, field: str) -> None:
    if not _CURRENCY_RE.fullmatch(value):
        raise SnapshotContentError(
            f"{field}: ISO-4217 alphabetic currency code required", field=field
        )


def _relayed_trading_day(value: str, *, field: str) -> None:
    if not _TRADING_DAY_RE.fullmatch(value):
        raise SnapshotContentError(
            f"{field}: ISO-8601 calendar day required", field=field
        )
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise SnapshotContentError(
            f"{field}: ISO-8601 calendar day required", field=field
        ) from exc


def _relayed_instant(value: str, *, field: str) -> None:
    _bounded(value, field=field, limit=MAX_RELAYED_INSTANT_LENGTH)
    _parse_utc(value, field=field)


@lru_cache(maxsize=512)
def _is_iana_timezone(value: str) -> bool:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        return False
    return True


def _relayed_timezone(value: str, *, field: str) -> None:
    """An exchange timezone must be an IANA zone the runtime can RESOLVE.

    P2-1: ``_require_str`` alone accepted ``Mars/Olympus`` and the calendar
    served it 200 with ``state = "ok"``. A timezone nothing resolves makes
    the local instants published beside it unverifiable, so it fails closed
    like every other present-but-unreadable value of page 02.
    """
    _bounded(value, field=field, limit=MAX_RELAYED_CODE_LENGTH)
    _reject_control_chars(value, field=field)
    if not _is_iana_timezone(value):
        raise SnapshotContentError(
            f"{field}: resolvable IANA timezone identifier required", field=field
        )


def _closed_set(labels: frozenset[str], what: str) -> Callable[..., None]:
    def _check(value: str, *, field: str) -> None:
        if value not in labels:
            raise SnapshotContentError(
                f"{field}: {what} outside its closed vocabulary", field=field
            )

    return _check


_relayed_population = _closed_set(POPULATION_LABELS, "nature label")
_relayed_value_nature = _closed_set(VALUE_NATURE_LABELS, "value nature")
_relayed_data_state = _closed_set(DATA_STATE_LABELS, "data state")
_relayed_delay_status = _closed_set(DELAY_STATUS_LABELS, "delay status")
_relayed_quality = _closed_set(_QUALITY_LABELS, "quality label")
_relayed_right = _closed_set(_OPTION_RIGHT_LABELS, "option right")
_relayed_style = _closed_set(_EXERCISE_STYLE_LABELS, "exercise style")
_relayed_settlement = _closed_set(_SETTLEMENT_LABELS, "settlement type")
_relayed_direction = _closed_set(_DIRECTION_LABELS, "direction")
_relayed_identity_status = _closed_set(_IDENTITY_STATUS_LABELS, "identity status")


_DECIMAL_KEYS: tuple[str, ...] = (
    "amount",
    "ask",
    "bid",
    "close",
    "coverage_threshold",
    "high",
    "iv",
    "iv_scenarios",
    "last_close",
    "low",
    "maturity_years",
    "open",
    "premium",
    "previous_close",
    "spot_grid",
    "strike",
    "time_grid_years",
    "value",
    "weight_global",
    "weight_in_sector",
)
"""Non-negative financial values relayed as decimal strings."""

_SIGNED_DECIMAL_KEYS: tuple[str, ...] = (
    # Les agrégats monétaires d'un portefeuille sont SIGNÉS : une position
    # vendeuse déclarée donne une valeur négative, un solde de trésorerie peut
    # être débiteur, une correction de frais peut être un remboursement. Les
    # exiger positifs refuserait des états réels — le contrat qui compte ici
    # est « c'est un décimal », pas « c'est positif ».
    "cash",
    "delta",
    "fees_cumulative",
    "gross_value",
    "net_value",
    "position_value",
    "dividend_yield",
    "gamma",
    "grid",
    "rate",
    "coverage_ratio",
    "return_1d",
    "rho",
    "rho_per_bp",
    "theta",
    "theta_per_calendar_day",
    "total_return",
    "vega",
    "vega_per_point",
)
"""Signed financial values (a Greek, a rate, a return, a P&L cell)."""

_PERCENT_KEYS: tuple[str, ...] = (
    "coverage_pct",
    "coverage_threshold_pct",
    "return_1d_pct",
    "value_pct",
    "weight_global_pct",
    "weight_in_sector_pct",
)

_INSTANT_KEYS: tuple[str, ...] = (
    "as_of",
    "content_as_of",
    "created_at",
    "event_time_local",
    "event_time_utc",
    "expires_at",
    "first_published_at",
    "last_received_at",
    "last_recorded_at",
    "last_reviewed_at",
    "observed_as_of",
    "observed_at",
    "previous_event_time_utc",
    "reference_instant",
    "revised_at",
    "review_due_at",
    "snapshot_as_of",
    "snooze_until",
    "stale_after",
    "tested_at",
    "valid_until",
)

_TRADING_DAY_KEYS: tuple[str, ...] = (
    "expiration",
    "first_trading_day",
    "last_trading_day",
    "previous_trading_day",
    "trading_day",
)

_CODE_KEYS: tuple[str, ...] = (
    "adjustment_basis",
    "advice_id",
    "calculation_id",
    "capability_id",
    "cluster_id",
    "content_schema_version",
    "degraded_gates",
    "engine_version",
    "event_id",
    "evidence_cluster_ids",
    "evidence_ids",
    "exchange",
    "field",
    "fusion_ruleset_version",
    "gate_id",
    "input_snapshot_id",
    "instrument",
    "instrument_id",
    "instrument_ref",
    "instrument_ticker",
    "item_id",
    "key",
    "kind",
    "id",
    "member_event_ids",
    "missing_evidence",
    "policy_version",
    "probe_id",
    "profile_id",
    "rel",
    "relevance_reasons",
    "resource",
    "rule_version",
    "scenario_ids",
    "ruleset_version",
    "schema_version",
    "sector",
    "source",
    "source_event_id",
    "source_tier",
    "sources",
    "ticker",
    "tickers",
    "trading_class",
    "underlying",
    "unit",
    "version",
)

_UPPER_CODE_KEYS: tuple[str, ...] = (
    "agenda_state",
    "bars_status",
    "category",
    "code",
    "failed_gates",
    "filtered_reason",
    "last_action",
    "open_interest_status",
    "premium_side",
    "previous_status",
    "quote_side",
    "quote_side_for_iv",
    "reason_code",
    "rights",
    "scenarios_status",
    "scope",
    "status",
    "version_state",
)
"""Uppercase tokens.

``rights`` sits here rather than in a closed set on purpose: no module of
``vertex_core`` owns an entitlement vocabulary (the edge publishes
``IBKR_MARKET_DATA_DISPLAY_ONLY``, the generator ``SYNTHETIC``, the probe
``DEMO``), so closing the set here would INVENT an authority this relay does
not hold. The constraint is therefore a shape one, and the residue is stated
in the lot report instead of being hidden.
"""

_HASH_KEYS: tuple[str, ...] = ("input_hash", "result_hash")
"""The two fields ``vertex_core`` really types as ``Sha256Ref``.

``advice_id``, ``cluster_id``, ``evidence_ids`` and ``scenario_ids`` HOLD a
canonical hash today but their contract type is ``NonEmptyStr``: they stay
technical codes here, because closing them tighter than their own contract
would make the relay stricter than the authority that produces them.
"""

_USER_TEXT_KEYS: tuple[str, ...] = ("hypotheses", "invalidation")

_CLASS_BY_LEAF_KEY: dict[str, Callable[..., None]] = {
    # Nature labels — CLOSED vocabularies (see POPULATION_LABELS).
    "population": _relayed_population,
    "theses": _relayed_population,
    "information_context": _relayed_population,
    "value_nature": _relayed_value_nature,
    "data_state": _relayed_data_state,
    "delay_status": _relayed_delay_status,
    # Canonical enumerations, READ from vertex_core.
    "quality": _relayed_quality,
    "right": _relayed_right,
    "style": _relayed_style,
    "settlement": _relayed_settlement,
    "direction": _relayed_direction,
    "identity_status": _relayed_identity_status,
    # Typed scalars.
    "currency": _relayed_currency,
    "exchange_timezone": _relayed_timezone,
    "display_unit": _relayed_unit,
}
_CLASS_BY_LEAF_KEY.update({key: _relayed_decimal for key in _DECIMAL_KEYS})
_CLASS_BY_LEAF_KEY.update(
    {key: _relayed_signed_decimal for key in _SIGNED_DECIMAL_KEYS}
)
_CLASS_BY_LEAF_KEY.update({key: _relayed_percent for key in _PERCENT_KEYS})
_CLASS_BY_LEAF_KEY.update({key: _relayed_instant for key in _INSTANT_KEYS})
_CLASS_BY_LEAF_KEY.update({key: _relayed_trading_day for key in _TRADING_DAY_KEYS})
_CLASS_BY_LEAF_KEY.update({key: _relayed_code for key in _CODE_KEYS})
_CLASS_BY_LEAF_KEY.update({key: _relayed_upper_code for key in _UPPER_CODE_KEYS})
_CLASS_BY_LEAF_KEY.update({key: _relayed_hash for key in _HASH_KEYS})
_CLASS_BY_LEAF_KEY.update({key: _relayed_user_text for key in _USER_TEXT_KEYS})


def _leaf_key(path: str) -> str:
    """The JSON key a leaf belongs to, list indices removed."""
    tail = path.rsplit(".", 1)[-1]
    bracket = tail.find("[")
    return tail if bracket < 0 else tail[:bracket]


def _check_relayed_string(value: str, *, field: str) -> None:
    if not value:
        raise SnapshotContentError(
            f"{field}: non-empty string required", field=field
        )
    _CLASS_BY_LEAF_KEY.get(_leaf_key(field), _relayed_text)(value, field=field)


def checked_relayed_content(
    content: Any, *, field: str = "content"
) -> Mapping[str, Any]:
    """Fail-closed FORM check of every value a relay is about to publish.

    Walks the persisted content and applies, to every string leaf and every
    mapping key, the contract of its field class: decimal, closed nature
    label, canonical enumeration, technical code, instant, calendar day, IANA
    timezone, or bounded control-free prose. The content is returned
    UNCHANGED — nothing is repaired, truncated, escaped or defaulted: a value
    out of shape is REFUSED, with a :class:`SnapshotContentError` naming its
    path and never its value.
    """
    mapping = _require_mapping(content, field=field)

    def walk(node: Any, path: str, depth: int) -> None:
        if depth > MAX_RELAYED_DEPTH:
            raise SnapshotContentError(
                f"{path or field}: relayed content nested deeper than the "
                f"{MAX_RELAYED_DEPTH}-level budget",
                field=path or field,
            )
        if isinstance(node, Mapping):
            for key, value in node.items():
                if not isinstance(key, str) or not key:
                    raise SnapshotContentError(
                        f"{path or field}: string keys required",
                        field=path or field,
                    )
                if not _MAPPING_KEY_RE.fullmatch(key):
                    raise SnapshotContentError(
                        f"{path or field}: relayed mapping key out of shape",
                        field=path or field,
                    )
                walk(value, f"{path}.{key}" if path else key, depth + 1)
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{path}[{index}]", depth + 1)
        elif isinstance(node, str):
            _check_relayed_string(node, field=path or field)

    walk(mapping, "", 0)
    return mapping


# ---------------------------------------------------------------------------
# Attention
# ---------------------------------------------------------------------------


def _attention_item(raw: Any, *, index: int) -> AttentionItem:
    item = _require_mapping(raw, field=f"items[{index}]")
    provenance = _wire_mapping(
        item.get("provenance"), field=f"items[{index}].provenance"
    )
    reasons = _str_tuple(
        item.get("relevance_reasons"), field=f"items[{index}].relevance_reasons"
    )
    synthetic = _require_bool(
        item.get("synthetic"), field=f"items[{index}].synthetic"
    )
    return AttentionItem(
        id=_require_str(item.get("item_id"), field=f"items[{index}].item_id"),
        title=_require_str(item.get("title"), field=f"items[{index}].title"),
        sources=_str_tuple(provenance.get("sources"), field=f"items[{index}].provenance.sources"),
        rights=_str_tuple(provenance.get("rights"), field=f"items[{index}].provenance.rights"),
        relevance_reasons=reasons[:3],
        synthetic=synthetic,
        provenance=provenance,
    )


def build_attention_response(
    snapshot: Optional[CurrentSnapshot],
) -> AttentionSnapshotResponse:
    """Render the last attention snapshot, or the honest empty state.

    Absence of a published snapshot is a NORMAL state (200): every
    snapshot-derived field stays ``None`` and ``reason`` explains why —
    nothing is invented, nothing degrades into a 500.
    """
    if snapshot is None:
        return AttentionSnapshotResponse(
            state="empty",
            snapshot_version=None,
            as_of=None,
            population=None,
            coverage=None,
            items=(),
            rejected_count=None,
            reason=REASON_NO_SNAPSHOT_PUBLISHED,
        )

    content = checked_relayed_content(snapshot.content)
    items_raw = _require_list(content.get("items"), field="items")
    rejected_raw = _require_list(content.get("rejected"), field="rejected")
    population = _require_str(content.get("population"), field="population")
    coverage = _wire_mapping(content.get("coverage"), field="coverage")

    return AttentionSnapshotResponse(
        state="ok",
        snapshot_version=snapshot.version,
        as_of=_parse_utc(content.get("as_of"), field="as_of"),
        population=population,
        coverage=coverage,
        items=tuple(
            _attention_item(raw, index=index) for index, raw in enumerate(items_raw)
        ),
        rejected_count=len(rejected_raw),
        reason=None,
    )


# ---------------------------------------------------------------------------
# Markets overview
# ---------------------------------------------------------------------------


def _require_str(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise SnapshotContentError(
            f"{field}: non-empty string required", field=field
        )
    return value


def _optional_str(value: Any, *, field: str) -> Optional[str]:
    if value is None:
        return None
    return _require_str(value, field=field)


def _require_int(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SnapshotContentError(f"{field}: integer required", field=field)
    return value


def _require_non_negative_int(value: Any, *, field: str) -> int:
    """An integer the wire contract constrains to ``>= 0``."""
    result = _require_int(value, field=field)
    if result < 0:
        raise SnapshotContentError(
            f"{field}: non-negative integer required", field=field
        )
    return result


def _require_positive_int(value: Any, *, field: str) -> int:
    """An integer the wire contract constrains to ``> 0``."""
    result = _require_int(value, field=field)
    if result <= 0:
        raise SnapshotContentError(
            f"{field}: positive integer required", field=field
        )
    return result


def _require_bool(value: Any, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise SnapshotContentError(f"{field}: boolean required", field=field)
    return value


def _markets_ticker(raw: Any, *, field: str) -> MarketsTicker:
    entry = _require_mapping(raw, field=field)
    return MarketsTicker(
        ticker=_require_str(entry.get("ticker"), field=f"{field}.ticker"),
        sector=_require_str(entry.get("sector"), field=f"{field}.sector"),
        trading_day=_require_str(entry.get("trading_day"), field=f"{field}.trading_day"),
        previous_trading_day=_require_str(
            entry.get("previous_trading_day"), field=f"{field}.previous_trading_day"
        ),
        last_close=_require_str(entry.get("last_close"), field=f"{field}.last_close"),
        previous_close=_require_str(
            entry.get("previous_close"), field=f"{field}.previous_close"
        ),
        currency=_optional_str(entry.get("currency"), field=f"{field}.currency"),
        return_1d=_require_str(entry.get("return_1d"), field=f"{field}.return_1d"),
        return_1d_pct=_require_str(
            entry.get("return_1d_pct"), field=f"{field}.return_1d_pct"
        ),
        weight_in_sector=_require_str(
            entry.get("weight_in_sector"), field=f"{field}.weight_in_sector"
        ),
        weight_in_sector_pct=_require_str(
            entry.get("weight_in_sector_pct"), field=f"{field}.weight_in_sector_pct"
        ),
        weight_global=_require_str(
            entry.get("weight_global"), field=f"{field}.weight_global"
        ),
        weight_global_pct=_require_str(
            entry.get("weight_global_pct"), field=f"{field}.weight_global_pct"
        ),
        quality=_require_str(entry.get("quality"), field=f"{field}.quality"),
        synthetic=_require_bool(entry.get("synthetic"), field=f"{field}.synthetic"),
        calculation=_wire_mapping(
            entry.get("calculation"), field=f"{field}.calculation"
        ),
    )


def _markets_sector(raw: Any, *, index: int) -> MarketsSector:
    field = f"sectors[{index}]"
    entry = _require_mapping(raw, field=field)
    tickers_raw = _require_list(entry.get("tickers"), field=f"{field}.tickers")
    return MarketsSector(
        sector=_require_str(entry.get("sector"), field=f"{field}.sector"),
        label=_require_str(entry.get("label"), field=f"{field}.label"),
        declared_count=_require_non_negative_int(
            entry.get("declared_count"), field=f"{field}.declared_count"
        ),
        covered_count=_require_non_negative_int(
            entry.get("covered_count"), field=f"{field}.covered_count"
        ),
        tickers=tuple(
            _markets_ticker(ticker, field=f"{field}.tickers[{i}]")
            for i, ticker in enumerate(tickers_raw)
        ),
    )


def _markets_breadth(raw: Any) -> MarketsBreadth:
    entry = _require_mapping(raw, field="breadth")
    status = entry.get("status")
    if status not in ("OK", "INVALID"):
        raise SnapshotContentError(
            "breadth.status: 'OK' or 'INVALID' required", field="breadth.status"
        )
    calculation = entry.get("calculation")
    return MarketsBreadth(
        status=status,
        reason=_optional_str(entry.get("reason"), field="breadth.reason"),
        value=_optional_str(entry.get("value"), field="breadth.value"),
        value_pct=_optional_str(entry.get("value_pct"), field="breadth.value_pct"),
        above_count=_require_non_negative_int(
            entry.get("above_count"), field="breadth.above_count"
        ),
        covered_count=_require_non_negative_int(
            entry.get("covered_count"), field="breadth.covered_count"
        ),
        universe_size=_require_positive_int(
            entry.get("universe_size"), field="breadth.universe_size"
        ),
        coverage_pct=_require_str(
            entry.get("coverage_pct"), field="breadth.coverage_pct"
        ),
        coverage_threshold=_require_str(
            entry.get("coverage_threshold"), field="breadth.coverage_threshold"
        ),
        coverage_threshold_pct=_require_str(
            entry.get("coverage_threshold_pct"), field="breadth.coverage_threshold_pct"
        ),
        calculation=(
            None
            if calculation is None
            else _wire_mapping(calculation, field="breadth.calculation")
        ),
    )


def _markets_coverage(raw: Any) -> MarketsCoverage:
    entry = _require_mapping(raw, field="coverage")
    discarded_raw = _require_list(
        entry.get("discarded_tickers"), field="coverage.discarded_tickers"
    )
    rejected_raw = _require_list(
        entry.get("rejected_records"), field="coverage.rejected_records"
    )
    discarded = []
    for i, item in enumerate(discarded_raw):
        mapping = _require_mapping(item, field=f"coverage.discarded_tickers[{i}]")
        discarded.append(
            MarketsDiscardedTicker(
                ticker=_require_str(
                    mapping.get("ticker"), field=f"coverage.discarded_tickers[{i}].ticker"
                ),
                reason=_require_str(
                    mapping.get("reason"), field=f"coverage.discarded_tickers[{i}].reason"
                ),
            )
        )
    rejected = []
    for i, item in enumerate(rejected_raw):
        mapping = _require_mapping(item, field=f"coverage.rejected_records[{i}]")
        rejected.append(
            MarketsRejectedRecord(
                event_id=_require_str(
                    mapping.get("event_id"), field=f"coverage.rejected_records[{i}].event_id"
                ),
                reason=_require_str(
                    mapping.get("reason"), field=f"coverage.rejected_records[{i}].reason"
                ),
            )
        )
    return MarketsCoverage(
        expected=_require_non_negative_int(
            entry.get("expected"), field="coverage.expected"
        ),
        received=_require_non_negative_int(
            entry.get("received"), field="coverage.received"
        ),
        covered=_require_non_negative_int(
            entry.get("covered"), field="coverage.covered"
        ),
        discarded=_require_non_negative_int(
            entry.get("discarded"), field="coverage.discarded"
        ),
        discarded_tickers=tuple(discarded),
        rejected_records=tuple(rejected),
        observations_considered=_require_non_negative_int(
            entry.get("observations_considered"),
            field="coverage.observations_considered",
        ),
        lookback_seconds=_require_positive_int(
            entry.get("lookback_seconds"), field="coverage.lookback_seconds"
        ),
    )


def build_markets_overview_response(
    snapshot: Optional[CurrentSnapshot],
) -> MarketsOverviewResponse:
    """Render the last markets overview snapshot, or the honest empty state.

    Presentation only: the persisted content is validated fail-closed into
    the wire DTOs and relayed VERBATIM — no price, return, weight, breadth or
    percentage is ever recomputed here. Absence of a published snapshot is a
    NORMAL state (200 with ``state = "empty"``), never a 500 and never an
    invented zero.
    """
    if snapshot is None:
        return MarketsOverviewResponse(
            state="empty",
            snapshot_version=None,
            as_of=None,
            population=None,
            data_state=None,
            unit=None,
            display_unit=None,
            engine_version=None,
            conclusion=None,
            sectors=(),
            breadth=None,
            coverage=None,
            reason=REASON_NO_SNAPSHOT_PUBLISHED,
        )

    content = checked_relayed_content(snapshot.content)
    sectors_raw = _require_list(content.get("sectors"), field="sectors")
    data_state = content.get("data_state")
    if data_state not in ("ok", "partial", "stale"):
        raise SnapshotContentError(
            "data_state: 'ok', 'partial' or 'stale' required", field="data_state"
        )

    return MarketsOverviewResponse(
        state="ok",
        snapshot_version=snapshot.version,
        as_of=_parse_utc(content.get("as_of"), field="as_of"),
        population=_require_str(content.get("population"), field="population"),
        data_state=data_state,
        unit=_require_str(content.get("unit"), field="unit"),
        display_unit=_require_str(content.get("display_unit"), field="display_unit"),
        engine_version=_require_str(
            content.get("engine_version"), field="engine_version"
        ),
        conclusion=_require_str(content.get("conclusion"), field="conclusion"),
        sectors=tuple(
            _markets_sector(raw, index=index) for index, raw in enumerate(sectors_raw)
        ),
        breadth=_markets_breadth(content.get("breadth")),
        coverage=_markets_coverage(content.get("coverage")),
        reason=None,
    )


# ---------------------------------------------------------------------------
# Analysis dossier
# ---------------------------------------------------------------------------

_ADVICE_STATUSES = frozenset(
    {"BLOCKED", "INSUFFICIENT_DATA", "OBSERVE", "REVIEW", "QUALIFIED"}
)
_GATE_STATUSES = frozenset({"PASS", "DEGRADE", "BLOCK"})


def _checked_advice(value: Any) -> Mapping[str, Any]:
    """Fail-closed shape check of the published ``AdviceResult`` mapping.

    The API never recomputes a verdict; it only refuses to relay a snapshot
    whose advice block does not look like the canonical contract (missing
    id, unknown status, gate without a reason code).
    """
    advice = _wire_mapping(value, field="advice")
    _require_str(advice.get("advice_id"), field="advice.advice_id")
    _require_str(advice.get("engine_version"), field="advice.engine_version")
    status = advice.get("status")
    if status not in _ADVICE_STATUSES:
        raise SnapshotContentError(
            "advice.status: canonical AdviceStatus required", field="advice.status"
        )
    gates = _require_list(advice.get("gates"), field="advice.gates")
    for index, raw_gate in enumerate(gates):
        gate = _require_mapping(raw_gate, field=f"advice.gates[{index}]")
        _require_str(gate.get("gate_id"), field=f"advice.gates[{index}].gate_id")
        _require_str(
            gate.get("reason_code"), field=f"advice.gates[{index}].reason_code"
        )
        if gate.get("status") not in _GATE_STATUSES:
            raise SnapshotContentError(
                f"advice.gates[{index}].status: PASS/DEGRADE/BLOCK required",
                field=f"advice.gates[{index}].status",
            )
    return advice


def build_analysis_response(
    snapshot: Optional[CurrentSnapshot], *, instrument: str
) -> AnalysisResponse:
    """Render the last analysis dossier, or the honest empty state.

    Presentation only: the persisted content is shape-checked fail-closed
    and relayed VERBATIM — no bar, cluster, scenario value or verdict is
    ever recomputed here. Absence of a published snapshot is a NORMAL state
    (200 with ``state = "empty"``), never a 500 and never an invented
    dossier.
    """
    if snapshot is None:
        return AnalysisResponse(
            state="empty",
            snapshot_version=None,
            as_of=None,
            population=None,
            instrument=instrument,
            engine_version=None,
            bars=None,
            evidence=None,
            scenarios=None,
            advice=None,
            coverage=None,
            reason=REASON_NO_SNAPSHOT_PUBLISHED,
        )

    content = checked_relayed_content(snapshot.content)
    published_instrument = _require_str(content.get("instrument"), field="instrument")
    if published_instrument != instrument:
        raise SnapshotContentError(
            "instrument: snapshot content does not match the requested key",
            field="instrument",
        )
    bars = _wire_mapping(content.get("bars"), field="bars")
    scenarios = _wire_mapping(content.get("scenarios"), field="scenarios")
    scenario_status = scenarios.get("status")
    if scenario_status not in ("OK", "ABSENT"):
        raise SnapshotContentError(
            "scenarios.status: 'OK' or 'ABSENT' required", field="scenarios.status"
        )
    if scenario_status == "OK" and scenarios.get("value_nature") != "THEORETICAL":
        raise SnapshotContentError(
            "scenarios.value_nature: 'THEORETICAL' required on a computed grid",
            field="scenarios.value_nature",
        )
    if scenario_status == "ABSENT":
        _require_str(scenarios.get("reason"), field="scenarios.reason")
    return AnalysisResponse(
        state="ok",
        snapshot_version=snapshot.version,
        as_of=_parse_utc(content.get("as_of"), field="as_of"),
        population=_require_str(content.get("population"), field="population"),
        instrument=published_instrument,
        engine_version=_require_str(
            content.get("engine_version"), field="engine_version"
        ),
        bars=bars,
        evidence=_wire_mapping(content.get("evidence"), field="evidence"),
        scenarios=scenarios,
        advice=dict(_checked_advice(content.get("advice"))),
        coverage=_wire_mapping(content.get("coverage"), field="coverage"),
        reason=None,
    )


# ---------------------------------------------------------------------------
# Option chain
# ---------------------------------------------------------------------------


def _optional_non_negative_int(value: Any, *, field: str) -> Optional[int]:
    if value is None:
        return None
    return _require_non_negative_int(value, field=field)


def _status_mapping(value: Any, *, field: str) -> Mapping[str, Any]:
    """A worker result block: a mapping carrying a non-empty ``status``."""
    mapping = _wire_mapping(value, field=field)
    _require_str(mapping.get("status"), field=f"{field}.status")
    return mapping


def _option_contract(raw: Any, *, field: str) -> OptionChainContract:
    entry = _require_mapping(raw, field=field)
    con_id = entry.get("con_id")
    if con_id is not None:
        con_id = _require_positive_int(con_id, field=f"{field}.con_id")
    right = entry.get("right")
    if right is not None and right not in ("CALL", "PUT"):
        raise SnapshotContentError(
            f"{field}.right: 'CALL', 'PUT' or null required", field=f"{field}.right"
        )
    return OptionChainContract(
        con_id=con_id,
        strike=_optional_str(entry.get("strike"), field=f"{field}.strike"),
        right=right,
        expiration=_require_str(entry.get("expiration"), field=f"{field}.expiration"),
        trading_class=_require_str(
            entry.get("trading_class"), field=f"{field}.trading_class"
        ),
        multiplier=_require_positive_int(
            entry.get("multiplier"), field=f"{field}.multiplier"
        ),
        currency=_require_str(entry.get("currency"), field=f"{field}.currency"),
        exchange=_require_str(entry.get("exchange"), field=f"{field}.exchange"),
        style=_require_str(entry.get("style"), field=f"{field}.style"),
        settlement=_require_str(entry.get("settlement"), field=f"{field}.settlement"),
        quote=dict(_status_mapping(entry.get("quote"), field=f"{field}.quote")),
        volume=_optional_non_negative_int(entry.get("volume"), field=f"{field}.volume"),
        open_interest=_optional_non_negative_int(
            entry.get("open_interest"), field=f"{field}.open_interest"
        ),
        open_interest_status=_optional_str(
            entry.get("open_interest_status"), field=f"{field}.open_interest_status"
        ),
        iv=dict(_status_mapping(entry.get("iv"), field=f"{field}.iv")),
        greeks=dict(_status_mapping(entry.get("greeks"), field=f"{field}.greeks")),
        synthetic=_require_bool(entry.get("synthetic"), field=f"{field}.synthetic"),
    )


def _option_expiration(raw: Any, *, index: int) -> OptionChainExpiration:
    field = f"expirations[{index}]"
    entry = _require_mapping(raw, field=field)
    contracts_raw = _require_list(entry.get("contracts"), field=f"{field}.contracts")
    return OptionChainExpiration(
        expiration=_require_str(entry.get("expiration"), field=f"{field}.expiration"),
        trading_class=_require_str(
            entry.get("trading_class"), field=f"{field}.trading_class"
        ),
        exchange=_require_str(entry.get("exchange"), field=f"{field}.exchange"),
        style=_require_str(entry.get("style"), field=f"{field}.style"),
        settlement=_require_str(entry.get("settlement"), field=f"{field}.settlement"),
        multiplier=_require_positive_int(
            entry.get("multiplier"), field=f"{field}.multiplier"
        ),
        currency=_require_str(entry.get("currency"), field=f"{field}.currency"),
        maturity_years=_require_str(
            entry.get("maturity_years"), field=f"{field}.maturity_years"
        ),
        quality=_require_str(entry.get("quality"), field=f"{field}.quality"),
        source_event_id=_require_str(
            entry.get("source_event_id"), field=f"{field}.source_event_id"
        ),
        contracts=tuple(
            _option_contract(contract, field=f"{field}.contracts[{i}]")
            for i, contract in enumerate(contracts_raw)
        ),
        coverage=_wire_mapping(entry.get("coverage"), field=f"{field}.coverage"),
    )


def build_option_chain_response(
    snapshot: Optional[CurrentSnapshot], *, underlying: str
) -> OptionChainResponse:
    """Render the last option-chain snapshot, or the honest empty state.

    Presentation only: the persisted content is validated fail-closed into
    the wire DTOs and relayed VERBATIM — no quote, IV, Greek or coverage
    figure is ever recomputed here. Absence of a published snapshot is a
    NORMAL state (200 with ``state = "empty"``), never a 500 and never an
    invented chain.
    """
    if snapshot is None:
        return OptionChainResponse(
            state="empty",
            snapshot_version=None,
            as_of=None,
            population=None,
            underlying=underlying,
            engine_version=None,
            value_nature=None,
            spot=None,
            assumptions=None,
            expirations=(),
            row_budget=None,
            coverage=None,
            reason=REASON_NO_SNAPSHOT_PUBLISHED,
        )

    content = checked_relayed_content(snapshot.content)
    published_underlying = _require_str(content.get("underlying"), field="underlying")
    if published_underlying != underlying:
        raise SnapshotContentError(
            "underlying: snapshot content does not match the requested key",
            field="underlying",
        )
    value_nature = content.get("value_nature")
    if value_nature != "THEORETICAL":
        raise SnapshotContentError(
            "value_nature: 'THEORETICAL' required", field="value_nature"
        )
    expirations_raw = _require_list(content.get("expirations"), field="expirations")
    spot = content.get("spot")
    assumptions = content.get("assumptions")
    return OptionChainResponse(
        state="ok",
        snapshot_version=snapshot.version,
        as_of=_parse_utc(content.get("as_of"), field="as_of"),
        population=_require_str(content.get("population"), field="population"),
        underlying=published_underlying,
        engine_version=_require_str(
            content.get("engine_version"), field="engine_version"
        ),
        value_nature="THEORETICAL",
        spot=None if spot is None else _wire_mapping(spot, field="spot"),
        assumptions=(
            None
            if assumptions is None
            else _wire_mapping(assumptions, field="assumptions")
        ),
        expirations=tuple(
            _option_expiration(raw, index=index)
            for index, raw in enumerate(expirations_raw)
        ),
        row_budget=_wire_mapping(content.get("row_budget"), field="row_budget"),
        coverage=_wire_mapping(content.get("coverage"), field="coverage"),
        reason=None,
    )


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------


def _probe_field_entries(
    snapshot: Optional[CurrentSnapshot],
) -> list[tuple[datetime, str, Mapping[str, Any]]]:
    """Flatten every probed field entry as (tested_at, capability_id, field).

    ``tested_at`` comes from the probe payload's own ``tested_at`` when it is
    a valid aware datetime, falling back to the probed source's ``as_of``;
    with neither parseable the entry sorts first (oldest) so any dated probe
    wins over it.
    """
    if snapshot is None:
        return []
    content = checked_relayed_content(snapshot.content)
    probed_sources = _require_list(content.get("probed_sources"), field="probed_sources")

    entries: list[tuple[datetime, str, Mapping[str, Any]]] = []
    for source_index, raw_source in enumerate(probed_sources):
        source_entry = _require_mapping(raw_source, field=f"probed_sources[{source_index}]")
        payload = _require_mapping(
            source_entry.get("snapshot"), field=f"probed_sources[{source_index}].snapshot"
        )
        tested_at = _parse_utc_or_none(payload.get("tested_at"))
        if tested_at is None:
            tested_at = _parse_utc_or_none(source_entry.get("as_of"))
        fields = payload.get("fields")
        if not isinstance(fields, list):
            continue
        for raw_field in fields:
            if not isinstance(raw_field, Mapping):
                continue
            capability_id = raw_field.get("capability_id")
            if not isinstance(capability_id, str) or not capability_id:
                continue
            entries.append((tested_at or _EPOCH, capability_id, raw_field))
    return entries


def _entry_for_declaration(
    declaration: CapabilityDeclaration,
    probes: Sequence[tuple[datetime, str, Mapping[str, Any]]],
) -> CapabilityStatusEntry:
    matching = [probe for probe in probes if probe[1] == declaration.capability_id]
    if not matching:
        return CapabilityStatusEntry(
            capability_id=declaration.capability_id,
            family=declaration.family,
            declared_mode=declaration.declared_mode,
            description=declaration.description,
            tested_status=SourceCapabilityStatus.ERROR,
            tested_at=None,
            reason=REASON_NEVER_TESTED,
        )

    latest_at = max(probe[0] for probe in matching)
    winning = [probe for probe in matching if probe[0] == latest_at]
    tested_at = None if latest_at == _EPOCH else latest_at

    statuses = {
        field.get("status") for _, _, field in winning
    }
    if len(statuses) > 1:
        return CapabilityStatusEntry(
            capability_id=declaration.capability_id,
            family=declaration.family,
            declared_mode=declaration.declared_mode,
            description=declaration.description,
            tested_status=SourceCapabilityStatus.ERROR,
            tested_at=tested_at,
            reason=REASON_CONFLICTING_FIELD_STATUSES,
        )

    raw_status = next(iter(statuses))
    try:
        status = SourceCapabilityStatus(raw_status)
    except ValueError:
        return CapabilityStatusEntry(
            capability_id=declaration.capability_id,
            family=declaration.family,
            declared_mode=declaration.declared_mode,
            description=declaration.description,
            tested_status=SourceCapabilityStatus.ERROR,
            tested_at=tested_at,
            reason=REASON_INVALID_STATUS,
        )

    reasons = {
        field.get("reason_code")
        for _, _, field in winning
        if isinstance(field.get("reason_code"), str) and field.get("reason_code")
    }
    reason = "; ".join(sorted(reasons)) if reasons else None
    return CapabilityStatusEntry(
        capability_id=declaration.capability_id,
        family=declaration.family,
        declared_mode=declaration.declared_mode,
        description=declaration.description,
        tested_status=status,
        tested_at=tested_at,
        reason=reason,
    )


def _snapshot_health(
    snapshot: Optional[CurrentSnapshot], *, now: datetime
) -> SnapshotHealth:
    if snapshot is None:
        return SnapshotHealth(present=False, version=None, as_of=None, age_seconds=None)
    return SnapshotHealth(
        present=True,
        version=snapshot.version,
        as_of=snapshot.as_of,
        age_seconds=int((now - snapshot.as_of).total_seconds()),
    )


def build_system_health(
    *,
    db_ok: bool,
    attention: Optional[CurrentSnapshot],
    capabilities: Optional[CurrentSnapshot],
    now: datetime,
) -> SystemHealth:
    """Assemble the health blocks; the worker block is an explicit proxy."""
    published = [s.as_of for s in (attention, capabilities) if s is not None]
    last_as_of = max(published) if published else None
    return SystemHealth(
        db=DbHealth(status="ok" if db_ok else "error"),
        attention_snapshot=_snapshot_health(attention, now=now),
        capabilities_snapshot=_snapshot_health(capabilities, now=now),
        worker=WorkerHealth(
            method="heartbeat_proxy",
            last_snapshot_as_of=last_as_of,
            age_seconds=(
                int((now - last_as_of).total_seconds()) if last_as_of is not None else None
            ),
        ),
    )


def build_capabilities_response(
    manifest: CapabilityManifest,
    *,
    snapshot: Optional[CurrentSnapshot],
    attention: Optional[CurrentSnapshot],
    db_ok: bool,
    now: datetime,
) -> SystemCapabilitiesResponse:
    """Cross the FULL declared manifest with the latest persisted probes."""
    probes = _probe_field_entries(snapshot)
    entries = tuple(
        _entry_for_declaration(declaration, probes)
        for declaration in sorted(manifest.declarations, key=lambda d: d.capability_id)
    )
    declared_ids = manifest.capability_ids
    unknown = tuple(
        sorted({capability_id for _, capability_id, _ in probes if capability_id not in declared_ids})
    )
    snapshot_as_of: Optional[datetime] = None
    if snapshot is not None:
        content = checked_relayed_content(snapshot.content)
        snapshot_as_of = _parse_utc(content.get("as_of"), field="as_of")
    return SystemCapabilitiesResponse(
        checked_at=now,
        snapshot_version=None if snapshot is None else snapshot.version,
        as_of=snapshot_as_of,
        total=len(entries),
        capabilities=entries,
        unknown_probed_capability_ids=unknown,
        health=build_system_health(
            db_ok=db_ok, attention=attention, capabilities=snapshot, now=now
        ),
    )
