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
ne persiste qu'après confirmation de l'annulation fournisseur. Une annulation
incertaine met la ligne en quarantaine et force la fermeture de session.

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

from vertex_core.contracts import DataEnvelope, EnvelopeQuality
from vertex_edge_ibkr.pacing import LineBudget, MessagePacer, Priority, QueueRefusalError
from vertex_edge_ibkr.port import (
    CancellationOutcome,
    ContractSpec,
    EdgeIbkrError,
    IbkrInformationPort,
    MarketDataSnapshotResult,
    ProviderError,
    ProviderStatusEvent,
)
from vertex_edge_ibkr.state import (
    PROVIDER_STATUS_CODES,
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
    "cancellation_retries",
    "cancellation_unconfirmed",
    "session_recycles",
    "disconnect_failures",
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
    cancellation_retries: int = 0
    cancellation_unconfirmed: int = 0
    session_recycles: int = 0
    disconnect_failures: int = 0


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
        self._needs_reconnect = True
        self._recycle_required = False
        self._provider_journal_id: str | None = None
        self._last_provider_sequence = 0
        self._provider_event_codes: dict[int, int] = {}
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
                self._drain_provider_status_events()
                if self._stop_requested:
                    break
                if (
                    self._port.pending_subscription_count
                    and not self._recycle_required
                ):
                    self._c["cancellation_unconfirmed"] += 1
                    self._mark_transport_failure(
                        "souscription déjà en quarantaine", None
                    )
                if self._recycle_required and not await self._recycle_session():
                    break
                if self._needs_reconnect and self._pending_backoff is not None:
                    delai, self._pending_backoff = self._pending_backoff, None
                    await self._sleep(delai)
                    if self._stop_requested:
                        break
                    self._drain_provider_status_events()
                if self._needs_reconnect:
                    if not await self._connect_once():
                        continue
                elif self._state.state is ConnectionState.DOWN:
                    # 1100 concerne la liaison TWS <-> IBKR, pas le socket
                    # local. Garder la session ouverte permet de recevoir
                    # 1101/1102 sans boucle de reconnexion agressive.
                    await self._sleep(self._poll_seconds)
                    continue
                await self._serve_session()
        finally:
            self._state.stop()
            try:
                await self._port.disconnect()
            except (EdgeIbkrError, OSError):
                # La déconnexion est au mieux : la session se ferme de toute façon.
                self._c["disconnect_failures"] += 1
                log.debug("déconnexion sans effet (session déjà fermée)")
        return self.stats()

    async def _recycle_session(self) -> bool:
        """Close a compromised session before any new provider request."""
        try:
            await self._port.disconnect()
        except (EdgeIbkrError, OSError, TimeoutError) as erreur:
            self._c["disconnect_failures"] += 1
            self._stop_requested = True
            log.error(
                "recyclage IBKR refusé (%s) — aucune reconnexion sans fermeture prouvée",
                type(erreur).__name__,
            )
            return False
        if self._port.pending_subscription_count != 0:
            self._c["disconnect_failures"] += 1
            self._stop_requested = True
            log.error("recyclage IBKR non prouvé — souscriptions encore en quarantaine")
            return False
        self._recycle_required = False
        self._c["session_recycles"] += 1
        return True

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
            self._drain_provider_status_events()
            delai = self._state.on_transport_error()
            self._c["transport_errors"] += 1
            log.warning(
                "connexion refusée (%s) — nouvelle tentative dans %.1f s",
                type(erreur).__name__,
                delai,
            )
            self._pending_backoff = delai
            self._needs_reconnect = True
            self._recycle_required = True
            return False
        self._state.on_connected()
        self._needs_reconnect = False
        self._c["reconnects"] += 1
        self._drain_provider_status_events()
        log.info(
            "connecté à TWS sur la boucle locale — epoch %d, état %s",
            self._state.connection_epoch,
            self._state.state.value,
        )
        return not self._stop_requested

    async def _serve_session(self) -> None:
        while not self._stop_requested and not self._cycle_limit_reached():
            self._drain_provider_status_events()
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
            self._drain_provider_status_events()
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
            self._drain_provider_status_events()
            if self._state.state in (ConnectionState.DOWN, ConnectionState.STOPPED):
                return
            await self._request_and_ingest(item, epoch)
            if self._needs_reconnect or self._state.state in (
                ConnectionState.DOWN,
                ConnectionState.STOPPED,
            ):
                return
        reste = self._pacer.pending()
        if reste:
            log.info("pacing : %d requêtes reportées au prochain cycle (jamais perdues)", reste)

    async def _request_and_ingest(self, spec: ContractSpec, epoch: int) -> None:
        self._drain_provider_status_events()
        if self._state.state in (ConnectionState.DOWN, ConnectionState.STOPPED):
            return
        if not self._lines.try_acquire():
            self._c["line_refused"] += 1
            log.warning(
                "plafond de lignes atteint (%d/%d) — con_id %s reporté, jamais abandonné",
                self._lines.in_use,
                self._lines.max_usable,
                spec.con_id,
            )
            return
        try:
            self._c["requested"] += 1
            resultat = await self._port.market_data_snapshot(
                spec, generic_ticks=self._generic_ticks, market_data_type=1
            )
            drained = self._drain_provider_status_events()
            acknowledged = {
                (event.journal_id, event.sequence, event.code) for event in drained
            }
            status_during_operation = bool(drained)
            for info in resultat.provider_errors:
                key = (info.status_journal_id, info.status_sequence, info.code)
                if info.code in PROVIDER_STATUS_CODES:
                    if key in acknowledged:
                        continue
                    # A request-local diagnostic never owns global connection
                    # state. Without the exact journal receipt, the causal
                    # record is incomplete or contradictory: stop fail-closed.
                    self._c["provider_errors"] += 1
                    self._mark_status_journal_failure(
                        "statut fournisseur sans événement journalisé concordant"
                    )
                    status_during_operation = True
                    break
                self._apply_provider_code(info.code)

            cancellation_confirmed = (
                resultat.cancellation_outcome is CancellationOutcome.CANCELLED
                and self._port.pending_subscription_count == 0
            )
            if not cancellation_confirmed:
                retry = resultat.cancellation_outcome
                if retry is not CancellationOutcome.SESSION_CLOSED:
                    self._c["cancellation_retries"] += 1
                    retry = await self._port.cancel_subscription(
                        resultat.subscription_id
                    )
                    retry_events = self._drain_provider_status_events()
                    status_during_operation = (
                        status_during_operation or bool(retry_events)
                    )
                cancellation_confirmed = (
                    retry is CancellationOutcome.CANCELLED
                    and self._port.pending_subscription_count == 0
                )
                if not cancellation_confirmed:
                    self._c["cancellation_unconfirmed"] += 1
                    if not self._stop_requested:
                        self._mark_transport_failure(
                            "annulation de souscription non confirmée", spec.con_id
                        )
                    return

            self._persist(
                resultat,
                epoch,
                status_during_operation=status_during_operation,
            )
        except ProviderError as erreur:
            drained = self._drain_provider_status_events()
            if erreur.code in PROVIDER_STATUS_CODES:
                if not any(event.code == erreur.code for event in drained):
                    self._c["provider_errors"] += 1
                    self._mark_status_journal_failure(
                        "exception de statut sans événement journalisé concordant"
                    )
            else:
                self._apply_provider_code(erreur.code)
            if self._port.pending_subscription_count:
                self._c["cancellation_unconfirmed"] += 1
                if not self._stop_requested:
                    self._mark_transport_failure(
                        "erreur fournisseur avec souscription en quarantaine", spec.con_id
                    )
        except (EdgeIbkrError, OSError, TimeoutError) as erreur:
            self._drain_provider_status_events()
            self._mark_transport_failure(type(erreur).__name__, spec.con_id)
        finally:
            # Le budget du runner est rendu, mais le registre de l'adaptateur
            # garde tout slot distant incertain en quarantaine jusqu'au recycle.
            self._lines.release()

    def _mark_transport_failure(self, reason: str, con_id: int | None) -> None:
        self._c["transport_errors"] += 1
        self._pending_backoff = self._state.on_transport_error()
        self._needs_reconnect = True
        self._recycle_required = True
        log.warning(
            "session IBKR compromise (%s) sur con_id %s — repli dans %.1f s",
            reason,
            con_id,
            self._pending_backoff,
        )

    def _drain_provider_status_events(self) -> tuple[ProviderStatusEvent, ...]:
        accepted: list[ProviderStatusEvent] = []
        for event in self._port.drain_provider_status_events():
            if (
                not event.journal_id
                or event.sequence < 1
                or event.code not in PROVIDER_STATUS_CODES
            ):
                self._mark_status_journal_failure("événement fournisseur mal formé")
                continue
            if self._provider_journal_id is None:
                self._provider_journal_id = event.journal_id
            if event.journal_id != self._provider_journal_id:
                self._mark_status_journal_failure("journal fournisseur incohérent")
                continue
            if event.sequence <= self._last_provider_sequence:
                if self._provider_event_codes.get(event.sequence) != event.code:
                    self._mark_status_journal_failure("rejeu fournisseur contradictoire")
                continue
            if event.sequence != self._last_provider_sequence + 1:
                self._mark_status_journal_failure("séquence fournisseur incomplète")
                self._last_provider_sequence = event.sequence
                self._provider_event_codes[event.sequence] = event.code
                self._apply_provider_code(event.code)
                accepted.append(event)
                continue
            self._last_provider_sequence = event.sequence
            self._provider_event_codes[event.sequence] = event.code
            self._apply_provider_code(event.code)
            accepted.append(event)
        return tuple(accepted)

    def _mark_status_journal_failure(self, reason: str) -> None:
        """Stop on journal corruption: reconnecting cannot recover a lost fact."""
        self._mark_transport_failure(reason, None)
        self._stop_requested = True

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
            self._needs_reconnect = True
            self._recycle_required = True
        if code == 1300:
            self._stop_requested = True

    def _persist(
        self,
        result: MarketDataSnapshotResult,
        epoch: int,
        *,
        status_during_operation: bool,
    ) -> None:
        """Écrit les observations prouvées de l'epoch courant ; rejette les autres.

        Une enveloppe estampillée d'un epoch antérieur n'est jamais fraîche
        (`ConnectionStateMachine.observation_is_fresh`) : la persister
        reviendrait à publier un ancien verdict comme s'il était actuel.
        Une session ``DOWN`` ou ``DEGRADED`` bloque aussi tout le résultat du
        cycle, même si le fournisseur a livré une quote avant son code 1100.
        """
        envelopes = result.envelopes
        if not envelopes:
            return
        current_epoch = self._state.connection_epoch
        operation = result.operation
        if self._provider_journal_id is None:
            self._provider_journal_id = operation.journal_id
        epochs = {envelope.connection_epoch for envelope in envelopes}
        causal_mismatch = (
            operation.journal_id != self._provider_journal_id
            or operation.connection_epoch_at_start != epoch
            or operation.provider_sequence_at_start != self._last_provider_sequence
            or epochs != {epoch}
            or epoch != current_epoch
        )
        if status_during_operation or causal_mismatch:
            self._c["stale_epoch"] += len(envelopes) if causal_mismatch else 0
            log.warning(
                "lot IBKR causalement incohérent rejeté — état %s, epoch cycle %d, "
                "epoch courant %d, observations %d, transition=%s",
                self._state.state.value,
                epoch,
                current_epoch,
                len(envelopes),
                status_during_operation,
            )
            return
        if self._state.state is ConnectionState.RECOVERING:
            valid = any(
                envelope.quality_status is EnvelopeQuality.VALID for envelope in envelopes
            )
            updated = (
                result.market_update_sequence_at_end
                > operation.market_update_sequence_at_start
            )
            if not valid or not updated:
                log.warning("reprise 1102 non prouvée par une mise à jour VALID ultérieure")
                return
            self._state.record_observation(epoch)
        if not self._state.observation_is_fresh(epoch):
            log.warning(
                "lot IBKR rejeté avant persistance — état %s, epoch %d",
                self._state.state.value,
                epoch,
            )
            return
        inserees, doublons = self._sink(envelopes)
        self._c["ingested"] += inserees
        self._c["duplicates"] += doublons
