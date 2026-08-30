"""Deterministic, replayable content deduplication (five documented levels).

Levels (docs/04-integrations/DATA_FUSION.md):

1. exact provider ``native_id`` per source;
2. normalized ``canonical_url`` (lowercase scheme/host, listed tracking
   parameters stripped, fragment stripped, remaining query sorted) within a
   bounded time window;
3. fingerprint of the normalized title (case, punctuation, whitespace and
   accents removed — but NOT the polarity of a figure) plus sorted
   normalized entities;
4. time-window similarity: a **reversible flag only** (``FLAGGED_SIMILAR``),
   never a destructive merge;
4b. polarity conflict: two observations asserting opposite directions
   (``+``/``-``, ``>``/``<``) are named by a reversible
   ``FLAGGED_POLARITY_CONFLICT`` decision — never merged, never split;
5. cluster construction preserving every provider, right, date and every
   :class:`FusionDecision`.

Polarity doctrine (``.claude/rules/financial-safety.md``, "convention de
signe"): the sign of a financial variation is data, not punctuation.
Normalization keeps four canonical markers so that ``"SPX -3,2 %"`` and
``"SPX +3,2 %"`` can never share a fingerprint. A sign binds to its digits
ACROSS what typography puts between them — currency symbol, space of any
width, bracket, quote, approximation mark or listed word — so ``-$2bn`` and
``Nasdaq - 3 %`` are signed too; the cost of that rule is a dash used as a
plain separator before a figure (``"Apple - 3 nouveaux produits"``) reading
as a sign, which splits a cluster instead of merging two opposites. Where
provider identity
(levels 1 and 2) still groups two opposite dispatches — one native id, one
canonical url — the group is kept and the contradiction is PUBLISHED rather
than resolved by electing one member; an absent marker is never treated as
the opposite of a present one.

Nothing is physically deleted: every input observation stays a member of
exactly one cluster (enforced by :class:`FusionResult`), and a member linked
as a duplicate keeps its full observation. The pipeline is a pure function of
its input set — input order never changes cluster ids, decisions or the
canonical hash of the result.
"""

from __future__ import annotations

import itertools
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timedelta
from types import MappingProxyType
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, model_validator

from vertex_core.contracts import ContractModel, NonEmptyStr, canonical_json_hash
from vertex_core.fusion.models import (
    ContentCluster,
    ContentObservation,
    FusionAction,
    FusionDecision,
)

__all__ = [
    "CANONICAL_URL_WINDOW",
    "FUSION_RULESET_VERSION",
    "POLARITY_MARKERS",
    "RULE_CANONICAL_URL",
    "RULE_FINGERPRINT",
    "RULE_KEPT_DISTINCT",
    "RULE_NATIVE_ID",
    "RULE_POLARITY_CONFLICT",
    "RULE_SIMILARITY_FLAG",
    "SIMILARITY_MIN_JACCARD_PERCENT",
    "SIMILARITY_MIN_SHARED_ENTITIES",
    "SIMILARITY_WINDOW",
    "TRACKING_PARAMS",
    "TRACKING_PARAM_PREFIXES",
    "FusionInputError",
    "FusionResult",
    "fuse",
    "fusion_result_hash",
    "normalize_canonical_url",
    "normalize_title",
    "opposed_markers",
    "title_fingerprint",
    "title_polarity_markers",
]


FUSION_RULESET_VERSION = "3.0.0"
"""Version stamped on every decision; bump on any behavioral rule change.

2.0.0 — title normalization stopped erasing the sign of a financial
variation (P1-6): fingerprints of previously fused opposite headlines now
differ, so this is a BREAKING rule change and replays across the boundary
are not comparable.

3.0.0 — the sign now BINDS to its digits across the transparent class
(currency symbol, space of any width, bracket, quote, approximation mark or
listed word), instead of requiring a digit immediately after it. ``-$2bn``
vs ``+$2bn`` and ``Nasdaq - 3 %`` vs ``Nasdaq + 3 %`` used to normalize
identically and fuse into one cluster with one elected representative.
Fingerprints of signed titles change again: BREAKING, replays across the
boundary are not comparable.
"""

