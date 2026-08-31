#!/usr/bin/env python3
"""Univers d'ingestion construit depuis les scanners DÉJÀ observés.

CE QUE CETTE COMMANDE RÉSOUT. `universe.py` refuse par construction toute
résolution réseau : un `con_id` absent est un REFUS, jamais une requête. C'est
la bonne règle — mais elle laissait une question sans réponse : *d'où viennent
les `con_id` quand on en veut mille ?* Les relever à la main avec la sonde,
un par un, n'est pas une réponse.

`reqScannerData` la donne. Chaque ligne de scanner porte déjà un `con_id` ET
un `symbol`, calculés chez IBKR sur l'ensemble du marché. Cette commande ne
fait que **relire ce qui est déjà en base** et l'écrire au format d'univers.

AUCUNE REQUÊTE IBKR N'EST ÉMISE ICI. Aucune connexion, aucun `client_id`.
C'est une transformation locale : observations → fichier. La collecte, elle,
appartient à `run_edge_discovery.py`.

CE QU'ELLE REFUSE, ET POURQUOI
------------------------------
- ligne sans `con_id` : sans identité exacte, l'instrument est écarté et
  COMPTÉ. Le symbole seul est ambigu — la sonde a mesuré 32 contrats « GOOG ».
- ligne sans `symbol` : la page Marchés compare un ticker et la dérivation des
  barres l'exige. Un instrument sans symbole entrerait en base pour rester
  invisible.
- `location_code` inconnu : la devise et la place ne sont PAS dans la ligne de
  scanner. Elles sont déduites du périmètre du scan, par la table déclarée
  ci-dessous. Un code absent de cette table est un refus, jamais une
  supposition — écrire USD pour un scan européen fausserait tout l'historique.

USAGE ::

    export VERTEX_DATABASE_URL='postgresql+psycopg://vertex:…@127.0.0.1:5432/vertex_live'
    .venv/bin/python tools/build_universe.py --out "$HOME/.vertex/univers-large.json"

Codes de sortie : ``0`` fin normale, ``2`` configuration invalide ou refus.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
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

from vertex_edge_ibkr.universe import (  # noqa: E402
    MAX_HISTORICAL_UNIVERSE_SIZE,
    parse_universe,
)

#: Périmètres de scan DÉCLARÉS. La ligne de scanner ne porte ni devise ni
#: place ; elles se déduisent du périmètre, et d'aucune autre façon. Ajouter
#: une entrée ici est une décision explicite, pas un effet de bord.
_PERIMETRES: dict[str, tuple[str, str]] = {
    # location_code      : (exchange, currency)
    "STK.US.MAJOR": ("SMART", "USD"),
    "STK.US.MINOR": ("SMART", "USD"),
    "STK.US": ("SMART", "USD"),
}

#: Forme d'un code technique relayable, recopiee de
#: `vertex_api.snapshot_views._CODE_RE`. Un symbole hors de cette forme fait
#: refuser le dossier ENTIER par l'API : mesure le 2026-08-31 avec `GNL PRE`,
#: une action privilegiee IBKR dont l'espace cassait toute la page
#: Opportunites. Le refuser ici coute un instrument ; le laisser passer coute
#: une page.
_SYMBOLE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@/+-]{0,127}$")

#: Seules les observations de scanner sont lues.
_SCHEMA_SCANNER = "ibkr.scanner/"


def _refuser(message: str) -> NoReturn:
    """Refus délibéré : message sur stderr et code de sortie 2."""
    print(f"REFUS: {message}", file=sys.stderr)
    raise SystemExit(2)


def _dsn() -> str:
    valeur = os.environ.get("VERTEX_DATABASE_URL")
    if not valeur:
        _refuser(
            "VERTEX_DATABASE_URL absent. Cette commande ne devine aucune base : "
            "sourcer ~/.vertex/env.live avant de la lancer."
        )
    if "CHANGEME" in valeur or "example" in valeur.lower():
        _refuser("VERTEX_DATABASE_URL porte une valeur d'exemple.")
    if valeur.rstrip("/").endswith("vertex_test") and os.environ.get("VERTEX_ALLOW_TEST_DB") != "1":
        _refuser(
            "VERTEX_DATABASE_URL vise la base de test. Poser VERTEX_ALLOW_TEST_DB=1 "
            "pour l'autoriser explicitement."
        )
    return valeur


def instruments_depuis_scanners(
    charges: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int], list[str]]:
    """Transforme des charges utiles de scanner en entrées d'univers.

    Renvoie ``(instruments, compteurs, refus)``. Rien n'est levé sur une ligne
    isolée : dans un balayage de 200 candidats, une ligne incomplète ne doit
    pas faire perdre les 199 autres. Elle est comptée.
    """
    vus: dict[int, dict[str, Any]] = {}
    compteurs = {
        "lignes": 0,
        "sans_con_id": 0,
        "sans_symbole": 0,
        "symbole_hors_forme": 0,
        "doublons": 0,
    }
    refus: list[str] = []

    for charge in charges:
        code = charge.get("location_code")
        perimetre = _PERIMETRES.get(code) if isinstance(code, str) else None
        if perimetre is None:
            message = (
                f"périmètre inconnu {code!r} : devise et place non déductibles. "
                f"Périmètres déclarés : {sorted(_PERIMETRES)}."
            )
            if message not in refus:
                refus.append(message)
            continue
        exchange, currency = perimetre

        for ligne in charge.get("rows") or []:
            compteurs["lignes"] += 1
            con_id = ligne.get("con_id")
            if not isinstance(con_id, int) or isinstance(con_id, bool) or con_id <= 0:
                compteurs["sans_con_id"] += 1
                continue
            symbole = ligne.get("symbol")
            if not isinstance(symbole, str) or not symbole.strip():
                compteurs["sans_symbole"] += 1
                continue
            if not _SYMBOLE_RE.fullmatch(symbole):
                # Un espace, et l'API refuse de relayer le dossier ENTIER.
                # Mieux vaut perdre cet instrument que la page.
                compteurs["symbole_hors_forme"] += 1
                continue
            if con_id in vus:
                compteurs["doublons"] += 1
                continue
            vus[con_id] = {
                "con_id": con_id,
                "sec_type": charge.get("instrument") or "STK",
                "symbol": symbole,
                "exchange": exchange,
                "currency": currency,
            }

    return list(vus.values()), compteurs, refus


def charger_univers_a_conserver(chemins: list[str]) -> list[dict[str, Any]]:
    """Instruments déclarés à conserver malgré la reconstruction.

    Relus tels quels : ce sont des entrées d'univers déjà valides, pas des
    lignes de scanner. Un fichier absent est un REFUS — le silence ferait
    perdre des instruments sans que personne le sache.
    """
    gardes: list[dict[str, Any]] = []
    for chemin in chemins:
        fichier = Path(chemin).expanduser()
        if not fichier.is_file():
            _refuser(f"--merge {fichier} : fichier introuvable.")
        try:
            document = json.loads(fichier.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as erreur:
            _refuser(f"--merge {fichier} : illisible ({erreur}).")
        entrees = document.get("instruments") if isinstance(document, dict) else None
        if not isinstance(entrees, list):
            _refuser(f"--merge {fichier} : `instruments` doit être une liste.")
        for entree in entrees:
            if isinstance(entree, dict):
                gardes.append(dict(entree))
    return gardes


def _charger_scanners(dsn: str, limite: int) -> list[dict[str, Any]]:
    from sqlalchemy import create_engine, text

    moteur = create_engine(dsn)
    with moteur.connect() as connexion:
        lignes = connexion.execute(
            text(
                "select payload from observations where schema_version like :prefixe"
                " order by as_of desc, id desc limit :limite"
            ),
            {"prefixe": _SCHEMA_SCANNER + "%", "limite": limite},
        ).fetchall()
    return [ligne[0] for ligne in lignes if isinstance(ligne[0], dict)]


def main(argv: list[str] | None = None) -> int:
    analyseur = argparse.ArgumentParser(
        description="Construit un fichier d'univers depuis les scanners observés."
    )
    analyseur.add_argument("--out", required=True, help="fichier d'univers à écrire")
    analyseur.add_argument(
        "--max",
        type=int,
        default=MAX_HISTORICAL_UNIVERSE_SIZE,
        help=f"borne haute (défaut {MAX_HISTORICAL_UNIVERSE_SIZE})",
    )
    analyseur.add_argument(
        "--max-observations",
        type=int,
        default=200,
        help="nombre de charges de scanner relues (défaut 200)",
    )
    analyseur.add_argument(
        "--merge",
        action="append",
        default=[],
        metavar="FICHIER",
        help=(
            "univers à CONSERVER en plus des scanners (répétable). Un classement "
            "change tous les jours : sans cela, chaque reconstruction effacerait "
            "les instruments suivis délibérément."
        ),
    )
    analyseur.add_argument(
        "--force", action="store_true", help="autorise l'écrasement du fichier existant"
    )
    arguments = analyseur.parse_args(argv)

    if arguments.max < 1 or arguments.max > MAX_HISTORICAL_UNIVERSE_SIZE:
        _refuser(f"--max doit rester dans [1, {MAX_HISTORICAL_UNIVERSE_SIZE}].")

    destination = Path(arguments.out).expanduser()
    if destination.exists() and not arguments.force:
        _refuser(
            f"{destination} existe déjà. Ajouter --force pour l'écraser "
            "délibérément — un univers écrasé par accident fait perdre la "
            "correspondance avec l'historique déjà collecté."
        )

    charges = _charger_scanners(_dsn(), arguments.max_observations)
    if not charges:
        _refuser(
            "aucune observation de scanner en base. Lancer d'abord la découverte "
            "(raccourci « 3 - Decouverte scanner ») : cette commande ne "
            "contacte jamais IBKR elle-même."
        )

    decouverts, compteurs, refus = instruments_depuis_scanners(charges)

    # Les instruments déclarés passent EN TÊTE et gagnent sur un doublon du
    # scanner : ce que l'utilisateur a écrit à la main fait autorité.
    conserves = charger_univers_a_conserver(arguments.merge)
    par_con_id: dict[Any, dict[str, Any]] = {}
    for entree in conserves + decouverts:
        par_con_id.setdefault(entree.get("con_id"), entree)
    instruments = list(par_con_id.values())
    compteurs["conserves"] = len(conserves)
    for message in refus:
        print(f"REFUS PARTIEL: {message}", file=sys.stderr)

    if not instruments:
        _refuser(
            "aucun instrument exploitable dans les scanners relus "
            f"({compteurs['lignes']} lignes, {compteurs['sans_con_id']} sans con_id, "
            f"{compteurs['sans_symbole']} sans symbole)."
        )

    tronques = 0
    if len(instruments) > arguments.max:
        tronques = len(instruments) - arguments.max
        instruments = instruments[: arguments.max]

    document = {"instruments": instruments}
    # Relu par le chargeur RÉEL avant écriture : un fichier que l'ingestion
    # refuserait ne doit jamais atteindre le disque.
    parse_universe(document, max_size=arguments.max)

    destination.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    try:
        destination.chmod(0o600)
    except OSError:
        pass

    print(f"univers écrit : {destination}")
    print(f"  instruments retenus  : {len(instruments)}")
    print(f"  lignes examinées     : {compteurs['lignes']}")
    print(f"  écartées sans con_id : {compteurs['sans_con_id']}")
    print(f"  écartées sans symbole: {compteurs['sans_symbole']}")
    print(f"  symbole hors forme   : {compteurs['symbole_hors_forme']}")
    print(f"  doublons fusionnés   : {compteurs['doublons']}")
    print(f"  conservés (--merge)  : {compteurs.get('conserves', 0)}")
    if tronques:
        print(f"  TRONQUÉ : {tronques} instruments au-delà de --max={arguments.max}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
