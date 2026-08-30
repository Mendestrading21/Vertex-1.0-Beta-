"""Vertex AI (page 11) — LOT-21 socle: the DETERMINISTIC template only.

Decision state (human decision B-05 pending): NO AI provider exists in this
repository — ``VERTEX_AI_PROVIDER=disabled`` is the declared state and the
status route says so. The ONLY explanation path is the deterministic
template of this module: a PURE function of one persisted snapshot that
performs no network call, invokes no model, reads no clock beyond the
snapshot's own ``as_of``, and is explicitly labeled
``provider = "DETERMINISTIC_TEMPLATE"`` — it is never presented as a model.

Grounding contract (ADR-008 / AI_GATEWAY.md, enforced by code and tests):

- every claim is typed ``FACT`` and MUST reference at least one
  ``evidence_ref`` that REALLY exists in the source snapshot (advice id,
  cluster ids, calculation input hashes, observation event ids, or the
  snapshot's own reference); :func:`validate_claims` runs as the LAST-LINE
  guard on the finished answer and fails closed on any reference outside
  the catalog;
- no claim text contains an instruction to transact, a promise, a
  probability, or any figure that is not a VERBATIM string of the snapshot
  content (counts and derived numbers stay out of claim texts);
- UNTRUSTED EXTERNAL CONTENT (news-cluster titles and any other source
  text) is NEVER concatenated into a ``FACT`` claim. A cluster is cited by
  its identifier and its declared item count only; an excerpt, when it is
  shown at all, travels in the separate :class:`AiExternalExcerpt` channel,
  labeled ``EXTERNAL_UNVERIFIED``, neutralized (markup escaped, control
  characters stripped) and truncated;
- a produced statement is COMPOSED of typed segments: free prose and
  CANONICAL VERTEX IDENTIFIERS. **The boundary classifies by ORIGIN, not by
  shape.** A segment escapes the forbidden-language screen only when its
  value BELONGS to :data:`CANONICAL_VOCABULARY` — a CLOSED set ENUMERATED
  by ``vertex_core`` (the gate ids of ``GATE_CATALOG``, the members of the
  canonical enums, the reason codes of the gate catalog) plus this module's
  own literal constants. Membership, never a regular expression: a snapshot
  field whose origin is not proven (a population label, a ticker, a lot id,
  a declared unit, a news-cluster id, a horizon, a decimal string) is FREE
  PROSE and IS screened, however much it looks like an identifier. This is
  what stops a stored string such as a ``unit`` reading
  ``pourcentage-de-gain-garanti`` or a ``ticker`` reading ``vendez-tout``
  from crossing into a ``FACT`` claim;
- only the free prose goes through the forbidden-language detection step of
  AI_GATEWAY.md (« détection de langage interdit ») — transactional
  injunction, unsupported certainty, uncalibrated probability and executable
  markup, all decided on the Unicode-normalized form (NFKC, no control or
  format character, no homoglyph, no diacritic, HTML entities and percent
  escapes decoded). A text that triggers it is REFUSED, never silently
  cleaned: it is replaced by an explicit ``missing_data`` entry naming what
  was refused, plus a visible limitation. A lexical rule can therefore NEVER
  delete a statement because of a CANONICAL identifier — in particular the
  ``probability_calibrated_if_used`` gate, whose disappearance would hide the
  very rule forbidding an uncalibrated probability;
- HONEST QUALIFICATION OF THAT DETECTOR (do not read more into it than it
  gives): :func:`detect_forbidden_language` is a **filtre de meilleur
  effort** — a best-effort keyword blacklist (French, English, and a few
  Spanish/German imperatives) over external content that is ALREADY
  cantoned. It is **jamais une classe fermée** / never a closed class: an
  unlisted language, an unlisted verb or a new obfuscation passes it. The
  guarantee that actually holds is STRUCTURAL, not lexical: an external
  excerpt is never a claim, it travels labeled ``EXTERNAL_UNVERIFIED``,
  escaped, truncated and carrying a visible limitation. The adversarial
  corpus in ``apps/api/tests/test_ai_explain.py`` MEASURES the blacklist's
  coverage; it proves no exhaustiveness;
- a percentage is refused only when it is FORWARD-LOOKING (a prediction, an
  expectation, a target, a stated probability). A measured, accounting or
  past percentage — « Marge brute de 42 % », « Résultat net en baisse de
  7 % » — is a fact and is kept: refusing it would turn the information
  rail into a wall of refusal notices;
- every gate the snapshot publishes as ``BLOCK`` is restituted, WHATEVER the
  shape of its identifier and whatever the subject kind: a gate whose id is
  not a canonical token becomes an ANONYMOUS contradiction plus a
  ``missing_data`` entry, and the completeness invariant counts it. The
  invariant is checked on the finished answer and fails closed with a typed
  :class:`AiGroundingError`. It counts by ORIGIN, never by string equality: a
  contradiction reference carries its :class:`_ReferenceNamespace`, and only
  :func:`_gate_parts` mints a ``GATE`` one. A STORED value that merely equals
  a ``gate_id`` — a ``coverage.invalid_positions[].ticker``, say — used to
  satisfy the invariant on its own, so a closed gate disappeared from the
  answer while an unrelated contradiction stating the OPPOSITE took its
  place; the namespace is what makes that unrepresentable;
- a value read from the snapshot is restituted only as a CANONICAL TOKEN
  (:func:`_token`, a ``fullmatch`` — a trailing newline is NOT a token): a
  source field carrying markup, spaces or invisible characters is reported as
  non-conforming instead of being relayed. Symmetrically, a legitimate
  identifier that this narrow ASCII shape refuses NEVER makes a statement
  disappear silently: the block it would have carried is named in
  ``missing_data`` (fail-closed reporting, never a mute availability
  regression);
- an empty or malformed corpus produces a STRUCTURED REFUSAL
  (``state = "refused"`` with a readable ``refusal_reason``), never an empty
  explanation presented as complete;
- contradictions (closed gates, contradictory positions) and missing data
  are listed separately from facts;
- ``limitations`` is NEVER empty: it always carries the B-05 notice
  :data:`LIMITATION_PROVIDER_DISABLED` plus the snapshot's own limitations;
- the answer carries its own traceability: ``snapshot_version``,
  ``content_hash`` and ``as_of`` of the explained snapshot.

The subject snapshot is one of ``analysis/{key}``,
``portfolio_valuation/{key}`` or ``performance/{key}``; an absent snapshot
is a clean 404 at the route level (nothing to explain, nothing invented).
"""

from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal, Mapping, NamedTuple, Optional, Sequence, Union

from pydantic import Field, model_validator

from vertex_core.contracts import enums as canonical_enums
from vertex_core.contracts.types import (
    ContractModel,
    NonEmptyStr,
    PositiveInt,
    UtcDatetime,
)
from vertex_core.decision.gates import GATE_ORDER, REASON_UNEVALUABLE
from vertex_persistence.repository.snapshots import CurrentSnapshot

__all__ = [
    "AI_ERROR_INCOMPLETE_ANSWER",
    "AI_ERROR_UNGROUNDED_CLAIM",
    "AI_STATUS_PROVIDER",
    "AI_STATUS_REASON",
    "CANONICAL_VOCABULARY",
    "ERROR_NO_SNAPSHOT_FOR_SUBJECT",
    "EXTERNAL_CONTENT_LABEL",
    "EXTERNAL_EXCERPT_MAX_LENGTH",
    "FORBIDDEN_LANGUAGE_CERTAINTY",
    "FORBIDDEN_LANGUAGE_MARKUP",
    "FORBIDDEN_LANGUAGE_PROBABILITY",
    "FORBIDDEN_LANGUAGE_TRANSACTIONAL",
    "LIMITATION_EXTERNAL_CONTENT",
    "LIMITATION_FORBIDDEN_LANGUAGE",
    "LIMITATION_PROVIDER_DISABLED",
    "LIMITATION_REFUSED_ANSWER",
    "LIMITATION_UNUSABLE_ADVICE",
    "PROVIDER_DETERMINISTIC_TEMPLATE",
    "REFUSAL_EMPTY_CORPUS",
    "REFUSAL_NO_GROUNDED_CLAIM",
    "SUBJECT_KEY_PATTERN",
    "SUBJECT_SNAPSHOT_KINDS",
    "TEMPLATE_VERSION",
    "AiAnswer",
    "AiClaim",
    "AiContradiction",
    "AiEvidenceCatalogEntry",
    "AiExplainRequest",
    "AiExternalExcerpt",
    "AiGroundingError",
    "AiStatusResponse",
    "AiSubject",
    "build_ai_answer",
    "detect_forbidden_language",
    "validate_claims",
]

PROVIDER_DETERMINISTIC_TEMPLATE = "DETERMINISTIC_TEMPLATE"
TEMPLATE_VERSION = "vertex.ai-deterministic-template/1.0"

AI_STATUS_PROVIDER = "DISABLED"
AI_STATUS_REASON = "B-05_HUMAN_DECISION_PENDING"

LIMITATION_PROVIDER_DISABLED = (
    "Fournisseur IA désactivé — décision B-05 en attente ; "
    "explication par gabarit déterministe"
)
"""Mandatory limitation of EVERY answer while decision B-05 is pending."""

LIMITATION_EXTERNAL_CONTENT = (
    "Extrait externe non vérifié, neutralisé et tronqué : contenu de source, "
    "jamais un fait Vertex ni une instruction"
)
"""Shown as soon as one external excerpt is carried by the answer."""

LIMITATION_FORBIDDEN_LANGUAGE = (
    "Une formulation a déclenché la détection de langage interdit "
    "(AI_GATEWAY) : elle est refusée, jamais nettoyée silencieusement"
)

LIMITATION_UNUSABLE_ADVICE = (
    "Bloc d'avis inexploitable : statut, direction et horizon ne sont pas "
    "restitués faute d'identifiant d'avis citable"
)

LIMITATION_REFUSED_ANSWER = (
    "Corpus inexploitable : aucune explication n'est produite (refus "
    "structuré) — cette réponse n'est pas une explication complète"
)

ERROR_NO_SNAPSHOT_FOR_SUBJECT = "NO_SNAPSHOT_FOR_SUBJECT"

REFUSAL_EMPTY_CORPUS = "EMPTY_OR_MALFORMED_SNAPSHOT_CONTENT"
REFUSAL_NO_GROUNDED_CLAIM = "NO_GROUNDED_CLAIM"