RULE_NATIVE_ID = "fusion.dedup.native_id"
RULE_CANONICAL_URL = "fusion.dedup.canonical_url"
RULE_FINGERPRINT = "fusion.dedup.title_fingerprint"
RULE_SIMILARITY_FLAG = "fusion.dedup.similarity_window_flag"
RULE_POLARITY_CONFLICT = "fusion.dedup.polarity_conflict"
RULE_KEPT_DISTINCT = "fusion.dedup.kept_distinct"

CANONICAL_URL_WINDOW = timedelta(hours=48)
"""Maximum event-time gap for two same-canonical-URL observations to link."""

SIMILARITY_WINDOW = timedelta(hours=24)
"""Maximum event-time gap for the reversible similarity flag (level 4)."""

SIMILARITY_MIN_SHARED_ENTITIES = 1
"""Minimum shared normalized entities for a similarity-flag candidate pair."""

SIMILARITY_MIN_JACCARD_PERCENT = 60
"""Minimum title-token Jaccard similarity, in integer percent (no floats)."""

TRACKING_PARAM_PREFIXES = ("utm_",)
"""Query-parameter name prefixes stripped during URL normalization."""

TRACKING_PARAMS = frozenset(
    {
        "cmpid",
        "fbclid",
        "gclid",
        "icid",
        "igshid",
        "mc_cid",
        "mc_eid",
        "mkt_tok",
        "msclkid",
        "s_kwcid",
        "smid",
        "spm",
        "twclid",
        "yclid",
        "_ga",
    }
)
"""Exact query-parameter names stripped during URL normalization."""


class FusionInputError(ValueError):
    """Raised when the input observation set is invalid (fail-closed)."""


class FusionResult(ContractModel):
    """Immutable outcome of one deterministic fusion run.

    Invariants: clusters are sorted by ``cluster_id`` and partition the input
    exactly — every observation is a member of exactly one cluster and every
    observation is retained verbatim (zero physical deletion).
    """

    ruleset_version: NonEmptyStr
    clusters: tuple[ContentCluster, ...]
    observations: tuple[ContentObservation, ...] = Field(min_length=0)

    @model_validator(mode="after")
    def _check_partition(self) -> FusionResult:
        cluster_ids = [cluster.cluster_id for cluster in self.clusters]
        if any(a >= b for a, b in itertools.pairwise(cluster_ids)):
            raise ValueError("clusters must be strictly sorted by cluster_id")
        observation_ids = [obs.content_id for obs in self.observations]
        if any(a >= b for a, b in itertools.pairwise(observation_ids)):
            raise ValueError("observations must be strictly sorted by content_id")
        member_ids = [member for cluster in self.clusters for member in cluster.member_ids]
        if len(member_ids) != len(set(member_ids)):
            raise ValueError("cluster memberships must not overlap")
        if set(member_ids) != set(observation_ids):
            raise ValueError(
                "clusters must partition the observations exactly (zero deletion, zero invention)"
            )
        return self


_SIGN_MARKERS: Mapping[str, str] = MappingProxyType(
    {
        # Negative sign family (canonicalized to ASCII "-").
        "-": "-",  # U+002D HYPHEN-MINUS
        "\u2010": "-",  # HYPHEN
        "\u2011": "-",  # NON-BREAKING HYPHEN
        "\u2012": "-",  # FIGURE DASH
        "\u2013": "-",  # EN DASH
        "\u2212": "-",  # MINUS SIGN
        "\u2796": "-",  # HEAVY MINUS SIGN
        # Positive sign family (canonicalized to ASCII "+").
        "+": "+",  # U+002B PLUS SIGN
        "\u2795": "+",  # HEAVY PLUS SIGN
    }
)
"""Sign characters: a POLARITY marker only when bound to a number.

These characters double as hyphens and dashes (``Compàny-1``, ``COVID-19``,
``Apple — Microsoft``), so they only count as a sign under the attachment
rule of :func:`_sign_binding_digit_index`; everywhere else they stay
punctuation.
"""


