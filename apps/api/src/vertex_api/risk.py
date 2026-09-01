"""API Risques : relais de l'instantané ``risk_matrix/global``.

L'API ne calcule AUCUN chiffre ici. Le worker publie la matrice déjà rendue en
chaînes (``vertex_worker.risk.build_risk_matrix_content``) ; ce module la
relaie telle quelle, ou sert un état vide honnête.

RELAIS VERBATIM N'EST PAS RELAIS NON VÉRIFIÉ (P1-G). La forme de chaque champ
publié est validée fail-closed avant d'être servie : une charge qui ne
correspond pas au schéma publié est REFUSÉE, jamais réparée ni complétée. Le
refus est une :class:`SnapshotContentError` qui ne nomme que le CHEMIN du
champ — aucune valeur stockée n'atteint le corps de la réponse ni un journal.

DEUX CHOSES QUE CE RELAIS REFUSE DE FAIRE.

1. **Recalculer un coefficient.** La matrice arrive en chaînes précisément
   pour que personne, en aval, ne redécide de son arrondi.
2. **Masquer un refus.** Quand le worker n'a pas pu construire la matrice —
   périmètre trop court, séances communes insuffisantes, variance nulle —
   l'instantané existe et porte son motif. Il est relayé comme tel, avec sa
   ``conclusion`` en français. Un écran vide sans motif serait pire qu'une
   absence : il laisserait croire à une panne.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Literal

from vertex_api.freshness import closed_session_budget, evaluate_relay_freshness
from vertex_api.snapshot_views import (
    SnapshotContentError,
    _optional_str,
    _require_list,
    _require_mapping,
    _require_non_negative_int,
    _require_str,
    require_snapshot_as_of,
)
from vertex_core.contracts.types import (
    ContractModel,
    FrozenStrMapping,
    NonEmptyStr,
    PositiveInt,
    UtcDatetime,
)
from vertex_core.data.freshness import get_freshness_policy
from vertex_persistence.repository.snapshots import CurrentSnapshot

__all__ = [
    "REASON_NO_SNAPSHOT_PUBLISHED",
    "RISK_CONTENT_SCHEMA_VERSION",
    "RISK_FRESHNESS_POLICY",
    "RISK_MAX_AGE",
    "SNAPSHOT_KIND_RISK",
    "RiskMatrixResponse",
    "build_risk_response",
    "checked_risk_content",
]

SNAPSHOT_KIND_RISK = "risk_matrix"
"""Genre publié par le worker ; la clé est ``global`` — la matrice décrit le
périmètre déclaré, pas un portefeuille."""

RISK_CONTENT_SCHEMA_VERSION = "vertex.risk-matrix/1.0"
"""Le SEUL schéma de contenu que ce relais sait lire.

