"""Boucle d'ingestion IBKR : reconnexion, epoch, pacing, lignes, arrêt propre.

Aucun test ici n'ouvre de socket, ne touche une base ni n'attend le temps réel :
le port, le puits, le sommeil et le générateur aléatoire sont tous injectés.
Ce que ces tests protègent est nommé explicitement dans chaque docstring — un
test dont on ne sait pas ce qu'il empêche ne protège rien.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any

import pytest
from fakes import (
    FakeIB,
    FakeTicker,
    fixed_clock,
    full_quote,
    instant_sleep,
    make_envelope,
    make_snapshot_result,
)

from vertex_edge_ibkr.adapter import IbAsyncInformationAdapter
from vertex_edge_ibkr.pacing import LineBudget, MessagePacer, Priority
from vertex_edge_ibkr.port import (
    CancellationOutcome,
    ContractSpec,
    EdgeIbkrError,
    OperationToken,
    ProviderError,
    ProviderErrorInfo,
    ProviderStatusEvent,
)
from vertex_edge_ibkr.runner import EdgeIbkrRunner
from vertex_edge_ibkr.state import ConnectionState, ConnectionStateMachine

CON_A = 1001
CON_B = 1002

SPEC_A = ContractSpec(sec_type="STK", con_id=CON_A, symbol="AAA", exchange="SMART")
SPEC_B = ContractSpec(sec_type="STK", con_id=CON_B, symbol="BBB", exchange="SMART")


class FakePort:
    """Port scriptable : comportements par ``con_id``, erreurs de connexion en file."""

    def __init__(
        self,
        *,
        snapshots: dict[int, Any] | None = None,
        connect_errors: list[BaseException | None] | None = None,
    ) -> None:
        self.snapshots = snapshots or {}
        self.connect_calls = 0
        self.disconnect_calls = 0
        self.cancelled: list[str] = []
        self.snapshot_calls: list[int] = []
        self.status_events: list[ProviderStatusEvent] = []
        self._connect_errors = list(connect_errors or [])

    async def connect(self) -> None:
        self.connect_calls += 1
        if self._connect_errors:
            erreur = self._connect_errors.pop(0)
            if erreur is not None:
                raise erreur

    async def disconnect(self) -> None:
        self.disconnect_calls += 1

    async def market_data_snapshot(
        self,
        spec: ContractSpec,
        *,
        generic_ticks: tuple[int, ...] = (),
        market_data_type: int = 1,
        timeout_seconds: float | None = None,
    ) -> Any:
        assert spec.con_id is not None
        self.snapshot_calls.append(spec.con_id)
        comportement = self.snapshots.get(spec.con_id)
        if isinstance(comportement, list):
            # Séquence : un comportement par appel, le dernier persiste.
            comportement = comportement.pop(0) if len(comportement) > 1 else comportement[0]
        if isinstance(comportement, BaseException):
            raise comportement
        if comportement is None:
            raise ProviderError(9999, "instantané non scripté")
        return comportement

    async def cancel_subscription(
        self, subscription_id: str
    ) -> CancellationOutcome:
        self.cancelled.append(subscription_id)
        return CancellationOutcome.CANCELLED

    def drain_provider_status_events(self) -> tuple[ProviderStatusEvent, ...]:
        events = tuple(self.status_events)
        self.status_events.clear()
        return events

    @property
    def pending_subscription_count(self) -> int:
        return 0


class RecordingSink:
    """Puits en mémoire : mémorise les lots, rend (insérées, doublons)."""

    def __init__(self, *, duplicates: int = 0) -> None:
        self.batches: list[tuple[Any, ...]] = []
        self._duplicates = duplicates

    def __call__(self, envelopes: Any) -> tuple[int, int]:
        lot = tuple(envelopes)
        self.batches.append(lot)
        doublons = min(self._duplicates, len(lot))
        return len(lot) - doublons, doublons

    @property
    def total(self) -> int:
        return sum(len(lot) for lot in self.batches)


class RecordingSleep:
    """Sommeil instantané qui MÉMORISE les délais : le backoff devient observable."""

    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


class StopOnSleep(RecordingSleep):
    """Stoppe le runner au premier backoff, avant toute nouvelle session."""

    def __init__(self) -> None:
        super().__init__()
        self.runner: EdgeIbkrRunner | None = None

    async def __call__(self, delay: float) -> None:
        await super().__call__(delay)
        assert self.runner is not None
        self.runner.request_stop()


def provider_status(
    code: int,
    sequence: int,
    *,
    journal_id: str = "journal-synthetique",
) -> ProviderStatusEvent:
    """Événement global synthétique, distinct des erreurs d'une requête."""
    return ProviderStatusEvent(
        journal_id=journal_id,
        sequence=sequence,
        code=code,
        req_id=None,
        received_at=fixed_clock()(),
        message=f"statut synthétique {code}",
    )


