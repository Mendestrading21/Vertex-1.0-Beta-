#!/usr/bin/env python3
"""Découverte par scanner IBKR — la largeur de marché, sans univers déclaré.

CE QUE CETTE COMMANDE RÉSOUT. Les deux autres régimes exigent des `con_id`
connus d'avance : `run_edge_ibkr.py` pour le temps réel, `run_edge_history.py`
pour la profondeur. Aucun des deux ne répond à « quoi regarder aujourd'hui ? ».
`reqScannerData` le fait : le classement est calculé chez IBKR sur l'ensemble
du marché, et seules les lignes retenues reviennent — au plus 50 par scan.

CE QU'UN CLASSEMENT N'EST PAS. Un déclencheur, jamais un verdict. Il ne porte
ni prix canonique ni décision : il dit seulement quels candidats méritent
d'être regardés. La revalidation appartient aux deux autres régimes — même
frontière que celle imposée aux alertes TradingView (ADR-005).

CLIENT ID DISTINCT. Le défaut est **73** : 71 pour le temps réel, 72 pour
l'historique. Deux clients API partageant un identifiant se déconnectent
mutuellement.

FAIL-CLOSED. DSN depuis l'environnement uniquement, valeur d'exemple refusée,
base de test refusée sans ``VERTEX_ALLOW_TEST_DB=1``, fichier de scans
OBLIGATOIRE, hôte ``127.0.0.1`` en dur, cadence d'un scan par seconde tenue par
attente — jamais par contournement.

FRONTIÈRE FINANCIÈRE. ``scanner_run`` est le seul appel utilisé.

USAGE ::

    export VERTEX_DATABASE_URL='postgresql+psycopg://vertex:…@127.0.0.1:5432/vertex'
    export VERTEX_IBKR_SCANS="$HOME/.vertex/scans.json"
    export VERTEX_IBKR_PORT=7497
    .venv/bin/python tools/run_edge_discovery.py

Format du fichier de scans ::

    {"scans": [
      {"instrument": "STK", "location_code": "STK.US.MAJOR",
       "scan_code": "TOP_PERC_GAIN", "number_of_rows": 50}
    ]}

Codes de sortie : ``0`` fin normale, ``2`` configuration invalide ou refus.
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
from vertex_edge_ibkr.discovery import (  # noqa: E402
    DEFAULT_SCAN_WINDOW_SECONDS,
    DEFAULT_SCANS_PER_WINDOW,
    ScanDefinitionError,
    ScannerDiscovery,
    load_scan_definitions,
)
from vertex_edge_ibkr.pacing import LineBudget, SlidingWindowPacer  # noqa: E402
from vertex_edge_ibkr.state import ConnectionStateMachine  # noqa: E402
from vertex_persistence.dsn import database_name  # noqa: E402
from vertex_worker.ingest import ingest_envelope  # noqa: E402

__all__ = ["main"]

log = logging.getLogger("vertex_edge_discovery")

_EXAMPLE_MARKERS = ("CHANGE_ME", "change_me", "example", "placeholder")
_TEST_DATABASE_MARKERS = ("_test", "test_", "vertex_test", "vertex_e2e")

#: 71 = temps réel, 72 = historique, 73 = découverte.
DEFAULT_CLIENT_ID = 73
DEFAULT_TWS_PORT = 7497

#: Un scan à la fois : la ligne est prise puis relâchée immédiatement.
MAX_CONCURRENT_LINES = 1


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
            "VERTEX_DATABASE_URL absent. La découverte ne devine aucune base : "
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


def _require_scans_path() -> Path:
    brut = os.environ.get("VERTEX_IBKR_SCANS", "").strip()
    if not brut:
        _refuser(
            "VERTEX_IBKR_SCANS absent. La découverte n'invente AUCUN scan par "
            "défaut : fournir le chemin d'un fichier JSON de définitions "
            "(voir docs/08-runbooks/IBKR_SETUP.md)."
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


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("VERTEX_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    url = _require_database_url()
    chemin_scans = _require_scans_path()
    port_tws = _positive_int("VERTEX_IBKR_PORT", DEFAULT_TWS_PORT)
    client_id = _positive_int("VERTEX_IBKR_DISCOVERY_CLIENT_ID", DEFAULT_CLIENT_ID)

    try:
        definitions = load_scan_definitions(chemin_scans)
    except ScanDefinitionError as erreur:
        _refuser(f"scans refusés : {erreur}")

    state = ConnectionStateMachine(rng=random.SystemRandom())
    adapter = IbAsyncInformationAdapter(port=port_tws, client_id=client_id, state=state)
    engine = create_engine(url, pool_pre_ping=True)

    decouverte = ScannerDiscovery(
        port=adapter,
        definitions=definitions,
        sink=PostgresObservationSink(engine),
        pacer=SlidingWindowPacer(
            max_requests=DEFAULT_SCANS_PER_WINDOW,
            window_seconds=DEFAULT_SCAN_WINDOW_SECONDS,
            clock=_monotonic,
        ),
        line_budget=LineBudget(MAX_CONCURRENT_LINES * 2, hard_cap=MAX_CONCURRENT_LINES),
        sleep=asyncio.sleep,
    )

    def _demander_arret(signum: int, _frame: FrameType | None) -> None:
        log.info("signal %s reçu — arrêt après le scan en cours", signal.Signals(signum).name)
        decouverte.request_stop()

    signal.signal(signal.SIGTERM, _demander_arret)
    signal.signal(signal.SIGINT, _demander_arret)

    log.info(
        "découverte par scanner : 127.0.0.1:%d, client_id=%d, %d scan(s), "
        "au plus 50 lignes par scan, une ligne de données à la fois",
        port_tws,
        client_id,
        len(definitions),
    )
    log.warning(
        "Un classement de scanner est un DÉCLENCHEUR, jamais un verdict : ni prix "
        "canonique, ni décision. Revalidation obligatoire par les autres régimes."
    )

    async def _session() -> Any:
        await adapter.connect()
        try:
            return await decouverte.run()
        finally:
            await adapter.disconnect()

    try:
        stats = asyncio.run(_session())
    finally:
        engine.dispose()

    log.info(
        "terminé — scans=%d insérés=%d doublons=%d attentes=%d "
        "erreurs_fournisseur=%d notices=%d transport=%d",
        stats.scans,
        stats.ingested,
        stats.duplicates,
        stats.deferred,
        stats.provider_errors,
        stats.notices,
        stats.transport_errors,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
