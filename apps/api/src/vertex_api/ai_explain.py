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
  snapshot's own reference); :func:`validate_claims` fails closed on any
  reference outside the catalog;
- no claim text contains an instruction to transact, a promise, a
  probability, or any figure that is not a VERBATIM string of the snapshot
  content (counts and derived numbers stay out of claim texts);
- contradictions (closed gates, contradictory positions) and missing data
  are listed separately from facts;
- ``limitations`` is NEVER empty: it always carries the B-05 notice
  :data:`LIMITATION_PROVIDER_DISABLED` plus the snapshot's own limitations.

The subject snapshot is one of ``analysis/{key}``,
``portfolio_valuation/{key}`` or ``performance/{key}``; an absent snapshot
is a clean 404 at the route level (nothing to explain, nothing invented).
"""

from __future__ import annotations

from typing import Any, Literal, Mapping, Optional, Sequence

from pydantic import Field

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
    "LIMITATION_PROVIDER_DISABLED",
    "PROVIDER_DETERMINISTIC_TEMPLATE",
    "SUBJECT_KEY_PATTERN",
    "SUBJECT_SNAPSHOT_KINDS",
    "TEMPLATE_VERSION",
    "AiAnswer",
    "AiClaim",
    "AiContradiction",
    "AiEvidenceCatalogEntry",
    "AiExplainRequest",
    "AiGroundingError",
    "AiStatusResponse",
    "AiSubject",
    "build_ai_answer",
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

ERROR_NO_SNAPSHOT_FOR_SUBJECT = "NO_SNAPSHOT_FOR_SUBJECT"

SUBJECT_KEY_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"
"""Accepted shape of a subject snapshot key (same shape as the snapshot
routes' path keys); anything else is rejected before any lookup."""

SUBJECT_SNAPSHOT_KINDS: Mapping[str, str] = {
    "analysis": "analysis",
    "portfolio_valuation": "portfolio_valuation",
    "performance": "performance",
}
"""Subject kind -> persisted snapshot kind (identity today, explicit map)."""


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
    """One factual sentence, grounded on evidence really present."""

    text: NonEmptyStr
    kind: Literal["FACT"]
    evidence_refs: tuple[NonEmptyStr, ...] = Field(min_length=1)


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
    """The structured deterministic answer (never presented as a model)."""

    provider: Literal["DETERMINISTIC_TEMPLATE"]
    template_version: Literal["vertex.ai-deterministic-template/1.0"]
    subject: AiSubject
    locale: Literal["fr"]
    as_of: UtcDatetime
    snapshot_version: PositiveInt
    claims: tuple[AiClaim, ...]
    contradictions: tuple[AiContradiction, ...]
    missing_data: tuple[NonEmptyStr, ...]
    limitations: tuple[NonEmptyStr, ...] = Field(min_length=1)
    evidence_catalog: tuple[AiEvidenceCatalogEntry, ...]


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
    cite des evidence_ids réellement présents ».
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
]:
    claims: list[AiClaim] = []
    contradictions: list[AiContradiction] = []
    missing: list[str] = []
    limitations: list[str] = []
    catalog: list[AiEvidenceCatalogEntry] = []

    advice = _mapping(content.get("advice"))
    advice_id = _text(advice.get("advice_id"))
    population = _text(content.get("population"))
    if population is not None:
        claims.append(
            _claim(f"Population des données : {population}.", self_ref)
        )

    if advice_id is not None:
        catalog.append(_entry(advice_id, "advice", "advice.advice_id"))
        status = _text(advice.get("status"))
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
        if status == "INSUFFICIENT_DATA" and blocked:
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
        for limitation in advice.get("limitations", ()):
            text = _text(limitation)
            if text is not None:
                limitations.append(text)

    bars = _mapping(content.get("bars"))
    bars_ref = _text(bars.get("source_event_id"))
    if bars.get("status") == "OK" and bars_ref is not None:
        catalog.append(_entry(bars_ref, "observation", "bars.source_event_id"))
        last_close = _text(bars.get("last_close"))
        currency = _text(bars.get("currency"))
        last_day = _text(bars.get("last_trading_day"))
        if last_close is not None and currency is not None and last_day is not None:
            claims.append(
                _claim(
                    f"Dernière clôture synthétique : {last_close} {currency} "
                    f"(journée {last_day}).",
                    bars_ref,
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
            claims.append(
                _claim(
                    "Une grille de scénarios est publiée avec la nature de "
                    "valeur THEORETICAL.",
                    scenario_ref,
                )
            )
    elif scenarios.get("status") == "ABSENT":
        reason = _text(scenarios.get("reason")) or "unknown"
        missing.append(f"scénarios absents ({reason})")

    evidence = _mapping(content.get("evidence"))
    clusters = evidence.get("clusters")
    if isinstance(clusters, list):
        for cluster in clusters:
            cluster_map = _mapping(cluster)
            cluster_id = _text(cluster_map.get("cluster_id"))
            title = _text(cluster_map.get("title"))
            if cluster_id is None:
                continue
            catalog.append(
                _entry(cluster_id, "news_cluster", "evidence.clusters[]")
            )
            if title is not None:
                claims.append(
                    _claim(
                        f"Élément d'information regroupé : {title}", cluster_id
                    )
                )
    return claims, contradictions, missing, limitations, catalog


def _portfolio_parts(
    content: Mapping[str, Any], self_ref: str
) -> tuple[
    list[AiClaim],
    list[AiContradiction],
    list[str],
    list[str],
    list[AiEvidenceCatalogEntry],
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
    return claims, contradictions, missing, limitations, catalog


_PERFORMANCE_METRIC_LABELS: tuple[tuple[str, str, str], ...] = (
    ("twr_gross", "TWR brut total", "total_return"),
    ("twr_net", "TWR net total", "total_return"),
    ("xirr_gross", "XIRR brut (taux annualisé)", "rate"),
    ("xirr_net", "XIRR net (taux annualisé)", "rate"),
    ("drawdown_gross", "Drawdown maximal brut", "max_drawdown"),
    ("drawdown_net", "Drawdown maximal net", "max_drawdown"),
)


def _performance_parts(
    content: Mapping[str, Any], self_ref: str
) -> tuple[
    list[AiClaim],
    list[AiContradiction],
    list[str],
    list[str],
    list[AiEvidenceCatalogEntry],
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
    for name, label, value_field in _PERFORMANCE_METRIC_LABELS:
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
                claims.append(_claim(f"{label} : {value}.", ref))
        elif status in ("INSUFFICIENT_DATA", "INVALID"):
            reason = _text(block.get("reason")) or "unknown"
            missing.append(f"métrique {name} indisponible ({reason})")

    if population is not None and "SYNTHETIC" in population:
        limitations.append(
            "Marques SYNTHETIC : aucune valeur ne provient d'un marché réel"
        )
    return claims, contradictions, missing, limitations, catalog


def build_ai_answer(
    subject: AiSubject, snapshot: CurrentSnapshot
) -> AiAnswer:
    """Build the deterministic answer for one subject snapshot (pure).

    Identical snapshots produce identical answers. Every claim is validated
    against the evidence catalog before the answer exists —
    :class:`AiGroundingError` on any violation, fail-closed.
    """
    content: Mapping[str, Any] = (
        snapshot.content if isinstance(snapshot.content, Mapping) else {}
    )
    self_ref, self_entry = _snapshot_self_ref(snapshot)

    if subject.kind == "analysis":
        parts = _analysis_parts(content, self_ref)
    elif subject.kind == "portfolio_valuation":
        parts = _portfolio_parts(content, self_ref)
    else:
        parts = _performance_parts(content, self_ref)
    claims, contradictions, missing, extra_limitations, catalog = parts

    catalog_entries: dict[str, AiEvidenceCatalogEntry] = {
        self_entry.evidence_id: self_entry
    }
    for entry in catalog:
        catalog_entries.setdefault(entry.evidence_id, entry)

    limitations: list[str] = [LIMITATION_PROVIDER_DISABLED]
    for limitation in extra_limitations:
        if limitation not in limitations:
            limitations.append(limitation)

    validate_claims(claims, frozenset(catalog_entries))

    return AiAnswer(
        provider=PROVIDER_DETERMINISTIC_TEMPLATE,
        template_version=TEMPLATE_VERSION,
        subject=subject,
        locale="fr",
        as_of=snapshot.as_of,
        snapshot_version=snapshot.version,
        claims=tuple(claims),
        contradictions=tuple(contradictions),
        missing_data=tuple(missing),
        limitations=tuple(limitations),
        evidence_catalog=tuple(
            catalog_entries[key] for key in sorted(catalog_entries)
        ),
    )