class EventsDuringSnapshotPort(FakePort):
    """Publie un lot d'événements globaux juste avant chaque résultat."""

    def __init__(
        self,
        *,
        snapshots: dict[int, Any],
        event_batches: list[tuple[ProviderStatusEvent, ...]],
    ) -> None:
        super().__init__(snapshots=snapshots)
        self._event_batches = list(event_batches)

    async def market_data_snapshot(
        self,
        spec: ContractSpec,
        *,
        generic_ticks: tuple[int, ...] = (),
        market_data_type: int = 1,
        timeout_seconds: float | None = None,
    ) -> Any:
        result = await super().market_data_snapshot(
            spec,
            generic_ticks=generic_ticks,
            market_data_type=market_data_type,
            timeout_seconds=timeout_seconds,
        )
        if self._event_batches:
            self.status_events.extend(self._event_batches.pop(0))
        return result


class UnconfirmedCancellationPort(FakePort):
    """Conserve la ligne distante tant que la fermeture de session n'est pas prouvée."""

    def __init__(
        self,
        *,
        snapshots: dict[int, Any],
        disconnect_fails: bool = False,
    ) -> None:
        super().__init__(snapshots=snapshots)
        self._pending = 0
        self._disconnect_fails = disconnect_fails

    async def market_data_snapshot(
        self,
        spec: ContractSpec,
        *,
        generic_ticks: tuple[int, ...] = (),
        market_data_type: int = 1,
        timeout_seconds: float | None = None,
    ) -> Any:
        result = await super().market_data_snapshot(
            spec,
            generic_ticks=generic_ticks,
            market_data_type=market_data_type,
            timeout_seconds=timeout_seconds,
        )
        if not result.cancelled:
            self._pending = 1
        return result

    async def cancel_subscription(
        self, subscription_id: str
    ) -> CancellationOutcome:
        self.cancelled.append(subscription_id)
        return CancellationOutcome.NOT_FOUND

    async def disconnect(self) -> None:
        self.disconnect_calls += 1
        if self._disconnect_fails:
            raise EdgeIbkrError("fermeture distante non prouvée")
        self._pending = 0

    @property
    def pending_subscription_count(self) -> int:
        return self._pending


class StatusThenProviderErrorPort(UnconfirmedCancellationPort):
    """Émet 502 puis lève la même panne avec une ligne distante incertaine."""

    async def market_data_snapshot(
        self,
        spec: ContractSpec,
        *,
        generic_ticks: tuple[int, ...] = (),
        market_data_type: int = 1,
        timeout_seconds: float | None = None,
    ) -> Any:
        assert spec.con_id is not None
        self.snapshot_calls.append(spec.con_id)
        self._pending = 1
        self.status_events.append(provider_status(502, 1))
        raise ProviderError(502, "transport synthétique")


class CancelledReceiptWithQuarantinedLinePort(UnconfirmedCancellationPort):
    """Ment sur CANCELLED tout en conservant la ligne dans son registre."""

    async def market_data_snapshot(
        self,
        spec: ContractSpec,
        *,
        generic_ticks: tuple[int, ...] = (),
        market_data_type: int = 1,
        timeout_seconds: float | None = None,
    ) -> Any:
        result = await FakePort.market_data_snapshot(
            self,
            spec,
            generic_ticks=generic_ticks,
            market_data_type=market_data_type,
            timeout_seconds=timeout_seconds,
        )
        self._pending = 1
        return result

    async def cancel_subscription(
        self, subscription_id: str
    ) -> CancellationOutcome:
        self.cancelled.append(subscription_id)
        return CancellationOutcome.CANCELLED


def build_runner(
    port: FakePort,
    *,
    universe: tuple[ContractSpec, ...] = (SPEC_A,),
    sink: RecordingSink | None = None,
    sleep: RecordingSleep | None = None,
    state: ConnectionStateMachine | None = None,
    max_cycles: int | None = 1,
    lines: int = 2,
    queue_capacity: int = 256,
) -> tuple[EdgeIbkrRunner, RecordingSink, RecordingSleep, ConnectionStateMachine]:
    sink = sink if sink is not None else RecordingSink()
    sleep = sleep if sleep is not None else RecordingSleep()
    state = state if state is not None else ConnectionStateMachine(rng=random.Random(1234))
    runner = EdgeIbkrRunner(
        port=port,
        universe=universe,
        state=state,
        sink=sink,
        line_budget=LineBudget(lines * 2, hard_cap=lines),
        # Horloge figée : le seau démarre plein (38 jetons) et ne se recharge
        # pas — le pacing est donc entièrement déterministe.
        pacer=MessagePacer(clock=lambda: 0.0, queue_capacity=queue_capacity),
        sleep=sleep,
        poll_seconds=1.0,
        max_cycles=max_cycles,
    )
    return runner, sink, sleep, state


def quote_result(con_id: int, *, epoch: int = 1, **kwargs: Any) -> Any:
    return make_snapshot_result(
        (make_envelope(full_quote(con_id), con_id=con_id, epoch=epoch),), **kwargs
    )