EXTERNAL_CONTENT_LABEL = "EXTERNAL_UNVERIFIED"
EXTERNAL_EXCERPT_MAX_LENGTH = 160
"""Hard truncation length of an external excerpt (before escaping)."""

SUBJECT_KEY_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"
"""Accepted shape of a subject snapshot key (same shape as the snapshot
routes' path keys); anything else is rejected before any lookup."""

SUBJECT_SNAPSHOT_KINDS: Mapping[str, str] = {
    "analysis": "analysis",
    "portfolio_valuation": "portfolio_valuation",
    "performance": "performance",
}
"""Subject kind -> persisted snapshot kind (identity today, explicit map)."""

AI_ERROR_UNGROUNDED_CLAIM = "AI_ANSWER_UNGROUNDED"
"""Typed code: a finished claim cites evidence absent from the catalog."""

AI_ERROR_INCOMPLETE_ANSWER = "AI_ANSWER_INCOMPLETE"
#: Le bloc d'avis publie des portes que l'on ne sait pas lire : une porte non
#: évaluable vaut BLOCK (ADR-014), donc la réponse est refusée plutôt que
#: construite en ignorant ce que l'on n'a pas compris.
AI_ERROR_UNREADABLE_GATES = "AI_ANSWER_UNREADABLE_GATES"
"""Typed code: a gate published as ``BLOCK`` is missing from the answer."""

_SAFE_EVIDENCE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9:._@/+-]{0,127}")
"""Shape an identifier coming from external content must have to be cited.

Matched with ``fullmatch``: ``$`` alone would accept a trailing newline, so
``"sha256:aaa\n"`` used to pass a boundary that ``NonEmptyStr`` refuses.
"""

_CANONICAL_TOKEN = re.compile(r"[-+]?[A-Za-z0-9][A-Za-z0-9:._@/+-]{0,127}")
"""Shape a value must have to be restituted VERBATIM at all (``fullmatch``).

This is a SANITY control on the characters of a relayed value — never a proof
of origin. A value carrying markup, spaces, invisible characters, homoglyphs
or a trailing control character is not relayed: it is reported as
non-conforming. Whether the relayed value may ALSO escape the
forbidden-language screen is a separate question, decided by MEMBERSHIP in
:data:`CANONICAL_VOCABULARY` — never by this shape.
"""


# ---------------------------------------------------------------------------
# CLOSED CANONICAL VOCABULARY — the origin test of the segment boundary
# ---------------------------------------------------------------------------

_GATE_REASON_CODES: frozenset[str] = frozenset(
    {
        REASON_UNEVALUABLE,
        "ALL_CALCULATIONS_VALID",
        "AMBIGUOUS_IDENTITY",
        "CALIBRATION_AGING",
        "CONSTRAINTS_VERSIONED",
        "CONTRADICTORY_SNAPSHOT",
        "DELAYED_DATA_ENTITLEMENT",
        "DELAYED_LIQUIDITY_OBSERVATION",
        "ENTITLED",
        "EVENT_CALENDAR_INCOMPLETE",
        "EXPLICIT_CONTRADICTIONS_PRESENT",
        "FRESH_AND_COHERENT",
        "INVALID_CALCULATION",
        "LIQUIDITY_BELOW_MINIMUM",
        "LIQUIDITY_SUFFICIENT",
        "MANUAL_EXPORT_SOURCE",
        "MISSING_CALCULATIONS",
        "MISSING_PORTFOLIO_RISK",
        "MISSING_SNAPSHOT",
        "NOT_IMPLEMENTED_CALCULATION",
        "NOT_REQUIRED",
        "NO_CRITICAL_CONTRADICTION",
        "NO_OUT_OF_SAMPLE_VALIDATION",
        "OUTDATED_CONSTRAINTS_ACKNOWLEDGEMENT",
        "PORTFOLIO_RISK_AVAILABLE",
        "PROBABILITY_CALIBRATED",
        "PROBABILITY_NOT_USED",
        "RESOLVED",
        "RESOLVED_WITHOUT_CONID",
        "SESSION_AND_EVENT_KNOWN",
        "SESSION_UNKNOWN",
        "STALE_PORTFOLIO_DECLARATIONS",
        "STALE_SNAPSHOT",
        "UNCALIBRATED_PROBABILITY",
        "UNRESOLVED_CRITICAL_CONTRADICTION",
        "UNRESOLVED_IDENTITY",
        "UNVERSIONED_CONSTRAINTS",
    }
)
"""The reason codes ``vertex_core.decision.gates`` really publishes.

``vertex_core`` does not export this vocabulary as a symbol (the codes are
literals inside the ten evaluators), so it is MIRRORED here and pinned by a
drift test that re-extracts them from the gate module's own source. A code
absent from this set is prose and is screened like any other free text.
"""

_MODULE_OWNED_TOKENS: frozenset[str] = frozenset(
    {
        # Forbidden-language categories named in a refusal note.
        "TRANSACTIONAL_LANGUAGE",
        "UNSUPPORTED_CERTAINTY",
        "UNCALIBRATED_PROBABILITY",
        "EXECUTABLE_MARKUP",
        # Advice fields this module restitutes BY NAME.
        "status",
        "direction",
        "horizon",
        # Performance metric keys and value fields (pinned by a drift test).
        "twr_gross",
        "twr_net",
        "xirr_gross",
        "xirr_net",
        "drawdown_gross",
        "drawdown_net",
        "total_return",
        "rate",
        "max_drawdown",
        # Portfolio sub-blocks restituted BY NAME.
        "unrealized",
        "realized",
    }
)
"""Literal constants OF THIS MODULE — never a value read from a snapshot.

They are enumerated, so they are as closed as the ``vertex_core`` vocabulary;
they are listed apart so the origin of every unscreened value stays legible.
"""

CANONICAL_VOCABULARY: frozenset[str] = frozenset(
    set(GATE_ORDER)
    | {
        member.value
        for name in canonical_enums.__all__
        for member in getattr(canonical_enums, name)
    }
    | _GATE_REASON_CODES
    | _MODULE_OWNED_TOKENS
)
"""The CLOSED set of values a produced statement may carry UNSCREENED.

Origin, not shape: a value belongs to it because ``vertex_core`` (or this
module) ENUMERATES it, never because it looks like an identifier. Everything
else read from a snapshot is free prose and goes through the
forbidden-language screen.
"""


# ---------------------------------------------------------------------------
# Unicode normalization — applied BEFORE any lexical decision
# ---------------------------------------------------------------------------

_INVISIBLE_CATEGORIES = frozenset({"Cc", "Cf"})
"""Unicode control (``Cc``) and format (``Cf``) characters.

``Cf`` carries the invisible separators and the BIDI overrides (``U+200B``,
``U+00AD``, ``U+2060``, ``U+202D``, ``U+202E``…): they hide a word from a
lexical scan and can visually reverse the text around an excerpt. They are
removed before detection AND when neutralizing untrusted content.
"""

_PERCENT_LOOKALIKES: Mapping[int, str] = {
    0x066A: "%",  # ARABIC PERCENT SIGN
    0x2030: "%",  # PER MILLE SIGN
    0x2031: "%",  # PER TEN THOUSAND SIGN
}
"""Percent signs NFKC does not fold (``%``, ``\uff05`` and ``\ufe6a`` are)."""

_HOMOGLYPHS: tuple[tuple[str, str], ...] = (
    ("\u0430", "a"), ("\u0410", "A"), ("\u0435", "e"), ("\u0415", "E"),
    ("\u043e", "o"), ("\u041e", "O"), ("\u0440", "p"), ("\u0420", "P"),
    ("\u0441", "c"), ("\u0421", "C"), ("\u0443", "y"), ("\u0423", "Y"),
    ("\u0445", "x"), ("\u0425", "X"), ("\u0456", "i"), ("\u0406", "I"),
    ("\u0455", "s"), ("\u0405", "S"), ("\u0458", "j"), ("\u0408", "J"),
    ("\u043a", "k"), ("\u041a", "K"), ("\u043c", "m"), ("\u041c", "M"),
    ("\u043d", "h"), ("\u041d", "H"), ("\u0432", "b"), ("\u0412", "B"),
    ("\u0442", "t"), ("\u0422", "T"), ("\u0433", "r"), ("\u0451", "e"),
    ("\u03b1", "a"), ("\u0391", "A"), ("\u03bf", "o"), ("\u039f", "O"),
    ("\u03b5", "e"), ("\u0395", "E"), ("\u03c1", "p"), ("\u03a1", "P"),
    ("\u03c4", "t"), ("\u03a4", "T"), ("\u03bd", "v"), ("\u039d", "N"),
    ("\u03b9", "i"), ("\u0399", "I"), ("\u03ba", "k"), ("\u039a", "K"),
    ("\u03c5", "u"), ("\u03a5", "Y"), ("\u03c7", "x"), ("\u03a7", "X"),
    ("\u0392", "B"), ("\u0396", "Z"), ("\u0397", "H"), ("\u039c", "M"),
    # IPA / phonetic letters drawn like Latin ones (U+0251 « \u0251 »...).
    ("\u0251", "a"), ("\u0261", "g"), ("\u026a", "i"), ("\u0269", "i"),
    ("\u0254", "c"), ("\u0299", "b"), ("\u0280", "r"), ("\u029c", "h"),
    # Latin small-capital letters (U+1D00 block).
    ("\u1d00", "a"), ("\u1d04", "c"), ("\u1d05", "d"), ("\u1d07", "e"),
    ("\u1d0a", "j"), ("\u1d0b", "k"), ("\u1d0f", "o"), ("\u1d18", "p"),
    ("\u1d1b", "t"), ("\u1d1c", "u"), ("\u1d20", "v"), ("\u1d21", "w"),
    ("\u1d22", "z"),
    # Cherokee syllabary letters drawn like Latin capitals.
    ("\u13aa", "A"), ("\u13a0", "D"), ("\u13c0", "G"), ("\u13ac", "S"),
    ("\u13a1", "R"), ("\u13ce", "P"), ("\u13a9", "Z"), ("\u13b3", "W"),
    ("\u13de", "L"), ("\u13df", "C"), ("\u13e2", "B"), ("\u13ef", "J"),
)
"""Letters of other scripts drawn like the frequent Latin ones.

Cyrillic, Greek, IPA/phonetic, Latin small capitals and Cherokee. The table
is a BEST-EFFORT list: Unicode holds far more lookalikes than any table can
enumerate, which is one reason the detector is not a closed class.
"""

