#!/usr/bin/env python3
"""Premier démarrage : prépare une base locale pour que Vertex soit AFFICHABLE.

POURQUOI CE SCRIPT EXISTE. La pile complète — migrations Alembic réelles,
ingestion par le vrai worker, API FastAPI, interface — démarrait déjà 402 fois
par jour, mais uniquement depuis l'échafaudage Playwright
(`apps/web/e2e/global.setup.ts`), sur `VERTEX_TEST_DATABASE_URL`, et précédée
d'un `DROP SCHEMA`. Autrement dit : le produit se lançait en CI et **jamais
pour son utilisateur**. `docs/08-runbooks/START_LOCAL.md` disait d'ailleurs
« ne pas inventer de commandes » et renvoyait au LOT-24.

Ce script est la moitié manquante. Il ne réimplémente rien : il appelle les
mêmes migrations et le même semis que la campagne E2E, dont le propriétaire
unique est `vertex_worker.demo_seed`.

CE QU'IL NE FAIT JAMAIS
-----------------------
- Il ne détruit AUCUN schéma. La destruction appartient aux fixtures de test,
  sur base jetable. Ici, la base peut contenir le journal de l'utilisateur.
- Il ne devine aucune base : la résolution du DSN passe par
  `vertex_persistence.dsn.resolve_migration_url`, fail-closed, qui refuse déjà
  une base de test implicite.
- Il ne contacte ni IBKR, ni TradingView, ni aucune source. La population de
  démonstration est SYNTHETIC de bout en bout et le reste jusqu'à l'écran.

USAGE
-----
    export VERTEX_DATABASE_URL='postgresql+psycopg://vertex:…@127.0.0.1:5432/vertex'
    python3 tools/bootstrap_local.py                    # migrations seules
    python3 tools/bootstrap_local.py --with-demo-data   # + population SYNTHETIC

Codes de sortie : ``0`` succès, ``2`` configuration invalide ou refus délibéré.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# src-layout : sans cela, aucun paquet du dépôt n'est importable depuis un
# script de `tools/` exécuté par `python3` nu (le cas du runbook).
for _package in (
    "packages/python/vertex_core/src",
    "packages/python/vertex_persistence/src",
    "apps/worker/src",
):
    _path = str(REPO_ROOT / _package)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from alembic import command  # noqa: E402 - après l'amorçage du sys.path
from alembic.config import Config  # noqa: E402
from sqlalchemy import Engine, create_engine, inspect, text  # noqa: E402

from vertex_persistence.dsn import resolve_migration_url  # noqa: E402
from vertex_persistence.errors import ConfigurationError  # noqa: E402
from vertex_worker.demo_seed import (  # noqa: E402
    drain_published_snapshots,
    seed_demo_population,
)

ALEMBIC_INI = REPO_ROOT / "packages" / "python" / "vertex_persistence" / "alembic.ini"

#: Tables dont la présence de lignes signifie « cette base a déjà servi ».
#: Le journal et les thèses sont saisis par l'UTILISATEUR : les écraser d'un
#: semis de démonstration détruirait un travail irremplaçable.
_USER_OWNED_TABLES = ("ledger_transactions", "theses")


def _has_user_data(url: str) -> str | None:
    """Nomme la première table utilisateur non vide, ou ``None``."""
    engine = create_engine(url)
    try:
        existing = set(inspect(engine).get_table_names())
        with engine.connect() as connection:
            for table in _USER_OWNED_TABLES:
                if table not in existing:
                    continue
                # Table nommée depuis une constante littérale du module,
                # jamais depuis une entrée : aucune interpolation d'utilisateur.
                count = connection.execute(
                    text(f"SELECT count(*) FROM {table}")  # noqa: S608
                ).scalar_one()
                if count:
                    return f"{table} ({count} ligne(s))"
    finally:
        engine.dispose()
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prépare une base locale Vertex : migrations, puis population "
        "de démonstration SYNTHETIC facultative.",
    )
    parser.add_argument(
        "--with-demo-data",
        action="store_true",
        help="sème une population SYNTHETIC et publie les snapshots, pour que "
        "les 13 pages soient peuplées sans aucune source réelle",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="autorise le semis alors que la base contient déjà des données "
        "utilisateur (journal, thèses). À n'utiliser qu'en connaissance de cause.",
    )
    args = parser.parse_args(argv)

    try:
        url = resolve_migration_url(os.environ)
    except ConfigurationError as erreur:
        print(f"ERREUR: {erreur}", file=sys.stderr)
        return 2

    # 1. Migrations. Idempotent : `upgrade head` sur une base déjà à jour ne
    #    fait rien. Aucun schéma n'est détruit.
    alembic_config = Config(str(ALEMBIC_INI))
    alembic_config.attributes["sqlalchemy_url"] = url
    command.upgrade(alembic_config, "head")
    print("migrations: à jour (alembic upgrade head)")

    if not args.with_demo_data:
        print(
            "base prête. Aucune donnée n'a été semée : les pages seront VIDES "
            "et le diront honnêtement. Relancer avec --with-demo-data pour une "
            "population SYNTHETIC de démonstration."
        )
        return 0

    # 2. Refus fail-closed avant d'écrire quoi que ce soit.
    occupee = _has_user_data(url)
    if occupee and not args.force:
        print(
            f"ERREUR: la base contient déjà des données utilisateur — {occupee}. "
            "Un semis de démonstration les mélangerait à des lignes SYNTHETIC. "
            "Refus. Utiliser --force uniquement si cette base est jetable.",
            file=sys.stderr,
        )
        return 2

    now = datetime.now(UTC)
    report = seed_demo_population(engine_for(url), now=now, reason="bootstrap-local")
    processed = drain_published_snapshots(engine_for(url))
    print(
        "population SYNTHETIC semée et publiée: "
        f"enveloppes={report.envelopes} quotes={report.quotes} "
        f"chaines={report.chains} barres={report.bars} "
        f"calendrier={report.calendar} portefeuille={report.portfolio_id} "
        f"messages_traites={processed}"
    )
    print(
        "Tout ce qui précède porte population = SYNTHETIC jusqu'à l'écran. "
        "Aucune donnée réelle n'a été observée."
    )
    return 0


def engine_for(url: str) -> Engine:
    """Un moteur par usage, refermé par SQLAlchemy en fin de processus."""
    return create_engine(url)


if __name__ == "__main__":
    sys.exit(main())
