"""Outbox topic handlers: deterministic fusion/attention and capabilities.

``observation.ingested`` recomputes the global attention queue: it loads the
recent observation window, runs the deterministic fusion engine
(dedup -> clusters) and the mandatory-gate relevance ranking
(RIGHTS/IDENTITY/TIME/SOURCE/QUALITY) from ``vertex_core.fusion``, then
publishes an ``attention`` snapshot with at most
:data:`MAX_ATTENTION_ITEMS` explained items.

One cluster publishes at most one item, through an elected representative.
That election must never SETTLE a contradiction: when a cluster holds two
members asserting opposite polarity (``FLAGGED_POLARITY_CONFLICT`` with both
sides inside the cluster), electing one of them would show a rise in place of
a fall. Such a cluster is therefore refused by the QUALITY_OK gate, appears
in ``rejected``, and the contradiction itself is published in the snapshot's
``conflicts`` block — an unsignalled conflict is worse than a duplicate. The handler is a pure
recomputation over its input window — replaying the same message with the
same clock produces byte-identical content.

``capabilities.refresh`` publishes a ``capabilities`` snapshot built ONLY
from actually persisted source-capability probe observations; when nothing
was ever probed the snapshot honestly carries an empty ``probed_sources``
list (per-capability ``NEVER_TESTED`` presentation belongs to the API layer).

Synthetic boundary guard: an observation is synthetic when it carries the
``SYNTHETIC`` rights label or the ``synthetic-dev`` source. If even ONE
considered observation is synthetic, the published attention snapshot is
labeled ``population = "SYNTHETIC"`` and every item lists its own nature
(``synthetic: true/false``) — synthetic data never blends silently into a
snapshot presented as real.

Re-publication semantics (documented contract): a handler run publishes a
new snapshot version ONLY when the canonical content hash changed
("publish-if-changed"). Re-handling the same message with identical inputs
and an identical clock instant is a no-op: the head keeps its version and
its ``content_hash``. Because ``as_of`` is part of the content, a later run
with a fresh clock publishes a new version even for identical items — age
and freshness are never silently frozen.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # import-time cycle avoidance (ingest -> markets)
    from vertex_worker.analysis import AnalysisConfig
    from vertex_worker.calendar import CalendarConfig
    from vertex_worker.markets import MarketsConfig
    from vertex_worker.options import OptionsConfig
    from vertex_worker.risk import RiskConfig

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql import ColumnElement

from vertex_core.contracts import (
    EnvelopeQuality,
    IdentityStatus,
    canonical_json_hash,
)
from vertex_core.fusion import (
    ContentObservation,
    FusionAction,
    RelevanceInput,
    fuse,
    rank_items,
)
from vertex_core.fusion.relevance import POLICY_VERSION
from vertex_core.synthetic import SYNTHETIC_RIGHTS, SYNTHETIC_SOURCE
from vertex_persistence.json_codec import to_jsonb_object
from vertex_persistence.models import Observation
from vertex_persistence.repository.outbox import ClaimedOutboxMessage
from vertex_persistence.repository.snapshots import (
    PublishedSnapshot,
    get_current_snapshot,
    publish_snapshot,
)
from vertex_worker.ingest import TOPIC_OBSERVATION_INGESTED
from vertex_worker.registry import HandlerRegistry

__all__ = [
    "ATTENTION_SCHEMA_VERSION",
    "CAPABILITIES_SCHEMA_VERSION",
    "CAPABILITY_SCHEMA_PREFIX",
    "CONTENT_SCHEMA_PREFIXES",
    "DEFAULT_SOURCE_TIER",
    "DEV_SYNTHETIC_CONFIG",
    "MAX_ATTENTION_ITEMS",
    "POPULATION_EMPTY",
    "POPULATION_REAL",
    "POPULATION_SYNTHETIC",
    "SNAPSHOT_KEY_GLOBAL",
    "SNAPSHOT_KIND_ATTENTION",
    "SNAPSHOT_KIND_CAPABILITIES",
    "TOPIC_CAPABILITIES_REFRESH",
    "AttentionFusionHandler",
    "CapabilitiesSnapshotHandler",
    "FusionConfig",
    "ObservationRecord",
    "build_attention_content",
    "build_capabilities_content",
    "build_registry",
    "is_synthetic_record",
    "load_capability_records",
    "load_recent_observation_records",
    "load_recent_observation_records_by_instrument",
    "publish_if_changed",
]

log = logging.getLogger("vertex_worker.handlers")

Clock = Callable[[], datetime]

TOPIC_CAPABILITIES_REFRESH = "capabilities.refresh"

SNAPSHOT_KIND_ATTENTION = "attention"
SNAPSHOT_KIND_CAPABILITIES = "capabilities"
SNAPSHOT_KEY_GLOBAL = "global"

ATTENTION_SCHEMA_VERSION = "vertex.attention-queue/1.0"
CAPABILITIES_SCHEMA_VERSION = "vertex.capabilities/1.0"

CAPABILITY_SCHEMA_PREFIX = "source-capability/"
"""Observations whose ``schema_version`` starts with this prefix are persisted
source-capability probe results (``SourceCapabilitySnapshot`` dumps)."""

CONTENT_SCHEMA_PREFIXES: tuple[str, ...] = (
    "synthetic-news/",
    "ibkr.news-headline/",
)
"""Familles de schéma ADMISES comme contenu par la file d'attention, la file
de revue et le rail de preuves (deny by default) : une dépêche par ligne,
porteuse d'un ``title`` et d'``entities``.