_APPROXIMATION_MARKS = frozenset(
    {
        "~",  # U+007E TILDE
        "\u223c",  # TILDE OPERATOR
        "\u2248",  # ALMOST EQUAL TO
        "\u2243",  # ASYMPTOTICALLY EQUAL TO
        "\u2245",  # APPROXIMATELY EQUAL TO
        "\u2242",  # MINUS TILDE
        ".",  # decimal point of a leading-dot figure (``-.5 %``)
        ",",  # decimal comma of a leading-comma figure (``-,5 %``)
    }
)
"""Approximation and decimal marks that may sit between a sign and its digits.

Deliberately an explicit set and NOT the ``Sm`` category: ``+``, ``-``,
``<``, ``>`` and ``±`` are also mathematical symbols and each carries its own
polarity, so none of them may be crossed silently.
"""

_TRANSPARENT_WORDS = frozenset(
    {
        # Approximation words (fr/en) — ``-environ 3 %``, ``- about 3 %``.
        "environ",
        "approx",
        "approximativement",
        "approximately",
        "about",
        "around",
        "circa",
        "quelque",
        "quelques",
        "pres",  # "près" after accent stripping
        "presque",
        "quasi",
        "quasiment",
        "roughly",
        "nearly",
        # ISO 4217 codes and the letter part of composite currency signs
        # (``US$``, ``HK$``) — ``-USD 2 bn``, ``-US$2 bn``.
        "usd",
        "eur",
        "gbp",
        "chf",
        "jpy",
        "cad",
        "aud",
        "nzd",
        "cny",
        "rmb",
        "hkd",
        "sek",
        "nok",
        "dkk",
        "sgd",
        "inr",
        "brl",
        "mxn",
        "zar",
        "krw",
        "rub",
        "pln",
        "us",
        "hk",
        "nt",
    }
)
"""Closed set of alphabetic tokens a sign may bind ACROSS.

Any other word blocks the binding, which is what keeps ``"Apple - Banque de
France 3 %"`` free of a fabricated sign. Single letters are excluded on
purpose (``"Apple - a 3e version"`` must not become a signed figure).
"""

_SIGN_BINDING_MAX_SCAN = 24
"""Maximum characters scanned between a sign and the digits it may bind to."""

_SIGN_BINDING_MAX_WORDS = 2
"""Maximum alphabetic tokens (currency code + approximation word) crossed."""


def _is_transparent_between_sign_and_digits(character: str) -> bool:
    """True for a character a sign may bind across without losing its meaning.

    The class is deliberately enumerated rather than guessed:

    * whitespace of any width — ASCII space, NO-BREAK SPACE (U+00A0),
      NARROW NO-BREAK SPACE (U+202F), THIN SPACE (U+2009), FIGURE SPACE
      (U+2007). NFKD maps them to a space and ``str.isspace`` accepts them;
    * currency symbols, by Unicode category ``Sc`` — ``$``, ``€``, ``£``,
      ``¥``, ``₹``, ``₽``… (``-$2bn``, ``-€2bn``);
    * opening brackets (``Ps``) and initial quotes (``Pi``) plus the two
      straight ASCII quotes — ``-(2 bn)``, ``-«3 %»``, ``-"3" %``;
    * approximation and leading decimal marks (:data:`_APPROXIMATION_MARKS`).

    Everything else — a letter, another sign, a comparison character — stops
    the scan, so the sign stays ordinary punctuation.
    """
    if character.isspace():
        return True
    if character in _APPROXIMATION_MARKS or character in "\"'":
        return True
    return unicodedata.category(character) in ("Sc", "Ps", "Pi")


def _sign_binding_digit_index(folded: str, index: int) -> int | None:
    """Index of the digit a sign at ``index`` binds to, or ``None``.

    A ``-``/``+`` family character asserts a polarity when a decimal digit
    follows it across nothing but the transparent class above (bounded by
    :data:`_SIGN_BINDING_MAX_SCAN` characters and
    :data:`_SIGN_BINDING_MAX_WORDS` listed words). Pure, deterministic and
    symmetric between ``+`` and ``-``: a rule that recognized one sign more
    readily than the other would let an unrecognized ``-`` and a recognized
    ``+`` share the empty marker set and merge as opposites.
    """
    cursor = index + 1
    length = len(folded)
    stop = min(length, cursor + _SIGN_BINDING_MAX_SCAN)
    words = 0
    while cursor < stop:
        character = folded[cursor]
        if character.isdigit():
            return cursor
        if _is_transparent_between_sign_and_digits(character):
            cursor += 1
            continue
        if character.isalpha():
            end = cursor
            while end < stop and folded[end].isalpha():
                end += 1
            words += 1
            if words > _SIGN_BINDING_MAX_WORDS or folded[cursor:end] not in _TRANSPARENT_WORDS:
                return None
            cursor = end
            continue
        return None
    return None