# --------------------------------------------------------------------------
# Chemin nominal
# --------------------------------------------------------------------------


def test_un_cycle_ingere_et_compte() -> None:
    """Le chemin nominal écrit l'observation et la compte comme insérée."""
    port = FakePort(snapshots={CON_A: quote_result(CON_A)})
    runner, sink, _, _ = build_runner(port)
    stats = asyncio.run(runner.run())
    assert port.connect_calls == 1
    assert port.snapshot_calls == [CON_A]
    assert sink.total == 1
    assert stats.ingested == 1
    assert stats.cycles == 1
    assert stats.requested == 1


def test_composition_reelle_runner_adapter_ne_double_pas_la_transition() -> None:
    """Le point d'entrée réel partage l'état sans bloquer avant connectAsync."""
    fake_ib = FakeIB(ticker=FakeTicker(bid=100.0, ask=100.5, last=100.2, volume=12.0))
    state = ConnectionStateMachine(rng=random.Random(1234))
    adapter = IbAsyncInformationAdapter(
        ib=fake_ib,
        state=state,
        manage_connection_state=False,
        clock=fixed_clock(),
        sleep=instant_sleep,
        snapshot_timeout_seconds=0.2,
        snapshot_poll_seconds=0.1,
        event_id_factory=iter(f"composition-{i}" for i in range(20)).__next__,
    )
    runner, sink, _, _ = build_runner(adapter, state=state)

    stats = asyncio.run(runner.run())

    assert len(fake_ib.connect_calls) == 1
    assert stats.reconnects == 1
    assert stats.ingested == 1
    assert sink.total == 1


def test_un_doublon_n_est_pas_compte_comme_insere() -> None:
    """Rejouer une observation connue n'ajoute aucun travail (idempotence)."""
    port = FakePort(snapshots={CON_A: quote_result(CON_A)})
    runner, _, _, _ = build_runner(port, sink=RecordingSink(duplicates=1))
    stats = asyncio.run(runner.run())
    assert stats.ingested == 0
    assert stats.duplicates == 1


def test_la_deconnexion_a_lieu_meme_apres_un_cycle_normal() -> None:
    port = FakePort(snapshots={CON_A: quote_result(CON_A)})
    runner, _, _, state = build_runner(port)
    asyncio.run(runner.run())
    assert port.disconnect_calls == 1
    assert state.state is ConnectionState.STOPPED


# --------------------------------------------------------------------------
# Fraîcheur : un epoch périmé n'est JAMAIS persisté
# --------------------------------------------------------------------------


def test_observation_d_un_epoch_perime_est_rejetee() -> None:
    """Persister un ancien epoch reviendrait à publier un verdict périmé comme actuel."""
    port = FakePort(snapshots={CON_A: quote_result(CON_A, epoch=99)})
    runner, sink, _, _ = build_runner(port)
    stats = asyncio.run(runner.run())
    assert stats.stale_epoch == 1
    assert stats.ingested == 0
    assert sink.batches == []


def test_observation_sans_epoch_est_rejetee() -> None:
    """Sans epoch prouvé, une quote live ne peut pas entrer dans la vérité canonique."""
    enveloppe = make_envelope(full_quote(CON_A), con_id=CON_A, epoch=1).model_copy(
        update={"connection_epoch": None}
    )
    port = FakePort(snapshots={CON_A: make_snapshot_result((enveloppe,))})
    runner, sink, _, _ = build_runner(port)

    stats = asyncio.run(runner.run())

    assert stats.stale_epoch == 1
    assert stats.ingested == 0
    assert sink.batches == []


def test_un_lot_aux_epochs_mixtes_est_rejete_atomiquement() -> None:
    """Un seul ancien epoch contamine le lot entier : aucune écriture partielle."""
    envelopes = (
        make_envelope(full_quote(CON_A), con_id=CON_A, epoch=1),
        make_envelope(full_quote(CON_A), con_id=CON_A, epoch=2),
    )
    port = FakePort(snapshots={CON_A: make_snapshot_result(envelopes)})
    runner, sink, _, _ = build_runner(port)

    stats = asyncio.run(runner.run())

    assert stats.stale_epoch == 2
    assert stats.ingested == 0
    assert sink.batches == []