_FOLDING_TABLE = str.maketrans(
    {
        **{ord(source): target for source, target in _HOMOGLYPHS},
        **{code: target for code, target in _PERCENT_LOOKALIKES.items()},
    }
)

_INTRA_WORD_HYPHEN = re.compile(r"(?<=\w)[-\u2010-\u2015](?=\w)")

_INTRA_WORD_SEPARATOR = re.compile(
    r"(?<=\w)[-.\u2010-\u2015_*+~/\\|:;'\u2019\u00b7\u2022](?=\w)"
)
"""Intra-word separators used to break a word out of a lexical scan.

``a.c.h.e.t.e.z`` and ``a_c_h_e_t_e_z`` are the reproduced bypasses. The
de-separated form is an ADDITIONAL candidate: it can only add a detection,
never remove one.
"""

_PERCENT_ESCAPE = re.compile(r"%([0-9A-Fa-f]{2})")


def _decode_escapes(text: str) -> tuple[str, ...]:
    """Return ``text`` plus its HTML-entity and percent-decoded variants.

    ``&#97;chetez`` and ``%61chetez`` reach the detector as ``achetez``.
    Decoding is done FOR DETECTION ONLY: the excerpt actually published is
    the escaped, truncated one produced by :func:`_neutralize_external_text`.
    """
    variants = [text]
    unescaped = html.unescape(text)
    if unescaped != text:
        variants.append(unescaped)
    try:
        decoded = _PERCENT_ESCAPE.sub(
            lambda match: chr(int(match.group(1), 16)), variants[-1]
        )
    except ValueError:  # pragma: no cover - the pattern guarantees hex pairs
        decoded = variants[-1]
    if decoded != variants[-1]:
        variants.append(decoded)
    return tuple(variants)


def _fold(text: str) -> str:
    """Return the canonical folded form used for EVERY lexical decision.

    NFKC (full-width and compatibility forms), removal of the control and
    format characters (invisible separators, BIDI overrides), homoglyph
    folding, removal of the diacritics and case folding. ``"ache\u200btez"``,
    ``"\u0430cheter"``, ``"\uff41cheter"`` and ``"assur\u00e9e"`` all reach the
    detector as plain ASCII words.
    """
    normalized = unicodedata.normalize("NFKC", text)
    visible = "".join(
        character
        for character in normalized
        if unicodedata.category(character) not in _INVISIBLE_CATEGORIES
    )
    mapped = visible.translate(_FOLDING_TABLE)
    decomposed = unicodedata.normalize("NFD", mapped)
    without_marks = "".join(
        character
        for character in decomposed
        if unicodedata.category(character) != "Mn"
    )
    return unicodedata.normalize("NFC", without_marks).casefold()


# ---------------------------------------------------------------------------
# Forbidden-language detection (AI_GATEWAY.md, output validation step 6)
#
# The rules read FOLDED text (lower case, no diacritics, no invisible
# character) and they screen FREE PROSE ONLY — a canonical identifier is a
# typed field, never prose (see :class:`_Segment`).
# ---------------------------------------------------------------------------

FORBIDDEN_LANGUAGE_TRANSACTIONAL = "TRANSACTIONAL_LANGUAGE"
FORBIDDEN_LANGUAGE_CERTAINTY = "UNSUPPORTED_CERTAINTY"
FORBIDDEN_LANGUAGE_PROBABILITY = "UNCALIBRATED_PROBABILITY"
FORBIDDEN_LANGUAGE_MARKUP = "EXECUTABLE_MARKUP"

_TRANSACTIONAL_VERB = re.compile(
    r"\b(?:"
    # French transaction VERBS (an order given), never the descriptive nouns
    # "achat"/"vente"/"ordre" of financial vocabulary.
    r"achet(?:e|es|ent|er|ez|ons|ee|ees)|rachet(?:e|es|ent|er|ez|ons)|"
    r"acquerir|acquerez|acquiers|"
    r"vendre|vendez|vends|vend|revendre|revendez|revends|"
    r"liquider|liquidez|souscrire|souscrivez|shorter|shortez|"
    r"buy|buys|buying|bought|sell|sells|selling|sold|"
    r"execut(?:e|es|ed|ing|er|ez|ons)"
    r")\b"
)

_TRANSACTIONAL_ORDER = re.compile(
    r"\b(?:pass(?:er|ez|e)|plac(?:er|ez|e)|transmett(?:re|ez)|envoy(?:er|ez)|"
    r"annul(?:er|ez)|modifi(?:er|ez)|soumett(?:re|ez)|saisi(?:r|ssez))\s+"
    r"(?:(?:un|une|des|le|la|les|l['\u2019])\s*)?ordres?\b"
    r"|\b(?:place|submit|send|cancel|modify|route|enter|fill)\s+"
    r"(?:(?:an?|the|your)\s+)?orders?\b"
)
"""An ORDER GIVEN. « ordres de grandeur » or « volume d'achat » are
descriptive financial vocabulary and stay allowed."""

_TRANSACTIONAL_INJUNCTION = re.compile(
    # French position injunctions (2nd person / infinitive imperative form).
    r"\b(?:renforc(?:ez|er|ons)|alleg(?:ez|er|eons)|sold(?:ez|er|ons)|"
    r"coup(?:ez|er)\s+(?:la\s+|votre\s+|vos\s+)?(?:position|ligne|titre)s?|"
    r"sort(?:ez|ir)\s+(?:du|de\s+la|des)\b|arbitr(?:ez|er)|"
    r"encaiss(?:ez|er)|empoch(?:ez|er)|position(?:nez|ner)\s+vous|"
    r"surachet(?:ez|ons)|survend(?:ez|ons))\b"
    # « prenez position », « prendre position ».
    r"|\b(?:pren(?:ez|ons|ds)|prendre)\s+"
    r"(?:(?:une|des|vos|votre|ta|sa)\s+)?positions?\b"
    # English directional injunctions.
    r"|\bgo\s+(?:long|short)\b"
    r"|\b(?:take|build|trim|exit|unwind|close)\s+"
    r"(?:(?:a|an|the|your)\s+)?positions?\b"
    # Spanish and German transaction verbs (imperative/infinitive).
    r"|\b(?:comprar|compra|compre|compren|compremos|"
    r"vender|venda|vende|vendan|vendamos)\b"
    r"|\b(?:kaufen|kaufe|kauft|verkaufen|verkaufe|verkauft)\b"
)
"""Transaction injunctions the base verb list does not reach.

Explicitly a BEST-EFFORT extension covering the bypasses the third audit
reproduced (French position imperatives, Spanish, German, « go long »). An
unlisted language or verb still passes: see the module docstring.
"""

_CERTAINTY = re.compile(
    r"\b(?:garanti(?:e|s|es)?|garantit|garantissent|guarantee(?:d|s)?|"
    r"infaillible|certitude|certain(?:e|s|es)?|certainly|"
    r"assure(?:e|s|es)?|sans\s+risques?|risque\s+nul|zero\s+risque|"
    r"surement|surely)\b"
)

_PROBABILITY_WORD = re.compile(r"\b(?:probabilit\w*|likelihood|odds)\b")

_CHANCE_OF_OUTCOME = re.compile(
    r"\bchances?\s+(?:de|d['\u2019]|sur|of)\s*(?:[a-z]+\s+)?"
    r"(?:gain|gains|profit|profits|hausse|baisse|succes|reussite|rendement|"
    r"perte|pertes|progression|croissance|surperformance)\b"
    # « trois chances sur quatre », « une chance sur deux ».
    r"|\bchances?\s+sur\s+(?:\d+|une?|deux|trois|quatre|cinq|six|sept|huit|"
    r"neuf|dix|vingt|cent)\b"
    # « chances que le titre monte » — an outcome stated as a clause.
    r"|\bchances?\s+(?:que|qu['\u2019])\b"
)
"""A PREDICTIVE chance. « aucune chance de recalcul » is not one."""

_PERCENTAGE = re.compile(
    r"\d+(?:[.,]\d+)?\s*(?:%|pour\s*cents?|percent|per\s*cent)"
)

_FORWARD_MARKER = (
    r"(?:attendue?s?|prevue?s?|previsions?|projetee?s?|esperee?s?|"
    r"anticipee?s?|garantie?s?|assuree?s?|visee?s?|ciblee?s?|"
    r"objectifs?|cibles?|devrait|devraient|pourrait|pourraient|"
    r"d['\u2019]ici|prochaine?s?|a\s+venir|"
    r"expected|forecasts?|forecasted|projected|targets?|targeted|"
    r"anticipated|guaranteed|upcoming|should|could|will)"
)
"""FORWARD-LOOKING markers: an expectation, a target, a coming event.

They are what turns a figure into a PREDICTION. They are deliberately NOT
the directional nouns (« hausse », « baisse », « gain »): those describe a
MEASURED variation just as often as a predicted one.
"""

_FORWARD_LOOKING = re.compile(
    rf"\b{_FORWARD_MARKER}\b"
    r"|\b(?:probabilit\w*|likelihood|odds|chances?)\b"
)

_OUTCOME_NOUN = (
    r"(?:gains?|profits?|rendements?|plus-values?|plus\s+values?|hausses?|"
    r"baisses?|pertes?|performances?|progressions?|croissances?|"
    r"surperformances?|returns?|upsides?|downsides?|yields?|growth)"
)

_PREDICTED_OUTCOME = re.compile(
    rf"\b{_OUTCOME_NOUN}\b[^.!?]{{0,40}}?\b{_FORWARD_MARKER}\b"
    rf"|\b{_FORWARD_MARKER}\b[^.!?]{{0,40}}?\b{_OUTCOME_NOUN}\b"
)
"""A gain/return announced as EXPECTED, TARGETED or GUARANTEED.

Catches the predictions a percentage rule cannot see because the figure is
spelled out (« cinquante pour cent de gain attendu ») or simply absent
(« plus-value attendue »).
"""

_EXECUTABLE_MARKUP = re.compile(
    r"</?\s*(?:script|iframe|object|embed|applet|svg|img|image|link|meta|"
    r"style|form|input|button|base|template|audio|video|source|marquee|"
    r"frame|frameset|html|body|math|animate|set|foreignobject|portal|"
    r"noscript|dialog|details|slot)\b"
    r"|javascript\s*:|vbscript\s*:|data\s*:[^,]*(?:html|script)"
    # ANY inline event handler, not a hand-listed few.
    r"|\bon[a-z]{3,20}\s*="
    r"|&lt;\s*/?\s*script"
)