_DIRECTION_MARKERS: Mapping[str, str] = MappingProxyType(
    {
        # Downward direction — same asserted polarity as a negative sign.
        "\u2193": "-",  # DOWNWARDS ARROW
        "\u2198": "-",  # SOUTH EAST ARROW
        "\u2199": "-",  # SOUTH WEST ARROW
        "\u25bc": "-",  # BLACK DOWN-POINTING TRIANGLE
        "\u2b07": "-",  # DOWNWARDS BLACK ARROW
        # Upward direction — same asserted polarity as a positive sign.
        "\u2191": "+",  # UPWARDS ARROW
        "\u2196": "+",  # NORTH WEST ARROW
        "\u2197": "+",  # NORTH EAST ARROW
        "\u25b2": "+",  # BLACK UP-POINTING TRIANGLE
        "\u2b06": "+",  # UPWARDS BLACK ARROW
        # Comparison direction — its own polarity axis, never a sign.
        ">": ">",
        "\u2265": ">",  # GREATER-THAN OR EQUAL TO
        "\u226b": ">",  # MUCH GREATER-THAN
        "<": "<",
        "\u2264": "<",  # LESS-THAN OR EQUAL TO
        "\u226a": "<",  # MUCH LESS-THAN
    }
)
"""Direction and comparison characters: ALWAYS a polarity marker.

Unlike ``-`` and ``+`` these never act as a hyphen or a separator inside a
headline, so no attachment rule is needed: they are meaning-bearing wherever
they appear.
"""

POLARITY_MARKERS = ("+", "-", "<", ">")
"""Canonical polarity markers produced by :func:`title_polarity_markers`."""

_OPPOSITE_MARKER: Mapping[str, str] = MappingProxyType(
    {"+": "-", "-": "+", ">": "<", "<": ">"}
)
"""The single explicit opposite of each canonical marker."""


def _scan_title(title: str) -> tuple[str, tuple[str, ...]]:
    """Normalize ``title`` and collect its polarity markers in one pass.

    Normalization (unchanged for ordinary text): NFKD decomposition,
    combining marks dropped, casefold, every non-alphanumeric character
    becomes a separator and whitespace collapses to single spaces.

    Polarity (the fix): the sign of a financial variation is DATA, not
    punctuation, so four canonical markers survive normalization.

    Attachment rule — a ``-``/``+`` family character is a sign when the
    previous character is not alphanumeric AND a decimal digit follows it
    across nothing but the transparent class of
    :func:`_is_transparent_between_sign_and_digits` (currency symbol,
    space of any width, bracket, quote, approximation mark, listed currency
    code or approximation word); otherwise it stays punctuation. The sign is
    then re-glued to those digits, so every typographic variant of one
    figure (``-2bn``, ``- 2bn``, ``-$2bn``, ``-\u202f2bn``) normalizes to the
    same token and the variants of one dispatch keep merging. A direction or
    comparison character (arrows, ``<``, ``>``) is always a marker: when a
    number follows the marker binds to it, otherwise it stands alone.
    """
    decomposed = unicodedata.normalize("NFKD", title)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    folded = stripped.casefold()

    pieces: list[str] = []
    markers: list[str] = []
    index, length = 0, len(folded)
    while index < length:
        character = folded[index]

        sign = _SIGN_MARKERS.get(character)
        if sign is not None:
            after_alphanumeric = index > 0 and folded[index - 1].isalnum()
            digit_index = (
                None if after_alphanumeric else _sign_binding_digit_index(folded, index)
            )
            if digit_index is None:
                pieces.append(" ")  # a hyphen or a dash: ordinary punctuation
                index += 1
                continue
            markers.append(sign)
            # Whatever separated the sign from its digits is normalized as
            # usual (a currency symbol or a bracket becomes a separator, a
            # listed word keeps its letters), then the sign is re-glued to
            # the number so typography cannot split one figure in two.
            for between in folded[index + 1 : digit_index]:
                pieces.append(between if between.isalnum() else " ")
            pieces.append(" " + sign + folded[digit_index])
            index = digit_index + 1
            continue

        direction = _DIRECTION_MARKERS.get(character)
        if direction is not None:
            markers.append(direction)
            digit_index = _sign_binding_digit_index(folded, index)
            if digit_index is None:
                pieces.append(" " + direction + " ")  # stands alone
                index += 1
                continue
            for between in folded[index + 1 : digit_index]:
                pieces.append(between if between.isalnum() else " ")
            pieces.append(" " + direction + folded[digit_index])
            index = digit_index + 1
            continue

        pieces.append(character if character.isalnum() else " ")
        index += 1

    return " ".join("".join(pieces).split()), tuple(markers)


