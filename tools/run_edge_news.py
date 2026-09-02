#!/usr/bin/env python3
"""Collecte de dépêches IBKR — ce qui remplit la page Aujourd'hui.

CE QUE CETTE COMMANDE RÉSOUT. Mesuré le 2026-09-01 : la file d'attention
considérait 500 observations et en classait ZÉRO. Elle fusionne des
observations de CONTENU — celles qui portent un titre — et une barre de prix
n'en a pas. Le cockpit était vide parce que Vertex ne collectait aucune
actualité, alors que le compte a droit à huit fournisseurs (Dow Jones,
Briefing.com) et que l'adaptateur sait les lire depuis toujours.

UN FOURNISSEUR À LA FOIS. Mesuré en direct : interroger cinq fournisseurs en
un appel rend `reqHistoricalNewsAsync: Timeout` et zéro dépêche ; les
interroger séparément rend vingt dépêches chacun. Le regroupement n'est donc
pas une optimisation, c'est une panne silencieuse.

CLIENT ID DISTINCT. Le défaut est **79** : 71 temps réel, 72 historique,
73 découverte. Deux clients API partageant un identifiant se déconnectent
mutuellement.

FAIL-CLOSED. DSN depuis l'environnement uniquement, valeur d'exemple refusée,
base de test refusée sans ``VERTEX_ALLOW_TEST_DB=1``, univers OBLIGATOIRE,
hôte ``127.0.0.1`` en dur, cadence tenue par attente.

FRONTIÈRE FINANCIÈRE. ``news_providers`` et ``news_headlines`` sont les seuls
appels utilisés. Aucune capacité compte, position, ordre ou exécution.

USAGE ::

    export VERTEX_DATABASE_URL='postgresql+psycopg://vertex:…@127.0.0.1:5432/vertex_live'
    export VERTEX_IBKR_UNIVERSE="$HOME/.vertex/univers-large.json"
    export VERTEX_IBKR_PORT=7496
    .venv/bin/python tools/run_edge_news.py

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
from types import FrameType
from typing import Any, NoReturn

_RACINE = Path(__file__).resolve().parent.parent
for _chemin in (
    "apps/edge-ibkr/src",
    "apps/worker/src",
    "packages/python/vertex_core/src",
    "packages/python/vertex_persistence/src",
):
    _complet = str(_RACINE / _chemin)
    if _complet not in sys.path:
        sys.path.insert(0, _complet)

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from vertex_core.contracts import DataEnvelope  # noqa: E402
from vertex_edge_ibkr.adapter import IbAsyncInformationAdapter  # noqa: E402
from vertex_edge_ibkr.news import news_headline_envelopes  # noqa: E402
from vertex_edge_ibkr.port import EdgeIbkrError  # noqa: E402
from vertex_edge_ibkr.state import ConnectionStateMachine  # noqa: E402
from vertex_edge_ibkr.universe import (  # noqa: E402
    MAX_HISTORICAL_UNIVERSE_SIZE,
    UniverseError,
    load_universe,
)
from vertex_persistence.dsn import database_name  # noqa: E402
from vertex_worker.ingest import ingest_envelope  # noqa: E402

log = logging.getLogger("vertex_edge_news")

_EXAMPLE_MARKERS = ("CHANGEME", "example", "EXAMPLE")
_TEST_DATABASE_MARKERS = ("_test", "-test")

#: Nombre de dépêches demandées par instrument et par fournisseur. IBKR
#: plafonne à 300 ; 20 suffisent à alimenter une file d'attention et gardent
#: la collecte courte.
DEFAULT_MAX_HEADLINES = 20

#: Secondes entre deux appels. La presse n'a pas la fenêtre glissante stricte
#: de l'historique, mais un rythme régulier évite de déclencher le contrôle
#: de cadence d'IBKR.
DEFAULT_DELAY_SECONDS = 1.0


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
                if ingest_envelope(session, enveloppe).inserted:
                    inserees += 1
                else:
                    doublons += 1
            session.commit()
        return inserees, doublons


def _require_database_url() -> str:
    url = os.environ.get("VERTEX_DATABASE_URL", "").strip()
    if not url:
        _refuser(
            "VERTEX_DATABASE_URL absent. La collecte ne devine aucune base : "
            "définir la variable d'environnement avant de démarrer."
        )
    if any(marqueur in url for marqueur in _EXAMPLE_MARKERS):
        _refuser("VERTEX_DATABASE_URL porte une valeur d'exemple.")
    base = database_name(url)
    if any(marqueur in base for marqueur in _TEST_DATABASE_MARKERS):
        if os.environ.get("VERTEX_ALLOW_TEST_DB") != "1":
            _refuser(
                f"La base « {base} » ressemble à une base de test. Poser "
                "VERTEX_ALLOW_TEST_DB=1 pour l'utiliser volontairement."
            )
    return url


def _require_universe_path() -> Path:
    brut = os.environ.get("VERTEX_IBKR_UNIVERSE", "").strip()
    if not brut:
        _refuser(
            "VERTEX_IBKR_UNIVERSE absent. Aucun instrument par défaut n'est "
            "choisi : la collecte ne décide pas de ce que vous suivez."
        )
    chemin = Path(brut).expanduser()
    if not chemin.is_file():
        _refuser(f"univers introuvable : {chemin}")
    return chemin


def _positive_int(nom: str, defaut: int) -> int:
    brut = os.environ.get(nom, "").strip()
    if not brut:
        return defaut
    try:
        valeur = int(brut)
    except ValueError:
        _refuser(f"{nom} : entier attendu, reçu {brut!r}.")
    if valeur < 1:
        _refuser(f"{nom} : entier strictement positif requis, reçu {valeur}.")
    return valeur


async def _collecter(
    adaptateur: IbAsyncInformationAdapter,
    univers: Sequence[Any],
    puits: PostgresObservationSink,
    *,
    max_headlines: int,
    delai: float,
    arret: asyncio.Event,
) -> dict[str, int]:
    compteurs = {
        "instruments": 0,
        "appels": 0,
        "depechees": 0,
        "inserees": 0,
        "doublons": 0,
        "ecartees": 0,
        "erreurs": 0,
    }

    enveloppe_fournisseurs = await adaptateur.news_providers()
    fournisseurs = tuple(
        code
        for code in (
            getattr(f, "code", None) or getattr(f, "provider_code", None)
            for f in (getattr(enveloppe_fournisseurs.payload, "providers", None) or ())
        )
        if isinstance(code, str) and code
    )
    if not fournisseurs:
        log.warning(
            "aucun fournisseur de presse autorisé — réponse VIDE, ce qui est "
            "INCONCLUSIF et jamais une preuve d'absence de droit"
        )
        return compteurs
    log.info("fournisseurs autorisés : %s", ", ".join(fournisseurs))

    for spec in univers:
        if arret.is_set():
            break
        if spec.con_id is None or spec.con_id <= 0:
            continue
        compteurs["instruments"] += 1

        for code in fournisseurs:
            if arret.is_set():
                break
            # UN fournisseur à la fois : le regroupement rend un timeout et
            # zéro dépêche, mesuré le 2026-09-01.
            try:
                enveloppe = await adaptateur.news_headlines(
                    spec.con_id, (code,), max_results=max_headlines
                )
            except (EdgeIbkrError, OSError, TimeoutError) as erreur:
                compteurs["erreurs"] += 1
                log.warning(
                    "erreur de transport (%s) sur con_id %s / %s",
                    type(erreur).__name__,
                    spec.con_id,
                    code,
                )
                continue
            compteurs["appels"] += 1

            derivees, resultat = news_headline_envelopes(
                enveloppe, enveloppe.payload, spec
            )
            compteurs["depechees"] += resultat.produced
            compteurs["ecartees"] += resultat.skipped
            if derivees:
                inserees, doublons = puits(derivees)
                compteurs["inserees"] += inserees
                compteurs["doublons"] += doublons
            await asyncio.sleep(delai)

    return compteurs


async def _principal() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    url = _require_database_url()
    chemin_univers = _require_universe_path()
    port_tws = _positive_int("VERTEX_IBKR_PORT", 7497)
    client_id = _positive_int("VERTEX_IBKR_CLIENT_ID", 79)
    max_headlines = _positive_int("VERTEX_IBKR_MAX_HEADLINES", DEFAULT_MAX_HEADLINES)

    try:
        univers = load_universe(chemin_univers, max_size=MAX_HISTORICAL_UNIVERSE_SIZE)
    except UniverseError as erreur:
        _refuser(f"univers refusé : {erreur}")

    log.info(
        "collecte de dépêches : 127.0.0.1:%s, client_id=%s, %s instrument(s), "
        "%s dépêches par instrument et par fournisseur",
        port_tws,
        client_id,
        len(univers),
        max_headlines,
    )
    log.warning(
        "AUCUNE capacité compte, position, P&L, ordre ou exécution n'est utilisée."
    )

    etat = ConnectionStateMachine(rng=random.SystemRandom())
    adaptateur = IbAsyncInformationAdapter(
        port=port_tws, client_id=client_id, state=etat
    )
    moteur = create_engine(url, pool_pre_ping=True)
    arret = asyncio.Event()

    def _demander_arret(signum: int, _frame: FrameType | None) -> None:
        log.info("signal %s reçu — arrêt après la requête en cours", signum)
        arret.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _demander_arret)

    await adaptateur.connect()
    try:
        compteurs = await _collecter(
            adaptateur,
            univers,
            PostgresObservationSink(moteur),
            max_headlines=max_headlines,
            delai=DEFAULT_DELAY_SECONDS,
            arret=arret,
        )
    finally:
        await adaptateur.disconnect()

    log.info(
        "terminé — instruments=%d appels=%d dépêches=%d insérées=%d doublons=%d "
        "écartées=%d erreurs=%d",
        compteurs["instruments"],
        compteurs["appels"],
        compteurs["depechees"],
        compteurs["inserees"],
        compteurs["doublons"],
        compteurs["ecartees"],
        compteurs["erreurs"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_principal()))
