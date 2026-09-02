"""Chaîne d'ingestion IBKR → PostgreSQL réel, prouvée de bout en bout.

CE QUE CE TEST ÉTABLIT, ET QUE RIEN D'AUTRE N'ÉTABLISSAIT. `EdgeIbkrRunner` est
couvert par des faux, et `ingest_envelope` par les suites du worker ; mais le
MAILLON entre les deux — `PostgresObservationSink`, défini dans
`tools/run_edge_ibkr.py` — n'était couvert par rien. C'est précisément là que
passeront les premières données de marché réelles.

Quatre propriétés sont vérifiées contre une vraie base migrée :

1. une observation produite par le runner arrive en base avec sa provenance
   IBKR intacte (`source`, `rights`, `connection_epoch`) ;
2. le travail de fusion est mis en file (`observation.ingested`), sans quoi le
   worker ne publierait jamais rien ;
3. rejouer la MÊME observation n'écrit rien et n'ajoute AUCUN travail — sinon
   une reconnexion dupliquerait le travail à chaque cycle ;
4. une observation d'un epoch périmé n'atteint JAMAIS la base.
"""

from __future__ import annotations

import asyncio
import importlib.util
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from vertex_core.contracts import DataEnvelope, DelayStatus, EnvelopeQuality
from vertex_core.contracts.hashing import canonical_json_hash
from vertex_edge_ibkr.pacing import LineBudget, MessagePacer
from vertex_edge_ibkr.port import (
    CancellationOutcome,
    ContractSpec,
    MarketDataSnapshotResult,
    OperationToken,
    ProviderStatusEvent,
)
from vertex_edge_ibkr.runner import EdgeIbkrRunner
from vertex_edge_ibkr.state import ConnectionStateMachine
from vertex_persistence.models import Observation, OutboxMessage
from vertex_worker.ingest import TOPIC_OBSERVATION_INGESTED

_REPO_ROOT = Path(__file__).resolve().parents[3]
_TOOL = _REPO_ROOT / "tools" / "run_edge_ibkr.py"

#: Habilitation publiée par l'edge IBKR : jamais SYNTHETIC, jamais DEMO.
REAL_RIGHTS = "IBKR_MARKET_DATA_DISPLAY_ONLY"

T0 = datetime(2026, 8, 31, 12, 0, 0, tzinfo=UTC)
CON_ID = 4242
SPEC = ContractSpec(sec_type="STK", con_id=CON_ID, symbol="AAA", exchange="SMART")