Les échanges entre processus passent par un contrat versionné
(``architecture.md``) : une charge annonçant une autre version — ou aucune —
est refusée plutôt que lue avec des règles qui ne la décrivent plus. Monter la
version côté worker est donc une migration explicite des deux côtés, jamais
une réinterprétation silencieuse.
"""

REASON_NO_SNAPSHOT_PUBLISHED = "no snapshot published"

#: Une corrélation est bâtie sur des CLÔTURES quotidiennes : la donnée la plus
#: fraîche dont elle puisse être issue est une barre quotidienne. Le budget de
#: fraîcheur est donc celui de ``daily_bar``, comme la page Performance.
RISK_FRESHNESS_POLICY = "daily_bar"

_FRESHNESS_POLICY = get_freshness_policy(RISK_FRESHNESS_POLICY)

RISK_MAX_AGE = closed_session_budget(_FRESHNESS_POLICY)

_POPULATIONS = frozenset({"REAL", "SYNTHETIC", "EMPTY"})
"""Aveux admis sur la fenêtre d'entrée. Deny-by-default : toute autre étiquette
est refusée plutôt que lue comme « pas REAL, donc inoffensif »."""

_DATA_STATES = frozenset({"ok", "partial", "insufficient"})

_COVERAGE_COUNTS: tuple[str, ...] = (
    "perimeter_size",
    "retained_count",
    "common_trading_days",
    "minimum_common_days",
    "observations_considered",
    "lookback_seconds",
)


def _checked_pair(raw: Any, *, field: str) -> None:
    """Une paire extrême : deux instruments nommés et un coefficient rendu."""
    if raw is None:
        return
    pair = _require_mapping(raw, field=field)
    _require_str(pair.get("a"), field=f"{field}.a")
    _require_str(pair.get("b"), field=f"{field}.b")
    # Le coefficient est une CHAÎNE déjà rendue : le relais ne la parse pas,
    # ne l'arrondit pas et ne la recalcule pas.
    _require_str(pair.get("value"), field=f"{field}.value")


def _checked_matrix(raw: Any, *, expected: int, field: str) -> None:
    """La grille : carrée, de la taille annoncée, en chaînes uniquement.

    La vérification de FORME est faite ici parce qu'une matrice non carrée
    casserait l'écran en silence — chaque ligne serait lue en face du mauvais
    instrument. Le CONTENU, lui, n'est pas jugé : le relais ne sait pas si un
    coefficient est juste, et ne prétend pas le savoir.
    """
    lignes = _require_list(raw, field=field)
    if len(lignes) != expected:
        raise SnapshotContentError(
            f"{field}: {expected} lignes attendues pour {expected} instruments",
            field=field,
        )
    for index, ligne in enumerate(lignes):
        cellules = _require_list(ligne, field=f"{field}[{index}]")
        if len(cellules) != expected:
            raise SnapshotContentError(
                f"{field}[{index}]: matrice non carrée — {expected} colonnes attendues",
                field=f"{field}[{index}]",
            )
        for colonne, cellule in enumerate(cellules):
            _require_str(cellule, field=f"{field}[{index}][{colonne}]")


def checked_risk_content(raw: Any) -> Mapping[str, Any]:
    """Valide la forme de l'instantané Risques, fail-closed, sans rien réparer.

    Les DEUX formes légitimes sont acceptées et distinguées :

    - une matrice construite (``refusal_reason`` absent) : la grille doit être
      carrée et de la taille de ``instruments`` ;
    - un refus nommé (``refusal_reason`` présent) : la matrice est vide, et
      c'est correct — le motif et la conclusion portent l'information.

    Confondre les deux servirait un écran vide sans dire pourquoi.
    """
    mapping = _require_mapping(raw, field="content")
    version = mapping.get("schema_version")
    if version != RISK_CONTENT_SCHEMA_VERSION:
        raise SnapshotContentError(
            f"content.schema_version: {RISK_CONTENT_SCHEMA_VERSION} requis",
            field="content.schema_version",
        )
    population = mapping.get("population")
    if population not in _POPULATIONS:
        raise SnapshotContentError(
            "content.population: aveu canonique requis", field="content.population"
        )
    if mapping.get("data_state") not in _DATA_STATES:
        raise SnapshotContentError(
            "content.data_state: état canonique requis", field="content.data_state"
        )
    _require_str(mapping.get("as_of"), field="content.as_of")
    _require_str(mapping.get("unit"), field="content.unit")
    _require_str(mapping.get("engine_version"), field="content.engine_version")
    _require_str(mapping.get("conclusion"), field="content.conclusion")
    _optional_str(mapping.get("synchronicity_warning"), field="content.synchronicity_warning")

    instruments = _require_list(mapping.get("instruments"), field="content.instruments")
    for index, instrument in enumerate(instruments):
        entry = _require_mapping(instrument, field=f"content.instruments[{index}]")
        _require_str(entry.get("ticker"), field=f"content.instruments[{index}].ticker")
        _require_str(entry.get("label"), field=f"content.instruments[{index}].label")

    coverage = _require_mapping(mapping.get("coverage"), field="content.coverage")
    for name in _COVERAGE_COUNTS:
        _require_non_negative_int(coverage.get(name), field=f"content.coverage.{name}")
    _require_list(coverage.get("perimeter"), field="content.coverage.perimeter")
    _require_list(coverage.get("retained"), field="content.coverage.retained")
    _require_list(coverage.get("discarded"), field="content.coverage.discarded")
    _require_list(coverage.get("rejected_records"), field="content.coverage.rejected_records")
    _optional_str(coverage.get("refusal_reason"), field="content.coverage.refusal_reason")

    _checked_matrix(
        mapping.get("matrix"), expected=len(instruments), field="content.matrix"
    )
    extremes = mapping.get("extremes")
    if extremes is not None:
        block = _require_mapping(extremes, field="content.extremes")
        _checked_pair(block.get("most_correlated"), field="content.extremes.most_correlated")
        _checked_pair(block.get("most_opposed"), field="content.extremes.most_opposed")
    return mapping


class RiskMatrixResponse(ContractModel):
    """La dernière matrice publiée — ou un état vide honnête.

    ``state = "ok"`` relaie le contenu persisté VERBATIM : instruments,
    matrice en chaînes, extrêmes, avertissement de synchronicité et
    couverture. L'API ne calcule aucun coefficient.

    ``state = "empty"`` signifie que le worker n'a JAMAIS publié — soit parce
    qu'aucun périmètre n'est déclaré, soit parce qu'aucune barre n'a encore
    été collectée. ``reason`` le dit ; rien n'est inventé.

    ``state = "stale"`` relaie le MÊME contenu mais signale que l'instantané a
    dépassé le budget de séance fermée : le worker n'a rien publié de plus
    récent. ``age_seconds`` est publié dans tous les états datables — une
    corrélation vieille de trois jours ne doit pas se lire comme une mesure
    de la minute.

    Un instantané qui porte ``coverage.refusal_reason`` reste ``state = "ok"``
    : le worker a bien publié, et ce qu'il a publié est un refus motivé. Le
    dégrader en ``empty`` effacerait le motif.
    """

    state: Literal["ok", "stale", "empty"]
    snapshot_version: PositiveInt | None
    as_of: UtcDatetime | None
    age_seconds: int | None
    content: FrozenStrMapping | None
    reason: NonEmptyStr | None


def build_risk_response(
    snapshot: CurrentSnapshot | None, *, now: datetime
) -> RiskMatrixResponse:
    """Relaie la dernière matrice, ou l'état vide honnête."""
    if snapshot is None:
        return RiskMatrixResponse(
            state="empty",
            snapshot_version=None,
            as_of=None,
            age_seconds=None,
            content=None,
            reason=REASON_NO_SNAPSHOT_PUBLISHED,
        )
    freshness = evaluate_relay_freshness(
        require_snapshot_as_of(snapshot), now=now, policy=_FRESHNESS_POLICY
    )
    return RiskMatrixResponse(
        state="stale" if freshness.stale else "ok",
        snapshot_version=snapshot.version,
        as_of=snapshot.as_of,
        age_seconds=freshness.age_seconds,
        content=dict(checked_risk_content(snapshot.content)),
        reason=freshness.stale_reason,
    )
