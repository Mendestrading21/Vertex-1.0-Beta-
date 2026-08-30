#!/usr/bin/env python3
"""Normalise une URL de base Vertex vers la forme libpq, pour les outils.

Le runtime configure `VERTEX_DATABASE_URL` en forme SQLAlchemy
(`postgresql+psycopg://…`) : c'est ce que `create_engine` exige, et le pilote
verrouillé est psycopg 3 (aucun `psycopg2` dans `uv.lock`). Les outils libpq —
`pg_dump`, `pg_restore`, `psql` — ne comprennent PAS cette forme.

Le danger n'est pas qu'ils échouent : c'est qu'ils **réussissent ailleurs**.
`pg_dump "postgresql+psycopg://…"` traite la chaîne comme un NOM DE BASE, se
rabat sur la socket locale et l'utilisateur système, et sauvegarderait une
autre base sans rien signaler si ce rôle existait.

Ce script ne réimplémente rien : il délègue à `vertex_persistence.dsn`,
autorité unique de cette conversion, déjà utilisée par le worker pour son
écoute LISTEN.

Usage :
    python3 tools/db_url.py libpq "$VERTEX_DATABASE_URL"   -> URI libpq
    python3 tools/db_url.py dbname "$VERTEX_DATABASE_URL"  -> nom de la base
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "packages" / "python" / "vertex_persistence" / "src"))

from vertex_persistence.dsn import (  # noqa: E402
    database_name,
    sqlalchemy_url_to_conninfo,
)

__all__ = ["database_name", "to_libpq"]


def to_libpq(url: str) -> str:
    """Forme utilisable par pg_dump / pg_restore / psql."""
    if not url.strip():
        raise SystemExit("URL vide : aucune base n'est désignée.")
    return sqlalchemy_url_to_conninfo(url)


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] not in ("libpq", "dbname"):
        print(__doc__, file=sys.stderr)
        return 2
    print(to_libpq(argv[2]) if argv[1] == "libpq" else database_name(argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
