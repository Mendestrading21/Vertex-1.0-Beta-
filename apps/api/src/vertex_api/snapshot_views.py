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

WHAT THE VALUE CONTRACT DOES AND DOES NOT GUARANTEE (P0-5). The relay checks
the FORM of what it is about to publish and the INTERNAL CONSISTENCY of the
payload. It never checks provenance: it did not observe the market, it did not
run the calculation, and it must not pretend otherwise.

- guaranteed: no label outside a closed vocabulary is published
  (:data:`POPULATION_LABELS`, :data:`VALUE_NATURE_LABELS`,
  :data:`DATA_STATE_LABELS`, the enumerations read from ``vertex_core``, and
  the two path-closed fields :data:`BARS_STATUS_LABELS` and
  :data:`MARKETS_UNIT`); no control character, no unbounded string, no
  malformed decimal, instant, day, currency, hash or IANA zone; and no
  content that claims an observation while carrying a synthetic marker.
  THE NATURE IS A CLASS, NOT A KEY (6th audit): the vocabulary and the
  contradiction check apply to ``population`` AND ``mark_population`` at any
  depth, to every leaf of a ``populations`` / ``population_components``
  grouping, and to the KEYS of a ``population_counts`` census — the previous
  wave closed the literal ``population`` at the top level only, which left
  the portfolio valuation banner reading « DONNÉES RÉELLES » over marks
  still stamped ``rights = SYNTHETIC``.
- NOT guaranteed: that a snapshot labeled ``REAL`` is real. Only the worker
  knows, and the relay never recomputes what the worker owns.
- KNOWN RESIDUE, stated rather than hidden. Several DISPLAYED fields keep a
  shape-only contract because no module of ``vertex_core`` owns a vocabulary
  for them, and inventing one here would create a second authority:
  ``rights`` (entitlement labels — the edge publishes
  ``IBKR_MARKET_DATA_DISPLAY_ONLY``, the generator ``SYNTHETIC``, a probe
  ``DEMO``; the edge value is a configurable constructor argument, so the set
  is not closed anywhere), ``ticker``, ``exchange``, ``sector`` and ``source``
  (open universes by construction — no registry exists in this repository),
  and the GENERIC ``status`` leaf key, whose producers span at least eight
  unrelated namespaces (``OK``/``ABSENT``, ``CROSSED``/``STALE``/``MISSING``,
  ``AdviceStatus``, ``GateStatus``, ``CalculationStatus``,
  ``SourceCapabilityStatus``, ``ESTIMATED``/``CONFIRMED``,
  ``ACTIVE``/``SNOOZED``/``ARCHIVED``). A union of all of them would still
  let a quote status stand where a verdict belongs, and would break the
  DESIGNED fail-closed downgrade of an unknown capability status to ``ERROR``
  / ``INVALID_STATUS`` — a better answer than a blanket refusal. So these
  stay open, on purpose, and are pinned by characterisation tests in
  ``test_relay_value_contracts`` so the residue cannot grow unnoticed.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from typing import Any, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from vertex_api.capability_manifest import CapabilityDeclaration, CapabilityManifest
from vertex_api.freshness import RelayFreshness, evaluate_relay_freshness
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
    SecFundamentalsResponse,
    SnapshotHealth,
    SystemCapabilitiesResponse,
    SystemHealth,
    WorkerHealth,
)
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
from vertex_core.data.freshness import FreshnessPolicy, get_freshness_policy
from vertex_persistence.repository.snapshots import CurrentSnapshot

__all__ = [
    "BARS_STATUS_LABELS",
    "DATA_STATE_LABELS",
    "DELAY_STATUS_LABELS",
    "GENERATED_NATURE_LABELS",
    "MARKETS_DISPLAY_UNIT",
    "MARKETS_UNIT",
    "MAX_RELAYED_CODE_LENGTH",
    "MAX_RELAYED_DEPTH",
    "MAX_RELAYED_TEXT_LENGTH",
    "MAX_RELAYED_USER_TEXT_LENGTH",
    "NATURE_CENSUS_KEYS",
    "NATURE_LEAF_KEYS",
    "NATURE_PARENT_KEYS",
    "OBSERVATION_CLAIM_LABELS",
    "POPULATION_LABELS",
    "REASON_CONFLICTING_FIELD_STATUSES",
    "REASON_INVALID_STATUS",
    "REASON_NEVER_TESTED",
    "REASON_NO_SNAPSHOT_PUBLISHED",
    "SYNTHETIC_IDENTIFIER_KEYS",
    "SYNTHETIC_MARKER_KEYS",
    "SYNTHETIC_MARKER_VALUES",
    "SYNTHETIC_VALUE_PREFIXES",
    "VALUE_NATURE_LABELS",
    "SnapshotContentError",
    "build_analysis_response",
    "build_attention_response",
    "build_capabilities_response",
    "build_markets_overview_response",
    "build_option_chain_response",
    "build_sec_fundamentals_response",
    "build_system_health",
    "checked_relayed_content",
    "is_synthetic_marker",
    "require_snapshot_as_of",
]

#: Politique de fraîcheur de chaque relais : celle de l'observation LA PLUS
#: FRAÎCHE dont l'instantané peut être issu. Le choix se LIT dans le worker,
#: il n'est pas décrété ici :
#:
#: - ``attention`` fusionne ``load_recent_observation_records`` (flux de news
#:   et observations récentes) -> ``news_attention`` ;
#: - ``markets_overview`` charge ``load_daily_quote_records`` -> ``daily_bar`` ;
#: - ``analysis`` charge ``load_daily_bar_records`` -> ``daily_bar`` ;
#: - ``option_chain`` charge ``load_option_chain_records`` -> ``option_surface``.
#:
#: Le budget servi est le TTL de SÉANCE FERMÉE de la politique : le relais ne
#: connaît aucun état de séance, il retient donc la borne conservatrice.
ATTENTION_FRESHNESS_POLICY = "news_attention"
MARKETS_FRESHNESS_POLICY = "daily_bar"
ANALYSIS_FRESHNESS_POLICY = "daily_bar"
OPTION_CHAIN_FRESHNESS_POLICY = "option_surface"
SEC_FUNDAMENTALS_FRESHNESS_POLICY = "fundamental_filing"

_ATTENTION_POLICY = get_freshness_policy(ATTENTION_FRESHNESS_POLICY)
_MARKETS_POLICY = get_freshness_policy(MARKETS_FRESHNESS_POLICY)
_ANALYSIS_POLICY = get_freshness_policy(ANALYSIS_FRESHNESS_POLICY)
_OPTION_CHAIN_POLICY = get_freshness_policy(OPTION_CHAIN_FRESHNESS_POLICY)
_SEC_FUNDAMENTALS_POLICY = get_freshness_policy(SEC_FUNDAMENTALS_FRESHNESS_POLICY)