def normalize_title(title: str) -> str:
    """Normalize a title: accents, case, punctuation and whitespace removed.

    Unicode is NFKD-decomposed and combining marks dropped, the result is
    casefolded, every non-alphanumeric character becomes a separator and
    whitespace collapses to single spaces. Polarity markers survive (see
    :func:`_scan_title`): ``"SPX -3,2 % sur la seance"`` normalizes to
    ``"spx -3 2 sur la seance"`` and never collides with its ``+3,2 %``
    opposite. Pure and deterministic.
    """
    return _scan_title(title)[0]


def title_polarity_markers(title: str) -> tuple[str, ...]:
    """Sorted, unique canonical polarity markers asserted by ``title``.

    An empty tuple means the title asserts NO direction — which is not the
    same as asserting a neutral or a positive one. Absent stays absent.
    """
    return tuple(sorted(set(_scan_title(title)[1])))


def opposed_markers(
    first: Iterable[str], second: Iterable[str]
) -> tuple[str, str] | None:
    """Return the first explicitly opposed marker pair, or ``None``.

    Two marker sets are opposed when one asserts a direction the other
    contradicts (``+`` against ``-``, ``>`` against ``<``) and does not
    itself assert. An ABSENT marker is never the opposite of a present one:
    an unsigned figure is of unknown polarity, not of the reverse polarity
    (absent, zero and opposite stay three distinct things).
    """
    left, right = frozenset(first), frozenset(second)
    if left == right:
        return None
    for marker in sorted(left):
        opposite = _OPPOSITE_MARKER[marker]
        if opposite in right and marker not in right:
            return (marker, opposite)
    return None


def _normalize_entities(entities: Iterable[str]) -> tuple[str, ...]:
    """Return sorted, unique, normalized, non-empty entity labels."""
    normalized = {normalize_title(entity) for entity in entities}
    normalized.discard("")
    return tuple(sorted(normalized))


def _is_tracking_param(name: str) -> bool:
    lowered = name.casefold()
    if lowered in TRACKING_PARAMS:
        return True
    return any(lowered.startswith(prefix) for prefix in TRACKING_PARAM_PREFIXES)


def normalize_canonical_url(url: str) -> str:
    """Normalize a URL for deduplication (level 2).

    Scheme and network location are lowercased (host names are
    case-insensitive), the fragment is dropped, listed tracking parameters
    are removed and the remaining query pairs are sorted for a canonical
    form. The path keeps its case (paths are case-sensitive).
    """
    parts = urlsplit(url)
    kept_pairs = sorted(
        (name, value)
        for name, value in parse_qsl(parts.query, keep_blank_values=True)
        if not _is_tracking_param(name)
    )
    return urlunsplit(
        (
            parts.scheme.casefold(),
            parts.netloc.casefold(),
            parts.path,
            urlencode(kept_pairs),
            "",
        )
    )


def title_fingerprint(title: str, entities: Iterable[str]) -> str | None:
    """Deterministic fingerprint of a normalized title plus sorted entities.

    Returns ``None`` when the normalized title carries no alphanumeric
    token (a punctuation-only or marker-only title must not link unrelated
    items — fail-closed, no wildcard bucket).
    """
    normalized_title = normalize_title(title)
    if not any(character.isalnum() for character in normalized_title):
        return None
    return canonical_json_hash(
        {"title": normalized_title, "entities": list(_normalize_entities(entities))}
    )


