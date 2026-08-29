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
- the produced output goes through the forbidden-language detection step of
  AI_GATEWAY.md (« détection de langage interdit ») — transactional
  vocabulary, unsupported certainty and uncalibrated probability. A text
  that triggers it is REFUSED, never silently cleaned: it is replaced by an
  explicit ``missing_data`` entry plus a visible limitation;
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
from typing import Any, Literal, Mapping, Optional, Sequence

from pydantic import Field, model_validator

from vertex_core.contracts.types import (
    ContractModel,
    NonEmptyStr,
    PositiveInt,
    UtcDatetime,
)
from vertex_persistence.repository.snapshots import CurrentSnapshot

__all__ = [
    "AI_STATUS_PROVIDER",
    "AI_STATUS_REASON",
    "ERROR_NO_SNAPSHOT_FOR_SUBJECT",
    "EXTERNAL_CONTENT_LABEL",
    "EXTERNAL_EXCERPT_MAX_LENGTH",
    "FORBIDDEN_LANGUAGE_CERTAINTY",
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

_SAFE_EVIDENCE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._@/+-]{0,127}$")
"""Shape an identifier coming from external content must have to be cited."""

_CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


# ---------------------------------------------------------------------------
# Forbidden-language detection (AI_GATEWAY.md, output validation step 6)
# ---------------------------------------------------------------------------

FORBIDDEN_LANGUAGE_TRANSACTIONAL = "TRANSACTIONAL_LANGUAGE"
FORBIDDEN_LANGUAGE_CERTAINTY = "UNSUPPORTED_CERTAINTY"
FORBIDDEN_LANGUAGE_PROBABILITY = "UNCALIBRATED_PROBABILITY"

_FORBIDDEN_LANGUAGE_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        FORBIDDEN_LANGUAGE_TRANSACTIONAL,
        re.compile(
            r"\b(?:"
            r"achet\w*|achat|achats|acquérir|acquerir|"
            r"vendre|vendez|vends|vente|ventes|revendre|"
            r"liquider|souscrire|shorter|"
            r"buy|buys|buying|sell|sells|selling|"
            r"ordre|ordres|order|orders|"
            r"exécut\w*|execut\w*|trade|trades|trading"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        FORBIDDEN_LANGUAGE_CERTAINTY,
        re.compile(
            r"\b(?:"
            r"garanti\w*|guarantee\w*|"
            r"certitude|certain|certaine|certains|certaines|certainly|"
            r"assuré|assurée|assurés|assurées|infaillible|"
            r"sans\s+risque|surely"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        FORBIDDEN_LANGUAGE_PROBABILITY,
        re.compile(
            r"(?:\d+(?:[.,]\d+)?\s*%)"
            r"|\b(?:probabilit\w*|probability|probabilities|"
            r"chance|chances|odds|likelihood)\b",
            re.IGNORECASE,
        ),
    ),
)


def detect_forbidden_language(text: str) -> Optional[str]:
    """Return the forbidden-language category of ``text``, or ``None``.

    Implements the AI_GATEWAY.md « détection de langage interdit » step on
    the PRODUCED output (not only on fixtures): transactional vocabulary,
    unsupported certainty and uncalibrated probability. The caller REFUSES
    the offending text (fail-closed) — it never rewrites it.
    """
    for category, pattern in _FORBIDDEN_LANGUAGE_RULES:
        if pattern.search(text):
            return category
    return None


def _neutralize_external_text(value: str) -> tuple[str, bool]:
    """Return ``(escaped_excerpt, truncated)`` for untrusted source text.

    Control characters are removed, whitespace collapsed, the text hard
    truncated, and every markup character escaped. The result is data, never
    markup and never an instruction.
    """
    collapsed = " ".join(_CONTROL_CHARACTERS.sub(" ", value).split())
    truncated = len(collapsed) > EXTERNAL_EXCERPT_MAX_LENGTH
    if truncated:
        collapsed = collapsed[:EXTERNAL_EXCERPT_MAX_LENGTH]
    return html.escape(collapsed, quote=True), truncated


