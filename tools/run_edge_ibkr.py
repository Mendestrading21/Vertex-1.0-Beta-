#!/usr/bin/env python3
"""Ingestion IBKR continue, read-only — la commande de démarrage live qui manquait.

POURQUOI CE FICHIER EST DANS `tools/` ET NON DANS LE PAQUET. Le premier essai
plaçait ce point d'entrée dans `vertex_edge_ibkr/__main__.py`, ce qui exigeait
d'ajouter `vertex-persistence` et `vertex-worker` aux dépendances de
`apps/edge-ibkr`. Mesuré sur le verrou : cette arête tirait SQLAlchemy, numpy et
scipy dans la fermeture d'un adaptateur IBKR censé rester mince, et changeait
`uv.lock` bien au-delà de l'intention (8 wheels `greenlet` retirées, marqueurs
`python_full_version` de scipy effondrés). `tools/probe_entitlements.py` avait
déjà résolu exactement ce problème : amorcer `sys.path` depuis la racine du
dépôt. On reprend ce motif — zéro dépendance ajoutée, zéro changement de verrou,
et `runner.py` reste découplé derrière `ObservationSink`.

CE QU'IL FAIT. Il fait tourner le VRAI `EdgeIbkrRunner` contre TWS sur la boucle
locale et écrit dans le MÊME chemin de persistance que le reste de Vertex :
`ingest_envelope` insère l'observation et met le travail de fusion en file ; le
worker existant publie les instantanés. Aucun code de publication dupliqué.

FAIL-CLOSED PAR CONSTRUCTION
----------------------------
- le DSN vient de l'environnement UNIQUEMENT — jamais d'un fichier du dépôt ;
- une valeur d'exemple (``CHANGE_ME``…) interrompt le démarrage ;
- une base au nom de test exige ``VERTEX_ALLOW_TEST_DB=1`` ;
- l'univers d'abonnement est OBLIGATOIRE et entièrement explicite : sans
  fichier, aucun instrument n'est deviné et le processus refuse de démarrer ;
- l'hôte est ``127.0.0.1`` EN DUR. Aucune option, aucune variable d'environnement
  ne permet d'en changer : ne pas offrir le réglage est plus fort que de le
  valider.

FRONTIÈRE FINANCIÈRE. Aucune capacité compte, position, P&L, ordre, exécution,
exercice ou ``whatIfOrder``. Le port ne les expose pas et
``tools/check_financial_boundary.py`` balaie ce fichier comme les autres.

USAGE ::

    export VERTEX_DATABASE_URL='postgresql+psycopg://vertex:…@127.0.0.1:5432/vertex'
    export VERTEX_IBKR_UNIVERSE="$HOME/.vertex/univers.json"
    export VERTEX_IBKR_PORT=7497          # port CONFIRMÉ dans TWS
    .venv/bin/python tools/run_edge_ibkr.py

Codes de sortie : ``0`` arrêt propre, ``2`` configuration invalide ou refus.
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

# src-layout : sans cela, aucun paquet du dépôt n'est importable depuis un
# script de `tools/` exécuté par `python` nu (le cas du runbook).
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
from vertex_edge_ibkr.pacing import (  # noqa: E402
    DEFAULT_MESSAGES_PER_SECOND,
    LineBudget,
    MessagePacer,
)
from vertex_edge_ibkr.runner import EdgeIbkrRunner  # noqa: E402
from vertex_edge_ibkr.state import ConnectionStateMachine  # noqa: E402
from vertex_edge_ibkr.universe import UniverseError, load_universe  # noqa: E402
from vertex_persistence.dsn import database_name  # noqa: E402
from vertex_worker.ingest import ingest_envelope  # noqa: E402

__all__ = ["main"]

log = logging.getLogger("vertex_edge_ibkr")

#: Valeurs d'exemple de `.env.example` : les accepter reviendrait à démarrer sur
#: une configuration fictive en croyant être en production.
_EXAMPLE_MARKERS = ("CHANGE_ME", "change_me", "example", "placeholder")

_TEST_DATABASE_MARKERS = ("_test", "test_", "vertex_test", "vertex_e2e")

#: Plafond LOCAL et volontairement conservateur de lignes de données
#: simultanées. Ce n'est PAS une mesure du droit réel du compte : Vertex ne
#: connaît pas ce nombre et ne l'invente pas. Le runner n'ouvre qu'une ligne à
#: la fois ; ce plafond garantit qu'un défaut de code ne peut pas en ouvrir dix.
#: L'élever exige de MESURER l'allocation réelle, jamais de la supposer.
DEFAULT_MAX_CONCURRENT_LINES = 2

DEFAULT_POLL_SECONDS = 60.0
DEFAULT_TWS_PORT = 7497
DEFAULT_CLIENT_ID = 71


def _refuser(message: str) -> NoReturn:
    """Refus delibere : message sur stderr et code de sortie 2.

    `raise SystemExit("texte")` sort en 1, pas en 2 : la valeur passee devient
    le message et Python retient 1. La convention du depot
    (`bootstrap_local.py`, `probe_entitlements.py`) reserve 2 a « configuration
    invalide ou refus delibere ». On imprime donc soi-meme, puis on sort en 2.
    """
    print(f"REFUS: {message}", file=sys.stderr)
    raise SystemExit(2)


class PostgresObservationSink:
    """Puits réel : une transaction par lot, le worker publie ensuite.

    Rend ``(insérées, doublons)``. Une enveloppe déjà connue par son
    ``event_id`` n'écrase rien et n'ajoute aucun travail — les observations
    sont des faits en ajout seul.
    """

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
            "VERTEX_DATABASE_URL absent. L'ingestion ne devine aucune base : "
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
            "VERTEX_IBKR_UNIVERSE absent. L'ingestion n'abonne AUCUN instrument par "
            "défaut : fournir le chemin d'un fichier d'univers JSON dont chaque "
            "entrée porte un con_id exact (voir docs/08-runbooks/IBKR_SETUP.md)."
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


def _positive_float(name: str, default: float) -> float:
    brut = os.environ.get(name, "").strip()
    if not brut:
        return default
    try:
        valeur = float(brut)
    except ValueError:
        _refuser(f"{name} doit être un nombre, reçu {brut!r}.")
    if valeur <= 0:
        _refuser(f"{name} doit être strictement positif, reçu {valeur}.")
    return valeur


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("VERTEX_LOG_LEVEL", "INFO"),
        # Journal structuré minimal : ni secret, ni DSN, ni charge utile.
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    url = _require_database_url()
    chemin_univers = _require_universe_path()
    port_tws = _positive_int("VERTEX_IBKR_PORT", DEFAULT_TWS_PORT)
    client_id = _positive_int("VERTEX_IBKR_CLIENT_ID", DEFAULT_CLIENT_ID)
    lignes_max = _positive_int("VERTEX_IBKR_MAX_LINES", DEFAULT_MAX_CONCURRENT_LINES)
    poll = _positive_float("VERTEX_IBKR_POLL_SECONDS", DEFAULT_POLL_SECONDS)

    try:
        univers = load_universe(chemin_univers)
    except UniverseError as erreur:
        _refuser(f"univers refusé : {erreur}")

    state = ConnectionStateMachine(rng=random.SystemRandom())
    adapter = IbAsyncInformationAdapter(port=port_tws, client_id=client_id, state=state)
    engine = create_engine(url, pool_pre_ping=True)

    runner = EdgeIbkrRunner(
        port=adapter,
        universe=univers,
        state=state,
        sink=PostgresObservationSink(engine),
        # `detected_lines` n'est PAS une mesure du droit réel du compte : c'est
        # le plafond dur ci-dessous qui contraint, et il reste volontairement bas.
        line_budget=LineBudget(lignes_max * 2, hard_cap=lignes_max),
        pacer=MessagePacer(
            messages_per_second=DEFAULT_MESSAGES_PER_SECOND,
            # Horloge MONOTONE en secondes, comme `probe.py`.
            clock=_monotonic,
        ),
        sleep=asyncio.sleep,
        poll_seconds=poll,
    )

    def _demander_arret(signum: int, _frame: FrameType | None) -> None:
        log.info("signal %s reçu — arrêt après le cycle en cours", signal.Signals(signum).name)
        runner.request_stop()

    signal.signal(signal.SIGTERM, _demander_arret)
    signal.signal(signal.SIGINT, _demander_arret)

    log.info(
        "ingestion IBKR read-only : 127.0.0.1:%d, client_id=%d, %d instrument(s), "
        "cycle %.0f s, %d ligne(s) simultanée(s) au maximum",
        port_tws,
        client_id,
        len(univers),
        poll,
        lignes_max,
    )
    log.warning(
        "AUCUNE capacité compte, position, P&L, ordre ou exécution n'est utilisée. "
        "Read-Only API doit rester activé dans TWS."
    )

    try:
        stats = asyncio.run(runner.run())
    finally:
        engine.dispose()

    log.info(
        "arrêt — cycles=%d requêtes=%d insérées=%d doublons=%d epoch_périmé=%d "
        "lignes_refusées=%d file_refusée=%d erreurs_fournisseur=%d transport=%d "
        "reconnexions=%d",
        stats.cycles,
        stats.requested,
        stats.ingested,
        stats.duplicates,
        stats.stale_epoch,
        stats.line_refused,
        stats.queue_refused,
        stats.provider_errors,
        stats.transport_errors,
        stats.reconnects,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