@pytest.mark.parametrize(
    "operation",
    [
        OperationToken(
            journal_id="journal-forgé",
            connection_epoch_at_start=1,
            provider_sequence_at_start=0,
            market_update_sequence_at_start=0,
        ),
        OperationToken(
            journal_id="journal-fiable",
            connection_epoch_at_start=2,
            provider_sequence_at_start=0,
            market_update_sequence_at_start=0,
        ),
        OperationToken(
            journal_id="journal-fiable",
            connection_epoch_at_start=1,
            provider_sequence_at_start=1,
            market_update_sequence_at_start=0,
        ),
    ],
    ids=("journal", "epoch", "sequence"),
)
def test_un_operation_token_incoherent_ne_peut_pas_fabriquer_de_fraicheur(
    operation: OperationToken,
) -> None:
    """Journal, epoch et séquence sont trois clôtures indépendantes du fence causal."""
    port = FakePort(
        snapshots={
            CON_A: quote_result(
                CON_A,
                operation=operation,
                market_update_sequence_at_end=1,
            )
        }
    )
    runner, sink, _, _ = build_runner(port)
    # Le journal et la séquence sont établis par le propriétaire de session,
    # indépendamment du résultat que le fournisseur essaie de faire admettre.
    runner._provider_journal_id = "journal-fiable"
    runner._last_provider_sequence = 0

    stats = asyncio.run(runner.run())

    assert stats.stale_epoch == 1
    assert stats.ingested == 0
    assert sink.batches == []


# --------------------------------------------------------------------------
# Souscriptions : annulation TOUJOURS, ligne TOUJOURS relâchée
# --------------------------------------------------------------------------


def test_souscription_non_annulee_par_le_port_est_annulee_par_le_runner() -> None:
    port = FakePort(snapshots={CON_A: quote_result(CON_A, cancelled=False, subscription_id="s-7")})
    runner, _, _, _ = build_runner(port)
    asyncio.run(runner.run())
    assert port.cancelled == ["s-7"]


def test_souscription_deja_annulee_n_est_pas_annulee_deux_fois() -> None:
    port = FakePort(snapshots={CON_A: quote_result(CON_A, cancelled=True)})
    runner, _, _, _ = build_runner(port)
    asyncio.run(runner.run())
    assert port.cancelled == []


def test_deux_annulations_non_confirmees_coupent_le_cycle_et_recyclent_la_session() -> None:
    """Après false→false, aucun second instrument ne touche la session compromise."""
    port = UnconfirmedCancellationPort(
        snapshots={
            CON_A: quote_result(
                CON_A,
                cancelled=False,
                subscription_id="s-incertaine",
            ),
            CON_B: quote_result(CON_B),
        }
    )
    sleep = StopOnSleep()
    runner, sink, _, _ = build_runner(
        port,
        universe=(SPEC_A, SPEC_B),
        sleep=sleep,
        max_cycles=2,
    )
    sleep.runner = runner

    stats = asyncio.run(runner.run())

    assert port.snapshot_calls == [CON_A]
    assert port.cancelled == ["s-incertaine"]
    assert port.connect_calls == 1
    assert port.pending_subscription_count == 0
    assert stats.cancellation_retries == 1
    assert stats.cancellation_unconfirmed == 1
    assert stats.session_recycles == 1
    assert stats.ingested == 0
    assert sink.batches == []


def test_recu_cancelled_avec_registre_non_vide_est_refuse_et_recycle() -> None:
    """Le mot CANCELLED ne remplace jamais la preuve d'un registre revenu à zéro."""
    port = CancelledReceiptWithQuarantinedLinePort(
        snapshots={
            CON_A: quote_result(CON_A, subscription_id="s-mensongere"),
            CON_B: quote_result(CON_B),
        }
    )
    sleep = StopOnSleep()
    runner, sink, _, _ = build_runner(
        port,
        universe=(SPEC_A, SPEC_B),
        sleep=sleep,
        max_cycles=2,
    )
    sleep.runner = runner

    stats = asyncio.run(runner.run())

    assert port.snapshot_calls == [CON_A]
    assert port.cancelled == ["s-mensongere"]
    assert stats.cancellation_retries == 1
    assert stats.cancellation_unconfirmed == 1
    assert stats.session_recycles == 1
    assert stats.ingested == 0
    assert sink.batches == []


def test_echec_de_disconnect_interdit_reconnexion_et_liberation_supposee() -> None:
    """Sans fermeture prouvée, la ligne reste en quarantaine et la boucle s'arrête."""
    port = UnconfirmedCancellationPort(
        snapshots={
            CON_A: quote_result(
                CON_A,
                cancelled=False,
                subscription_id="s-bloquée",
            ),
            CON_B: quote_result(CON_B),
        },
        disconnect_fails=True,
    )
    runner, sink, _, _ = build_runner(
        port,
        universe=(SPEC_A, SPEC_B),
        max_cycles=2,
    )

    stats = asyncio.run(runner.run())

    assert port.snapshot_calls == [CON_A]
    assert port.connect_calls == 1
    assert port.pending_subscription_count == 1
    assert stats.session_recycles == 0
    assert stats.disconnect_failures == 2
    assert stats.ingested == 0
    assert sink.batches == []


def test_la_ligne_est_relachee_meme_quand_l_instantane_echoue() -> None:
    """Une ligne fuitée finirait par bloquer toute l'ingestion en silence."""
    port = FakePort(snapshots={CON_A: EdgeIbkrError("panne synthétique")})
    runner, _, _, _ = build_runner(port)
    budget = runner._lines  # invariant interne délibérément vérifié
    asyncio.run(runner.run())
    assert budget.in_use == 0