class AiGroundingError(ValueError):
    """A claim references evidence that does not exist in the snapshot."""


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
    for claim in claims:
        for reference in claim.evidence_refs:
            if reference not in catalog_ids:
                raise AiGroundingError(
                    f"claim cites unknown evidence {reference!r}: "
                    f"{claim.text[:80]!r}"
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


def _claim(text: str, *refs: str) -> AiClaim:
    return AiClaim(text=text, kind="FACT", evidence_refs=tuple(refs))


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _text(value: Any) -> Optional[str]:
    return value if isinstance(value, str) and value else None


def _count(value: Any) -> Optional[int]:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if value >= 0 else None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _gate_blocks(advice: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    gates = advice.get("gates")
    if not isinstance(gates, list):
        return []
    return [
        gate
        for gate in gates
        if isinstance(gate, Mapping) and gate.get("status") == "BLOCK"
    ]


def _analysis_parts(
    content: Mapping[str, Any], self_ref: str
) -> tuple[
    list[AiClaim],
    list[AiContradiction],
    list[str],
    list[str],
    list[AiEvidenceCatalogEntry],
    list[AiExternalExcerpt],
]:
    claims: list[AiClaim] = []
    contradictions: list[AiContradiction] = []
    missing: list[str] = []
    limitations: list[str] = []
    catalog: list[AiEvidenceCatalogEntry] = []
    excerpts: list[AiExternalExcerpt] = []

    raw_advice = content.get("advice")
    advice = _mapping(raw_advice)
    advice_id = _text(advice.get("advice_id"))
    status = _text(advice.get("status"))
    population = _text(content.get("population"))
    if population is not None:
        claims.append(
            _claim(f"Population des données : {population}.", self_ref)
        )

    # The advice block is processed whether or not it is citable: an
    # unusable block is REPORTED, never silently dropped (fail-closed).
    if advice_id is not None:
        catalog.append(_entry(advice_id, "advice", "advice.advice_id"))
        direction = _text(advice.get("direction"))
        horizon = _text(advice.get("horizon"))
        if status is not None:
            claims.append(_claim(f"Statut du verdict : {status}.", advice_id))
        if direction is not None:
            claims.append(
                _claim(f"Direction analytique : {direction}.", advice_id)
            )
        if horizon is not None:
            claims.append(_claim(f"Horizon : {horizon}.", advice_id))
    elif raw_advice is not None:
        missing.append(
            "bloc d'avis inexploitable : identifiant d'avis absent ou non "
            "citable — statut, direction et horizon non restitués"
        )
        limitations.append(LIMITATION_UNUSABLE_ADVICE)

    # Closed gates cite the gate itself: they stay visible even when the
    # advice block carries no citable identifier.
    blocked = _gate_blocks(advice)
    for gate in blocked:
        gate_id = _text(gate.get("gate_id")) or "unknown_gate"
        reason = _text(gate.get("reason_code")) or "UNKNOWN"
        contradictions.append(
            AiContradiction(
                code=reason,
                reference=gate_id,
                text=f"Gate {gate_id} fermée : {reason}.",
            )
        )
        if reason == "UNEVALUABLE" or reason.startswith("MISSING"):
            missing.append(
                f"gate {gate_id} : donnée requise absente ({reason})"
            )
    if status == "INSUFFICIENT_DATA" and blocked and advice_id is not None:
        gate_ids = ", ".join(
            _text(gate.get("gate_id")) or "unknown_gate" for gate in blocked
        )
        claims.append(
            _claim(
                "Le statut INSUFFICIENT_DATA provient des gates fermées "
                f"suivantes : {gate_ids}.",
                advice_id,
            )
        )
    # The snapshot's own limitations are ALWAYS carried over.
    limitations.extend(_string_list(advice.get("limitations")))

    bars = _mapping(content.get("bars"))
    bars_ref = _text(bars.get("source_event_id"))
    if bars.get("status") == "OK" and bars_ref is not None:
        catalog.append(_entry(bars_ref, "observation", "bars.source_event_id"))
        last_close = _text(bars.get("last_close"))
        currency = _text(bars.get("currency"))
        last_day = _text(bars.get("last_trading_day"))
        if last_close is not None and currency is not None and last_day is not None:
            bars_population = _text(bars.get("population"))
            if bars_population is not None:
                refs = (bars_ref,)
            elif population is not None:
                bars_population = population
                refs = (bars_ref, self_ref)
            else:
                refs = (bars_ref,)
            if bars_population is None:
                # The nature of the value is NOT declared: do not assert one.
                claims.append(
                    _claim(
                        f"Dernière clôture : {last_close} {currency} "
                        f"(journée {last_day}).",
                        *refs,
                    )
                )
                missing.append(
                    "population des barres non déclarée : la nature de la "
                    "dernière clôture n'est pas affirmée"
                )
            else:
                claims.append(
                    _claim(
                        f"Dernière clôture (population {bars_population}) : "
                        f"{last_close} {currency} (journée {last_day}).",
                        *refs,
                    )
                )
    elif bars.get("status") == "ABSENT":
        missing.append("aucune série de barres validée pour cet instrument")

    scenarios = _mapping(content.get("scenarios"))
    if scenarios.get("status") == "OK":
        calculation = _mapping(scenarios.get("calculation"))
        scenario_ref = _text(calculation.get("input_hash"))
        if scenario_ref is not None:
            catalog.append(
                _entry(scenario_ref, "calculation", "scenarios.calculation")
            )
            value_nature = _text(scenarios.get("value_nature"))
            if value_nature is not None:
                claims.append(
                    _claim(
                        "Une grille de scénarios est publiée avec la nature de "
                        f"valeur {value_nature}.",
                        scenario_ref,
                    )
                )
            else:
                claims.append(
                    _claim(
                        "Une grille de scénarios est publiée.", scenario_ref
                    )
                )
                missing.append(
                    "nature de valeur des scénarios non déclarée par le "
                    "snapshot"
                )
    elif scenarios.get("status") == "ABSENT":
        reason = _text(scenarios.get("reason")) or "unknown"
        missing.append(f"scénarios absents ({reason})")

    # ---- UNTRUSTED external content ---------------------------------------
    evidence = _mapping(content.get("evidence"))
    clusters = evidence.get("clusters")
    if isinstance(clusters, list):
        for index, cluster in enumerate(clusters):
            cluster_map = _mapping(cluster)
            cluster_id = _text(cluster_map.get("cluster_id"))
            if cluster_id is None or _SAFE_EVIDENCE_ID.match(cluster_id) is None:
                missing.append(
                    f"regroupement d'information n°{index} ignoré : "
                    "identifiant absent ou non conforme"
                )
                continue
            catalog.append(
                _entry(cluster_id, "news_cluster", "evidence.clusters[]")
            )
            item_count = _count(cluster_map.get("item_count"))
            if item_count is None:
                claims.append(
                    _claim(
                        "Élément d'information regroupé sous l'identifiant "
                        f"{cluster_id}.",
                        cluster_id,
                    )
                )
            else:
                claims.append(
                    _claim(
                        "Élément d'information regroupé sous l'identifiant "
                        f"{cluster_id} ({item_count} éléments).",
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
                    f"extrait externe du regroupement {cluster_id} refusé "
                    f"(détection de langage interdit : {category})"
                )
                limitations.append(LIMITATION_FORBIDDEN_LANGUAGE)
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
            limitations.append(LIMITATION_EXTERNAL_CONTENT)
    return claims, contradictions, missing, limitations, catalog, excerpts


def _portfolio_parts(
    content: Mapping[str, Any], self_ref: str
) -> tuple[
    list[AiClaim],
    list[AiContradiction],
    list[str],
    list[str],
    list[AiEvidenceCatalogEntry],
    list[AiExternalExcerpt],
]:
    claims: list[AiClaim] = []
    contradictions: list[AiContradiction] = []
    missing: list[str] = []
    limitations: list[str] = []
    catalog: list[AiEvidenceCatalogEntry] = []

    mark_population = _text(content.get("mark_population"))
    if mark_population is not None:
        claims.append(
            _claim(f"Population des marques : {mark_population}.", self_ref)
        )
    lot_method = _text(content.get("lot_method"))
    if lot_method is not None:
        claims.append(
            _claim(f"Méthode de dérivation des lots : {lot_method}.", self_ref)
        )

    positions = content.get("positions_by_currency")
    if isinstance(positions, list):
        for block in positions:
            block_map = _mapping(block)
            currency = _text(block_map.get("currency")) or "?"
            for name, label in (
                ("unrealized", "Latent total"),
                ("realized", "Réalisé total"),
            ):
                sub = _mapping(block_map.get(name))
                calculation = _mapping(sub.get("calculation"))
                ref = _text(calculation.get("input_hash"))
                value = _text(
                    sub.get(
                        "total_unrealized" if name == "unrealized" else "total_pnl"
                    )
                )
                if sub.get("status") == "OK" and ref is not None:
                    catalog.append(
                        _entry(
                            ref,
                            "calculation",
                            f"positions_by_currency[].{name}.calculation",
                        )
                    )
                    if value is not None:
                        claims.append(
                            _claim(f"{label} ({currency}) : {value}.", ref)
                        )
                elif sub.get("status") == "ABSENT":
                    reason = _text(sub.get("reason")) or "unknown"
                    missing.append(f"{name} absent en {currency} ({reason})")

    excluded = content.get("excluded_lots")
    if isinstance(excluded, list):
        for entry in excluded:
            entry_map = _mapping(entry)
            lot_id = _text(entry_map.get("lot_id")) or "?"
            reason = _text(entry_map.get("reason")) or "unknown"
            missing.append(f"lot {lot_id} exclu de la valorisation ({reason})")

    coverage = _mapping(content.get("coverage"))
    invalid_positions = coverage.get("invalid_positions")
    if isinstance(invalid_positions, list):
        for entry in invalid_positions:
            entry_map = _mapping(entry)
            ticker = _text(entry_map.get("ticker")) or "?"
            reason = _text(entry_map.get("reason")) or "unknown"
            contradictions.append(
                AiContradiction(
                    code=reason,
                    reference=ticker,
                    text=(
                        f"Position contradictoire sur {ticker} : {reason} "
                        "(exclue de la valorisation)."
                    ),
                )
            )
    marks = _mapping(content.get("marks"))
    if marks.get("status") == "ABSENT":
        reason = _text(marks.get("reason")) or "unknown"
        missing.append(f"aucune source de marques ({reason})")
    if mark_population == "SYNTHETIC":
        limitations.append(
            "Marques SYNTHETIC : aucune valeur ne provient d'un marché réel"
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


def _performance_parts(
    content: Mapping[str, Any], self_ref: str
) -> tuple[
    list[AiClaim],
    list[AiContradiction],
    list[str],
    list[str],
    list[AiEvidenceCatalogEntry],
    list[AiExternalExcerpt],
]:
    claims: list[AiClaim] = []
    contradictions: list[AiContradiction] = []
    missing: list[str] = []
    limitations: list[str] = []
    catalog: list[AiEvidenceCatalogEntry] = []

    population = _text(content.get("population"))
    if population is not None:
        claims.append(
            _claim(f"Population des données : {population}.", self_ref)
        )

    series = _mapping(content.get("series"))
    if series.get("status") not in (None, "OK"):
        reason = _text(series.get("reason")) or "unknown"
        missing.append(f"série de valorisation non exploitable ({reason})")

    metrics = _mapping(content.get("metrics"))
    for name, label, value_field, default_unit in _PERFORMANCE_METRIC_LABELS:
        block = _mapping(metrics.get(name))
        status = block.get("status")
        calculation = _mapping(block.get("calculation"))
        ref = _text(calculation.get("input_hash"))
        if status == "OK" and ref is not None:
            catalog.append(
                _entry(ref, "calculation", f"metrics.{name}.calculation")
            )
            value = _text(block.get(value_field))
            if value is not None:
                unit = _text(block.get("unit")) or default_unit
                claims.append(
                    _claim(f"{label} : {value} (unité : {unit}).", ref)
                )
            else:
                missing.append(
                    f"métrique {name} annoncée OK sans valeur exploitable "
                    f"(champ {value_field})"
                )
        elif status in ("INSUFFICIENT_DATA", "INVALID"):
            reason = _text(block.get("reason")) or "unknown"
            missing.append(f"métrique {name} indisponible ({reason})")

    if population is not None and "SYNTHETIC" in population:
        limitations.append(
            "Marques SYNTHETIC : aucune valeur ne provient d'un marché réel"
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

    limitations: list[str] = [
        *extra_limitations,
        *_string_list(content.get("limitations")),
    ]

    # (3) Forbidden-language detection on the produced output.
    kept_claims: list[AiClaim] = []
    kept_contradictions: list[AiContradiction] = []
    kept_missing: list[str] = []
    kept_limitations: list[str] = []
    kept_excerpts: list[AiExternalExcerpt] = []
    reports: list[str] = []
    for index, claim in enumerate(claims):
        category = detect_forbidden_language(claim.text)
        if category is None:
            kept_claims.append(claim)
        else:
            reports.append(
                f"affirmation n°{index} refusée par la détection de langage "
                f"interdit ({category})"
            )
    for index, contradiction in enumerate(contradictions):
        category = detect_forbidden_language(contradiction.text)
        if category is None:
            kept_contradictions.append(contradiction)
        else:
            reports.append(
                f"contradiction n°{index} refusée par la détection de langage "
                f"interdit ({category})"
            )
    for index, item in enumerate(missing):
        category = detect_forbidden_language(item)
        if category is None:
            kept_missing.append(item)
        else:
            reports.append(
                f"donnée manquante n°{index} refusée par la détection de "
                f"langage interdit ({category})"
            )
    for index, item in enumerate(limitations):
        category = detect_forbidden_language(item)
        if category is None:
            kept_limitations.append(item)
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