def _load_tool() -> Any:
    """Charge `tools/run_edge_ibkr.py` — même motif que `test_probe_entitlements.py`."""
    spec = importlib.util.spec_from_file_location("run_edge_ibkr_tool", _TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_ibkr_envelope(event_id: str, *, epoch: int) -> DataEnvelope[Any]:
    """Enveloppe telle que l'adaptateur réel la produit : source et droits IBKR."""
    payload = {"con_id": CON_ID, "bid": "101.25", "ask": "101.30"}
    return DataEnvelope(
        event_id=event_id,
        schema_version="ibkr.quote/1",
        source="ibkr",
        instrument_id=str(CON_ID),
        observed_at=T0,
        received_at=T0,
        as_of=T0,
        stale_after=T0 + timedelta(seconds=60),
        quality_status=EnvelopeQuality.VALID,
        delay_status=DelayStatus.LIVE,
        connection_epoch=epoch,
        rights=REAL_RIGHTS,
        payload_hash=canonical_json_hash(payload),
        payload=payload,
    )


class OneShotPort:
    """Port minimal : un instantané scripté, puis plus rien à faire."""

    def __init__(
        self,
        envelopes: tuple[DataEnvelope[Any], ...],
        *,
        events_during_snapshot: tuple[ProviderStatusEvent, ...] = (),
    ) -> None:
        self._envelopes = envelopes
        self._events_during_snapshot = events_during_snapshot
        self._status_events: list[ProviderStatusEvent] = []
        self.cancelled: list[str] = []

    async def connect(self) -> None:
        return None

    async def disconnect(self) -> None:
        return None

    async def market_data_snapshot(
        self,
        spec: ContractSpec,
        *,
        generic_ticks: tuple[int, ...] = (),
        market_data_type: int = 1,
        timeout_seconds: float | None = None,
    ) -> MarketDataSnapshotResult:
        self._status_events.extend(self._events_during_snapshot)
        return MarketDataSnapshotResult(
            envelopes=self._envelopes,
            provider_errors=(),
            requested_market_data_type=1,
            reported_market_data_type=1,
            generic_ticks=(),
            subscription_id="sub-it",
            operation=OperationToken(
                journal_id="integration-journal",
                connection_epoch_at_start=self._envelopes[0].connection_epoch,
                provider_sequence_at_start=0,
                market_update_sequence_at_start=0,
            ),
            market_update_sequence_at_end=1,
            cancellation_outcome=CancellationOutcome.CANCELLED,
        )

    async def cancel_subscription(
        self, subscription_id: str
    ) -> CancellationOutcome:
        self.cancelled.append(subscription_id)
        return CancellationOutcome.CANCELLED

    def drain_provider_status_events(self) -> tuple[ProviderStatusEvent, ...]:
        events = tuple(self._status_events)
        self._status_events.clear()
        return events

    @property
    def pending_subscription_count(self) -> int:
        return 0


async def _noop_sleep(_delay: float) -> None:
    return None


def run_one_cycle(
    engine: Engine,
    envelopes: tuple[DataEnvelope[Any], ...],
    *,
    events_during_snapshot: tuple[ProviderStatusEvent, ...] = (),
) -> Any:
    """Un cycle complet du VRAI runner, à travers le VRAI puits PostgreSQL."""
    outil = _load_tool()
    runner = EdgeIbkrRunner(
        port=OneShotPort(
            envelopes,
            events_during_snapshot=events_during_snapshot,
        ),
        universe=(SPEC,),
        state=ConnectionStateMachine(rng=random.Random(7)),
        sink=outil.PostgresObservationSink(engine),
        line_budget=LineBudget(4, hard_cap=2),
        pacer=MessagePacer(clock=lambda: 0.0),
        sleep=_noop_sleep,
        poll_seconds=1.0,
        max_cycles=1,
    )
    return asyncio.run(runner.run())


@pytest.mark.usefixtures("clean_database")
def test_une_observation_ibkr_atteint_la_base_avec_sa_provenance(
    migrated_engine: Engine,
) -> None:
    stats = run_one_cycle(migrated_engine, (make_ibkr_envelope("ibkr-evt-1", epoch=1),))
    assert stats.ingested == 1

    with Session(migrated_engine) as session:
        observation = session.scalars(
            select(Observation).where(Observation.event_id == "ibkr-evt-1")
        ).one()
        # La provenance n'est jamais réécrite en SYNTHETIC ni en DEMO.
        assert observation.source == "ibkr"
        assert observation.rights == REAL_RIGHTS
        # L'epoch de connexion est conservé : c'est lui qui rend la fraîcheur
        # vérifiable après une reconnexion.
        assert observation.connection_epoch == 1


@pytest.mark.usefixtures("clean_database")
def test_le_travail_de_fusion_est_mis_en_file(migrated_engine: Engine) -> None:
    """Sans ce message, le worker ne publierait jamais rien : les pages resteraient vides."""
    run_one_cycle(migrated_engine, (make_ibkr_envelope("ibkr-evt-2", epoch=1),))

    with Session(migrated_engine) as session:
        topics = list(
            session.scalars(
                select(OutboxMessage.topic).where(
                    OutboxMessage.topic == TOPIC_OBSERVATION_INGESTED
                )
            )
        )
        assert topics == [TOPIC_OBSERVATION_INGESTED]


@pytest.mark.usefixtures("clean_database")
def test_rejouer_la_meme_observation_n_ecrit_rien_et_n_ajoute_aucun_travail(
    migrated_engine: Engine,
) -> None:
    """Sinon chaque reconnexion dupliquerait le travail de fusion à l'infini.

    On MESURE le delta entre les deux cycles plutôt que de fixer un nombre
    absolu : une observation ingérée déclenche plusieurs travaux en aval
    (`observation.ingested`, mais aussi `review_queue.refresh`), et ce nombre
    appartient au worker, pas à ce test. Ce qui doit être prouvé ici est que le
    second cycle n'ajoute RIEN.
    """
    enveloppe = make_ibkr_envelope("ibkr-evt-3", epoch=1)

    premier = run_one_cycle(migrated_engine, (enveloppe,))
    with Session(migrated_engine) as session:
        observations_apres_1 = session.scalar(select(func.count()).select_from(Observation))
        messages_apres_1 = session.scalar(select(func.count()).select_from(OutboxMessage))

    second = run_one_cycle(migrated_engine, (enveloppe,))
    with Session(migrated_engine) as session:
        observations_apres_2 = session.scalar(select(func.count()).select_from(Observation))
        messages_apres_2 = session.scalar(select(func.count()).select_from(OutboxMessage))

    assert premier.ingested == 1
    assert second.ingested == 0
    assert second.duplicates == 1
    assert observations_apres_1 == 1
    assert messages_apres_1 >= 1
    # Le rejeu n'écrit rien et n'ajoute aucun travail : les deux comptes sont figés.
    assert observations_apres_2 == observations_apres_1
    assert messages_apres_2 == messages_apres_1


@pytest.mark.usefixtures("clean_database")
def test_une_observation_d_un_epoch_perime_n_atteint_jamais_la_base(
    migrated_engine: Engine,
) -> None:
    """Persister un ancien epoch publierait un verdict périmé comme s'il était actuel."""
    stats = run_one_cycle(migrated_engine, (make_ibkr_envelope("ibkr-evt-4", epoch=99),))
    assert stats.stale_epoch == 1
    assert stats.ingested == 0

    with Session(migrated_engine) as session:
        assert session.scalar(select(func.count()).select_from(Observation)) == 0
        assert session.scalar(select(func.count()).select_from(OutboxMessage)) == 0


@pytest.mark.usefixtures("clean_database")
def test_une_perte_de_session_en_vol_n_ecrit_ni_observation_ni_travail(
    migrated_engine: Engine,
) -> None:
    """Une réponse apparemment VALID ne traverse jamais une coupure 1100."""
    event = ProviderStatusEvent(
        journal_id="integration-journal",
        sequence=1,
        code=1100,
        req_id=None,
        received_at=T0,
        message="synthetic connectivity loss",
    )

    stats = run_one_cycle(
        migrated_engine,
        (make_ibkr_envelope("ibkr-evt-session-loss", epoch=1),),
        events_during_snapshot=(event,),
    )

    assert stats.provider_errors == 1
    assert stats.ingested == 0
    with Session(migrated_engine) as session:
        assert session.scalar(select(func.count()).select_from(Observation)) == 0
        assert session.scalar(select(func.count()).select_from(OutboxMessage)) == 0