- ``synthetic-news/`` : la population de développement
  (``vertex_core.synthetic.SYNTHETIC_SCHEMA_NEWS``) ;
- ``ibkr.news-headline/`` : la dépêche DÉRIVÉE par l'adaptateur IBKR
  (``vertex_edge_ibkr.news.NEWS_HEADLINE_SCHEMA_VERSION``, une ligne par
  titre). Le lot brut ``ibkr.news-headlines/`` (une liste par réponse) n'en
  fait pas partie : il ne porte pas de titre.

POURQUOI CETTE DÉCLARATION EXISTE. Mesuré le 2026-09-03 à 08:40 UTC :
``today/attention`` servait 0 item sur données réelles alors que des dépêches
valides existaient en base. Le collecteur temps réel écrit une cotation
instantanée par instrument et par cycle de 60 s (``ibkr.quote/1`` depuis le
lot L1, ``ibkr.daily-quote/1`` pour les 3 197 lignes déjà écrites) : sans
titre, jamais du contenu — mais les 500 observations les plus récentes,
toutes familles confondues, n'étaient plus QUE des instantanées. Rien
n'échouait, rien n'était journalisé : la file était vide.

Le remède n'est pas une borne plus large (la famine reviendrait avec le
prochain instrument) : le consommateur déclare les familles qu'il sait lire
et le chargeur les applique AVANT la borne, comme ``DAILY_QUOTE_SCHEMA_PREFIXES``
(page Marchés) et ``DAILY_BARS_SCHEMA_PREFIXES`` (page Analyse) le font déjà
pour leurs propres familles. Les familles de marché (cotations, barres,
chaînes d'options, sondes de capacité, faits SEC) ne portent jamais de titre :
les déclarer ici n'ajouterait aucun contenu et rouvrirait la famine.
"""

MAX_ATTENTION_ITEMS = 15
"""Hard cap of the published attention queue (explained truncation)."""

DEFAULT_SOURCE_TIER = "P4"
"""Trust tier assumed for a source absent from the tier registry (lowest)."""

POPULATION_SYNTHETIC = "SYNTHETIC"
POPULATION_REAL = "REAL"
POPULATION_EMPTY = "EMPTY"


def _require_aware_utc_now(now: datetime) -> datetime:
    if not isinstance(now, datetime):
        raise TypeError(f"now: expected datetime, got {type(now).__name__}")
    if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
        raise ValueError("now: naive datetime rejected, aware UTC required")
    return now.astimezone(UTC)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _require_aware_utc_now(value).isoformat()


def _require_schema_prefixes(prefixes: Sequence[str], *, name: str) -> tuple[str, ...]:
    """Au moins une famille, chacune un préfixe non vide : rien de déclaré,
    rien de lu — le refus est explicite plutôt qu'une fenêtre vide muette."""
    if isinstance(prefixes, (str, bytes)) or not isinstance(prefixes, Sequence) or not prefixes:
        raise ValueError(f"{name}: at least one schema family prefix required")
    for prefix in prefixes:
        if not isinstance(prefix, str) or not prefix.strip():
            raise ValueError(f"{name}: non-empty string prefixes required")
    return tuple(prefixes)


def _schema_family_filter(familles: tuple[str, ...]) -> ColumnElement[bool]:
    """``schema_version`` COMMENCE PAR l'une des familles, caractère pour
    caractère : ``%``, ``_`` et le caractère d'échappement sont échappés
    (``autoescape``). Mesuré (revue S0, réserve 4) : ``LIKE 'demo_news/%'``
    lisait le souligné comme « n'importe quel caractère » et laissait entrer
    ``demoXnews/1.0`` dans une fenêtre qui ne l'avait pas déclarée."""
    return or_(
        *(
            Observation.schema_version.startswith(prefix, autoescape=True)
            for prefix in familles
        )
    )


@dataclass(frozen=True)
class ObservationRecord:
    """Lightweight, ORM-free view of one persisted observation.

    Keeps the pure content builders testable without a database session.
    """

    event_id: str
    source: str
    source_event_id: str | None
    instrument_ref: str | None
    published_at: datetime | None
    received_at: datetime
    as_of: datetime
    quality_status: str
    rights: str
    schema_version: str
    payload: Mapping[str, Any]


def is_synthetic_record(record: ObservationRecord) -> bool:
    """Synthetic when either marker is present (fail-closed, same rule as
    :func:`vertex_core.synthetic.is_synthetic`)."""
    return record.rights == SYNTHETIC_RIGHTS or record.source == SYNTHETIC_SOURCE


@dataclass(frozen=True)
class FusionConfig:
    """Registries the fusion handler needs (owned upstream, injected here).

    ``allowed_sources`` and ``usable_rights`` mirror the source/rights
    registries: anything not explicitly declared is refused by the SOURCE_OK
    / RIGHTS_OK gates (deny by default). ``source_tiers`` maps a source to
    its trust tier; an undeclared source gets :data:`DEFAULT_SOURCE_TIER`
    (the lowest trust), never a promotion.

    ``content_schema_prefixes`` déclare les familles de schéma que ce
    consommateur SAIT LIRE ; le chargeur les applique avant la borne
    ``max_observations`` (voir :data:`CONTENT_SCHEMA_PREFIXES`). Une famille
    non déclarée n'entre jamais dans la fenêtre — ni dans le classement, ni
    dans la couverture publiée.
    """

    allowed_sources: frozenset[str]
    usable_rights: frozenset[str]
    source_tiers: Mapping[str, str] = field(default_factory=dict)
    lookback: timedelta = timedelta(hours=72)
    max_observations: int = 500
    content_schema_prefixes: tuple[str, ...] = CONTENT_SCHEMA_PREFIXES

    def __post_init__(self) -> None:
        if self.lookback <= timedelta(0):
            raise ValueError("lookback: must be a positive duration")
        if not isinstance(self.max_observations, int) or self.max_observations < 1:
            raise ValueError("max_observations: must be an int >= 1")
        _require_schema_prefixes(self.content_schema_prefixes, name="content_schema_prefixes")
        object.__setattr__(
            self, "source_tiers", MappingProxyType(dict(self.source_tiers))
        )


DEV_SYNTHETIC_CONFIG = FusionConfig(
    allowed_sources=frozenset({SYNTHETIC_SOURCE}),
    usable_rights=frozenset({SYNTHETIC_RIGHTS}),
    source_tiers={SYNTHETIC_SOURCE: DEFAULT_SOURCE_TIER},
)
"""Development-only registry: accepts ONLY the synthetic source and rights.
Every snapshot it produces is labeled ``population = "SYNTHETIC"``."""


# --------------------------------------------------------------------------
# Loading (session-facing, deterministic ordering)
# --------------------------------------------------------------------------


def _record_from_row(row: Observation) -> ObservationRecord:
    return ObservationRecord(
        event_id=row.event_id,
        source=row.source,
        source_event_id=row.source_event_id,
        instrument_ref=row.instrument_ref,
        published_at=row.published_at,
        received_at=row.received_at,
        as_of=row.as_of,
        quality_status=row.quality_status,
        rights=row.rights,
        schema_version=row.schema_version,
        payload=row.payload,
    )


def load_recent_observation_records(
    session: Session,
    *,
    now: datetime,
    lookback: timedelta,
    limit: int,
    schema_prefixes: Sequence[str],
    instrument_ref: str | None = None,
) -> list[ObservationRecord]:
    """Load the bounded recent observation window, deterministically ordered.

    The window is ``[now - lookback, now]`` on ``as_of`` (future rows are
    excluded — the TIME gate would refuse them anyway), most recent first,
    capped at ``limit`` rows.

    ``schema_prefixes`` sont les familles que l'APPELANT sait lire ; elles
    s'appliquent AVANT la borne, et il n'y a pas de défaut. Chaque préfixe
    est un LITTÉRAL (``%`` et ``_`` échappés), jamais un motif. Mesuré le
    2026-09-03 : les 500 lignes les plus récentes étaient toutes des
    cotations instantanées (une par instrument et par minute), et la file
    d'attention ne voyait plus aucune dépêche — voir
    :data:`CONTENT_SCHEMA_PREFIXES`. Une famille absente de la liste n'est ni
    chargée ni comptée : la couverture publiée dit ce qu'elle a regardé.

    ``instrument_ref`` RESTREINT la fenêtre à un instrument, et le cadrage se
    fait alors AVANT la borne. Mesuré le 2026-09-01 : avec 1376 dépêches sur
    28 instruments, la fenêtre globale de 500 ne contenait plus AUCUNE dépêche
    de GOOG — collectées en premier, donc chassées par les suivantes. Le rail
    de preuves affichait « aucune preuve » alors que 140 existaient en base.

    L'appelant qui veut le classement TOUS instruments confondus — la file
    d'attention — laisse ce paramètre absent : ce sont deux besoins distincts,
    d'où un filtre optionnel plutôt qu'un changement de comportement.
    """
    now = _require_aware_utc_now(now)
    familles = _require_schema_prefixes(schema_prefixes, name="schema_prefixes")
    requete = select(Observation).where(
        Observation.as_of <= now,
        Observation.as_of >= now - lookback,
        _schema_family_filter(familles),
    )
    if instrument_ref is not None:
        requete = requete.where(Observation.instrument_ref == instrument_ref)
    rows = (
        session.execute(
            requete.order_by(Observation.as_of.desc(), Observation.id.desc()).limit(
                limit
            )
        )
        .scalars()
        .all()
    )
    return [_record_from_row(row) for row in rows]


def load_recent_observation_records_by_instrument(
    session: Session,
    *,
    now: datetime,
    lookback: timedelta,
    limit: int,
    schema_prefixes: Sequence[str],
    instrument_refs: Sequence[str],
) -> dict[str, list[ObservationRecord]]:
    """Une fenêtre PAR INSTRUMENT, en UNE lecture de ``observations``.

    Pour chaque référence de ``instrument_refs``, exactement ce que
    :func:`load_recent_observation_records` rend avec ``instrument_ref=ref`` :
    mêmes bornes sur ``as_of``, mêmes familles (préfixes littéraux), même
    ordre ``as_of DESC, id DESC`` et même ``limit`` — PAR instrument, jamais
    partagé entre eux. Une référence sans observation dans la fenêtre rend
    une liste vide, comme le chargeur unitaire ; une référence non demandée
    n'apparaît pas.

    POURQUOI. Mesuré (revue S0, réserve 3) : la page Opportunités exécutait
    une requête de preuves par instrument à barres, ≈161 en profil réel,
    chacune parcourant toute la plage ``as_of`` du lookback — le seul index
    de ``observations`` porte sur ``as_of``. Ici la plage est lue une fois :
    numérotation par instrument (``row_number() OVER (PARTITION BY
    instrument_ref ORDER BY as_of DESC, id DESC)``) puis coupe à ``limit``.
    Ce n'est pas un index : le coût reste proportionnel à la plage, mais il
    ne croît plus avec la taille de l'univers.
    """
    now = _require_aware_utc_now(now)
    familles = _require_schema_prefixes(schema_prefixes, name="schema_prefixes")
    if (
        isinstance(instrument_refs, (str, bytes))
        or not isinstance(instrument_refs, Sequence)
        or not instrument_refs
    ):
        raise ValueError("instrument_refs: at least one instrument reference required")
    references: list[str] = []
    for ref in instrument_refs:
        if not isinstance(ref, str) or not ref.strip():
            raise ValueError("instrument_refs: non-empty string references required")
        if ref not in references:
            references.append(ref)
    rang = (
        func.row_number()
        .over(
            partition_by=Observation.instrument_ref,
            order_by=(Observation.as_of.desc(), Observation.id.desc()),
        )
        .label("rang")
    )
    interieur = (
        select(Observation, rang)
        .where(
            Observation.as_of <= now,
            Observation.as_of >= now - lookback,
            _schema_family_filter(familles),
            Observation.instrument_ref.in_(references),
        )
        .subquery()
    )
    fenetre = aliased(Observation, interieur)
    rows = (
        session.execute(
            select(fenetre)
            .where(interieur.c.rang <= limit)
            .order_by(fenetre.instrument_ref, fenetre.as_of.desc(), fenetre.id.desc())
        )
        .scalars()
        .all()
    )
    par_instrument: dict[str, list[ObservationRecord]] = {ref: [] for ref in references}
    for row in rows:
        par_instrument[str(row.instrument_ref)].append(_record_from_row(row))
    return par_instrument


def load_capability_records(session: Session) -> list[ObservationRecord]:
    """Load persisted source-capability probe observations, oldest first."""
    rows = (
        session.execute(
            select(Observation)
            .where(Observation.schema_version.like(f"{CAPABILITY_SCHEMA_PREFIX}%"))
            .order_by(Observation.as_of.asc(), Observation.id.asc())
        )
        .scalars()
        .all()
    )
    return [_record_from_row(row) for row in rows]


# --------------------------------------------------------------------------
# Pure content builders (no session, fully deterministic)
# --------------------------------------------------------------------------


def _content_title(record: ObservationRecord) -> str | None:
    title = record.payload.get("title") if isinstance(record.payload, Mapping) else None
    if isinstance(title, str) and title.strip():
        return title
    return None


def _content_entities(record: ObservationRecord) -> tuple[str, ...]:
    raw = record.payload.get("entities") if isinstance(record.payload, Mapping) else None
    entities: list[str] = []
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        entities = [e for e in raw if isinstance(e, str) and e.strip()]
    if not entities and record.instrument_ref:
        entities = [record.instrument_ref]
    return tuple(entities)


def _content_url(record: ObservationRecord) -> str | None:
    url = (
        record.payload.get("canonical_url")
        if isinstance(record.payload, Mapping)
        else None
    )
    if isinstance(url, str) and url.strip():
        return url
    return None


def _content_observation(
    record: ObservationRecord, config: FusionConfig, title: str
) -> ContentObservation:
    return ContentObservation(
        content_id=record.event_id,
        source=record.source,
        source_tier=config.source_tiers.get(record.source, DEFAULT_SOURCE_TIER),
        native_id=record.source_event_id,
        canonical_url=_content_url(record),
        title=title,
        entities=_content_entities(record),
        published_at=record.published_at,
        received_at=record.received_at,
        rights=record.rights,
        quality=EnvelopeQuality(record.quality_status),
        is_deleted=False,
    )


def _event_time(observation: ContentObservation) -> datetime:
    return (
        observation.published_at
        if observation.published_at is not None
        else observation.received_at
    )


def build_attention_content(
    records: Sequence[ObservationRecord], *, now: datetime, config: FusionConfig
) -> dict[str, Any]:
    """Build the attention snapshot content: dedup, gates, ranking, budget.

    Pure and deterministic: identical ``records`` (in any order), ``now`` and
    ``config`` produce an identical dict. Nothing is silently dropped — the
    coverage block accounts for every considered observation and the
    ``rejected`` list explains every gated-out item.
    """
    now = _require_aware_utc_now(now)

    content_records: dict[str, ObservationRecord] = {}
    observations: list[ContentObservation] = []
    non_content = 0
    for record in records:
        title = _content_title(record)
        if title is None:
            non_content += 1
            continue
        if record.event_id in content_records:
            # Persisted observations are unique by event_id; a duplicate here
            # means the caller passed the same record twice — refuse it.
            raise ValueError(f"duplicate event_id in records: {record.event_id!r}")
        content_records[record.event_id] = record
        observations.append(_content_observation(record, config, title))

    fusion = fuse(observations)
    observation_by_id = {obs.content_id: obs for obs in fusion.observations}

    conflicts: list[dict[str, Any]] = []
    seen_conflicts: set[str] = set()
    inputs: list[RelevanceInput] = []
    cluster_by_representative: dict[str, Any] = {}
    for cluster in fusion.clusters:
        members = [observation_by_id[member_id] for member_id in cluster.member_ids]
        member_ids = set(cluster.member_ids)
        # A polarity conflict whose BOTH sides sit in this cluster cannot be
        # resolved by electing a representative: publishing one member would
        # show a rise in place of a fall. A conflict whose other side lives
        # in another cluster is not hidden by the election — both clusters
        # stay publishable — so it is reported without closing the gate.
        internal_conflicts = [
            decision
            for decision in cluster.decisions
            if decision.action is FusionAction.FLAGGED_POLARITY_CONFLICT
            and member_ids.issuperset(decision.inputs)
        ]
        for decision in cluster.decisions:
            if decision.action is not FusionAction.FLAGGED_POLARITY_CONFLICT:
                continue
            if decision.decision_id in seen_conflicts:
                continue
            seen_conflicts.add(decision.decision_id)
            conflicts.append(
                {
                    "kind": "POLARITY",
                    "scope": (
                        "INTRA_CLUSTER"
                        if member_ids.issuperset(decision.inputs)
                        else "CROSS_CLUSTER"
                    ),
                    "cluster_id": cluster.cluster_id,
                    "member_event_ids": list(decision.inputs),
                    "rule_id": decision.rule_id,
                    "rule_version": decision.rule_version,
                    "rationale": decision.rationale,
                    "reversible": decision.reversible,
                }
            )
        representative = min(
            members, key=lambda obs: (obs.source_tier, _event_time(obs), obs.content_id)
        )
        record = content_records[representative.content_id]
        cluster_by_representative[representative.content_id] = cluster
        # The candidate carries the CLUSTER's quality, not only its own — the
        # same aggregation already applied to rights and sources below. An
        # unresolved internal contradiction is exactly EnvelopeQuality.CONFLICT,
        # which the mandatory QUALITY_OK gate refuses (fail-closed). The
        # observation itself is untouched and stays in the snapshot's cluster
        # provenance; nothing is deleted, nothing is rewritten.
        candidate = representative
        if internal_conflicts:
            candidate = representative.model_copy(
                update={"quality": EnvelopeQuality.CONFLICT}
            )
        inputs.append(
            RelevanceInput(
                observation=candidate,
                identity_status=(
                    IdentityStatus.RESOLVED
                    if record.instrument_ref
                    else IdentityStatus.UNRESOLVED
                ),
                # Fail-closed at cluster level: ONE member with undeclared
                # rights or an undeclared source closes the gate for the
                # whole cluster — never a silent partial acceptance.
                rights_usable=all(r in config.usable_rights for r in cluster.rights),
                source_allowed=all(s in config.allowed_sources for s in cluster.sources),
                novelty=True,
            )
        )
    conflicts.sort(key=lambda entry: (entry["scope"], entry["member_event_ids"]))

    ranking = rank_items(inputs, as_of=now)
    published_items = ranking.ranked[:MAX_ATTENTION_ITEMS]

    synthetic_count = sum(1 for record in records if is_synthetic_record(record))
    if not records:
        population = POPULATION_EMPTY
    elif synthetic_count > 0:
        population = POPULATION_SYNTHETIC
    else:
        population = POPULATION_REAL

    items: list[dict[str, Any]] = []
    for ranked in published_items:
        cluster = cluster_by_representative[ranked.item_id]
        representative = observation_by_id[ranked.item_id]
        record = content_records[ranked.item_id]
        member_records = [content_records[member] for member in cluster.member_ids]
        items.append(
            {
                "item_id": ranked.item_id,
                "title": representative.title,
                "synthetic": any(is_synthetic_record(r) for r in member_records),
                "priority_class": ranked.priority_class,
                "relevance_reasons": list(ranked.relevance_reasons),
                "age_seconds": ranked.subscores.age_seconds,
                "source_tier": ranked.subscores.source_tier,
                "quality": representative.quality.value,
                "provenance": {
                    "cluster_id": cluster.cluster_id,
                    "member_event_ids": list(cluster.member_ids),
                    "sources": list(cluster.sources),
                    "rights": list(cluster.rights),
                    "first_published_at": _iso(cluster.first_published_at),
                    "last_received_at": _iso(cluster.last_received_at),
                    "instrument_ref": record.instrument_ref,
                },
            }
        )

    return {
        "schema_version": ATTENTION_SCHEMA_VERSION,
        "as_of": _iso(now),
        "population": population,
        "policy_version": POLICY_VERSION,
        "fusion_ruleset_version": fusion.ruleset_version,
        "items": items,
        "conflicts": conflicts,
        "rejected": [
            {
                "item_id": rejection.item_id,
                "filtered_reason": rejection.filtered_reason,
                "failed_gates": list(rejection.failed_gates),
            }
            for rejection in ranking.rejected
        ],
        "coverage": {
            "lookback_seconds": int(config.lookback.total_seconds()),
            "content_schema_prefixes": list(config.content_schema_prefixes),
            "max_items": MAX_ATTENTION_ITEMS,
            "observations_considered": len(records),
            "content_observations": len(observations),
            "non_content_observations": non_content,
            "synthetic_observations": synthetic_count,
            "non_synthetic_observations": len(records) - synthetic_count,
            "clusters": len(fusion.clusters),
            "polarity_conflicts": len(conflicts),
            "ranked": len(ranking.ranked),
            "rejected": len(ranking.rejected),
            "published_items": len(items),
            "truncated_ranked": max(0, len(ranking.ranked) - MAX_ATTENTION_ITEMS),
        },
    }


def build_capabilities_content(
    records: Sequence[ObservationRecord], *, now: datetime
) -> dict[str, Any]:
    """Build the capabilities snapshot from persisted probe observations only.

    ``records`` must be ordered oldest-first (as
    :func:`load_capability_records` returns them): the latest probe per
    source wins. With no persisted probe the content honestly carries an
    empty ``probed_sources`` list — nothing is invented, no status is
    fabricated (the API layer renders untested capabilities as
    ``NEVER_TESTED``).
    """
    now = _require_aware_utc_now(now)
    latest_by_source: dict[str, ObservationRecord] = {}
    for record in records:
        latest_by_source[record.source] = record

    probed_sources = [
        {
            "source": source,
            "event_id": record.event_id,
            "schema_version": record.schema_version,
            "as_of": _iso(record.as_of),
            "rights": record.rights,
            "synthetic": is_synthetic_record(record),
            "snapshot": dict(record.payload),
        }
        for source, record in sorted(latest_by_source.items())
    ]
    return {
        "schema_version": CAPABILITIES_SCHEMA_VERSION,
        "as_of": _iso(now),
        "probed_sources": probed_sources,
    }


# --------------------------------------------------------------------------
# Publication (publish-if-changed semantics)
# --------------------------------------------------------------------------


#: Cle d'horodatage de PUBLICATION portee par le contenu des snapshots.
#: Elle bouge a chaque recalcul : toute comparaison qui cherche un changement
#: d'INFORMATION doit l'exclure. `publish_if_changed`, lui, l'inclut
#: deliberement — un recalcul plus tard est un fait publie nouveau.
PUBLICATION_TIMESTAMP_KEY = "as_of"


def publish_if_changed(
    session: Session, *, kind: str, key: str, content: Any, as_of: datetime
) -> PublishedSnapshot | None:
    """Publish a new version of ``(kind, key)`` only when the content changed.

    Compares the canonical content hash with the current head: identical
    content is a no-op returning ``None`` (idempotent replay keeps the same
    version and hash); changed content publishes the next version. Never
    overwrites an existing version.
    """
    encoded = to_jsonb_object("content", content)
    new_hash = canonical_json_hash(encoded)
    current = get_current_snapshot(session, kind=kind, key=key)
    if current is not None and current.content_hash == new_hash:
        return None
    return publish_snapshot(session, kind=kind, key=key, content=content, as_of=as_of)


# --------------------------------------------------------------------------
# Handlers
# --------------------------------------------------------------------------


class AttentionFusionHandler:
    """Handler of ``observation.ingested``: recompute the attention queue."""

    def __init__(self, *, config: FusionConfig, clock: Clock) -> None:
        self._config = config
        self._clock = clock

    def __call__(self, session: Session, message: ClaimedOutboxMessage) -> None:
        now = _require_aware_utc_now(self._clock())
        records = load_recent_observation_records(
            session,
            now=now,
            lookback=self._config.lookback,
            limit=self._config.max_observations,
            schema_prefixes=self._config.content_schema_prefixes,
        )
        content = build_attention_content(records, now=now, config=self._config)
        published = publish_if_changed(
            session,
            kind=SNAPSHOT_KIND_ATTENTION,
            key=SNAPSHOT_KEY_GLOBAL,
            content=content,
            as_of=now,
        )
        if published is None:
            log.info(
                "attention snapshot unchanged (message_id=%s)", message.id
            )
        else:
            log.info(
                "attention snapshot published version=%s (message_id=%s)",
                published.version,
                message.id,
            )


class CapabilitiesSnapshotHandler:
    """Handler of ``capabilities.refresh``: publish really-probed capabilities."""

    def __init__(self, *, clock: Clock) -> None:
        self._clock = clock

    def __call__(self, session: Session, message: ClaimedOutboxMessage) -> None:
        now = _require_aware_utc_now(self._clock())
        records = load_capability_records(session)
        content = build_capabilities_content(records, now=now)
        published = publish_if_changed(
            session,
            kind=SNAPSHOT_KIND_CAPABILITIES,
            key=SNAPSHOT_KEY_GLOBAL,
            content=content,
            as_of=now,
        )
        if published is None:
            log.info(
                "capabilities snapshot unchanged (message_id=%s)", message.id
            )
        else:
            log.info(
                "capabilities snapshot published version=%s (message_id=%s)",
                published.version,
                message.id,
            )


def build_registry(
    *,
    clock: Clock,
    fusion_config: FusionConfig,
    markets_config: MarketsConfig | None = None,
    options_config: OptionsConfig | None = None,
    analysis_config: AnalysisConfig | None = None,
    calendar_config: CalendarConfig | None = None,
    opportunities_config: AnalysisConfig | None = None,
    risk_config: RiskConfig | None = None,
) -> HandlerRegistry:
    """Build the worker registry with the canonical topics.

    ``markets_config`` and ``options_config`` default to the development-only
    synthetic registries (``DEV_SYNTHETIC_MARKETS_CONFIG`` /
    ``DEV_SYNTHETIC_OPTIONS_CONFIG``) — the same dev posture as the callers
    passing ``DEV_SYNTHETIC_CONFIG`` here; every snapshot they produce is
    honestly labeled ``population = "SYNTHETIC"``.
    """
    from vertex_worker.analysis import (
        DEV_SYNTHETIC_ANALYSIS_CONFIG,
        register_analysis_handler,
    )
    from vertex_worker.calendar import (
        DEV_SYNTHETIC_CALENDAR_CONFIG,
        register_calendar_handler,
    )
    from vertex_worker.follow_up import register_follow_up_handler
    from vertex_worker.markets import (
        DEV_SYNTHETIC_MARKETS_CONFIG,
        register_markets_handler,
    )
    from vertex_worker.opportunities import (
        DEV_SYNTHETIC_OPPORTUNITIES_CONFIG,
        register_opportunities_handler,
    )
    from vertex_worker.options import (
        DEV_SYNTHETIC_OPTIONS_CONFIG,
        register_options_handler,
    )
    from vertex_worker.performance import register_performance_handler
    from vertex_worker.portfolio import register_portfolio_handler
    from vertex_worker.risk import register_risk_handler
    from vertex_worker.sec_fundamentals import register_sec_fundamentals_handler

    registry = HandlerRegistry()
    registry.register(
        TOPIC_OBSERVATION_INGESTED,
        AttentionFusionHandler(config=fusion_config, clock=clock),
    )
    registry.register(
        TOPIC_CAPABILITIES_REFRESH, CapabilitiesSnapshotHandler(clock=clock)
    )
    resolved_markets_config = (
        markets_config if markets_config is not None else DEV_SYNTHETIC_MARKETS_CONFIG
    )
    # Le constructeur est le SEUL a savoir si un handler de risque sera
    # enregistre : il transmet ce fait plutot que de le laisser supposer.
    register_markets_handler(
        registry,
        clock=clock,
        config=resolved_markets_config,
        risk_enabled=risk_config is not None,
    )
    register_options_handler(
        registry,
        clock=clock,
        config=options_config if options_config is not None else DEV_SYNTHETIC_OPTIONS_CONFIG,
    )
    register_analysis_handler(
        registry,
        clock=clock,
        config=analysis_config if analysis_config is not None else DEV_SYNTHETIC_ANALYSIS_CONFIG,
    )
    register_portfolio_handler(registry, clock=clock)
    # Calendar (page 02): the dev synthetic registry (declared universe as
    # watchlist); positions/theses are read inside the handler.
    register_calendar_handler(
        registry,
        clock=clock,
        config=(
            calendar_config
            if calendar_config is not None
            else DEV_SYNTHETIC_CALENDAR_CONFIG
        ),
    )
    # Opportunities (page 04): the full declared universe under the single
    # AdviceEngine and the manifest profile equity_etf_swing_3_12m.
    register_opportunities_handler(
        registry,
        clock=clock,
        config=(
            opportunities_config
            if opportunities_config is not None
            else DEV_SYNTHETIC_OPPORTUNITIES_CONFIG
        ),
    )
    # Review queue (page 09): same fusion registry as the attention handler.
    register_follow_up_handler(registry, clock=clock, config=fusion_config)
    # Performance (page 10): same quote registry as the markets handler.
    register_performance_handler(registry, clock=clock, config=resolved_markets_config)
    # Risques : le handler n'existe QUE si un perimetre est declare. Sans
    # perimetre, aucun instantane n'est publie et la page reste vide EN LE
    # DISANT — plutot que de comparer des instruments choisis au hasard.
    if risk_config is not None:
        register_risk_handler(registry, clock=clock, config=risk_config)
    register_sec_fundamentals_handler(registry, clock=clock)
    return registry