def test_plafond_de_lignes_refuse_explicitement_et_ne_perd_rien() -> None:
    """Au-delà du plafond, le refus est COMPTÉ — jamais un abandon silencieux."""
    port = FakePort(snapshots={CON_A: quote_result(CON_A), CON_B: quote_result(CON_B)})
    runner, _, _, _ = build_runner(port, universe=(SPEC_A, SPEC_B), lines=1)
    budget = runner._lines
    # Une ligne est déjà tenue par ailleurs : le plafond de 1 est saturé.
    budget.acquire()
    stats = asyncio.run(runner.run())
    assert stats.line_refused == 2
    assert stats.ingested == 0


# --------------------------------------------------------------------------
# Pacing : un refus de file est explicite et compté
# --------------------------------------------------------------------------


def test_file_de_pacing_pleine_refuse_explicitement() -> None:
    """`QueueRefusalError` doit être compté, pas avalé."""
    port = FakePort(snapshots={CON_A: quote_result(CON_A), CON_B: quote_result(CON_B)})
    runner, _, _, _ = build_runner(port, universe=(SPEC_A, SPEC_B), queue_capacity=1)
    stats = asyncio.run(runner.run())
    assert stats.queue_refused == 1
    assert stats.requested == 1


def test_le_pacer_recoit_la_priorite_durable() -> None:
    """Une ingestion durable ne doit jamais passer devant une commande P0."""
    port = FakePort(snapshots={CON_A: quote_result(CON_A)})
    runner, _, _, _ = build_runner(port)
    asyncio.run(runner.run())
    assert runner._pacer.counters.dispatched[Priority.P2_DURABLE] == 1
    assert runner._pacer.counters.dispatched[Priority.P0_CONTROL] == 0


# --------------------------------------------------------------------------
# Codes fournisseur et machine à états
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    (
        "code",
        "expected_state",
        "expected_epoch",
        "resubscribe_required",
        "awaiting_observation",
        "reread_port_required",
        "needs_reconnect",
        "stop_requested",
    ),
    [
        (502, ConnectionState.DOWN, 1, False, False, False, True, False),
        (1100, ConnectionState.DOWN, 1, False, False, False, False, False),
        (1101, ConnectionState.DEGRADED, 2, True, False, False, False, False),
        (1102, ConnectionState.RECOVERING, 1, False, True, False, False, False),
        (1300, ConnectionState.DOWN, 1, False, False, True, False, True),
    ],
)
def test_journal_global_applique_un_statut_meme_hors_instantane(
    code: int,
    expected_state: ConnectionState,
    expected_epoch: int,
    resubscribe_required: bool,
    awaiting_observation: bool,
    reread_port_required: bool,
    needs_reconnect: bool,
    stop_requested: bool,
) -> None:
    """Les statuts de session ne dépendent jamais d'une fenêtre de snapshot."""
    port = FakePort(snapshots={CON_A: quote_result(CON_A)})
    runner, _, _, state = build_runner(port)
    state.begin_connect()
    state.on_connected()
    runner._needs_reconnect = False
    event = provider_status(code, 1)
    port.status_events.append(event)

    accepted = runner._drain_provider_status_events()

    assert accepted == (event,)
    assert runner.stats().provider_errors == 1
    assert state.state is expected_state
    assert state.connection_epoch == expected_epoch
    assert state.resubscribe_required is resubscribe_required
    assert state.awaiting_post_reconnect_observation is awaiting_observation
    assert state.reread_port_required is reread_port_required
    assert runner._needs_reconnect is needs_reconnect
    assert runner._stop_requested is stop_requested
    assert state.transport_failures == (1 if code == 502 else 0)


@pytest.mark.parametrize(
    ("sequence", "code"),
    [
        (0, 1100),
        (-1, 1100),
        (1, 2104),
    ],
    ids=("sequence-zero", "sequence-negative", "code-not-status"),
)
def test_evenement_global_mal_forme_compromet_le_transport_et_bloque_le_lot(
    sequence: int,
    code: int,
) -> None:
    """Une séquence invalide ou un faux code de statut échoue fermé."""
    port = EventsDuringSnapshotPort(
        snapshots={CON_A: quote_result(CON_A)},
        event_batches=[(provider_status(code, sequence),)],
    )
    runner, sink, _, state = build_runner(port)

    stats = asyncio.run(runner.run())

    assert stats.transport_errors == 1
    assert state.transport_failures == 1
    assert stats.provider_errors == 0
    assert stats.ingested == 0
    assert sink.batches == []


