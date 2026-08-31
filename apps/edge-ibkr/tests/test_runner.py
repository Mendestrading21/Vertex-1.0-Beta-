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
from fakes import full_quote, make_envelope, make_snapshot_result

from vertex_edge_ibkr.pacing import LineBudget, MessagePacer, Priority
from vertex_edge_ibkr.port import ContractSpec, EdgeIbkrError, ProviderError, ProviderErrorInfo
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

    async def cancel_subscription(self, subscription_id: str) -> bool:
        self.cancelled.append(subscription_id)
        return True


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


def test_1101_declenche_un_reabonnement_complet() -> None:
    """1101 = données PERDUES : nouvel epoch, réabonnement complet, puis reprise.

    Le 1101 n'est émis qu'UNE fois : on vérifie que le réabonnement est
    effectivement soldé au cycle suivant, et que l'observation du NOUVEL epoch
    est bien ingérée. Un fake qui répéterait l'erreur ne prouverait pas la reprise.
    """
    port = FakePort(
        snapshots={
            CON_A: [
                make_snapshot_result(
                    (), errors=(ProviderErrorInfo(code=1101, message="perte"),)
                ),
                quote_result(CON_A, epoch=2),
            ]
        }
    )
    runner, sink, _, state = build_runner(port, max_cycles=2)
    asyncio.run(runner.run())
    # 1101 incrémente l'epoch : toute observation antérieure devient périmée.
    assert state.connection_epoch == 2
    # Le réabonnement a été soldé au cycle suivant.
    assert not state.resubscribe_required
    # Et la reprise a réellement ingéré l'observation du nouvel epoch.
    assert sink.total == 1


def test_1300_arrete_l_ingestion_sans_reconnexion_automatique() -> None:
    """Le port socket a changé : reconnecter à l'aveugle joindrait une AUTRE session."""
    port = FakePort(
        snapshots={
            CON_A: make_snapshot_result(
                (), errors=(ProviderErrorInfo(code=1300, message="port changé"),)
            )
        }
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