def _event_time(observation: ContentObservation) -> datetime:
    """Best available event time: ``published_at`` when present, else ``received_at``."""
    if observation.published_at is not None:
        return observation.published_at
    return observation.received_at


def _decision_id(rule_id: str, action: FusionAction, inputs: Sequence[str]) -> str:
    return canonical_json_hash(
        {
            "rule_id": rule_id,
            "rule_version": FUSION_RULESET_VERSION,
            "action": action.value,
            "inputs": list(inputs),
        }
    )


def _make_decision(
    rule_id: str,
    action: FusionAction,
    inputs: Sequence[str],
    rationale: str,
    reversible: bool,
) -> FusionDecision:
    ordered = tuple(sorted(inputs))
    return FusionDecision(
        decision_id=_decision_id(rule_id, action, ordered),
        rule_id=rule_id,
        rule_version=FUSION_RULESET_VERSION,
        inputs=ordered,
        action=action,
        rationale=rationale,
        reversible=reversible,
    )


class _UnionFind:
    """Union-find with deterministic roots (smallest content_id wins)."""

    def __init__(self, ids: Iterable[str]) -> None:
        self._parent: dict[str, str] = {content_id: content_id for content_id in ids}

    def find(self, content_id: str) -> str:
        parent = self._parent
        root = content_id
        while parent[root] != root:
            root = parent[root]
        while parent[content_id] != root:
            parent[content_id], content_id = root, parent[content_id]
        return root

    def union(self, first: str, second: str) -> None:
        root_a, root_b = self.find(first), self.find(second)
        if root_a == root_b:
            return
        keep, absorb = (root_a, root_b) if root_a < root_b else (root_b, root_a)
        self._parent[absorb] = keep


def _link_group(
    union: _UnionFind,
    member_ids: Sequence[str],
    rule_id: str,
    action: FusionAction,
    rationale: str,
    decisions: list[FusionDecision],
) -> None:
    """Link a group via edges from its smallest member (deterministic)."""
    ordered = sorted(member_ids)
    representative = ordered[0]
    for other in ordered[1:]:
        decisions.append(
            _make_decision(rule_id, action, (representative, other), rationale, reversible=False)
        )
        union.union(representative, other)