def _uncalibrated_percentage(folded: str) -> bool:
    """A percentage is refused ONLY when it is FORWARD-LOOKING.

    Distinguishes a FACTUAL percentage — a measured, accounting or past
    magnitude (« Marge brute de 42 % », « Résultat net en baisse de 7 % ») —
    from a PREDICTIVE probability (a future event, « chances de », « attendu
    », « probabilité de »). Refusing every percentage, as the previous
    deny-by-default rule did, refused the majority of legitimate financial
    headlines and turned the information rail into refusal notices.
    """
    if _PERCENTAGE.search(folded) is None:
        return False
    return _FORWARD_LOOKING.search(folded) is not None


_FORBIDDEN_LANGUAGE_RULES: tuple[tuple[str, Any], ...] = (
    (
        FORBIDDEN_LANGUAGE_TRANSACTIONAL,
        lambda folded: _TRANSACTIONAL_VERB.search(folded) is not None
        or _TRANSACTIONAL_ORDER.search(folded) is not None
        or _TRANSACTIONAL_INJUNCTION.search(folded) is not None,
    ),
    (
        FORBIDDEN_LANGUAGE_CERTAINTY,
        lambda folded: _CERTAINTY.search(folded) is not None,
    ),
    (
        FORBIDDEN_LANGUAGE_PROBABILITY,
        lambda folded: _PROBABILITY_WORD.search(folded) is not None
        or _CHANCE_OF_OUTCOME.search(folded) is not None
        or _PREDICTED_OUTCOME.search(folded) is not None
        or _uncalibrated_percentage(folded),
    ),
    (
        FORBIDDEN_LANGUAGE_MARKUP,
        lambda folded: _EXECUTABLE_MARKUP.search(folded) is not None,
    ),
)


def detect_forbidden_language(text: str) -> Optional[str]:
    """Return the forbidden-language category of ``text``, or ``None``.

    Implements the AI_GATEWAY.md « détection de langage interdit » step on
    FREE TEXT (untrusted source content and produced prose): transactional
    injunction, unsupported certainty, uncalibrated probability and
    executable markup. The caller REFUSES the offending text (fail-closed) —
    it never rewrites it.

    HONEST QUALIFICATION — this is a **filtre de meilleur effort** (a
    best-effort keyword blacklist), **jamais une classe fermée**. It covers
    French and English plus a few Spanish/German imperatives, a homoglyph
    table that cannot enumerate Unicode, and the obfuscations reproduced by
    audit. An unlisted language, verb or trick passes it. It is a
    defence-in-depth layer over content that is ALREADY cantoned: the
    guarantee that holds is that an external excerpt is never a claim (it is
    labeled ``EXTERNAL_UNVERIFIED``, escaped, truncated and carries a visible
    limitation). Never present this function as a proof of safety.

    The scan runs on the NORMALIZED form (:func:`_fold`) of the text and of
    its HTML-entity / percent-decoded variants, plus de-hyphenated and
    de-separated forms — so invisible characters, BIDI overrides, homoglyphs,
    full-width letters, spelled-out percent signs, missing diacritics,
    ``a.c.h.e.t.e.z`` and ``&#97;chetez`` do not hide a forbidden
    formulation.

    It is NEVER applied to a canonical Vertex identifier (gate id, reason
    code, status, calculation hash): such an identifier is a typed field, and
    filtering it lexically would delete a safety statement — for instance the
    ``probability_calibrated_if_used`` gate.
    """
    candidates: list[str] = []
    for variant in _decode_escapes(text):
        folded = _fold(variant)
        for candidate in (
            folded,
            _INTRA_WORD_HYPHEN.sub("", folded),
            _INTRA_WORD_SEPARATOR.sub("", folded),
        ):
            if candidate not in candidates:
                candidates.append(candidate)
    for category, rule in _FORBIDDEN_LANGUAGE_RULES:
        for candidate in candidates:
            if rule(candidate):
                return category
    return None


def _neutralize_external_text(value: str) -> tuple[str, bool]:
    """Return ``(escaped_excerpt, truncated)`` for untrusted source text.

    NFKC normalization, removal of the format characters (invisible
    separators and BIDI overrides — an excerpt can never reverse the text
    around it), control characters turned into whitespace, whitespace
    collapsed, hard truncation and markup escaping. The result is data,
    never markup and never an instruction.
    """
    normalized = unicodedata.normalize("NFKC", value)
    visible: list[str] = []
    for character in normalized:
        category = unicodedata.category(character)
        if category == "Cf":
            continue
        visible.append(" " if category == "Cc" else character)
    collapsed = " ".join("".join(visible).split())
    truncated = len(collapsed) > EXTERNAL_EXCERPT_MAX_LENGTH
    if truncated:
        collapsed = collapsed[:EXTERNAL_EXCERPT_MAX_LENGTH]
    return html.escape(collapsed, quote=True), truncated


# ---------------------------------------------------------------------------
# Composed text: typed identifiers vs free prose
# ---------------------------------------------------------------------------


class _Segment(NamedTuple):
    """One piece of a produced text.

    ``screened`` marks FREE PROSE — template wording and every value whose
    ORIGIN is not proven — which the forbidden-language detector reads. A
    segment with ``screened = False`` carries a value BELONGING to
    :data:`CANONICAL_VOCABULARY`, so a lexical rule can never delete the
    statement carrying it (the ``probability_calibrated_if_used`` gate above
    all).
    """

    value: str
    screened: bool


def _prose(value: str) -> _Segment:
    return _Segment(value, True)


def _ident(value: str) -> _Segment:
    """Return an UNSCREENED segment only for a CLOSED-VOCABULARY value.

    The origin test of the whole boundary, and deliberately a MEMBERSHIP
    test: ``value in CANONICAL_VOCABULARY``. A value that merely LOOKS like a
    canonical identifier — a stored ``unit``, a ``ticker``, a population
    label, a lot id, a news-cluster id — degrades to free prose and is
    screened like any other untrusted text. Fail-closed by construction: the
    exemption is granted by an enumeration, never by a regular expression.
    """
    return _Segment(value, value not in CANONICAL_VOCABULARY)


_Composable = Union[str, Sequence[_Segment]]


def _segments(value: _Composable) -> tuple[_Segment, ...]:
    if isinstance(value, str):
        return (_prose(value),)
    return tuple(value)


@dataclass(frozen=True)
class _Draft:
    """A produced text before the output screen (missing data, limitation)."""

    segments: tuple[_Segment, ...]

    @property
    def text(self) -> str:
        return "".join(segment.value for segment in self.segments)

    @property
    def prose(self) -> str:
        """Only the free-text parts, joined so no word is formed across
        segments."""
        return " ".join(
            segment.value for segment in self.segments if segment.screened
        )


@dataclass(frozen=True)
class _DraftClaim(_Draft):
    refs: tuple[str, ...] = ()

    def claim(self) -> "AiClaim":
        return AiClaim(text=self.text, kind="FACT", evidence_refs=self.refs)


class _ReferenceNamespace(Enum):
    """WHERE a contradiction's reference comes from — its namespace.

    A contradiction reference used to be a BARE STRING, and the completeness
    invariant of :func:`build_ai_answer` compared the published ``BLOCK``
    gate ids to those strings by simple equality. A contradiction built from
    ``coverage.invalid_positions`` carries a STORED ``ticker``: a snapshot
    whose ticker copied a ``gate_id`` made the invariant believe the gate had
    been restituted, and the closed gate silently disappeared from the answer
    while an unrelated contradiction — saying the OPPOSITE — took its place.

    Values from different origins are not comparable. The namespace is
    therefore carried by the reference itself and the invariant only ever
    looks at :data:`GATE` references, which ONLY :func:`_gate_parts` mints.
    """

    GATE = "gate"
    """Reference minted from an advice ``gates[].gate_id`` (a Vertex gate)."""

    POSITION = "position"
    """Reference minted from a STORED position identifier (a ticker)."""


@dataclass(frozen=True)
class _Reference:
    """A contradiction reference AND its namespace — never a bare string.

    ``value`` is ``None`` when the origin is known but its identifier is not
    relayable (an anonymous ``BLOCK`` gate): the contradiction is still
    published, anonymously, and still counted by the invariant.
    """

    namespace: _ReferenceNamespace
    value: Optional[str]


def _gate_ref(gate_id: Optional[str]) -> _Reference:
    """Mint the ONLY kind of reference the completeness invariant accepts."""
    return _Reference(_ReferenceNamespace.GATE, gate_id)


def _position_ref(ticker: Optional[str]) -> _Reference:
    """Mint a reference to a STORED position — never comparable to a gate."""
    return _Reference(_ReferenceNamespace.POSITION, ticker)


@dataclass(frozen=True)
class _DraftContradiction(_Draft):
    code: str = "UNKNOWN"
    reference: Optional[_Reference] = None

    @property
    def restitutes_a_gate(self) -> bool:
        """True only for a contradiction MINTED FROM A GATE.

        The default (``reference is None``) is fail-closed: a contradiction
        source added later that forgets to declare its namespace can never
        satisfy the gate completeness invariant — it can only make the answer
        fail closed, never make a closed gate disappear.
        """
        return (
            self.reference is not None
            and self.reference.namespace is _ReferenceNamespace.GATE
        )

    @property
    def restituted_gate_id(self) -> Optional[str]:
        """The gate id this contradiction restitutes, else ``None``.

        ``None`` also means « an anonymous gate » when
        :attr:`restitutes_a_gate` is true — the two cases are told apart by
        reading both properties, never by the string alone.
        """
        return self.reference.value if self.restitutes_a_gate else None

    def contradiction(self) -> "AiContradiction":
        return AiContradiction(
            code=self.code,
            reference=None if self.reference is None else self.reference.value,
            text=self.text,
        )


def _note(value: _Composable) -> _Draft:
    return _Draft(_segments(value))


