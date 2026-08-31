#!/usr/bin/env python3
"""Remplissage historique IBKR — la profondeur, sur des milliers de titres.

CE QUE CETTE COMMANDE FAIT, ET QUE `run_edge_ibkr.py` NE FAIT PAS.
`run_edge_ibkr.py` couvre le TEMPS RÉEL et reste limité à quelques dizaines
d'instruments : chaque abonnement consomme une ligne de données, et IBKR n'en
accorde qu'une centaine. Cette commande-ci utilise `reqHistoricalData`, qui ne
consomme AUCUNE ligne mais obéit à un pacing propre : 60 requêtes par fenêtre
glissante de 10 minutes, soit ~6/min. Des milliers de titres sont donc
possibles — en heures, pas en secondes. Environ 2 h 50 pour mille.

CLIENT ID DISTINCT. Le défaut est **72**, pas 71. Deux clients API partageant
le même identifiant se déconnectent mutuellement : faire tourner ce
remplissage en même temps que l'ingestion temps réel exige deux identifiants.

FAIL-CLOSED PAR CONSTRUCTION
----------------------------
- DSN depuis l'environnement UNIQUEMENT, valeur d'exemple refusée, base de
  test refusée sans ``VERTEX_ALLOW_TEST_DB=1`` ;
- univers OBLIGATOIRE, chaque entrée portant un ``con_id`` exact ;
- hôte ``127.0.0.1`` EN DUR, aucune option pour en changer ;
- quand la fenêtre de pacing est pleine, le processus ATTEND. Il ne force
  jamais le passage : un dépassement produit un refus IBKR, pas de la vitesse.

FRONTIÈRE FINANCIÈRE. Aucune capacité compte, position, P&L, ordre ou
exécution. ``historical_bars`` est le seul appel utilisé.

USAGE ::

    export VERTEX_DATABASE_URL='postgresql+psycopg://vertex:…@127.0.0.1:5432/vertex'
    export VERTEX_IBKR_UNIVERSE="$HOME/.vertex/univers-large.json"
    export VERTEX_IBKR_PORT=7497
    .venv/bin/python tools/run_edge_history.py

Codes de sortie : ``0`` fin normale ou arrêt propre, ``2`` configuration
invalide ou refus délibéré.
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
import signal
import sys
from collections.abc import Sequence
from pathlib import Path
from time import monotonic as _monotonic
from types import FrameType
from typing import Any, NoReturn

REPO_ROOT = Path(__file__).resolve().parents[1]

for _package in (
    "packages/python/vertex_core/src",
    "packages/python/vertex_persistence/src",
    "apps/edge-ibkr/src",
    "apps/worker/src",
):
    _path = str(REPO_ROOT / _package)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from sqlalchemy import create_engine  # noqa: E402 - après l'amorçage du sys.path
from sqlalchemy.orm import Session  # noqa: E402

from vertex_core.contracts import DataEnvelope  # noqa: E402
from vertex_edge_ibkr.adapter import IbAsyncInformationAdapter  # noqa: E402
from vertex_edge_ibkr.history import HistoryBackfiller  # noqa: E402
from vertex_edge_ibkr.pacing import (  # noqa: E402
    DEFAULT_HISTORICAL_REQUESTS_PER_WINDOW,
    DEFAULT_HISTORICAL_WINDOW_SECONDS,
    SlidingWindowPacer,
)
from vertex_edge_ibkr.state import ConnectionStateMachine  # noqa: E402
from vertex_edge_ibkr.universe import (  # noqa: E402
    MAX_HISTORICAL_UNIVERSE_SIZE,
    UniverseError,
    load_universe,
)
from vertex_persistence.dsn import database_name  # noqa: E402
from vertex_worker.ingest import ingest_envelope  # noqa: E402

__all__ = ["main"]

log = logging.getLogger("vertex_edge_history")

_EXAMPLE_MARKERS = ("CHANGE_ME", "change_me", "example", "placeholder")
_TEST_DATABASE_MARKERS = ("_test", "test_", "vertex_test", "vertex_e2e")

#: Client ID distinct de celui de l'ingestion temps réel (71) : deux clients
#: API portant le même identifiant se déconnectent l'un l'autre.
DEFAULT_CLIENT_ID = 72
DEFAULT_TWS_PORT = 7497
DEFAULT_DURATION = "1 Y"
DEFAULT_BAR_SIZE = "1 day"
DEFAULT_WHAT_TO_SHOW = "TRADES"


def _refuser(message: str) -> NoReturn:
    """Refus délibéré : message sur stderr et code de sortie 2."""
    print(f"REFUS: {message}", file=sys.stderr)
    raise SystemExit(2)


class PostgresObservationSink:
    """Puits réel : une transaction par lot, le worker publie ensuite."""

    def __init__(self, engine: Any) -> None:
        self._engine = engine

    def __call__(self, envelopes: Sequence[DataEnvelope[Any]]) -> tuple[int, int]:
        inserees = 0
        doublons = 0
        with Session(self._engine) as session:
            for enveloppe in envelopes:
                resultat = ingest_envelope(session, enveloppe)
                if resultat.inserted:
                    inserees += 1
                else:
                    doublons += 1
            session.commit()
        return inserees, doublons


def _require_database_url() -> str:
    url = os.environ.get("VERTEX_DATABASE_URL", "").strip()
    if not url:
        _refuser(
            "VERTEX_DATABASE_URL absent. Le remplissage ne devine aucune base : "
            "définir la variable d'environnement avant de démarrer."
        )
    if any(marker in url for marker in _EXAMPLE_MARKERS):
        _refuser(
            "VERTEX_DATABASE_URL porte une valeur d'exemple. Refus de démarrer "
            "sur une configuration fictive."
        )
    base = database_name(url)
    if any(marker in base for marker in _TEST_DATABASE_MARKERS):
        if os.environ.get("VERTEX_ALLOW_TEST_DB") != "1":
            _refuser(
                f"La base « {base} » ressemble à une base de test. Pour l'utiliser "
                "volontairement, définir VERTEX_ALLOW_TEST_DB=1."
            )
    return url


def _require_universe_path() -> Path:
    brut = os.environ.get("VERTEX_IBKR_UNIVERSE", "").strip()
    if not brut:
        _refuser(
            "VERTEX_IBKR_UNIVERSE absent. Le remplissage n'invente AUCUN instrument : "
            "fournir le chemin d'un fichier d'univers JSON dont chaque entrée porte "
            "un con_id exact (voir docs/08-runbooks/IBKR_SETUP.md)."
        )
    return Path(brut).expanduser()


def _positive_int(name: str, default: int) -> int:
    brut = os.environ.get(name, "").strip()
    if not brut:
        return default
    try:
        valeur = int(brut)
    except ValueError:
        _refuser(f"{name} doit être un entier, reçu {brut!r}.")
    if valeur <= 0:
        _refuser(f"{name} doit être strictement positif, reçu {valeur}.")
    return valeur


def _text(name: str, default: str) -> str:
    return os.environ.get(name, "").strip() or default


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("VERTEX_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    url = _require_database_url()
    chemin_univers = _require_universe_path()
    port_tws = _positive_int("VERTEX_IBKR_PORT", DEFAULT_TWS_PORT)
    client_id = _positive_int("VERTEX_IBKR_HISTORY_CLIENT_ID", DEFAULT_CLIENT_ID)
    duration = _text("VERTEX_IBKR_HISTORY_DURATION", DEFAULT_DURATION)
    bar_size = _text("VERTEX_IBKR_HISTORY_BAR_SIZE", DEFAULT_BAR_SIZE)
    what_to_show = _text("VERTEX_IBKR_HISTORY_WHAT", DEFAULT_WHAT_TO_SHOW)

    try:
        univers = load_universe(chemin_univers, max_size=MAX_HISTORICAL_UNIVERSE_SIZE)
    except UniverseError as erreur:
        _refuser(f"univers refusé : {erreur}")

    state = ConnectionStateMachine(rng=random.SystemRandom())
    adapter = IbAsyncInformationAdapter(port=port_tws, client_id=client_id, state=state)
    engine = create_engine(url, pool_pre_ping=True)

    backfiller = HistoryBackfiller(
        port=adapter,
        universe=univers,
        sink=PostgresObservationSink(engine),
        pacer=SlidingWindowPacer(
            max_requests=DEFAULT_HISTORICAL_REQUESTS_PER_WINDOW,
            window_seconds=DEFAULT_HISTORICAL_WINDOW_SECONDS,
            clock=_monotonic,
        ),
        sleep=asyncio.sleep,
        duration=duration,
        bar_size=bar_size,
        what_to_show=what_to_show,
    )

    def _demander_arret(signum: int, _frame: FrameType | None) -> None:
        log.info(
            "signal %s reçu — arrêt après la requête en cours",
            signal.Signals(signum).name,
        )
        backfiller.request_stop()

    signal.signal(signal.SIGTERM, _demander_arret)
    signal.signal(signal.SIGINT, _demander_arret)

    heures = len(univers) / 6.0 / 60.0
    log.info(
        "remplissage historique : 127.0.0.1:%d, client_id=%d, %d instrument(s), "
        "%s / %s / %s — durée attendue ~%.1f h au rythme IBKR de 6 requêtes/min",
        port_tws,
        client_id,
        len(univers),
        duration,
        bar_size,
        what_to_show,
        heures,
    )
    log.warning(
        "AUCUNE capacité compte, position, P&L, ordre ou exécution n'est utilisée. "
        "Ce régime ne consomme AUCUNE ligne de données de marché."
    )

    async def _session() -> Any:
        await adapter.connect()
        try:
            return await backfiller.run()
        finally:
            await adapter.disconnect()

    try:
        stats = asyncio.run(_session())
    finally:
        engine.dispose()

    log.info(
        "terminé — demandées=%d insérées=%d doublons=%d attentes=%d (%.0f s cumulées) "
        "erreurs_fournisseur=%d notices=%d transport=%d",
        stats.requested,
        stats.ingested,
        stats.duplicates,
        stats.deferred,
        stats.waited_seconds,
        stats.provider_errors,
        stats.notices,
        stats.transport_errors,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