def fuse(observations: Sequence[ContentObservation]) -> FusionResult:
    """Run the deterministic deduplication levels and build clusters.

    Levels 1 to 3 link, level 4 flags similarity, level 4b flags an opposite
    polarity (never merging, never splitting) and level 5 builds the
    clusters. Pure function of the input set: any permutation of
    ``observations`` yields identical cluster ids, identical decisions and an
    identical canonical result hash. Raises :class:`FusionInputError` on
    duplicate ``content_id`` values (two distinct observations may not share
    an id).
    """
    by_id: dict[str, ContentObservation] = {}
    for observation in observations:
        if observation.content_id in by_id:
            raise FusionInputError(
                f"duplicate content_id rejected: {observation.content_id!r} appears more than once"
            )
        by_id[observation.content_id] = observation

    ordered_ids = sorted(by_id)
    union = _UnionFind(ordered_ids)
    link_decisions: list[FusionDecision] = []
    markers: dict[str, tuple[str, ...]] = {
        content_id: title_polarity_markers(by_id[content_id].title)
        for content_id in ordered_ids
    }

    # Level 1 — exact provider native id, per source.
    native_groups: dict[tuple[str, str], list[str]] = {}
    for content_id in ordered_ids:
        observation = by_id[content_id]
        if observation.native_id is not None:
            native_groups.setdefault((observation.source, observation.native_id), []).append(
                content_id
            )
    for (source, native_id), members in sorted(native_groups.items()):
        if len(members) > 1:
            _link_group(
                union,
                members,
                RULE_NATIVE_ID,
                FusionAction.LINKED_NATIVE_ID,
                f"same provider native id {native_id!r} from source {source!r}",
                link_decisions,
            )

    # Level 2 — normalized canonical URL within a bounded time window.
    url_groups: dict[str, list[str]] = {}
    for content_id in ordered_ids:
        observation = by_id[content_id]
        if observation.canonical_url is not None:
            url_groups.setdefault(normalize_canonical_url(observation.canonical_url), []).append(
                content_id
            )
    for normalized_url, members in sorted(url_groups.items()):
        if len(members) < 2:
            continue
        timeline = sorted(members, key=lambda cid: (_event_time(by_id[cid]), cid))
        for previous, current in itertools.pairwise(timeline):
            gap = _event_time(by_id[current]) - _event_time(by_id[previous])
            if gap <= CANONICAL_URL_WINDOW:
                link_decisions.append(
                    _make_decision(
                        RULE_CANONICAL_URL,
                        FusionAction.LINKED_CANONICAL_URL,
                        (previous, current),
                        f"same normalized canonical url {normalized_url!r} within "
                        f"{CANONICAL_URL_WINDOW}",
                        reversible=False,
                    )
                )
                union.union(previous, current)

    # Level 3 — normalized title + sorted entities fingerprint.
    fingerprint_groups: dict[str, list[str]] = {}
    for content_id in ordered_ids:
        observation = by_id[content_id]
        fingerprint = title_fingerprint(observation.title, observation.entities)
        if fingerprint is not None:
            fingerprint_groups.setdefault(fingerprint, []).append(content_id)
    for fingerprint, members in sorted(fingerprint_groups.items()):
        if len(members) > 1:
            _link_group(
                union,
                members,
                RULE_FINGERPRINT,
                FusionAction.LINKED_FINGERPRINT,
                f"same normalized title and entity fingerprint {fingerprint}",
                link_decisions,
            )

    # Level 4 — time-window similarity: reversible flag only, never a merge.
    entity_index: dict[str, list[str]] = {}
    tokens: dict[str, frozenset[str]] = {}
    for content_id in ordered_ids:
        observation = by_id[content_id]
        tokens[content_id] = frozenset(normalize_title(observation.title).split())
        for entity in _normalize_entities(observation.entities):
            entity_index.setdefault(entity, []).append(content_id)
    candidate_pairs: set[tuple[str, str]] = set()
    for members in entity_index.values():
        for index, first in enumerate(members):
            for second in members[index + 1 :]:
                candidate_pairs.add((first, second))
    flag_decisions: list[FusionDecision] = []
    for first, second in sorted(candidate_pairs):
        if union.find(first) == union.find(second):
            continue
        obs_a, obs_b = by_id[first], by_id[second]
        gap = abs(_event_time(obs_a) - _event_time(obs_b))
        if gap > SIMILARITY_WINDOW:
            continue
        shared_entities = set(_normalize_entities(obs_a.entities)).intersection(
            _normalize_entities(obs_b.entities)
        )
        if len(shared_entities) < SIMILARITY_MIN_SHARED_ENTITIES:
            continue
        union_tokens = tokens[first] | tokens[second]
        intersection_tokens = tokens[first] & tokens[second]
        if not union_tokens:
            continue
        # Integer cross-multiplication: no float comparison in the rule.
        if 100 * len(intersection_tokens) < SIMILARITY_MIN_JACCARD_PERCENT * len(union_tokens):
            continue
        opposed = opposed_markers(markers[first], markers[second])
        if opposed is not None:
            # Calling two contradictory headlines "similar" would hide the
            # contradiction behind a reassuring word. Both stay published in
            # their own cluster; the opposition itself is named.
            flag_decisions.append(
                _make_decision(
                    RULE_POLARITY_CONFLICT,
                    FusionAction.FLAGGED_POLARITY_CONFLICT,
                    (first, second),
                    f"opposite polarity {opposed[0]!r} vs {opposed[1]!r} on two "
                    f"otherwise similar titles within {SIMILARITY_WINDOW}; "
                    "reversible flag, never a merge",
                    reversible=True,
                )
            )
            continue
        flag_decisions.append(
            _make_decision(
                RULE_SIMILARITY_FLAG,
                FusionAction.FLAGGED_SIMILAR,
                (first, second),
                "similar title and shared entities within "
                f"{SIMILARITY_WINDOW}; reversible flag, never a merge",
                reversible=True,
            )
        )

    # Level 5 — cluster construction: every provider, right, date and
    # decision is preserved; nothing is deleted.
    members_by_root: dict[str, list[str]] = {}
    for content_id in ordered_ids:
        members_by_root.setdefault(union.find(content_id), []).append(content_id)

    # Level 4b — polarity conflict INSIDE a cluster. Levels 1 and 2 link on
    # provider identity (same native id, same canonical url), which is
    # stronger evidence than wording: two dispatches under one provider
    # identity are one item, typically a correction. Splitting them would
    # fabricate two events out of one and would lose the correction link, so
    # the cluster is kept and the contradiction is PUBLISHED instead. One
    # decision per opposed pair of distinct marker sets, named by each set's
    # smallest member (marker sets are a subset of POLARITY_MARKERS, so the
    # number of decisions per cluster is bounded and order-independent).
    conflict_decisions: list[FusionDecision] = []
    for members in members_by_root.values():
        if len(members) < 2:
            continue
        first_member_by_markers: dict[tuple[str, ...], str] = {}
        for content_id in members:  # members are already sorted by content_id
            first_member_by_markers.setdefault(markers[content_id], content_id)
        marker_sets = sorted(first_member_by_markers)
        for index, left in enumerate(marker_sets):
            for right in marker_sets[index + 1 :]:
                opposed = opposed_markers(left, right)
                if opposed is None:
                    continue
                conflict_decisions.append(
                    _make_decision(
                        RULE_POLARITY_CONFLICT,
                        FusionAction.FLAGGED_POLARITY_CONFLICT,
                        (
                            first_member_by_markers[left],
                            first_member_by_markers[right],
                        ),
                        f"cluster members assert opposite polarity {opposed[0]!r} "
                        f"vs {opposed[1]!r}; both members kept, the contradiction "
                        "is published and never resolved by election",
                        reversible=True,
                    )
                )

    decisions_by_root: dict[str, list[FusionDecision]] = {}
    for decision in (*link_decisions, *conflict_decisions):
        root = union.find(decision.inputs[0])
        decisions_by_root.setdefault(root, []).append(decision)
    for decision in flag_decisions:
        touched_roots = {union.find(content_id) for content_id in decision.inputs}
        for root in touched_roots:
            decisions_by_root.setdefault(root, []).append(decision)

    clusters: list[ContentCluster] = []
    for root, members in members_by_root.items():
        decisions = decisions_by_root.get(root, [])
        if len(members) == 1:
            # A singleton was linked by no rule; similarity flags (if any) are
            # not links, so the KEPT_DISTINCT record is always due.
            decisions = [
                *decisions,
                _make_decision(
                    RULE_KEPT_DISTINCT,
                    FusionAction.KEPT_DISTINCT,
                    (members[0],),
                    "no deduplication rule linked this observation to another",
                    reversible=True,
                ),
            ]
        decisions = sorted(decisions, key=lambda d: (d.rule_id, d.inputs, d.decision_id))
        member_observations = [by_id[content_id] for content_id in members]
        published = [
            obs.published_at for obs in member_observations if obs.published_at is not None
        ]
        clusters.append(
            ContentCluster(
                cluster_id=canonical_json_hash({"members": members}),
                member_ids=tuple(members),
                sources=tuple(sorted({obs.source for obs in member_observations})),
                tiers=tuple(sorted({obs.source_tier for obs in member_observations})),
                rights=tuple(sorted({obs.rights for obs in member_observations})),
                first_published_at=min(published) if published else None,
                last_received_at=max(obs.received_at for obs in member_observations),
                decisions=tuple(decisions),
            )
        )

    return FusionResult(
        ruleset_version=FUSION_RULESET_VERSION,
        clusters=tuple(sorted(clusters, key=lambda cluster: cluster.cluster_id)),
        observations=tuple(by_id[content_id] for content_id in ordered_ids),
    )


def fusion_result_hash(result: FusionResult) -> str:
    """Canonical ``sha256:`` hash of a fusion result (replay comparison aid)."""
    return canonical_json_hash(result)