def test_trou_de_sequence_applique_quand_meme_le_1300_critique() -> None:
    """Perdre l'événement 1 ne doit jamais faire ignorer le 1300 reçu en position 2."""
    event = provider_status(1300, 2, journal_id="journal-troué")
    port = EventsDuringSnapshotPort(
        snapshots={
            CON_A: quote_result(
                CON_A,
                operation=OperationToken(
                    journal_id="journal-troué",
                    connection_epoch_at_start=1,
                    provider_sequence_at_start=0,
                    market_update_sequence_at_start=0,
                ),
            )
        },
        event_batches=[(event,)],
    )
    runner, sink, _, state = build_runner(port)

    stats = asyncio.run(runner.run())

    assert state.reread_port_required is True
    assert state.transport_failures == 1
    assert stats.provider_errors == 1
    assert stats.transport_errors == 1
    assert stats.ingested == 0
    assert sink.batches == []
    assert port.connect_calls == 1


def test_rejeu_exact_du_meme_evenement_global_est_idempotent() -> None:
    """Le même (journal, séquence, code) n'incrémente ni epoch ni compteurs."""
    port = FakePort(snapshots={CON_A: quote_result(CON_A)})
    runner, _, _, state = build_runner(port)
    state.begin_connect()
    state.on_connected()
    runner._needs_reconnect = False
    event = provider_status(1101, 1, journal_id="journal-rejeu")
    port.status_events.append(event)

    first = runner._drain_provider_status_events()
    port.status_events.append(event)
    replay = runner._drain_provider_status_events()

    assert first == (event,)
    assert replay == ()
    assert state.connection_epoch == 2
    assert state.resubscribe_required is True
    assert runner.stats().provider_errors == 1
    assert runner.stats().transport_errors == 0


def test_meme_sequence_avec_code_contradictoire_compromet_la_session() -> None:
    """Une identité rejouée avec un autre fait n'est jamais traitée comme doublon sûr."""
    port = FakePort(snapshots={CON_A: quote_result(CON_A)})
    runner, _, _, state = build_runner(port)
    state.begin_connect()
    state.on_connected()
    runner._needs_reconnect = False
    first = provider_status(1102, 1, journal_id="journal-contradictoire")
    contradiction = provider_status(1101, 1, journal_id="journal-contradictoire")
    port.status_events.append(first)
    assert runner._drain_provider_status_events() == (first,)
    port.status_events.append(contradiction)

    accepted = runner._drain_provider_status_events()

    assert accepted == ()
    assert state.state is ConnectionState.DOWN
    assert state.connection_epoch == 1
    assert state.transport_failures == 1
    assert runner.stats().provider_errors == 1
    assert runner.stats().transport_errors == 1
    assert runner._needs_reconnect is True
    assert runner._recycle_required is True


def test_1101_declenche_un_reabonnement_complet() -> None:
    """1101 = données PERDUES : nouvel epoch, réabonnement complet, puis reprise.

    Le 1101 n'est émis qu'UNE fois : on vérifie que le réabonnement est
    effectivement soldé au cycle suivant, et que l'observation du NOUVEL epoch
    est bien ingérée. Un fake qui répéterait l'erreur ne prouverait pas la reprise.
    """
    journal_id = "journal-1101"
    first = make_snapshot_result(
        (),
        errors=(
            ProviderErrorInfo(
                code=1101,
                message="perte",
                status_journal_id=journal_id,
                status_sequence=1,
            ),
        ),
        operation=OperationToken(
            journal_id=journal_id,
            connection_epoch_at_start=1,
            provider_sequence_at_start=0,
            market_update_sequence_at_start=0,
        ),
    )
    second = quote_result(
        CON_A,
        epoch=2,
        operation=OperationToken(
            journal_id=journal_id,
            connection_epoch_at_start=2,
            provider_sequence_at_start=1,
            market_update_sequence_at_start=0,
        ),
    )
    port = EventsDuringSnapshotPort(
        snapshots={
            CON_A: [first, second],
        },
        event_batches=[(provider_status(1101, 1, journal_id=journal_id),), ()],
    )
    runner, sink, _, state = build_runner(port, max_cycles=2)
    asyncio.run(runner.run())
    # 1101 incrémente l'epoch : toute observation antérieure devient périmée.
    assert state.connection_epoch == 2
    # Le réabonnement a été soldé au cycle suivant.
    assert not state.resubscribe_required
    # Et la reprise a réellement ingéré l'observation du nouvel epoch.
    assert sink.total == 1


def test_1100_dans_un_resultat_bloque_toute_persistance_du_cycle() -> None:
    """Une quote reçue avec une perte de connexion n'est jamais publiée comme fraîche."""
    port = FakePort(
        snapshots={
            CON_A: quote_result(
                CON_A,
                errors=(ProviderErrorInfo(code=1100, message="connexion perdue"),),
            )
        }
    )
    runner, sink, _, _ = build_runner(port)

    stats = asyncio.run(runner.run())

    assert stats.provider_errors == 1
    assert stats.ingested == 0
    assert sink.batches == []


def test_information_locale_non_globale_reste_diagnostique() -> None:
    """Une notice 2104 ne corrompt pas le journal et n'annule pas une quote valide."""
    port = FakePort(
        snapshots={
            CON_A: quote_result(
                CON_A,
                errors=(ProviderErrorInfo(code=2104, message="farm is OK"),),
            )
        }
    )
    runner, sink, _, _ = build_runner(port)

    stats = asyncio.run(runner.run())

    assert stats.provider_errors == 1
    assert stats.transport_errors == 0
    assert stats.ingested == 1
    assert sink.total == 1


