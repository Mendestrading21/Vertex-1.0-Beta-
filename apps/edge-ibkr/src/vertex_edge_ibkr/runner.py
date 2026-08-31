"""Ingestion IBKR continue, read-only — la boucle qui manquait.

POURQUOI CE FICHIER EXISTE. `apps/edge-ibkr` contenait l'adaptateur, la machine
à états, le pacing et la sonde de droits — tous testés — mais AUCUN point
d'entrée. Autrement dit : Vertex savait sonder ses droits une fois, et rien
d'autre. Les pages ne pouvaient donc jamais quitter `population = SYNTHETIC`,
non par choix de conception mais par absence de processus. Ce fichier est cette
absence, comblée.

CE QU'IL EST — ET CE QU'IL N'EST PAS
------------------------------------
C'est une ingestion par INSTANTANÉS PÉRIODIQUES BORNÉS, pas un flux de ticks
permanent. Ce n'est pas un compromis de facilité : le port `IbkrInformationPort`
n'expose que `market_data_snapshot`, `LineBudget` interdit de tenir plus de 80 %
des lignes de données ouvertes, et un droit « display only » ne justifie pas de
mobiliser des lignes en continu. Chaque cycle acquiert une ligne, la relâche, et
annule sa souscription dans un `finally`.

FRONTIÈRE FINANCIÈRE
--------------------
Aucune capacité compte, position, P&L, ordre, exécution, exercice ou
`whatIfOrder`. Le port ne les expose pas ; `tools/check_financial_boundary.py`
balaie ce fichier comme tous les autres. La seule annulation pratiquée ici est
`cancel_subscription` — une souscription de DONNÉES, jamais un ordre.

DÉCOUPLAGE
----------
Le runner ne connaît ni SQLAlchemy ni PostgreSQL : il écrit à travers
`ObservationSink`. Les tests le pilotent avec un puits en mémoire, sans base.
`__main__.py` fournit le puits réel.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from vertex_core.contracts import DataEnvelope
from vertex_edge_ibkr.pacing import LineBudget, MessagePacer, Priority, QueueRefusalError
from vertex_edge_ibkr.port import ContractSpec, EdgeIbkrError, IbkrInformationPort, ProviderError
from vertex_edge_ibkr.state import (
    ConnectionState,
    ConnectionStateMachine,
    InvalidTransitionError,
    PortRereadRequiredError,
    ReconnectInProgressError,
)

__all__ = [
    "EdgeIbkrRunner",
    "ObservationSink",
    "RunnerStats",
]

log = logging.getLogger("vertex_edge_ibkr.runner")

_COUNTER_NAMES = (
    "cycles",
    "requested",
    "ingested",
    "duplicates",
    "stale_epoch",
    "line_refused",
    "queue_refused",
    "provider_errors",
    "transport_errors",
    "reconnects",
)


class ObservationSink(Protocol):
    """Puits durable des observations. Rend le couple (insérées, doublons)."""

    def __call__(self, envelopes: Sequence[DataEnvelope[Any]]) -> tuple[int, int]:
        ...


@dataclass(frozen=True)
class RunnerStats:
    """Compteurs observables. Un refus est visible, jamais silencieux."""

    cycles: int = 0
    requested: int = 0
    ingested: int = 0
    duplicates: int = 0
    stale_epoch: int = 0
    line_refused: int = 0
    queue_refused: int = 0
    provider_errors: int = 0
    transport_errors: int = 0
    reconnects: int = 0


class EdgeIbkrRunner:
    """Boucle d'ingestion : connecter, servir, se reconnecter, s'arrêter proprement.

    Tout est injecté — port, machine à états, pacing, puits, sommeil — afin
    qu'aucun test n'ait besoin de réseau, de base ni de temps réel.
    ``max_cycles`` borne l'exécution pour les tests ; ``None`` tourne jusqu'à
    ``request_stop()`` ou un signal.
    """

    def __init__(
        self,
        *,
        port: IbkrInformationPort,
        universe: Sequence[ContractSpec],
        state: ConnectionStateMachine,
        sink: ObservationSink,
        line_budget: LineBudget,
        pacer: MessagePacer,
        sleep: Callable[[float], Awaitable[None]],
        poll_seconds: float = 60.0,
        generic_ticks: tuple[int, ...] = (),
        max_cycles: int | None = None,
    ) -> None:
        if not universe:
            raise ValueError("univers vide : l'ingestion ne devine aucun instrument")
        if poll_seconds <= 0:
            raise ValueError("poll_seconds doit être strictement positif")
        if max_cycles is not None and max_cycles < 1:
            raise ValueError("max_cycles doit être >= 1 quand il est fourni")
        self._port = port
        self._universe = tuple(universe)
        self._state = state
        self._sink = sink
        self._lines = line_budget
        self._pacer = pacer
        self._sleep = sleep
        self._poll_seconds = poll_seconds
        self._generic_ticks = generic_ticks
        self._max_cycles = max_cycles
        self._stop_requested = False
        self._pending_backoff: float | None = None
        self._c: dict[str, int] = dict.fromkeys(_COUNTER_NAMES, 0)

    # -- pilotage ----------------------------------------------------------

    def request_stop(self) -> None:
        """Demande un arrêt : le cycle en cours se termine, puis la boucle sort."""
        self._stop_requested = True

    def stats(self) -> RunnerStats:
        return RunnerStats(**self._c)

    # -- boucle principale -------------------------------------------------

    async def run(self) -> RunnerStats:
        """Connecte, sert, reconnecte — jusqu'à l'arrêt demandé ou la borne."""
        try:
            while not self._stop_requested and not self._cycle_limit_reached():
                if self._pending_backoff is not None:
                    delai, self._pending_backoff = self._pending_backoff, None
                    await self._sleep(delai)
                    if self._stop_requested:
                        break
                if not await self._connect_once():
                    continue
                await self._serve_session()
        finally:
            self._state.stop()
            try:
                await self._port.disconnect()
            except (EdgeIbkrError, OSError):
                # La déconnexion est au mieux : la session se ferme de toute façon.
                log.debug("déconnexion sans effet (session déjà fermée)")
        return self.stats()

    async def _connect_once(self) -> bool:
        try:
            self._state.begin_connect()
        except PortRereadRequiredError:
            # 1300 : le port socket a changé. Reconnecter à l'aveugle joindrait
            # potentiellement une AUTRE session que celle validée par l'humain.
            log.error(
                "code 1300 reçu : le port socket TWS a changé. Relire le port dans "
                "TWS et redémarrer. Aucune reconnexion automatique."
            )
            self._stop_requested = True
            return False
        except (InvalidTransitionError, ReconnectInProgressError) as erreur:
            log.debug("connexion non tentée : %s", erreur)
            return False
        try:
            await self._port.connect()
        except (EdgeIbkrError, OSError, TimeoutError) as erreur:
            delai = self._state.on_connect_failed()
            self._c["transport_errors"] += 1
            log.warning(
                "connexion refusée (%s) — nouvelle tentative dans %.1f s",
                type(erreur).__name__,
                delai,
            )
            self._pending_backoff = delai
            return False
        self._state.on_connected()
        self._c["reconnects"] += 1
        log.info(
            "connecté à TWS sur la boucle locale — epoch %d, état %s",
            self._state.connection_epoch,
            self._state.state.value,
        )
        return True

    async def _serve_session(self) -> None:
        while not self._stop_requested and not self._cycle_limit_reached():
            if self._state.state in (ConnectionState.DOWN, ConnectionState.STOPPED):
                return
            if self._state.resubscribe_required:
                # 1101 : les données ont été PERDUES. Le nouvel epoch invalide
                # toute observation antérieure ; le cycle qui suit réabonne tout.
                self._state.mark_resubscribed()
                log.warning(
                    "réabonnement complet après 1101 — epoch %d",
                    self._state.connection_epoch,
                )
            await self._cycle()
            self._c["cycles"] += 1
            if self._stop_requested or self._cycle_limit_reached():
                return
            if self._state.state in (ConnectionState.DOWN, ConnectionState.STOPPED):
                return
            await self._sleep(self._poll_seconds)

    def _cycle_limit_reached(self) -> bool:
        return self._max_cycles is not None and self._c["cycles"] >= self._max_cycles

    # -- un passage sur l'univers -----------------------------------------

    async def _cycle(self) -> None:
        epoch = self._state.connection_epoch
        for spec in self._universe:
            try:
                self._pacer.submit(spec, Priority.P2_DURABLE)
            except QueueRefusalError as refus:
                # Refus EXPLICITE : rien n'est abandonné en silence.
                self._c["queue_refused"] += 1
                log.warning("pacing : requête refusée — %s", refus)
        for item in self._pacer.drain():
            if self._stop_requested:
                return
            await self._request_and_ingest(item, epoch)
        reste = self._pacer.pending()
        if reste:
            log.info("pacing : %d requêtes reportées au prochain cycle (jamais perdues)", reste)

    async def _request_and_ingest(self, spec: ContractSpec, epoch: int) -> None:
        if not self._lines.try_acquire():
            self._c["line_refused"] += 1
            log.warning(
                "plafond de lignes atteint (%d/%d) — con_id %s reporté, jamais abandonné",
                self._lines.in_use,
                self._lines.max_usable,
                spec.con_id,
            )
            return
        subscription_id: str | None = None
        try:
            self._c["requested"] += 1
            resultat = await self._port.market_data_snapshot(
                spec, generic_ticks=self._generic_ticks, market_data_type=1
            )
            if not resultat.cancelled:
                subscription_id = resultat.subscription_id
            for info in resultat.provider_errors:
                self._apply_provider_code(info.code)
            self._persist(resultat.envelopes, epoch)
        except ProviderError as erreur:
            self._apply_provider_code(erreur.code)
        except (EdgeIbkrError, OSError, TimeoutError) as erreur:
            self._c["transport_errors"] += 1
            self._pending_backoff = self._state.on_transport_error()
            log.warning(
                "erreur de transport (%s) sur con_id %s — repli dans %.1f s",
                type(erreur).__name__,
                spec.con_id,
                self._pending_backoff,
            )
        finally:
            # Une ligne est TOUJOURS relâchée et une souscription de données
            # TOUJOURS annulée, quoi qu'il arrive au-dessus.
            self._lines.release()
            if subscription_id is not None:
                try:
                    await self._port.cancel_subscription(subscription_id)
                except (EdgeIbkrError, OSError):
                    log.debug("annulation sans effet pour %s", subscription_id)

    def _apply_provider_code(self, code: int) -> None:
        self._c["provider_errors"] += 1
        delai = self._state.on_error_code(code)
        if code in (1100, 1101, 1102, 1300):
            log.warning(
                "code fournisseur %d — état %s, epoch %d",
                code,
                self._state.state.value,
                self._state.connection_epoch,
            )
        if delai is not None:
            self._pending_backoff = delai

    def _persist(self, envelopes: Sequence[DataEnvelope[Any]], epoch: int) -> None:
        """Écrit les observations de l'epoch COURANT ; rejette les autres.

        Une enveloppe estampillée d'un epoch antérieur n'est jamais fraîche
        (`ConnectionStateMachine.observation_is_fresh`) : la persister
        reviendrait à publier un ancien verdict comme s'il était actuel.
        """
        fraiches: list[DataEnvelope[Any]] = []
        for enveloppe in envelopes:
            if enveloppe.connection_epoch is not None and enveloppe.connection_epoch != epoch:
                self._c["stale_epoch"] += 1
                log.warning(
                    "observation d'un epoch périmé (%s != %d) rejetée",
                    enveloppe.connection_epoch,
                    epoch,
                )
                continue
            fraiches.append(enveloppe)
        if not fraiches:
            return
        inserees, doublons = self._sink(fraiches)
        self._c["ingested"] += inserees
        self._c["duplicates"] += doublons
        for _ in fraiches:
            # Promeut RECOVERING -> HEALTHY à la première observation du
            # nouvel epoch, après un 1102.
            self._state.record_observation(epoch)