#: La matrice de capacités n'a AUCUN budget de relais, et c'est DÉCLARÉ : la
#: péremption d'une capacité est portée champ par champ par le ``expires_at``
#: de la sonde qui l'a établie. Inventer un TTL ici serait la valeur non
#: justifiée que ce dépôt refuse ailleurs. L'âge, lui, est publié.
CAPABILITIES_FRESHNESS_POLICY: FreshnessPolicy | None = None


def _relay_freshness(
    snapshot: CurrentSnapshot, *, now: datetime, policy: FreshnessPolicy | None
) -> RelayFreshness:
    """Fraîcheur d'un instantané relayé. ``now`` est TOUJOURS injecté.

    Ces relais ne déclarent aucune tolérance de dérive d'horloge : ils ne
    recalculent rien contre elle, donc une avance de quelques secondes est
    bornée à un âge de zéro par le propriétaire et rien d'autre n'en dépend.
    """
    return evaluate_relay_freshness(
        require_snapshot_as_of(snapshot), now=now, policy=policy
    )


REASON_NO_SNAPSHOT_PUBLISHED = "no snapshot published"
REASON_NEVER_TESTED = "NEVER_TESTED"
REASON_INVALID_STATUS = "INVALID_STATUS"
REASON_CONFLICTING_FIELD_STATUSES = "CONFLICTING_FIELD_STATUSES"

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


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

    def __init__(self, message: str, *, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


def require_snapshot_as_of(snapshot: CurrentSnapshot) -> datetime:
    """Instant de PUBLICATION de l'instantané, validé une fois pour toutes.

    L'âge d'un relais se mesure sur cet horodatage SERVEUR, jamais sur le
    contenu : un contenu date sa propre vérité métier, il ne date pas sa
    publication. Un horodatage absent, non daté ou naïf est un défaut de
    contenu persisté — d'où `SnapshotContentError`, dont ce module est le
    propriétaire.

    Le calcul de fraîcheur lui-même appartient à `vertex_api.freshness`, qui
    n'importe rien d'ici : la frontière évite un import cyclique.
    """
    as_of = snapshot.as_of
    if not isinstance(as_of, datetime):
        raise SnapshotContentError(
            "snapshot.as_of: datetime required", field="snapshot.as_of"
        )
    if as_of.tzinfo is None or as_of.tzinfo.utcoffset(as_of) is None:
        raise SnapshotContentError(
            "snapshot.as_of: naive datetime rejected", field="snapshot.as_of"
        )
    return as_of


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
    return parsed.astimezone(UTC)


def _parse_utc_or_none(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        return None
    return parsed.astimezone(UTC)


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
# Deny-by-default applies to the LEAF KEY NAME **of a string leaf**: a key
# this map does not know falls back to the PROSE contract, which is still
# bounded and control-free. A string field added upstream is therefore
# relayed under a real constraint before this map learns about it — it is
# simply not YET constrained as a decimal or as a closed label, which is what
# the lot report quantifies as residual.
#
# THAT SENTENCE WAS FALSE FOR EVERY NON-STRING LEAF until the 8th audit, and
# it is corrected here rather than defended. There was no fallback for a
# number: the walk knew ``Mapping``, ``list``, ``bool`` and ``str``, and an
# ``int`` or a ``float`` matched NO branch — no contract applied, not even a
# length. ``{"population": "SYNTHETIC", "last_price": 10**5000}`` passed and
# was relayed verbatim, which is the amplification the portfolio WRITE
# contract had just closed, still open on the relay side for every producer.
# The walk is now EXHAUSTIVE: a number obeys :func:`_check_relayed_number`,
# ``null`` is accepted as the explicit ABSENCE of a value, and any other type
# is refused. "Falls back to the prose contract" is now true of strings and
# only of strings, which is what the map indexes.
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

MAX_RELAYED_NUMBER_MAGNITUDE = 2**53 - 1
"""Magnitude ceiling of every relayed JSON NUMBER (``int`` and ``float``).

WHY A NUMBER NEEDED A CONTRACT AT ALL (8th audit). The walk knew mappings,
lists, booleans and strings; an ``int`` or a ``float`` fell through EVERY
branch, so ``{"last_price": 10**5000}`` was relayed verbatim — a 5 001-digit
integer crossing the last frontier before a human reads the value. That is
the amplification class the portfolio write contract had just closed on the
WRITE side, still open on the RELAY side, for every producer at once.

WHY 2**53 - 1 = 9 007 199 254 740 991, and NOT the 10**24 of
``vertex_api.portfolio.MAX_DECIMAL_MAGNITUDE_EXPONENT``. The two bounds
protect different things and the relay's is deliberately TIGHTER:

- 10**24 bounds a value the USER DECLARES and Vertex stores as an exact
  decimal STRING; its ceiling is placed where no honest declaration can
  reach, whatever the currency;
- this bound governs a JSON NUMBER, which every consumer of this API — the
  browser, the generated TypeScript client — parses into an IEEE-754 double.
  2**53 - 1 is the largest integer that survives that trip EXACTLY. Above it
  the figure displayed is no longer the figure stored, and a relay that
  silently changes a financial value is worse than one that refuses it
  (``financial-safety.md``: "aucune conversion flottante silencieuse").
  10**24 would be LOOSER than what the consumer can represent, i.e. it would
  authorize the corruption;
- it also bounds the rendered length to 16 characters, where the previous
  contract bounded nothing at all.

A value spelled as a decimal STRING keeps its own, wider contract
(:data:`_UNSIGNED_DECIMAL_RE`) precisely because a string crosses the wire
unchanged. Nothing honest is refused here: the producers publish counts of
observations, lookback seconds, ranks and census buckets.
"""

MIN_RELAYED_NONZERO_FLOAT = 1e-30
"""Granularity floor of a relayed non-zero ``float`` (zero itself is exact).

Parity with the relay's OWN decimal-string contract, which accepts at most 30
fractional digits: the same number spelled as a string is already refused
below this granularity, so accepting it as a float would make the guard
depend on the spelling. It also bounds positional rendering to some thirty
characters — the smallest subnormal double (~4.9e-324) written out in full
costs more than a thousand.
"""

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

_CODE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@/+$-]{0,127}$")
"""Technical code: identity, version, hash, event id, resource path.

Le `$` est admis DANS la classe, jamais en premier caractère, parce qu'un
``event_id`` de presse encastre l'``article_id`` frappé PAR LE FOURNISSEUR :
IBKR News émet ``DJ-RT$1e0664c8``, d'où ``ibkr:news:DJ-RT:DJ-RT$1e0664c8``.

MESURE DU 2026-09-01 sur ``vertex_live`` — l'ampleur était très supérieure aux
deux routes d'abord constatées : 6108 observations concernées, toutes de
schéma ``ibkr.news-headline/1`` ; 1207 valeurs refusées sur les 170 têtes
publiées, soit **72 réponses HTTP en 500** (1 ``attention``, 71 des 162
dossiers ``analysis``, soit 43,8 % d'entre eux).

POURQUOI ÉLARGIR LE LECTEUR PLUTÔT QUE D'ASSAINIR À LA FRAPPE. ``event_id``
est la CLÉ D'IDEMPOTENCE de ``ingest_envelope`` : changer sa dérivation
ré-ingérerait les 6108 dépêches en doublons. Et la migration de rattrapage est
IMPOSSIBLE — ``UPDATE``/``DELETE`` sur ``observations`` et ``snapshots`` sont
refusés par le déclencheur ``vertex_forbid_mutation``. Élargir le lecteur est
la seule voie non destructrice, et la seule qui rende servables des
instantanés immuables sans les toucher.

Mesuré aussi : ré-écrire l'identité ne corrigerait même pas les 500. Sur 40
dépêches réelles, 40/40 des clusters mêlent ancienne et nouvelle identité, et
40/40 élisent un représentant portant encore le `$`.

L'AUTORITÉ DE CONTRAT N'IMPOSE AUCUNE FORME ICI :
``vertex_core.contracts.envelope`` déclare ``event_id: NonEmptyStr``, soit
``StringConstraints(min_length=1)``. Fermer plus étroitement que l'autorité
qui PRODUIT la valeur est exactement ce que le docstring de ``_HASH_KEYS``
interdit plus bas dans ce même fichier.

ORDRE OBLIGATOIRE : le `$` est placé AVANT le `-` final. Écrit ``+-$``,
Python lirait une plage de caractères au lieu de trois littéraux.

CE QUE CELA NE RÈGLE PAS, et qu'il ne faut pas annoncer réglé : deux valeurs
restent refusées après ce correctif, ``instrument`` et ``instrument_id`` de
l'instantané ``analysis/GNL PRE``. Le caractère fautif y est l'ESPACE, jamais
adressé par le `$`. Cet instantané est de toute façon inatteignable —
``UNDERLYING_PATTERN`` le refuse en 422 avant toute lecture de base.

LA VRAIE PARADE n'est pas dans ce motif. Ce caractère est calibré sur UN
fournisseur observé UN jour ; Reuters ou un identifiant en UUID à accolades
rouvriront la question. Ce qui ferme la classe, c'est le test structurel de
``test_relay_value_contracts.py`` : ce que l'edge frappe, le relais doit le
relayer."""

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
demonstration or a user declaration.

WHAT THIS SET GUARANTEES. No label outside it can be PUBLISHED: a persisted
``population`` reading ``LIVE``, ``IBKR_REALTIME_ENTITLED``, ``PRODUCTION``
or free text is refused, and the declared natures stay DISTINCT members —
none is a synonym of another, as ``financial-safety.md`` requires. Adding a
member is an explicit, reviewed contract change, never an accident of a
persisted payload.

WHAT THIS SET DOES NOT GUARANTEE — and the earlier wording of this docstring
over-promised it. Membership is a FORM check. The relay CANNOT verify that a
snapshot labeled ``REAL`` really carries observations: that truth belongs to
the worker that produced it, and the API never recomputes a provenance it did
not observe. A worker defect, or a tampered snapshot row, that writes ``REAL``
over synthetic content is still served as ``REAL`` — except where the payload
CONTRADICTS ITSELF, which is the one thing a relay can honestly check (see
:data:`OBSERVATION_CLAIM_LABELS`).
"""

OBSERVATION_CLAIM_LABELS: frozenset[str] = frozenset({"REAL", "DELAYED"})
"""The two labels that CLAIM an observation of a real market.

Every other member of :data:`POPULATION_LABELS` announces that what is shown
was generated, computed, simulated, demonstrated or declared by the user.
These two do not: they tell the reader that a real quote was seen, live or
delayed. They are therefore the only two a forged or defective payload gains
anything from.
"""

GENERATED_NATURE_LABELS: frozenset[str] = frozenset(
    {"SYNTHETIC", "SIMULATED", "DEMO"}
)
"""The nature labels that state, by themselves, that nothing was observed.

They are a STRICT SUBSET of :data:`POPULATION_LABELS` and disjoint from
:data:`OBSERVATION_CLAIM_LABELS`. ``THEORETICAL``, ``USER_DECLARED``,
``EMPTY`` and ``SYNTHETIC_MARKS_REAL_LEDGER`` are deliberately ABSENT: a
theoretical price, a declared lot or an empty census legitimately sit beside
real observations (``vertex_worker.performance`` publishes exactly that), so
treating them as contradictions would refuse honest product states.
"""

SYNTHETIC_MARKER_VALUES: frozenset[str] = frozenset({"SYNTHETIC", "synthetic-dev"})
"""The two markers ``vertex_core.synthetic`` stamps on everything it makes.

They are ``vertex_core.synthetic.SYNTHETIC_RIGHTS`` and
``vertex_core.synthetic.SYNTHETIC_SOURCE``. They are restated here rather than
imported so that a read-only relay does not load a data GENERATOR into the API
process; ``test_relay_value_contracts`` pins them against that authority, so a
change there fails the build instead of silently widening this check.
"""

SYNTHETIC_MARKER_KEYS: frozenset[str] = frozenset({"rights", "sources", "source"})
"""The provenance keys under which those markers HISTORICALLY travelled.

Kept as documentation of where the 5th audit looked. The 6th audit showed the
restriction was the defect, not the protection: ``generator``,
``source_system``, ``schema_version`` and ``title`` carry the same markers and
were all served under a ``REAL`` claim. :func:`is_synthetic_marker` therefore
no longer restricts the EXACT markers to these keys — only the IDENTIFIER
shapes stay key-scoped (:data:`SYNTHETIC_IDENTIFIER_KEYS`).
"""

SYNTHETIC_VALUE_PREFIXES: tuple[str, ...] = ("synthetic-", "[SYNTHETIC] ")
"""Prefixes ``vertex_core.synthetic`` puts in front of what it names.

``synthetic-`` opens every generated ``schema_version``
(``synthetic-news/1.0``, ``synthetic-quote/1.0``, ``synthetic-daily-bars/1.0``,
``synthetic-option-chain/1.0``, ``synthetic-calendar-event/1.0``,
``synthetic-daily-quote/1.0``), its ``source`` (``synthetic-dev``) and its
adjustment basis (``synthetic-unadjusted``); ``[SYNTHETIC] `` opens every
generated news title. A PREFIX rather than the six literals: a schema the
generator adds tomorrow is covered the day it is added, and the drift test
proves the coverage against the authority instead of trusting this list.
"""

SYNTHETIC_IDENTIFIER_KEYS: frozenset[str] = frozenset(
    {
        "currency",
        "exchange",
        "instrument",
        "sector",
        "symbol",
        "ticker",
        "tickers",
        "trading_class",
        "underlying",
    }
)
"""Keys where a SYNTHETIC identifier shape counts as a marker.

Scoped to identifier fields on purpose: matching the shape inside free prose
would turn a sentence into a provenance verdict.
"""

_SYNTHETIC_IDENTIFIER_RE = re.compile(r"SYN(?:[0-9]|TH|-[A-Z]{4}(?:-[0-9]{2})?)?")
"""EXACT shapes of the identifiers ``vertex_core.synthetic`` mints.

``SYN`` (the generated currency), ``SYN1``..``SYN9`` (the news tickers),
``SYNTH`` (the generated option exchange), ``SYN-TECH`` (the sectors) and
``SYN-TECH-01`` (the sector/focus tickers). It is a FULL match, never a
``SYN`` prefix: ``SYNA`` is Synaptics, a real instrument, and a prefix rule
would refuse a genuine snapshot mentioning it.

RESIDUE, stated rather than hidden: if a real instrument ever carried one of
these exact shapes, a genuine ``REAL`` snapshot naming it would be REFUSED.
That direction is fail-closed — an honest error state instead of a synthetic
value shown as an observation — which is the direction
``financial-safety.md`` requires.
"""

NATURE_LEAF_KEYS: frozenset[str] = frozenset({"population", "mark_population"})
"""Leaf keys that carry a nature label, AT ANY DEPTH.

``population`` is published by ``vertex_worker.{analysis, markets, calendar,
opportunities, handlers, follow_up}`` — as a HEAD label and, in
``opportunities``, once per dossier beside it. ``mark_population`` is
``vertex_worker.portfolio``'s: the nature of the marks a valuation is priced
with. The 6th audit found the guard closed on the literal ``population``
alone, so ``mark_population = "REAL"`` beside ``rights = SYNTHETIC`` reached
the portfolio banner reading « DONNÉES RÉELLES ».
"""

NATURE_PARENT_KEYS: frozenset[str] = frozenset(
    {"populations", "population_components"}
)
"""Mappings whose EVERY leaf is a nature label, whatever the leaf is called.

``vertex_worker.follow_up`` publishes ``populations = {theses,
information_context}`` and ``vertex_worker.performance`` publishes
``population_components = {marks, ledger}``. Their leaf keys (``marks``,
``ledger``) are ordinary words: closing them by leaf key would both miss them
here and wrongly constrain a ``marks`` key elsewhere. They are therefore
closed by PATH.
"""

NATURE_CENSUS_KEYS: frozenset[str] = frozenset({"population_counts"})
"""Mappings whose KEYS are nature labels and whose values are counts.

``vertex_worker.opportunities`` publishes ``population_counts = {"SYNTHETIC":
2, "REAL": 1}``. Three things are closed here, and the 7th audit showed that
closing only the first was a hole:

1. the KEYS obey the same closed vocabulary — a census bucket named
   ``IBKR_LIVE`` asserts a nature no producer declares;
2. the VALUES are plain non-negative integers
   (:func:`_relayed_census_count`). The cross-check below READS those counts;
   a bucket holding ``"24"``, ``"beaucoup"``, ``true`` or ``-4`` would make
   the rule silently unenforceable while still looking enforced;
3. a census CONSTRAINS the observation claim that governs it
   (:func:`checked_relayed_content`), in the OVER-CLAIM direction only.

The previous wave excluded the census from the cross-check on the ground that
"a census DESCRIBES a mix, it does not claim one". That is true of the census
ALONE and says nothing about the head placed ABOVE it: ``population = "REAL"``
over ``population_counts = {"SYNTHETIC": 24}`` was served, and reached the
page banner as « DONNÉES RÉELLES ». The mix itself remains a legitimate
product state — under a PRUDENT head, which is the direction the rule keeps
serving.
"""

BARS_STATUS_LABELS: frozenset[str] = frozenset({"OK", "ABSENT"})
"""CLOSED vocabulary of ``bars.status`` in an analysis dossier.

``vertex_worker.analysis`` publishes ``OK`` when at least one bar survived
validation and ``ABSENT`` otherwise — there is no third value. Left as a mere
uppercase token, the field accepted ``REAL_TIME_IBKR`` and ``LIVE``, i.e. a
delay claim on a block that carries none. Closed by PATH (not by leaf key):
``status`` elsewhere belongs to other producers with other vocabularies.
"""

MARKETS_UNIT = "return_ratio"
"""The single machine unit ``vertex_worker.markets`` publishes for its sector
returns. Left as a technical code, ``unit`` accepted ``USD`` — a ratio reading
as money. Closed by PATH for the same reason as :data:`BARS_STATUS_LABELS`."""

MARKETS_DISPLAY_UNIT = "%"
"""The single display unit that pairs with :data:`MARKETS_UNIT`."""

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
    # Une correlation « la plus opposee » est NEGATIVE par definition — c'est
    # ce que le mot veut dire. `value` vivait dans la classe non signee, ce qui
    # rendait `extremes.most_opposed.value = -0.803` irrelayable : un 500
    # latent sur la page Risques, invisible tant que la route garde son
    # validateur propre (REPRENDRE_ICI.md §4.3).
    #
    # LE DESSERRAGE NE PERD RIEN, parce que les DEUX bornes semantiques que
    # cette classe ne peut pas connaitre sont desormais tenues la ou elles ont
    # un sens : `_checked_correlation` pour [-1, 1] cote Risques, et
    # `_markets_breadth` pour [0, 1] cote Marches. La classe dit « c'est un
    # decimal signe » ; la borne appartient a la page.
    "value",
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
_CLASS_BY_LEAF_KEY.update(dict.fromkeys(_DECIMAL_KEYS, _relayed_decimal))
_CLASS_BY_LEAF_KEY.update(
    dict.fromkeys(_SIGNED_DECIMAL_KEYS, _relayed_signed_decimal)
)
_CLASS_BY_LEAF_KEY.update(dict.fromkeys(_PERCENT_KEYS, _relayed_percent))
_CLASS_BY_LEAF_KEY.update(dict.fromkeys(_INSTANT_KEYS, _relayed_instant))
_CLASS_BY_LEAF_KEY.update(dict.fromkeys(_TRADING_DAY_KEYS, _relayed_trading_day))
_CLASS_BY_LEAF_KEY.update(dict.fromkeys(_CODE_KEYS, _relayed_code))
_CLASS_BY_LEAF_KEY.update(dict.fromkeys(_UPPER_CODE_KEYS, _relayed_upper_code))
_CLASS_BY_LEAF_KEY.update(dict.fromkeys(_HASH_KEYS, _relayed_hash))
_CLASS_BY_LEAF_KEY.update(dict.fromkeys(_USER_TEXT_KEYS, _relayed_user_text))


def _check_relayed_number(value: Any, *, field: str) -> None:
    """Contract of a relayed JSON NUMBER — the leaves the walk used to skip.

    Three refusals, none of which repairs anything:

    1. a non-finite ``float``. ``NaN`` and ``±Infinity`` are not JSON
       (RFC 8259); Python's serializer emits the bare tokens ``NaN`` and
       ``Infinity``, which a strict parser rejects and a lenient one turns
       into a value no reader can interpret. Neither is a financial
       quantity: absent, zero and unknown are three distinct states and none
       of them is ``NaN``;
    2. a magnitude above :data:`MAX_RELAYED_NUMBER_MAGNITUDE`. For an
       ``int`` this is the amplification bound (a 5 001-digit integer was
       relayed verbatim before this wave); for a ``float`` it is the same
       ceiling, because the consumer is one positional format away from
       turning ``1.79e308`` into 309 characters;
    3. a non-zero ``float`` finer than :data:`MIN_RELAYED_NONZERO_FLOAT`.

    The magnitude is read WITHOUT materializing the number:
    ``int.bit_length()`` is computed from the coefficient, exactly as
    ``Decimal.adjusted()`` is on the write side — the check must cost
    nothing on the very input it refuses. ``str(value)`` on a 5 001-digit
    integer would itself raise, so it is never called.

    The refusal names the FIELD PATH only, never the value.
    """
    if isinstance(value, float):
        if not math.isfinite(value):
            raise SnapshotContentError(
                f"{field}: relayed number must be finite", field=field
            )
        magnitude = abs(value)
        if magnitude > MAX_RELAYED_NUMBER_MAGNITUDE:
            raise SnapshotContentError(
                f"{field}: relayed number outside the representable magnitude "
                "of the contract",
                field=field,
            )
        if magnitude != 0.0 and magnitude < MIN_RELAYED_NONZERO_FLOAT:
            raise SnapshotContentError(
                f"{field}: relayed number finer than the contract granularity",
                field=field,
            )
        return
    # ``int``: the bit length is read from the stored coefficient, so the
    # bound costs nothing on the very input it refuses. ``bit_length() > 53``
    # is exactly ``abs(value) > 2**53 - 1``, without materializing a digit.
    if value.bit_length() > MAX_RELAYED_NUMBER_MAGNITUDE.bit_length():
        raise SnapshotContentError(
            f"{field}: relayed number outside the representable magnitude "
            "of the contract",
            field=field,
        )


def _relayed_census_count(value: Any, *, field: str) -> int:
    """A nature-census bucket holds a COUNT of members, nothing else.

    Plain, non-negative, integral. ``bool`` is excluded EXPLICITLY: it is an
    ``int`` subclass in Python, so ``{"SYNTHETIC": true}`` would otherwise
    read as a count of one and a ``false`` bucket would read as zero.

    WHY THIS IS CLOSED AT ALL (7th audit). Until this wave only the census
    KEYS were checked; the values took anything the walk did not visit —
    numbers were never reached, and a string fell back on free prose. The
    cross-check in :func:`checked_relayed_content` READS these counts to
    decide whether a census supports the claim above it, so an unreadable
    value would not be a cosmetic defect: it would be a guard that reports
    itself as applied while being inapplicable. Its single producer
    (``vertex_worker.opportunities``) already writes ``int``, so nothing
    honest is refused.

    The refusal names the PATH of the bucket and never its stored value.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise SnapshotContentError(
            f"{field}: nature census count must be a non-negative integer",
            field=field,
        )
    if value < 0:
        raise SnapshotContentError(
            f"{field}: nature census count must be a non-negative integer",
            field=field,
        )
    # A count is a number like any other: same magnitude ceiling, so a bucket
    # cannot be the one integer that escapes the bound (8th audit).
    _check_relayed_number(value, field=field)
    return cast(int, value)  # restreint en `int` par les deux gardes ci-dessus


def _leaf_key(path: str) -> str:
    """The JSON key a leaf belongs to, list indices removed."""
    tail = path.rsplit(".", 1)[-1]
    bracket = tail.find("[")
    return tail if bracket < 0 else tail[:bracket]


def _parent_path(path: str) -> str:
    """The path of the container a leaf sits in (``""`` at the top level)."""
    head, sep, _ = path.rpartition(".")
    return head if sep else ""


def _nature_scope(path: str) -> str | None:
    """The SUBTREE a nature label at ``path`` governs, or ``None``.

    A nature label describes the container it sits in, not the whole
    document: ``dossiers[0].population`` speaks for ``dossiers[0]``, the
    top-level ``population`` speaks for everything. A label under a grouping
    mapping (:data:`NATURE_PARENT_KEYS`) speaks for the container that HOLDS
    the grouping — ``populations`` and ``population_components`` carry no
    data of their own, so scoping to them would make the label govern
    nothing.
    """
    parent = _parent_path(path)
    if _leaf_key(path) in NATURE_LEAF_KEYS:
        return parent
    if parent and _leaf_key(parent) in NATURE_PARENT_KEYS:
        return _parent_path(parent)
    return None


def _within(path: str, scope: str) -> bool:
    """Whether ``path`` sits inside the subtree ``scope`` (``""`` = all)."""
    if not scope:
        return True
    return path == scope or path.startswith(f"{scope}.") or path.startswith(
        f"{scope}["
    )


def is_synthetic_marker(value: str, path: str) -> bool:
    """Whether a relayed string ANNOUNCES that it was generated, not observed.

    Three independent tells, all traceable to ``vertex_core.synthetic``:

    1. an EXACT marker (:data:`SYNTHETIC_MARKER_VALUES`) — under any key now,
       not only under ``rights``/``sources``/``source``: the 6th audit served
       ``generator = "synthetic-dev"`` and ``source_system = "synthetic-dev"``
       untouched beneath a ``REAL`` claim;
    2. a marker PREFIX (:data:`SYNTHETIC_VALUE_PREFIXES`) — the generated
       ``schema_version``, the generated adjustment basis, the ``[SYNTHETIC] ``
       news-title prefix;
    3. an identifier the generator MINTS (:data:`SYNTHETIC_IDENTIFIER_KEYS`
       crossed with :data:`_SYNTHETIC_IDENTIFIER_RE`) — a ``REAL`` snapshot
       priced on ``SYN-TECH-01`` contradicts itself.

    It proves nothing about content that carries NO marker: a producer that
    scrubs every tell is still relayed as it declares itself. That limit is
    pinned by ``test_residue_a_fully_scrubbed_payload_still_passes``.
    """
    if value in SYNTHETIC_MARKER_VALUES:
        return True
    if value.startswith(SYNTHETIC_VALUE_PREFIXES):
        return True
    return (
        _leaf_key(path) in SYNTHETIC_IDENTIFIER_KEYS
        and _SYNTHETIC_IDENTIFIER_RE.fullmatch(value) is not None
    )


def _check_relayed_string(value: str, *, field: str) -> None:
    if not value:
        raise SnapshotContentError(
            f"{field}: non-empty string required", field=field
        )
    if _nature_scope(field) is not None:
        # A nature label obeys its closed vocabulary WHEREVER it sits, and
        # whatever its leaf is called (``marks``, ``ledger``, ``theses``).
        _relayed_population(value, field=field)
        return
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

    THE WALK IS EXHAUSTIVE OVER THE JSON TYPES (8th audit). A ``bool`` is a
    self-declaration, a ``str`` obeys its field class, a NUMBER obeys
    :func:`_check_relayed_number` (finite, magnitude and granularity),
    ``null`` is the accepted ABSENCE of a value, and anything else is
    refused. Before this wave a number matched no branch at all: an integer
    of five thousand digits was relayed verbatim under any key, including
    under a head claiming ``REAL``.

    THE NATURE IS A CLASS OF FIELDS, NOT ONE KEY (6th audit). Every location
    that carries a nature — :data:`NATURE_LEAF_KEYS` at ANY depth, every leaf
    under a :data:`NATURE_PARENT_KEYS` grouping, and the KEYS of a
    :data:`NATURE_CENSUS_KEYS` census — obeys :data:`POPULATION_LABELS`. The
    previous wave closed the literal ``population`` only, so
    ``mark_population`` (``vertex_worker.portfolio``) and
    ``population_components.marks`` (``vertex_worker.performance``) took free
    text, and a nested dossier nature was neither a claim nor a marker.

    ONE CROSS-FIELD INVARIANT, and its exact scope. A nature label GOVERNS
    THE CONTAINER IT SITS IN (:func:`_nature_scope`). A label that claims an
    observation (:data:`OBSERVATION_CLAIM_LABELS`) is REFUSED when a
    synthetic marker appears anywhere in the subtree it governs — a marker
    being :func:`is_synthetic_marker`, an explicit ``synthetic: true``, or a
    generated nature (:data:`GENERATED_NATURE_LABELS`) declared at another
    nature-bearing location inside that subtree.

    THE CENSUS CONSTRAINS THE CLAIM ABOVE IT (7th audit). A nature census
    (:data:`NATURE_CENSUS_KEYS`) DESCRIBES the members of the container it
    belongs to. An observation claim governing a subtree that holds a census
    is therefore REFUSED when that census does not SUPPORT it — see the rule
    stated in full below. The previous wave excluded the census from the
    cross-check on the ground that "a census describes a mix, it does not
    claim one"; that is true of the census alone and says nothing about the
    HEAD above it, so ``population = "REAL"`` over ``population_counts =
    {"SYNTHETIC": 24}`` was served and reached the page banner as
    « DONNÉES RÉELLES ».

    THE RULE, EXACTLY. A census with no populated bucket (empty, absent, or
    all-zero) carries NO information and refuses nothing — refusing it would
    mean refusing its ABSENCE too, hence every producer that publishes none.
    A census with at least one populated bucket refuses an observation claim
    that governs it when EITHER a populated bucket names a generated nature
    (:data:`GENERATED_NATURE_LABELS`) — the claim counts a member that states
    it was never observed — OR no populated bucket names an observation claim
    label — the claim counts no observed member at all. A bucket whose count
    is ZERO is not a member: the rule reads counts, not key presence.

    WHAT THE RULE DELIBERATELY DOES NOT REFUSE, and why. Only the
    OVER-CLAIM direction is a contradiction. A prudent head above a
    claiming leaf — ``population = "SYNTHETIC"`` over a ``REAL`` dossier, or
    over a mixed ``population_counts = {"REAL": 1, "SYNTHETIC": 1}`` — is the
    degradation ``vertex_worker.opportunities`` performs ON PURPOSE ("a
    single synthetic dossier makes the whole snapshot synthetic"), published
    with its ``limitations`` and its ``population_counts``. Refusing it would
    break a legitimate product state while protecting nobody: no reader of
    that snapshot is told "real". The rule is asymmetric BY DESIGN, and the
    census is now read in that same one direction.

    None of this proves that a ``REAL`` snapshot is real. Only the worker
    knows. It refuses a payload that contradicts ITSELF, which is the
    strongest statement a relay is entitled to make.
    """
    mapping = _require_mapping(content, field=field)
    # (path of the claim, subtree it governs) and paths of the markers found.
    claims: list[tuple[str, str]] = []
    markers: list[str] = []
    # (path of a nature census, its buckets that really COUNT a member).
    censuses: list[tuple[str, frozenset[str]]] = []

    def walk(node: Any, path: str, depth: int) -> None:
        if depth > MAX_RELAYED_DEPTH:
            raise SnapshotContentError(
                f"{path or field}: relayed content nested deeper than the "
                f"{MAX_RELAYED_DEPTH}-level budget",
                field=path or field,
            )
        if isinstance(node, Mapping):
            census = bool(path) and _leaf_key(path) in NATURE_CENSUS_KEYS
            populated: set[str] = set()
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
                if census:
                    if key not in POPULATION_LABELS:
                        raise SnapshotContentError(
                            f"{path}: nature census key outside its closed "
                            "vocabulary",
                            field=path,
                        )
                    # A census bucket is a COUNT, fully checked here: it is
                    # a scalar, so it is never walked further.
                    if _relayed_census_count(value, field=f"{path}.{key}"):
                        populated.add(key)
                    continue
                walk(value, f"{path}.{key}" if path else key, depth + 1)
            if census:
                censuses.append((path, frozenset(populated)))
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{path}[{index}]", depth + 1)
        elif isinstance(node, bool):
            # ``synthetic: true`` is the producers' explicit self-declaration
            # (attention items, evidence clusters, calendar events). Checked
            # BEFORE the number branch: ``bool`` is an ``int`` subclass.
            if node and _leaf_key(path) == "synthetic":
                markers.append(path)
        elif isinstance(node, str):
            _check_relayed_string(node, field=path or field)
            scope = _nature_scope(path)
            if scope is not None and node in OBSERVATION_CLAIM_LABELS:
                claims.append((path, scope))
            elif is_synthetic_marker(node, path) or (
                scope is not None and node in GENERATED_NATURE_LABELS
            ):
                markers.append(path)
        elif isinstance(node, (int, float)):
            _check_relayed_number(node, field=path or field)
        elif node is None:
            # JSON ``null`` is the ABSENCE of a value, which the contracts
            # require to stay distinct from zero and from a stale figure. It
            # carries no length, no control character and no claim, so it is
            # relayed as it is — explicitly, not by falling through.
            pass
        else:
            # Deny by default. The walk is now EXHAUSTIVE over the JSON
            # types; anything else (a ``Decimal``, a ``datetime``, an object
            # that only a repr could render) is a producer publishing outside
            # the contract, and the relay refuses rather than guesses.
            raise SnapshotContentError(
                f"{path or field}: relayed leaf of a type the contract does "
                "not carry",
                field=path or field,
            )

    walk(mapping, "", 0)
    for claim_path, scope in claims:
        for marker_path in markers:
            if marker_path != claim_path and _within(marker_path, scope):
                raise SnapshotContentError(
                    f"{claim_path}: the content claims an observation while "
                    f"carrying a synthetic provenance marker at {marker_path}",
                    field=claim_path,
                )
        for census_path, populated in censuses:
            if not populated or not _within(census_path, scope):
                continue
            # The bucket names below are members of POPULATION_LABELS — the
            # key vocabulary was closed during the walk — so naming one is
            # naming a PATH SEGMENT built from a nine-member constant set,
            # never echoing a stored value.
            generated = sorted(populated & GENERATED_NATURE_LABELS)
            if generated:
                raise SnapshotContentError(
                    f"{claim_path}: the content claims an observation while "
                    f"its nature census counts a generated member at "
                    f"{census_path}.{generated[0]}",
                    field=claim_path,
                )
            if not populated & OBSERVATION_CLAIM_LABELS:
                raise SnapshotContentError(
                    f"{claim_path}: the content claims an observation while "
                    f"its nature census at {census_path} counts no observed "
                    "member",
                    field=claim_path,
                )
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
    snapshot: CurrentSnapshot | None, *, now: datetime
) -> AttentionSnapshotResponse:
    """Render the last attention snapshot, or the honest empty state.

    Absence of a published snapshot is a NORMAL state (200): every
    snapshot-derived field stays ``None`` and ``reason`` explains why —
    nothing is invented, nothing degrades into a 500.

    Past the ``news_attention`` closed-session budget the SAME content is
    served with ``state = "stale"``, its age and its reason. ``age_seconds``
    is published in every datable state: its absence made a three-day queue
    look exactly like a one-minute one.
    """
    if snapshot is None:
        return AttentionSnapshotResponse(
            state="empty",
            snapshot_version=None,
            as_of=None,
            age_seconds=None,
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
    freshness = _relay_freshness(snapshot, now=now, policy=_ATTENTION_POLICY)

    return AttentionSnapshotResponse(
        state="stale" if freshness.stale else "ok",
        snapshot_version=snapshot.version,
        as_of=_parse_utc(content.get("as_of"), field="as_of"),
        age_seconds=freshness.age_seconds,
        population=population,
        coverage=coverage,
        items=tuple(
            _attention_item(raw, index=index) for index, raw in enumerate(items_raw)
        ),
        rejected_count=len(rejected_raw),
        reason=freshness.stale_reason,
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


def _optional_str(value: Any, *, field: str) -> str | None:
    if value is None:
        return None
    return _require_str(value, field=field)


def _require_int(value: Any, *, field: str) -> int:
    if isinstance(value, bool):
        raise SnapshotContentError(f"{field}: integer required", field=field)
    if not isinstance(value, int):
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


def _bounded_ratio(raw: Any, *, field: str) -> str | None:
    """Une PARTICIPATION vit dans [0, 1] — jamais negative, jamais au-dessus de 1.

    `breadth.value` est le nombre d'instruments au-dessus de leur repere
    rapporte aux couverts. Elle n'etait lue que par `_optional_str` : le garde
    commun, via la classe NON SIGNEE, etait sa SEULE protection. Depuis que
    `value` a rejoint la classe signee (une correlation opposee est negative),
    cette borne doit vivre ICI, sinon le desserrage aurait troque un faux refus
    sur Risques contre une vraie perte sur Marches.
    """
    value = _optional_str(raw, field=field)
    if value is None:
        return None
    try:
        ratio = Decimal(value)
    except InvalidOperation as exc:
        raise SnapshotContentError(
            f"{field}: plain decimal string required", field=field
        ) from exc
    if not ratio.is_finite() or ratio < 0 or ratio > 1:
        raise SnapshotContentError(
            f"{field}: participation ratio within [0, 1] required", field=field
        )
    return value


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
        value=_bounded_ratio(entry.get("value"), field="breadth.value"),
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
    snapshot: CurrentSnapshot | None, *, now: datetime
) -> MarketsOverviewResponse:
    """Render the last markets overview snapshot, or the honest empty state.

    Presentation only: the persisted content is validated fail-closed into
    the wire DTOs and relayed VERBATIM — no price, return, weight, breadth or
    percentage is ever recomputed here. Absence of a published snapshot is a
    NORMAL state (200 with ``state = "empty"``), never a 500 and never an
    invented zero.

    Past the ``daily_bar`` closed-session budget the SAME content is served with
    ``state = "stale"``, its age and its reason. ``age_seconds`` is published
    in every datable state: its absence made a three-day snapshot look
    exactly like a one-minute one.
    """
    if snapshot is None:
        return MarketsOverviewResponse(
            state="empty",
            snapshot_version=None,
            as_of=None,
            age_seconds=None,
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
    if content.get("unit") != MARKETS_UNIT:
        raise SnapshotContentError(
            "unit: the published sector-return unit is required", field="unit"
        )
    if content.get("display_unit") != MARKETS_DISPLAY_UNIT:
        raise SnapshotContentError(
            "display_unit: the published display unit is required",
            field="display_unit",
        )

    freshness = _relay_freshness(snapshot, now=now, policy=_MARKETS_POLICY)
    return MarketsOverviewResponse(
        state="stale" if freshness.stale else "ok",
        snapshot_version=snapshot.version,
        as_of=_parse_utc(content.get("as_of"), field="as_of"),
        age_seconds=freshness.age_seconds,
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
        reason=freshness.stale_reason,
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
    snapshot: CurrentSnapshot | None, *, instrument: str, now: datetime
) -> AnalysisResponse:
    """Render the last analysis dossier, or the honest empty state.

    Presentation only: the persisted content is shape-checked fail-closed
    and relayed VERBATIM — no bar, cluster, scenario value or verdict is
    ever recomputed here. Absence of a published snapshot is a NORMAL state
    (200 with ``state = "empty"``), never a 500 and never an invented
    dossier.

    Past the ``daily_bar`` closed-session budget the SAME dossier is served
    with ``state = "stale"``, its age and its reason. ``age_seconds`` is
    published in every datable state, INSIDE the budget too: a dossier at
    +71 h is not stale — 71 h fit in the declared 72 h — but it must never
    again be served without its date. That silent freezing is exactly what
    `.claude/rules/financial-safety.md` forbids as "silently keeping an old
    verdict"; the ``advice`` block itself is still relayed verbatim and
    never recomputed here.
    """
    if snapshot is None:
        return AnalysisResponse(
            state="empty",
            snapshot_version=None,
            as_of=None,
            age_seconds=None,
            population=None,
            instrument=instrument,
            engine_version=None,
            bars=None,
            indicators=None,
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
    if bars.get("status") not in BARS_STATUS_LABELS:
        raise SnapshotContentError(
            "bars.status: 'OK' or 'ABSENT' required", field="bars.status"
        )
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
    freshness = _relay_freshness(snapshot, now=now, policy=_ANALYSIS_POLICY)
    return AnalysisResponse(
        state="stale" if freshness.stale else "ok",
        snapshot_version=snapshot.version,
        as_of=_parse_utc(content.get("as_of"), field="as_of"),
        age_seconds=freshness.age_seconds,
        population=_require_str(content.get("population"), field="population"),
        instrument=published_instrument,
        engine_version=_require_str(
            content.get("engine_version"), field="engine_version"
        ),
        bars=bars,
        # FACULTATIF : un dossier publié avant l'ajout des indicateurs n'en
        # porte aucun. Exiger la clé transformerait cette absence légitime
        # en 500 — une absence n'est jamais une erreur.
        indicators=(
            _wire_mapping(content["indicators"], field="indicators")
            if content.get("indicators") is not None
            else None
        ),
        evidence=_wire_mapping(content.get("evidence"), field="evidence"),
        scenarios=scenarios,
        advice=dict(_checked_advice(content.get("advice"))),
        coverage=_wire_mapping(content.get("coverage"), field="coverage"),
        reason=freshness.stale_reason,
    )


def build_sec_fundamentals_response(
    snapshot: CurrentSnapshot | None, *, instrument: str, now: datetime
) -> SecFundamentalsResponse:
    """Relay one official SEC snapshot, or preserve its honest absence."""
    if snapshot is None:
        return SecFundamentalsResponse(
            state="empty",
            snapshot_version=None,
            as_of=None,
            age_seconds=None,
            population=None,
            instrument=instrument,
            source=None,
            rights=None,
            identity_state=None,
            cik=None,
            entity_name=None,
            data_as_of=None,
            filings=(),
            facts=(),
            conflicts=(),
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
    if content.get("source") != "sec_edgar":
        raise SnapshotContentError("source: sec_edgar required", field="source")
    if content.get("rights") != "R1_PUBLIC_FACT_SEC_EDGAR_POLICY_2026_08_28":
        raise SnapshotContentError("rights: SEC public-fact policy required", field="rights")
    identity_state = content.get("identity_state")
    if identity_state not in ("RESOLVED", "CONFLICTING_IDENTITY", "ABSENT"):
        raise SnapshotContentError(
            "identity_state: canonical SEC identity state required",
            field="identity_state",
        )

    def mappings(field: str) -> tuple[dict[str, Any], ...]:
        values = _require_list(content.get(field), field=field)
        return tuple(
            dict(_wire_mapping(value, field=f"{field}[{index}]"))
            for index, value in enumerate(values)
        )

    cik_value = content.get("cik")
    entity_value = content.get("entity_name")
    data_as_of_value = content.get("data_as_of")
    if identity_state == "RESOLVED":
        cik = _require_str(cik_value, field="cik")
        entity_name = _require_str(entity_value, field="entity_name")
    else:
        if cik_value is not None or entity_value is not None:
            raise SnapshotContentError(
                "cik/entity_name: must be absent when identity is unresolved",
                field="identity_state",
            )
        cik = None
        entity_name = None
    data_as_of = (
        _parse_utc(data_as_of_value, field="data_as_of")
        if data_as_of_value is not None
        else None
    )
    freshness = _relay_freshness(snapshot, now=now, policy=_SEC_FUNDAMENTALS_POLICY)
    return SecFundamentalsResponse(
        state="stale" if freshness.stale else "ok",
        snapshot_version=snapshot.version,
        as_of=_parse_utc(content.get("as_of"), field="as_of"),
        age_seconds=freshness.age_seconds,
        population=_require_str(content.get("population"), field="population"),
        instrument=published_instrument,
        source="sec_edgar",
        rights="R1_PUBLIC_FACT_SEC_EDGAR_POLICY_2026_08_28",
        identity_state=identity_state,
        cik=cik,
        entity_name=entity_name,
        data_as_of=data_as_of,
        filings=mappings("filings"),
        facts=mappings("facts"),
        conflicts=mappings("conflicts"),
        coverage=_wire_mapping(content.get("coverage"), field="coverage"),
        reason=freshness.stale_reason,
    )


# ---------------------------------------------------------------------------
# Option chain
# ---------------------------------------------------------------------------


def _optional_non_negative_int(value: Any, *, field: str) -> int | None:
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
    snapshot: CurrentSnapshot | None, *, underlying: str, now: datetime
) -> OptionChainResponse:
    """Render the last option-chain snapshot, or the honest empty state.

    Presentation only: the persisted content is validated fail-closed into
    the wire DTOs and relayed VERBATIM — no quote, IV, Greek or coverage
    figure is ever recomputed here. Absence of a published snapshot is a
    NORMAL state (200 with ``state = "empty"``), never a 500 and never an
    invented chain.

    Past the ``option_surface`` closed-session budget the SAME chain is
    served with ``state = "stale"``, its age and its reason. ``age_seconds``
    is published in every datable state: its absence made a three-day
    surface look exactly like a one-minute one.
    """
    if snapshot is None:
        return OptionChainResponse(
            state="empty",
            snapshot_version=None,
            as_of=None,
            age_seconds=None,
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
    freshness = _relay_freshness(snapshot, now=now, policy=_OPTION_CHAIN_POLICY)
    return OptionChainResponse(
        state="stale" if freshness.stale else "ok",
        snapshot_version=snapshot.version,
        as_of=_parse_utc(content.get("as_of"), field="as_of"),
        age_seconds=freshness.age_seconds,
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
        reason=freshness.stale_reason,
    )


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------


def _probe_field_entries(
    snapshot: CurrentSnapshot | None,
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

    reasons: set[str] = set()
    for _, _, field in winning:
        reason_code = field.get("reason_code")
        if isinstance(reason_code, str) and reason_code:
            reasons.add(reason_code)
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
    snapshot: CurrentSnapshot | None, *, now: datetime
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
    attention: CurrentSnapshot | None,
    capabilities: CurrentSnapshot | None,
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
    snapshot: CurrentSnapshot | None,
    attention: CurrentSnapshot | None,
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
        sorted(
            {capability_id for _, capability_id, _ in probes if capability_id not in declared_ids}
        )
    )
    snapshot_as_of: datetime | None = None
    snapshot_age: int | None = None
    if snapshot is not None:
        content = checked_relayed_content(snapshot.content)
        snapshot_as_of = _parse_utc(content.get("as_of"), field="as_of")
        # Aucun budget déclaré pour cette famille : l'âge est publié, rien
        # n'est jugé périmé ici. La péremption d'une capacité appartient au
        # ``expires_at`` de la sonde, champ par champ.
        snapshot_age = _relay_freshness(
            snapshot, now=now, policy=CAPABILITIES_FRESHNESS_POLICY
        ).age_seconds
    return SystemCapabilitiesResponse(
        checked_at=now,
        snapshot_version=None if snapshot is None else snapshot.version,
        as_of=snapshot_as_of,
        age_seconds=snapshot_age,
        total=len(entries),
        capabilities=entries,
        unknown_probed_capability_ids=unknown,
        health=build_system_health(
            db_ok=db_ok, attention=attention, capabilities=snapshot, now=now
        ),
    )