def test_statut_local_non_journalise_compromet_la_session_sans_piloter_l_epoch() -> None:
    """Un ProviderErrorInfo local n'est jamais propriétaire de l'état global."""
    port = FakePort(
        snapshots={
            CON_A: make_snapshot_result(
                (), errors=(ProviderErrorInfo(code=1101, message="sans reçu"),)
            )
        }
    )
    runner, sink, _, state = build_runner(port)

    stats = asyncio.run(runner.run())

    assert state.connection_epoch == 1
    assert state.state is ConnectionState.STOPPED
    assert stats.provider_errors == 1
    assert stats.transport_errors == 1
    assert stats.ingested == 0
    assert sink.batches == []


def test_statut_local_contradictoire_avec_le_recu_compromet_le_journal() -> None:
    """Même journal/séquence mais autre code = contradiction, jamais transition 1101."""
    journal_id = "journal-info-contradictoire"
    result = make_snapshot_result(
        (),
        errors=(
            ProviderErrorInfo(
                code=1101,
                message="fait contradictoire",
                status_journal_id=journal_id,
                status_sequence=1,
            ),
        ),
        operation=OperationToken(
            journal_id=journal_id,
            connection_epoch_at_start=1,
            provider_sequence_at_start=0,
            market_update_sequence_at_start=0,
        ),
    )
    port = EventsDuringSnapshotPort(
        snapshots={CON_A: result},
        event_batches=[(provider_status(1102, 1, journal_id=journal_id),)],
    )
    runner, sink, _, state = build_runner(port)

    stats = asyncio.run(runner.run())

    assert state.connection_epoch == 1
    assert state.state is ConnectionState.STOPPED
    assert stats.provider_errors == 2
    assert stats.transport_errors == 1
    assert stats.ingested == 0
    assert sink.batches == []


def test_1100_puis_1102_dans_la_meme_operation_ne_valide_pas_sa_quote() -> None:
    """1102 exige une opération VALID ultérieure, jamais la quote du même appel."""
    journal_id = "journal-reprise"
    first = quote_result(
        CON_A,
        operation=OperationToken(
            journal_id=journal_id,
            connection_epoch_at_start=1,
            provider_sequence_at_start=0,
            market_update_sequence_at_start=0,
        ),
        market_update_sequence_at_end=1,
    )
    second = quote_result(
        CON_A,
        operation=OperationToken(
            journal_id=journal_id,
            connection_epoch_at_start=1,
            provider_sequence_at_start=2,
            market_update_sequence_at_start=1,
        ),
        market_update_sequence_at_end=2,
    )
    port = EventsDuringSnapshotPort(
        snapshots={CON_A: [first, second]},
        event_batches=[
            (
                provider_status(1100, 1, journal_id=journal_id),
                provider_status(1102, 2, journal_id=journal_id),
            ),
            (),
        ],
    )
    runner, sink, _, _ = build_runner(port, max_cycles=2)

    stats = asyncio.run(runner.run())

    assert stats.provider_errors == 2
    assert stats.stale_epoch == 1
    assert stats.ingested == 1
    assert len(sink.batches) == 1


def test_502_evenement_et_exception_ne_doublent_ni_transition_ni_backoff() -> None:
    """Un même incident global+exception avec ligne incertaine reste un seul 502."""
    port = StatusThenProviderErrorPort(snapshots={})
    sleep = StopOnSleep()
    state = ConnectionStateMachine(rng=random.Random(1234))
    runner, sink, _, _ = build_runner(
        port,
        universe=(SPEC_A, SPEC_B),
        state=state,
        sleep=sleep,
        max_cycles=2,
    )
    sleep.runner = runner

    stats = asyncio.run(runner.run())

    assert port.snapshot_calls == [CON_A]
    assert state.transport_failures == 1
    assert stats.provider_errors == 1
    assert stats.transport_errors == 1
    assert stats.cancellation_unconfirmed == 1
    assert stats.session_recycles == 1
    assert stats.ingested == 0
    assert sink.batches == []


def test_composition_reelle_applique_1101_une_seule_fois() -> None:
    """Le runner est l'unique propriétaire des transitions fournisseur en production."""
    fake_ib = FakeIB(
        ticker=FakeTicker(bid=100.0, ask=100.5, last=100.2, volume=12.0),
        subscribe_errors=((7, 1101, "données perdues"),),
    )
    state = ConnectionStateMachine(rng=random.Random(1234))
    adapter = IbAsyncInformationAdapter(
        ib=fake_ib,
        state=state,
        manage_connection_state=False,
        clock=fixed_clock(),
        sleep=instant_sleep,
        snapshot_timeout_seconds=0.2,
        snapshot_poll_seconds=0.1,
        event_id_factory=iter(f"composition-1101-{i}" for i in range(20)).__next__,
    )
    runner, sink, _, _ = build_runner(adapter, state=state)

    stats = asyncio.run(runner.run())

    # Connexion initiale = epoch 1 ; le 1101 doit l'incrémenter UNE fois.
    assert state.connection_epoch == 2
    assert stats.provider_errors == 1
    assert stats.ingested == 0
    assert stats.stale_epoch == 1
    assert sink.batches == []