_CITATION_LABELS: Mapping[tuple[Optional[_ReferenceNamespace], bool], str] = {
    (_ReferenceNamespace.GATE, True): "identifiant de porte cité",
    (_ReferenceNamespace.GATE, False): "porte non identifiable",
    (_ReferenceNamespace.POSITION, True): "identifiant de position cité",
    (_ReferenceNamespace.POSITION, False): "position non identifiable",
    (None, False): "contradiction sans référence",
}
"""How a REFUSAL NOTE names what it refused: the ORIGIN and the SHAPE only.

Every label is a constant of this module. The note never echoes the refused
reference or reason code — quoting them would re-publish, inside
``missing_data``, the very stored value the screen had just rejected. The
namespace is named because « porte » and « position » are not the same
refusal: the previous wording called every refused contradiction a « porte ».
"""


def _citation(draft: "_DraftContradiction") -> str:
    """Name the origin and shape of a refused contradiction's reference."""
    reference = draft.reference
    if reference is None:
        return _CITATION_LABELS[(None, False)]
    return _CITATION_LABELS[(reference.namespace, reference.value is not None)]


def _screen(draft: _Draft) -> Optional[str]:
    """Run the detector on the FREE PROSE of a produced text only."""
    prose = draft.prose
    if not prose.strip():
        return None
    return detect_forbidden_language(prose)


class AiGroundingError(ValueError):
    """The finished answer breaks a grounding or completeness invariant.

    Either a claim references evidence absent from the snapshot
    (:data:`AI_ERROR_UNGROUNDED_CLAIM`), or a gate the snapshot publishes as
    ``BLOCK`` is missing from the answer
    (:data:`AI_ERROR_INCOMPLETE_ANSWER`). Both are fail-closed: nothing
    partial is served instead.

    The exception carries a TYPED ``code`` and, at most, canonical
    ``references`` (evidence ids and gate ids, already reduced to canonical
    tokens). It NEVER carries a fragment of stored content — quoting the
    offending claim text, as the previous message did, published persisted
    payload into the server log (``.claude/rules/security.md``). ``str(exc)``
    is the code alone, so even a careless ``logging.exception`` leaks
    nothing.
    """

    def __init__(self, code: str, *, references: Sequence[str] = ()) -> None:
        self.code = code
        self.references = tuple(references)
        super().__init__(code)


class AiSubject(ContractModel):
    """What the template explains: one persisted snapshot."""

    kind: Literal["analysis", "portfolio_valuation", "performance"]
    key: NonEmptyStr = Field(pattern=SUBJECT_KEY_PATTERN)


class AiExplainRequest(ContractModel):
    """Wire contract of ``POST /api/v1/ai/explain``."""

    subject: AiSubject
    locale: Literal["fr"]


class AiClaim(ContractModel):
    """One factual sentence, grounded on evidence really present.

    A claim text is built ONLY from Vertex-owned canonical values; untrusted
    external content never enters it.
    """

    text: NonEmptyStr
    kind: Literal["FACT"]
    evidence_refs: tuple[NonEmptyStr, ...] = Field(min_length=1)


class AiExternalExcerpt(ContractModel):
    """One excerpt of UNTRUSTED external content — never a Vertex fact.

    Carried in its own channel, typed ``EXTERNAL_UNVERIFIED``, escaped and
    truncated. It is displayed as quoted source material, never as a claim.
    """

    evidence_ref: NonEmptyStr
    label: Literal["EXTERNAL_UNVERIFIED"]
    excerpt: NonEmptyStr
    truncated: bool


class AiContradiction(ContractModel):
    """One contradiction carried by the snapshot (e.g. a closed gate)."""

    code: NonEmptyStr
    reference: Optional[NonEmptyStr]
    text: NonEmptyStr


class AiEvidenceCatalogEntry(ContractModel):
    """One resolvable evidence id of the source snapshot (server catalog)."""

    evidence_id: NonEmptyStr
    evidence_type: NonEmptyStr
    path: NonEmptyStr


class AiAnswer(ContractModel):
    """The structured deterministic answer (never presented as a model).

    ``state = "ok"`` carries at least one grounded claim. ``state =
    "refused"`` is the STRUCTURED REFUSAL of an empty or unusable corpus:
    no claim, a readable ``refusal_reason`` and explicit missing data — it
    is never an empty explanation presented as complete.
    """

    provider: Literal["DETERMINISTIC_TEMPLATE"]
    template_version: Literal["vertex.ai-deterministic-template/1.0"]
    subject: AiSubject
    locale: Literal["fr"]
    state: Literal["ok", "refused"]
    refusal_reason: Optional[NonEmptyStr]
    as_of: UtcDatetime
    snapshot_version: PositiveInt
    content_hash: NonEmptyStr
    claims: tuple[AiClaim, ...]
    external_excerpts: tuple[AiExternalExcerpt, ...]
    contradictions: tuple[AiContradiction, ...]
    missing_data: tuple[NonEmptyStr, ...]
    limitations: tuple[NonEmptyStr, ...] = Field(min_length=1)
    evidence_catalog: tuple[AiEvidenceCatalogEntry, ...]

    @model_validator(mode="after")
    def _state_is_coherent(self) -> "AiAnswer":
        if self.state == "ok":
            if not self.claims:
                raise ValueError(
                    "state 'ok' requires at least one grounded claim: an empty "
                    "explanation must be a structured refusal"
                )
            if self.refusal_reason is not None:
                raise ValueError("state 'ok' cannot carry a refusal reason")
            return self
        if self.claims or self.external_excerpts:
            raise ValueError("a refused answer carries no claim and no excerpt")
        if self.refusal_reason is None:
            raise ValueError("a refused answer must name its reason")
        if not self.missing_data:
            raise ValueError("a refused answer must report what is missing")
        return self


class AiStatusResponse(ContractModel):
    """State of the AI provider: disabled until human decision B-05."""

    provider: Literal["DISABLED"]
    reason: Literal["B-05_HUMAN_DECISION_PENDING"]
    deterministic_template_available: Literal[True]


def validate_claims(
    claims: Sequence[AiClaim], catalog_ids: frozenset[str]
) -> None:
    """Fail closed when ANY claim cites evidence outside the catalog.

    Every claim must carry at least one reference (enforced by the model)
    and every reference must name evidence REALLY present in the source
    snapshot. This is the code-level guarantee behind « chaque affirmation
    cite des evidence_ids réellement présents »; :func:`build_ai_answer`
    runs it as the LAST-LINE guard on the finished answer.
    """
    unknown = [
        reference
        for claim in claims
        for reference in claim.evidence_refs
        if reference not in catalog_ids
    ]
    if unknown:
        # References only — never ``claim.text``: a claim text is built from
        # stored content and must not travel into a trace.
        raise AiGroundingError(
            AI_ERROR_UNGROUNDED_CLAIM, references=sorted(set(unknown))
        )


# ---------------------------------------------------------------------------
# Catalog and template builders (pure functions of the snapshot content)
# ---------------------------------------------------------------------------


def _snapshot_self_ref(snapshot: CurrentSnapshot) -> tuple[str, AiEvidenceCatalogEntry]:
    evidence_id = f"snapshot:{snapshot.kind}/{snapshot.key}/v{snapshot.version}"
    return evidence_id, AiEvidenceCatalogEntry(
        evidence_id=evidence_id,
        evidence_type="snapshot",
        path=f"{snapshot.kind}/{snapshot.key}",
    )


def _entry(evidence_id: str, evidence_type: str, path: str) -> AiEvidenceCatalogEntry:
    return AiEvidenceCatalogEntry(
        evidence_id=evidence_id, evidence_type=evidence_type, path=path
    )


def _claim(text: _Composable, *refs: str) -> _DraftClaim:
    return _DraftClaim(_segments(text), tuple(refs))


def _contradiction(
    code: str, reference: Optional[_Reference], text: _Composable
) -> _DraftContradiction:
    """Build a contradiction draft.

    ``reference`` is a NAMESPACED :class:`_Reference`, never a bare string:
    the type is what stops a stored value from standing in for a gate id.
    """
    return _DraftContradiction(_segments(text), code, reference)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _text(value: Any) -> Optional[str]:
    return value if isinstance(value, str) and value else None


def _token(value: Any) -> Optional[str]:
    """Return ``value`` when its characters are relayable, else ``None``.

    Applied to every value read from the snapshot before it is restituted:
    an identifier, a code, a status, a currency, a trading day or a decimal
    string. A value carrying markup, spaces, invisible characters, homoglyphs
    or a trailing control character is not relayed — it is reported as
    non-conforming instead. ``fullmatch``, not ``match``: ``$`` accepts a
    final newline, which would let a control character travel inside a
    « canonical token » while ``NonEmptyStr`` refuses the very same value.

    Passing this control does NOT exempt the value from the
    forbidden-language screen; only membership in
    :data:`CANONICAL_VOCABULARY` does (see :func:`_ident`).
    """
    text = _text(value)
    if text is None or _CANONICAL_TOKEN.fullmatch(text) is None:
        return None
    return text


def _count(value: Any) -> Optional[int]:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if value >= 0 else None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [item for item in value if isinstance(item, str) and item]


#: Statuts de porte canoniques (ADR-014). Lus depuis ``vertex_core``, jamais
#: redéfinis ici : l'IA n'est pas une seconde autorité sur ce vocabulaire.
_GATE_STATUS_VALUES: frozenset[str] = frozenset(member.value for member in canonical_enums.GateStatus)


