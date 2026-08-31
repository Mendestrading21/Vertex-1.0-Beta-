"""Remplissage historique borné : la profondeur, sur des milliers de titres.

POURQUOI CE FICHIER EXISTE. `runner.py` couvre le temps réel, et il est
structurellement limité à quelques dizaines d'instruments : chaque abonnement
consomme une ligne de données, et IBKR n'en accorde qu'une centaine. Les
milliers de titres ne passent donc PAS par là — ils passent par
`reqHistoricalData`, qui ne consomme aucune ligne mais obéit à un pacing
entièrement différent.

CE QUI REND CE RÉGIME POSSIBLE. `SlidingWindowPacer` : au plus 60 requêtes sur
toute fenêtre de 10 minutes, plus un délai minimal entre deux requêtes
identiques. Soit **6 requêtes par minute en régime soutenu** — environ 2 h 50
pour mille titres. C'est lent, et c'est la vitesse réelle du fournisseur : rien
ici ne prétend l'accélérer.

CE QU'IL NE FAIT JAMAIS
-----------------------
- Aucune capacité compte, position, P&L, ordre ou exécution. `historical_bars`
  est le seul appel utilisé, et il figure dans la liste autorisée.
- Aucune ligne de données de marché : ce régime n'en consomme pas.
- Aucun contournement du pacing : quand la fenêtre est pleine, on ATTEND. Un
  dépassement déclencherait un refus IBKR, pas un gain de vitesse.
- Aucune reprise destructive : `ingest_envelope` est idempotent sur
  `event_id`, donc relancer un remplissage interrompu ne duplique rien.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any

from vertex_core.contracts import DataEnvelope
from vertex_core.contracts.market_quote import UNCLASSIFIED_SECTOR_CODE
from vertex_edge_ibkr.normalize import daily_bars_envelope, daily_quote_envelopes
from vertex_edge_ibkr.pacing import SlidingWindowPacer
from vertex_edge_ibkr.port import (
    BarsPayload,
    ContractSpec,
    EdgeIbkrError,
    IbkrInformationPort,
    ProviderError,
)
from vertex_edge_ibkr.probe import is_informational_code
from vertex_edge_ibkr.runner import ObservationSink

__all__ = [
    "BackfillStats",
    "HistoryBackfiller",
]

log = logging.getLogger("vertex_edge_ibkr.history")

_COUNTER_NAMES = (
    "requested",
    "ingested",
    "duplicates",
    "deferred",
    "provider_errors",
    "transport_errors",
    "notices",
    "derived_quotes",
    "derived_bars",
    "skipped_bars",
    "normalization_refused",
)


@dataclass(frozen=True)
class BackfillStats:
    """Compteurs observables. Une attente est visible, jamais silencieuse."""

    requested: int = 0
    ingested: int = 0
    duplicates: int = 0
    deferred: int = 0
    provider_errors: int = 0
    transport_errors: int = 0
    notices: int = 0
    derived_quotes: int = 0
    derived_bars: int = 0
    skipped_bars: int = 0
    normalization_refused: int = 0
    waited_seconds: float = 0.0


class HistoryBackfiller:
    """Parcourt un univers et remplit son historique, au rythme d'IBKR.

    Tout est injecté — port, puits, pacer, sommeil — donc aucun test n'ouvre
    de socket ni n'attend le temps réel. ``max_requests`` borne l'exécution
    pour les tests ; ``None`` traite tout l'univers.
    """

    def __init__(
        self,
        *,
        port: IbkrInformationPort,
        universe: Sequence[ContractSpec],
        sink: ObservationSink,
        pacer: SlidingWindowPacer,
        sleep: Callable[[float], Awaitable[None]],
        duration: str = "1 Y",
        bar_size: str = "1 day",
        what_to_show: str = "TRADES",
        use_rth: bool = True,
        sector: str = UNCLASSIFIED_SECTOR_CODE,
        max_requests: int | None = None,
    ) -> None:
        if not universe:
            raise ValueError("univers vide : le remplissage ne devine aucun instrument")
        if not duration or not bar_size or not what_to_show:
            raise ValueError("duration, bar_size et what_to_show sont requis")
        if max_requests is not None and max_requests < 1:
            raise ValueError("max_requests doit être >= 1 quand il est fourni")
        self._port = port
        self._universe = tuple(universe)
        self._sink = sink
        self._pacer = pacer
        self._sleep = sleep
        self._duration = duration
        self._bar_size = bar_size
        self._what_to_show = what_to_show
        self._use_rth = use_rth
        self._sector = sector
        self._max_requests = max_requests
        self._stop_requested = False
        self._waited = 0.0
        self._c: dict[str, int] = dict.fromkeys(_COUNTER_NAMES, 0)

    # -- pilotage ----------------------------------------------------------

    def request_stop(self) -> None:
        """Arrêt demandé : la requête en cours se termine, puis la boucle sort."""
        self._stop_requested = True

    def stats(self) -> BackfillStats:
        return BackfillStats(waited_seconds=self._waited, **self._c)

    def request_key(self, spec: ContractSpec) -> str:
        """Clé d'unicité d'une requête : contrat + granularité + nature.

        Deux barres différentes du MÊME contrat ne sont pas des requêtes
        identiques pour IBKR ; les confondre ferait attendre pour rien.
        """
        return f"{spec.con_id}:{self._bar_size}:{self._what_to_show}:{self._duration}"

    # -- boucle ------------------------------------------------------------

    async def run(self) -> BackfillStats:
        """Traite l'univers en respectant la fenêtre glissante."""
        for spec in self._universe:
            if self._stop_requested or self._limit_reached():
                break
            if not await self._await_slot(spec):
                break
            await self._fetch_and_ingest(spec)
        log.info(
            "remplissage terminé — demandées=%d insérées=%d doublons=%d "
            "cotations_dérivées=%d barres_dérivées=%d barres_écartées=%d "
            "attentes=%d (%.0f s cumulées)",
            self._c["requested"],
            self._c["ingested"],
            self._c["duplicates"],
            self._c["derived_quotes"],
            self._c["derived_bars"],
            self._c["skipped_bars"],
            self._c["deferred"],
            self._waited,
        )
        return self.stats()

    async def _await_slot(self, spec: ContractSpec) -> bool:
        """Attend que le pacing autorise ``spec``. ``False`` si arrêt demandé."""
        cle = self.request_key(spec)
        attente = self._pacer.seconds_until_allowed(cle)
        while attente > 0.0:
            if self._stop_requested:
                return False
            self._c["deferred"] += 1
            self._waited += attente
            log.info(
                "pacing historique : %d/%d dans la fenêtre — attente de %.0f s avant con_id %s",
                self._pacer.in_window,
                self._pacer.capacity,
                attente,
                spec.con_id,
            )
            await self._sleep(attente)
            attente = self._pacer.seconds_until_allowed(cle)
        if self._stop_requested:
            return False
        # Course improbable mais possible : un autre appelant a pris le slot.
        return self._pacer.try_acquire(cle)

    def _limit_reached(self) -> bool:
        return self._max_requests is not None and self._c["requested"] >= self._max_requests

    async def _fetch_and_ingest(self, spec: ContractSpec) -> None:
        self._c["requested"] += 1
        try:
            enveloppe = await self._port.historical_bars(
                spec,
                duration=self._duration,
                bar_size=self._bar_size,
                what_to_show=self._what_to_show,
                use_rth=self._use_rth,
            )
        except ProviderError as erreur:
            if is_informational_code(erreur.code):
                # Une NOTICE fournisseur n'est pas un échec : ne pas la compter
                # comme telle, sous peine de croire à une panne inexistante.
                self._c["notices"] += 1
                log.info("notice fournisseur %d sur con_id %s", erreur.code, spec.con_id)
                return
            self._c["provider_errors"] += 1
            log.warning(
                "erreur fournisseur %d sur con_id %s — instrument sauté, jamais "
                "converti en absence de donnée",
                erreur.code,
                spec.con_id,
            )
            return
        except (EdgeIbkrError, OSError, TimeoutError) as erreur:
            self._c["transport_errors"] += 1
            log.warning(
                "erreur de transport (%s) sur con_id %s", type(erreur).__name__, spec.con_id
            )
            return
        a_ecrire: list[DataEnvelope[Any]] = [enveloppe]
        charge = enveloppe.payload
        if isinstance(charge, BarsPayload):
            # La page Marches lit une COTATION QUOTIDIENNE, pas une barre. La
            # transformation vit dans `normalize.py` : elle refuse tout ce qui
            # n'est pas une cloture de seance, et l'identite derivee est stable
            # pour qu'une relance ne duplique rien.
            derivees, normalisation = daily_quote_envelopes(
                enveloppe, charge, spec, sector=self._sector
            )
            a_ecrire.extend(derivees)
            self._c["derived_quotes"] += len(derivees)
            self._c["skipped_bars"] += normalisation.skipped_bars
            if normalisation.refused_reason is not None:
                self._c["normalization_refused"] += 1
                log.info(
                    "aucune cotation derivee pour con_id %s : %s",
                    spec.con_id,
                    normalisation.refused_reason,
                )
            # La page Analyse lit un OHLC complet, pas une cloture seule : une
            # SECONDE derivation, sur la meme barre. Ne produire que la
            # cotation laissait la page Analyse vide alors que la donnee etait
            # deja en base.
            barres_derivees, resultat_barres = daily_bars_envelope(enveloppe, charge, spec)
            if barres_derivees is not None:
                a_ecrire.append(barres_derivees)
                self._c["derived_bars"] += resultat_barres.produced
            elif resultat_barres.refused_reason is not None:
                self._c["normalization_refused"] += 1
                log.info(
                    "aucune barre derivee pour con_id %s : %s",
                    spec.con_id,
                    resultat_barres.refused_reason,
                )
        # Barres et cotations derivees dans la MEME transaction : publier l'une
        # sans l'autre laisserait la page dans un etat incoherent.
        inserees, doublons = self._sink(tuple(a_ecrire))
        self._c["ingested"] += inserees
        self._c["duplicates"] += doublons