def test_composition_reelle_applique_502_une_seule_fois() -> None:
    """Un seul événement transport ne double ni l'échec ni le backoff de reconnexion."""
    fake_ib = FakeIB(ticker=FakeTicker(), subscribe_errors=((7, 502, "transport"),))
    state = ConnectionStateMachine(rng=random.Random(1234))
    adapter = IbAsyncInformationAdapter(
        ib=fake_ib,
        state=state,
        manage_connection_state=False,
        clock=fixed_clock(),
        sleep=instant_sleep,
        snapshot_timeout_seconds=0.2,
        snapshot_poll_seconds=0.1,
        event_id_factory=iter(f"composition-502-{i}" for i in range(20)).__next__,
    )
    runner, sink, _, _ = build_runner(adapter, state=state)

    stats = asyncio.run(runner.run())

    assert state.transport_failures == 1
    assert stats.provider_errors == 1
    assert stats.ingested == 0
    assert sink.batches == []


def test_1300_arrete_l_ingestion_sans_reconnexion_automatique() -> None:
    """Le port socket a changé : reconnecter à l'aveugle joindrait une AUTRE session."""
    journal_id = "journal-1300"
    port = EventsDuringSnapshotPort(
        snapshots={
            CON_A: make_snapshot_result(
                (),
                errors=(
                    ProviderErrorInfo(
                        code=1300,
                        message="port changé",
                        status_journal_id=journal_id,
                        status_sequence=1,
                    ),
                ),
                operation=OperationToken(
                    journal_id=journal_id,
                    connection_epoch_at_start=1,
                    provider_sequence_at_start=0,
                    market_update_sequence_at_start=0,
                ),
            )
        },
        event_batches=[(provider_status(1300, 1, journal_id=journal_id),)],
    )
    runner, _, _, state = build_runner(port, max_cycles=5)
    asyncio.run(runner.run())
    assert state.reread_port_required is True
    # Une seule connexion : aucune tentative automatique après un 1300.
    assert port.connect_calls == 1


def test_erreur_de_transport_arme_un_backoff_borne() -> None:
    """502/EOF : repli exponentiel jitteré, jamais une reconnexion en boucle serrée."""
    port = FakePort(snapshots={CON_A: EdgeIbkrError("EOF synthétique")})
    runner, _, sleep, _ = build_runner(port, max_cycles=1)
    stats = asyncio.run(runner.run())
    assert stats.transport_errors == 1
    assert all(d > 0 for d in sleep.delays)


def test_echec_de_connexion_reessaie_apres_un_delai() -> None:
    port = FakePort(
        connect_errors=[OSError("refus synthétique"), None],
        # `on_connect_failed` n'incrémente PAS l'epoch : seul `on_connected` le
        # fait. Après un échec puis un succès, l'epoch courant vaut donc 1.
        snapshots={CON_A: quote_result(CON_A, epoch=1)},
    )
    runner, sink, sleep, _ = build_runner(port, max_cycles=1)
    stats = asyncio.run(runner.run())
    assert port.connect_calls == 2
    assert stats.transport_errors == 1
    assert len(sleep.delays) >= 1
    assert sink.total == 1


# --------------------------------------------------------------------------
# Arrêt
# --------------------------------------------------------------------------


def test_request_stop_termine_proprement() -> None:
    port = FakePort(snapshots={CON_A: quote_result(CON_A)})
    runner, _, _, state = build_runner(port, max_cycles=None)
    runner.request_stop()
    stats = asyncio.run(runner.run())
    assert stats.cycles == 0
    assert state.state is ConnectionState.STOPPED
    assert port.disconnect_calls == 1


# --------------------------------------------------------------------------
# Refus de configuration
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kwargs", "motif"),
    [
        ({"universe": ()}, "univers vide"),
        ({"poll_seconds": 0.0}, "poll_seconds"),
        ({"max_cycles": 0}, "max_cycles"),
    ],
)
def test_configuration_invalide_est_refusee(kwargs: dict[str, Any], motif: str) -> None:
    base: dict[str, Any] = {
        "port": FakePort(),
        "universe": (SPEC_A,),
        "state": ConnectionStateMachine(rng=random.Random(1)),
        "sink": RecordingSink(),
        "line_budget": LineBudget(4, hard_cap=2),
        "pacer": MessagePacer(clock=lambda: 0.0),
        "sleep": RecordingSleep(),
    }
    base.update(kwargs)
    with pytest.raises(ValueError, match=motif):
        EdgeIbkrRunner(**base)