def _gate_blocks(advice: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Les portes publiées ``BLOCK``, ou un REFUS si elles sont illisibles.

    Cette fonction sert à la fois au calcul de l'invariant de complétude et à
    la restitution. Elle IGNORAIT silencieusement ce qu'elle ne savait pas
    lire — ``gates`` qui n'est pas une liste, une entrée qui n'est pas un
    mapping, un ``status`` hors vocabulaire (``"block"`` en minuscules par
    exemple). Les deux vues ignorant la même chose, l'invariant était
    satisfait et la réponse partait en ``state="ok"`` SANS aucune
    contradiction : une porte fermée pouvait disparaître par simple casse.

    La constitution tranche le cas (ADR-014) : une porte qui ne peut pas être
    évaluée vaut ``BLOCK``. Une forme illisible échoue donc FERMÉ, avec un
    code typé, plutôt que d'être écartée.
    """
    gates = advice.get("gates")
    if gates is None:
        return []  # absence déclarée : il n'y a pas de portes, ce n'est pas un défaut
    if not isinstance(gates, list):
        raise AiGroundingError(AI_ERROR_UNREADABLE_GATES)
    blocks: list[Mapping[str, Any]] = []
    for gate in gates:
        if not isinstance(gate, Mapping):
            raise AiGroundingError(AI_ERROR_UNREADABLE_GATES)
        status = gate.get("status")
        if not isinstance(status, str) or status not in _GATE_STATUS_VALUES:
            raise AiGroundingError(AI_ERROR_UNREADABLE_GATES)
        if status == canonical_enums.GateStatus.BLOCK.value:
            blocks.append(gate)
    return blocks


class _BlockedGates(NamedTuple):
    """Every gate published as ``BLOCK``, split by CITABILITY of its id.

    ``anonymous`` counts the BLOCK gates whose ``gate_id`` is not a relayable
    token (a space, an invisible character, markup, an empty string). They
    used to fall OUTSIDE the completeness invariant: an anonymous
    contradiction could be deleted by the output screen and nobody noticed.
    """

    named: frozenset[str]
    anonymous: int


def _blocked_gates(content: Mapping[str, Any]) -> _BlockedGates:
    """Split the ``BLOCK`` gates of the snapshot, WHATEVER their id shape."""
    named: set[str] = set()
    anonymous = 0
    for gate in _gate_blocks(_mapping(content.get("advice"))):
        gate_id = _token(gate.get("gate_id"))
        if gate_id is None:
            anonymous += 1
        else:
            named.add(gate_id)
    return _BlockedGates(frozenset(named), anonymous)


def _gate_parts(
    advice: Mapping[str, Any],
) -> tuple[list[str], list[_DraftContradiction], list[_Draft]]:
    """Restitute EVERY ``BLOCK`` gate of an advice block.

    Shared by the three subject kinds on purpose: the completeness invariant
    is agnostic of the subject kind, so the restitution must be too. A
    portfolio or performance snapshot carrying an advice block used to raise
    :class:`AiGroundingError` for the sole reason that its builder ignored
    the gates — a mute availability regression dressed as fail-closed.

    Gate texts are built from CANONICAL identifiers whenever the snapshot
    provides them, so the output screen cannot delete a BLOCK gate published
    by the engine. A gate whose id or reason is NOT canonical degrades to
    prose, is screened like any other untrusted value, and its disappearance
    is then caught by the invariant (typed failure, never silence).
    """
    blocked_ids: list[str] = []
    contradictions: list[_DraftContradiction] = []
    missing: list[_Draft] = []
    for gate in _gate_blocks(advice):
        gate_id = _token(gate.get("gate_id"))
        reason = _token(gate.get("reason_code")) or "UNKNOWN"
        if gate_id is None:
            contradictions.append(
                _contradiction(
                    reason,
                    _gate_ref(None),
                    (
                        _prose("Gate fermée non identifiable ("),
                        _ident(reason),
                        _prose(")."),
                    ),
                )
            )
            missing.append(
                _note(
                    "gate fermée non identifiable : identifiant absent ou non "
                    "conforme au format canonique"
                )
            )
            continue
        blocked_ids.append(gate_id)
        contradictions.append(
            _contradiction(
                reason,
                _gate_ref(gate_id),
                (
                    _prose("Gate "),
                    _ident(gate_id),
                    _prose(" fermée : "),
                    _ident(reason),
                    _prose("."),
                ),
            )
        )
        if reason == "UNEVALUABLE" or reason.startswith("MISSING"):
            missing.append(
                _note(
                    (
                        _prose("gate "),
                        _ident(gate_id),
                        _prose(" : donnée requise absente ("),
                        _ident(reason),
                        _prose(")"),
                    )
                )
            )
    return blocked_ids, contradictions, missing


_Parts = tuple[
    list[_DraftClaim],
    list[_DraftContradiction],
    list[_Draft],
    list[_Draft],
    list[AiEvidenceCatalogEntry],
    list[AiExternalExcerpt],
]


def _analysis_parts(content: Mapping[str, Any], self_ref: str) -> _Parts:
    claims: list[_DraftClaim] = []
    contradictions: list[_DraftContradiction] = []
    missing: list[_Draft] = []
    limitations: list[_Draft] = []
    catalog: list[AiEvidenceCatalogEntry] = []
    excerpts: list[AiExternalExcerpt] = []

    raw_advice = content.get("advice")
    advice = _mapping(raw_advice)
    advice_id = _token(advice.get("advice_id"))
    status = _token(advice.get("status"))
    population = _token(content.get("population"))
    if population is not None:
        claims.append(
            _claim(
                (_prose("Population des données : "), _ident(population), _prose(".")),
                self_ref,
            )
        )
    elif _text(content.get("population")) is not None:
        missing.append(
            _note(
                "population du snapshot non conforme au format canonique : "
                "elle n'est pas restituée"
            )
        )

    # The advice block is processed whether or not it is citable: an
    # unusable block is REPORTED, never silently dropped (fail-closed).
    if advice_id is not None:
        catalog.append(_entry(advice_id, "advice", "advice.advice_id"))
        for field_name, label in (
            ("status", "Statut du verdict"),
            ("direction", "Direction analytique"),
            ("horizon", "Horizon"),
        ):
            value = _token(advice.get(field_name))
            if value is not None:
                claims.append(
                    _claim(
                        (_prose(f"{label} : "), _ident(value), _prose(".")),
                        advice_id,
                    )
                )
            elif _text(advice.get(field_name)) is not None:
                missing.append(
                    _note(
                        (
                            _prose("champ "),
                            _ident(field_name),
                            _prose(
                                " de l'avis non conforme au format canonique : "
                                "non restitué"
                            ),
                        )
                    )
                )
    elif raw_advice is not None:
        missing.append(
            _note(
                "bloc d'avis inexploitable : identifiant d'avis absent ou non "
                "citable — statut, direction et horizon non restitués"
            )
        )
        limitations.append(_note(LIMITATION_UNUSABLE_ADVICE))

    # Closed gates cite the gate itself: they stay visible even when the
    # advice block carries no citable identifier (see :func:`_gate_parts`
    # and the invariant enforced in :func:`build_ai_answer`).
    blocked_ids, gate_contradictions, gate_missing = _gate_parts(advice)
    contradictions.extend(gate_contradictions)
    missing.extend(gate_missing)
    if status == "INSUFFICIENT_DATA" and blocked_ids and advice_id is not None:
        segments: list[_Segment] = [
            _prose("Le statut "),
            _ident(status),
            _prose(" provient des gates fermées suivantes : "),
        ]
        for index, gate_id in enumerate(blocked_ids):
            if index:
                segments.append(_prose(", "))
            segments.append(_ident(gate_id))
        segments.append(_prose("."))
        claims.append(_claim(tuple(segments), advice_id))
    # The snapshot's own limitations are ALWAYS carried over.
    limitations.extend(_note(item) for item in _string_list(advice.get("limitations")))

    bars = _mapping(content.get("bars"))
    bars_ref = _token(bars.get("source_event_id"))
    if bars.get("status") == "OK" and bars_ref is None:
        # ``EnvelopeContract.event_id`` is a ``NonEmptyStr`` with NO imposed
        # shape: a legitimate id outside this narrow ASCII form must NOT make
        # the whole block vanish without a word (fail-closed REPORTING).
        missing.append(
            _note(
                "bloc de barres annoncé OK sans identifiant d'observation "
                "citable : dernière clôture non restituée"
            )
        )
    elif bars.get("status") == "OK" and bars_ref is not None:
        catalog.append(_entry(bars_ref, "observation", "bars.source_event_id"))
        # SOURCE fields: admitted only as canonical tokens, and screened as
        # free text afterwards — they never travel as trusted identifiers.
        last_close = _token(bars.get("last_close"))
        currency = _token(bars.get("currency"))
        last_day = _token(bars.get("last_trading_day"))
        declared = [
            bars.get(name)
            for name in ("last_close", "currency", "last_trading_day")
        ]
        if last_close is not None and currency is not None and last_day is not None:
            bars_population = _token(bars.get("population"))
            if bars_population is not None:
                refs = (bars_ref,)
            elif population is not None:
                bars_population = population
                refs = (bars_ref, self_ref)
            else:
                refs = (bars_ref,)
            value_segments = (
                _prose(last_close),
                _prose(" "),
                _prose(currency),
                _prose(" (journée "),
                _prose(last_day),
                _prose(")."),
            )
            if bars_population is None:
                # The nature of the value is NOT declared: do not assert one.
                claims.append(
                    _claim(
                        (_prose("Dernière clôture : "), *value_segments), *refs
                    )
                )
                missing.append(
                    _note(
                        "population des barres non déclarée : la nature de la "
                        "dernière clôture n'est pas affirmée"
                    )
                )
            else:
                claims.append(
                    _claim(
                        (
                            _prose("Dernière clôture (population "),
                            _ident(bars_population),
                            _prose(") : "),
                            *value_segments,
                        ),
                        *refs,
                    )
                )
        elif any(value is not None for value in declared):
            missing.append(
                _note(
                    "dernière clôture non restituée : clôture, devise ou "
                    "journée absente ou non conforme au format canonique"
                )
            )
    elif bars.get("status") == "ABSENT":
        missing.append(_note("aucune série de barres validée pour cet instrument"))

    scenarios = _mapping(content.get("scenarios"))
    if scenarios.get("status") == "OK":
        calculation = _mapping(scenarios.get("calculation"))
        scenario_ref = _token(calculation.get("input_hash"))
        if scenario_ref is None:
            missing.append(
                _note(
                    "grille de scénarios annoncée OK sans empreinte de calcul "
                    "citable : elle n'est pas restituée"
                )
            )
        else:
            catalog.append(
                _entry(scenario_ref, "calculation", "scenarios.calculation")
            )
            value_nature = _token(scenarios.get("value_nature"))
            if value_nature is not None:
                claims.append(
                    _claim(
                        (
                            _prose(
                                "Une grille de scénarios est publiée avec la "
                                "nature de valeur "
                            ),
                            _ident(value_nature),
                            _prose("."),
                        ),
                        scenario_ref,
                    )
                )
            else:
                claims.append(
                    _claim("Une grille de scénarios est publiée.", scenario_ref)
                )
                missing.append(
                    _note(
                        "nature de valeur des scénarios non déclarée par le "
                        "snapshot"
                    )
                )
    elif scenarios.get("status") == "ABSENT":
        reason = _token(scenarios.get("reason")) or "UNKNOWN"
        missing.append(
            _note((_prose("scénarios absents ("), _ident(reason), _prose(")")))
        )

    # ---- UNTRUSTED external content ---------------------------------------
    evidence = _mapping(content.get("evidence"))
    clusters = evidence.get("clusters")
    if isinstance(clusters, list):
        for index, cluster in enumerate(clusters):
            cluster_map = _mapping(cluster)
            cluster_id = _text(cluster_map.get("cluster_id"))
            if (
                cluster_id is None
                or _SAFE_EVIDENCE_ID.fullmatch(cluster_id) is None
            ):
                missing.append(
                    _note(
                        f"regroupement d'information n°{index} ignoré : "
                        "identifiant absent ou non conforme"
                    )
                )
                continue
            catalog.append(
                _entry(cluster_id, "news_cluster", "evidence.clusters[]")
            )
            # ``member_count`` is the name the producer really writes
            # (vertex_worker.analysis): reading anything else announces a
            # count that is never displayed.
            member_count = _count(cluster_map.get("member_count"))
            if member_count is None:
                claims.append(
                    _claim(
                        (
                            _prose(
                                "Élément d'information regroupé sous "
                                "l'identifiant "
                            ),
                            _ident(cluster_id),
                            _prose("."),
                        ),
                        cluster_id,
                    )
                )
            else:
                claims.append(
                    _claim(
                        (
                            _prose(
                                "Élément d'information regroupé sous "
                                "l'identifiant "
                            ),
                            _ident(cluster_id),
                            _prose(f" ({member_count} éléments)."),
                        ),
                        cluster_id,
                    )
                )
            title = _text(cluster_map.get("title"))
            if title is None:
                continue
            category = detect_forbidden_language(title)
            if category is not None:
                # Fail-closed: the excerpt is REFUSED, never cleaned.
                missing.append(
                    _note(
                        (
                            _prose("extrait externe du regroupement "),
                            _ident(cluster_id),
                            _prose(
                                " refusé (détection de langage interdit : "
                            ),
                            _ident(category),
                            _prose(")"),
                        )
                    )
                )
                limitations.append(_note(LIMITATION_FORBIDDEN_LANGUAGE))
                continue
            excerpt, truncated = _neutralize_external_text(title)
            if not excerpt:
                continue
            excerpts.append(
                AiExternalExcerpt(
                    evidence_ref=cluster_id,
                    label=EXTERNAL_CONTENT_LABEL,
                    excerpt=excerpt,
                    truncated=truncated,
                )
            )
            limitations.append(_note(LIMITATION_EXTERNAL_CONTENT))
    return claims, contradictions, missing, limitations, catalog, excerpts


def _portfolio_parts(content: Mapping[str, Any], self_ref: str) -> _Parts:
    claims: list[_DraftClaim] = []
    contradictions: list[_DraftContradiction] = []
    missing: list[_Draft] = []
    limitations: list[_Draft] = []
    catalog: list[AiEvidenceCatalogEntry] = []

    # A portfolio snapshot is not supposed to carry an advice block; when a
    # stored one does, its BLOCK gates are restituted like anywhere else
    # (the completeness invariant is kind-agnostic, so this must be too).
    _, gate_contradictions, gate_missing = _gate_parts(
        _mapping(content.get("advice"))
    )
    contradictions.extend(gate_contradictions)
    missing.extend(gate_missing)

    mark_population = _token(content.get("mark_population"))
    if mark_population is not None:
        claims.append(
            _claim(
                (
                    _prose("Population des marques : "),
                    _ident(mark_population),
                    _prose("."),
                ),
                self_ref,
            )
        )
    lot_method = _token(content.get("lot_method"))
    if lot_method is not None:
        claims.append(
            _claim(
                (
                    _prose("Méthode de dérivation des lots : "),
                    _ident(lot_method),
                    _prose("."),
                ),
                self_ref,
            )
        )

    positions = content.get("positions_by_currency")
    if isinstance(positions, list):
        for index, block in enumerate(positions):
            block_map = _mapping(block)
            currency = _token(block_map.get("currency"))
            if currency is None:
                missing.append(
                    _note(
                        f"bloc de positions n°{index} ignoré : devise absente "
                        "ou non conforme au format canonique"
                    )
                )
                continue
            for name, label in (
                ("unrealized", "Latent total"),
                ("realized", "Réalisé total"),
            ):
                sub = _mapping(block_map.get(name))
                calculation = _mapping(sub.get("calculation"))
                ref = _token(calculation.get("input_hash"))
                value = _token(
                    sub.get(
                        "total_unrealized" if name == "unrealized" else "total_pnl"
                    )
                )
                if sub.get("status") == "OK" and ref is None:
                    missing.append(
                        _note(
                            (
                                _ident(name),
                                _prose(" annoncé OK en "),
                                _prose(currency),
                                _prose(
                                    " sans empreinte de calcul citable : "
                                    "non restitué"
                                ),
                            )
                        )
                    )
                elif sub.get("status") == "OK" and ref is not None:
                    catalog.append(
                        _entry(
                            ref,
                            "calculation",
                            f"positions_by_currency[].{name}.calculation",
                        )
                    )
                    if value is not None:
                        claims.append(
                            _claim(
                                (
                                    _prose(f"{label} ("),
                                    _prose(currency),
                                    _prose(") : "),
                                    _prose(value),
                                    _prose("."),
                                ),
                                ref,
                            )
                        )
                elif sub.get("status") == "ABSENT":
                    reason = _token(sub.get("reason")) or "UNKNOWN"
                    missing.append(
                        _note(
                            (
                                _prose(f"{name} absent en "),
                                _prose(currency),
                                _prose(" ("),
                                _ident(reason),
                                _prose(")"),
                            )
                        )
                    )

    excluded = content.get("excluded_lots")
    if isinstance(excluded, list):
        for entry in excluded:
            entry_map = _mapping(entry)
            lot_id = _token(entry_map.get("lot_id")) or "?"
            reason = _token(entry_map.get("reason")) or "UNKNOWN"
            missing.append(
                _note(
                    (
                        _prose("lot "),
                        _ident(lot_id),
                        _prose(" exclu de la valorisation ("),
                        _ident(reason),
                        _prose(")"),
                    )
                )
            )

    coverage = _mapping(content.get("coverage"))
    invalid_positions = coverage.get("invalid_positions")
    if isinstance(invalid_positions, list):
        for entry in invalid_positions:
            entry_map = _mapping(entry)
            ticker = _token(entry_map.get("ticker")) or "?"
            reason = _token(entry_map.get("reason")) or "UNKNOWN"
            contradictions.append(
                _contradiction(
                    reason,
                    _position_ref(ticker),
                    (
                        _prose("Position contradictoire sur "),
                        _ident(ticker),
                        _prose(" : "),
                        _ident(reason),
                        _prose(" (exclue de la valorisation)."),
                    ),
                )
            )
    marks = _mapping(content.get("marks"))
    if marks.get("status") == "ABSENT":
        reason = _token(marks.get("reason")) or "UNKNOWN"
        missing.append(
            _note(
                (
                    _prose("aucune source de marques ("),
                    _ident(reason),
                    _prose(")"),
                )
            )
        )
    if mark_population == "SYNTHETIC":
        limitations.append(
            _note("Marques SYNTHETIC : aucune valeur ne provient d'un marché réel")
        )
    return claims, contradictions, missing, limitations, catalog, []


_PERFORMANCE_UNIT_DECIMAL_RATIO = "ratio décimal"

_PERFORMANCE_METRIC_LABELS: tuple[tuple[str, str, str, str], ...] = (
    ("twr_gross", "TWR brut total", "total_return", _PERFORMANCE_UNIT_DECIMAL_RATIO),
    ("twr_net", "TWR net total", "total_return", _PERFORMANCE_UNIT_DECIMAL_RATIO),
    (
        "xirr_gross",
        "XIRR brut (taux annualisé)",
        "rate",
        _PERFORMANCE_UNIT_DECIMAL_RATIO,
    ),
    (
        "xirr_net",
        "XIRR net (taux annualisé)",
        "rate",
        _PERFORMANCE_UNIT_DECIMAL_RATIO,
    ),
    (
        "drawdown_gross",
        "Drawdown maximal brut",
        "max_drawdown",
        _PERFORMANCE_UNIT_DECIMAL_RATIO,
    ),
    (
        "drawdown_net",
        "Drawdown maximal net",
        "max_drawdown",
        _PERFORMANCE_UNIT_DECIMAL_RATIO,
    ),
)
"""``(snapshot key, French label, value field, declared default unit)``.

The unit is MANDATORY at the boundary (financial-safety.md): it is quoted
from the snapshot when it carries one, otherwise the documented default is
named in the text — a bare ratio is never displayed.
"""


def _performance_parts(content: Mapping[str, Any], self_ref: str) -> _Parts:
    claims: list[_DraftClaim] = []
    contradictions: list[_DraftContradiction] = []
    missing: list[_Draft] = []
    limitations: list[_Draft] = []
    catalog: list[AiEvidenceCatalogEntry] = []

    # Same rule as the portfolio builder: a stored advice block's BLOCK
    # gates are restituted whatever the subject kind.
    _, gate_contradictions, gate_missing = _gate_parts(
        _mapping(content.get("advice"))
    )
    contradictions.extend(gate_contradictions)
    missing.extend(gate_missing)

    population = _token(content.get("population"))
    if population is not None:
        claims.append(
            _claim(
                (_prose("Population des données : "), _ident(population), _prose(".")),
                self_ref,
            )
        )

    series = _mapping(content.get("series"))
    if series.get("status") not in (None, "OK"):
        reason = _token(series.get("reason")) or "UNKNOWN"
        missing.append(
            _note(
                (
                    _prose("série de valorisation non exploitable ("),
                    _ident(reason),
                    _prose(")"),
                )
            )
        )

    metrics = _mapping(content.get("metrics"))
    for name, label, value_field, default_unit in _PERFORMANCE_METRIC_LABELS:
        block = _mapping(metrics.get(name))
        status = block.get("status")
        calculation = _mapping(block.get("calculation"))
        ref = _token(calculation.get("input_hash"))
        if status == "OK" and ref is None:
            missing.append(
                _note(
                    (
                        _prose("métrique "),
                        _ident(name),
                        _prose(
                            " annoncée OK sans empreinte de calcul citable : "
                            "non restituée"
                        ),
                    )
                )
            )
        elif status == "OK" and ref is not None:
            catalog.append(
                _entry(ref, "calculation", f"metrics.{name}.calculation")
            )
            value = _token(block.get(value_field))
            declared_unit = _token(block.get("unit"))
            if value is not None and (
                declared_unit is not None or _text(block.get("unit")) is None
            ):
                unit_segment = (
                    _ident(declared_unit)
                    if declared_unit is not None
                    else _prose(default_unit)
                )
                claims.append(
                    _claim(
                        (
                            _prose(f"{label} : "),
                            _prose(value),
                            _prose(" (unité : "),
                            unit_segment,
                            _prose(")."),
                        ),
                        ref,
                    )
                )
            else:
                missing.append(
                    _note(
                        (
                            _prose("métrique "),
                            _ident(name),
                            _prose(
                                " annoncée OK sans valeur ou unité exploitable "
                                "(champ "
                            ),
                            _ident(value_field),
                            _prose(")"),
                        )
                    )
                )
        elif status in ("INSUFFICIENT_DATA", "INVALID"):
            reason = _token(block.get("reason")) or "UNKNOWN"
            missing.append(
                _note(
                    (
                        _prose("métrique "),
                        _ident(name),
                        _prose(" indisponible ("),
                        _ident(reason),
                        _prose(")"),
                    )
                )
            )

    if population is not None and "SYNTHETIC" in population:
        limitations.append(
            _note("Marques SYNTHETIC : aucune valeur ne provient d'un marché réel")
        )
    return claims, contradictions, missing, limitations, catalog, []


# ---------------------------------------------------------------------------
# Answer assembly, output screening and last-line grounding guard
# ---------------------------------------------------------------------------


def _dedupe(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def _refused_answer(
    subject: AiSubject,
    snapshot: CurrentSnapshot,
    self_entry: AiEvidenceCatalogEntry,
    reason: str,
    missing: Sequence[str],
    contradictions: Sequence[AiContradiction] = (),
    limitations: Sequence[str] = (),
) -> AiAnswer:
    """Build the STRUCTURED REFUSAL: no claim, an explicit readable reason."""
    every_limitation = _dedupe(
        [LIMITATION_PROVIDER_DISABLED, LIMITATION_REFUSED_ANSWER, *limitations]
    )
    return AiAnswer(
        provider=PROVIDER_DETERMINISTIC_TEMPLATE,
        template_version=TEMPLATE_VERSION,
        subject=subject,
        locale="fr",
        state="refused",
        refusal_reason=reason,
        as_of=snapshot.as_of,
        snapshot_version=snapshot.version,
        content_hash=snapshot.content_hash,
        claims=(),
        external_excerpts=(),
        contradictions=tuple(contradictions),
        missing_data=tuple(_dedupe(list(missing))),
        limitations=tuple(every_limitation),
        evidence_catalog=(self_entry,),
    )


def build_ai_answer(
    subject: AiSubject, snapshot: CurrentSnapshot
) -> AiAnswer:
    """Build the deterministic answer for one subject snapshot (pure).

    Identical snapshots produce identical answers. The pipeline is
    fail-closed at every step:

    1. shape control — an empty or malformed content is a STRUCTURED REFUSAL
       (``state = "refused"``), never a 200 with zero claim presented as a
       complete explanation;
    2. template assembly — untrusted external content never enters a
       ``FACT`` claim (it travels escaped and truncated in
       ``external_excerpts``);
    3. forbidden-language detection on the PRODUCED output — an offending
       text is refused and replaced by an explicit ``missing_data`` entry
       plus a visible limitation, never silently cleaned;
    4. last-line grounding guard — :func:`validate_claims` runs on the
       finished answer and raises :class:`AiGroundingError` on any claim
       citing evidence outside the catalog.
    """
    raw_content = snapshot.content
    self_ref, self_entry = _snapshot_self_ref(snapshot)
    content: Mapping[str, Any] = (
        raw_content if isinstance(raw_content, Mapping) else {}
    )

    # (1) Shape control, fail-closed.
    if not content:
        return _refused_answer(
            subject,
            snapshot,
            self_entry,
            REFUSAL_EMPTY_CORPUS,
            [
                "contenu du snapshot vide ou non conforme : aucun fait "
                "citable n'est disponible"
            ],
        )

    # (2) Template assembly.
    if subject.kind == "analysis":
        parts = _analysis_parts(content, self_ref)
    elif subject.kind == "portfolio_valuation":
        parts = _portfolio_parts(content, self_ref)
    else:
        parts = _performance_parts(content, self_ref)
    claims, contradictions, missing, extra_limitations, catalog, excerpts = parts

    limitations: list[_Draft] = [
        *extra_limitations,
        *(_note(item) for item in _string_list(content.get("limitations"))),
    ]

    # (3) Forbidden-language detection on the FREE PROSE of the produced
    # output. A canonical identifier is a typed field, never prose: it is
    # never screened, so no lexical rule can delete a safety statement.
    kept_claims: list[AiClaim] = []
    # The DRAFTS are kept, not only the published models: the completeness
    # invariant below needs the reference NAMESPACE, which the wire contract
    # does not carry.
    kept_contradiction_drafts: list[_DraftContradiction] = []
    kept_missing: list[str] = []
    kept_limitations: list[str] = []
    kept_excerpts: list[AiExternalExcerpt] = []
    reports: list[str] = []
    # A REFUSAL NOTE NEVER ECHOES WHAT IT REFUSED. Quoting the offending
    # reference or reason code re-published, inside ``missing_data``, the very
    # value the screen had just rejected (« vendez-tout », « GARANTI-100 »):
    # the report names the position, the category and the shape of the
    # citation only. ``category`` is a constant of this module, never a
    # snapshot value.
    for index, draft_claim in enumerate(claims):
        category = _screen(draft_claim)
        if category is None:
            kept_claims.append(draft_claim.claim())
        else:
            reports.append(
                f"affirmation n°{index} refusée par la détection de langage "
                f"interdit ({category}) — {len(draft_claim.refs)} source(s) "
                "citée(s), aucune valeur refusée n'est relayée"
            )
    for index, draft_contradiction in enumerate(contradictions):
        category = _screen(draft_contradiction)
        if category is None:
            kept_contradiction_drafts.append(draft_contradiction)
        else:
            reports.append(
                f"contradiction n°{index} ({_citation(draft_contradiction)}) "
                f"refusée par la détection de langage interdit ({category})"
            )
    for index, draft in enumerate(missing):
        category = _screen(draft)
        if category is None:
            kept_missing.append(draft.text)
        else:
            reports.append(
                f"donnée manquante n°{index} refusée par la détection de "
                f"langage interdit ({category})"
            )
    for index, draft in enumerate(limitations):
        category = _screen(draft)
        if category is None:
            kept_limitations.append(draft.text)
        else:
            reports.append(
                f"limite n°{index} refusée par la détection de langage "
                f"interdit ({category})"
            )
    for index, excerpt in enumerate(excerpts):
        category = detect_forbidden_language(excerpt.excerpt)
        if category is None:
            kept_excerpts.append(excerpt)
        else:
            reports.append(
                f"extrait externe n°{index} refusé par la détection de "
                f"langage interdit ({category})"
            )
    if reports:
        kept_missing.extend(reports)
        kept_limitations.append(LIMITATION_FORBIDDEN_LANGUAGE)

    # (3 bis) Completeness invariant: EVERY gate the snapshot publishes as
    # BLOCK is restituted — whatever the shape of its identifier and whatever
    # the subject kind. Deleting one would hide the very reason of the
    # verdict; an output filter must never be able to do that. A gate whose
    # id is not a relayable token is restituted as an ANONYMOUS
    # contradiction, and those are COUNTED here: they used to sit outside
    # the invariant, so a refused anonymous contradiction vanished silently.
    published = _blocked_gates(content)
    # ONLY the gate-namespaced references count. Comparing bare strings let a
    # STORED value (a ``coverage.invalid_positions[].ticker``) that merely
    # equalled a ``gate_id`` satisfy the invariant, so the closed gate
    # vanished from the answer while an unrelated contradiction — the OPPOSITE
    # statement — stood in its place. A reference now carries its namespace,
    # and only :func:`_gate_parts` mints a GATE one.
    restituted = {
        draft.restituted_gate_id
        for draft in kept_contradiction_drafts
        if draft.restituted_gate_id is not None
    }
    unrestituted = sorted(published.named - restituted)
    anonymous_kept = sum(
        1
        for draft in kept_contradiction_drafts
        if draft.restitutes_a_gate and draft.restituted_gate_id is None
    )
    if unrestituted or anonymous_kept < published.anonymous:
        raise AiGroundingError(
            AI_ERROR_INCOMPLETE_ANSWER, references=unrestituted
        )

    kept_contradictions = [
        draft.contradiction() for draft in kept_contradiction_drafts
    ]

    catalog_entries: dict[str, AiEvidenceCatalogEntry] = {
        self_entry.evidence_id: self_entry
    }
    for entry in catalog:
        catalog_entries.setdefault(entry.evidence_id, entry)

    every_limitation = _dedupe([LIMITATION_PROVIDER_DISABLED, *kept_limitations])

    # (1 bis) Nothing grounded left to say: STRUCTURED REFUSAL, never an
    # empty explanation presented as complete.
    if not kept_claims:
        return _refused_answer(
            subject,
            snapshot,
            self_entry,
            REFUSAL_NO_GROUNDED_CLAIM,
            [
                *kept_missing,
                "aucune affirmation sourcée ne peut être produite depuis ce "
                "snapshot",
            ],
            contradictions=kept_contradictions,
            limitations=kept_limitations,
        )

    answer = AiAnswer(
        provider=PROVIDER_DETERMINISTIC_TEMPLATE,
        template_version=TEMPLATE_VERSION,
        subject=subject,
        locale="fr",
        state="ok",
        refusal_reason=None,
        as_of=snapshot.as_of,
        snapshot_version=snapshot.version,
        content_hash=snapshot.content_hash,
        claims=tuple(kept_claims),
        external_excerpts=tuple(kept_excerpts),
        contradictions=tuple(kept_contradictions),
        missing_data=tuple(_dedupe(kept_missing)),
        limitations=tuple(every_limitation),
        evidence_catalog=tuple(
            catalog_entries[key] for key in sorted(catalog_entries)
        ),
    )

    # (4) Last-line grounding guard on the FINISHED answer.
    validate_claims(
        answer.claims,
        frozenset(entry.evidence_id for entry in answer.evidence_catalog),
    )
    return answer
