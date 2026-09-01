"""Production entry point of the worker: ``python -m vertex_worker``.

Runs the REAL :class:`~vertex_worker.runner.WorkerRunner` against the outbox
of the configured PostgreSQL database, with a best-effort ``LISTEN`` wake-up
and a clean shutdown on ``SIGTERM``/``SIGINT``.

Fail-closed by construction:

* the DSN comes from the environment ONLY (``VERTEX_DATABASE_URL``) — never a
  file, never a default, never an inline literal;
* a missing or example DSN aborts the start instead of guessing;
* running against a database whose name looks like a test database requires an
  explicit ``VERTEX_ALLOW_TEST_DB=1``, so a production worker never silently
  consumes a test outbox;
* the handler registry is built with the DEVELOPMENT synthetic configuration
  while no real source is connected, and the fact is LOGGED at start. Nothing
  it publishes is presented as real: every snapshot carries
  ``population = "SYNTHETIC"``.

Exit codes: ``0`` clean stop, ``2`` invalid configuration.
"""

from __future__ import annotations

import logging
import os
import signal
import sys
from datetime import UTC, datetime
from types import FrameType

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from vertex_persistence.dsn import database_name
from vertex_worker.handlers import build_registry
from vertex_worker.ingest import OUTBOX_NOTIFY_CHANNEL
from vertex_worker.profiles import ProfileError, resolve_profile
from vertex_worker.runner import (
    PostgresNotifyListener,
    WorkerRunner,
    sqlalchemy_url_to_conninfo,
)

__all__ = ["main"]

log = logging.getLogger("vertex_worker")

# Valeurs d'exemple de `.env.example` : les accepter reviendrait à démarrer sur
# une configuration fictive en croyant être en production.
_EXAMPLE_MARKERS = ("CHANGE_ME", "change_me", "example", "placeholder")

_TEST_DATABASE_MARKERS = ("_test", "test_", "vertex_test", "vertex_e2e")


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _require_database_url() -> str:
    url = os.environ.get("VERTEX_DATABASE_URL", "").strip()
    if not url:
        raise SystemExit(
            "VERTEX_DATABASE_URL absent. Le worker ne devine aucune base : "
            "définir la variable d'environnement avant de démarrer."
        )
    if any(marker in url for marker in _EXAMPLE_MARKERS):
        raise SystemExit(
            "VERTEX_DATABASE_URL porte une valeur d'exemple. Refus de démarrer "
            "sur une configuration fictive."
        )
    # Le nom de la base vient de l'analyseur d'URL, PAS d'un découpage de
    # chaîne : `postgresql+psycopg://…:5432/?dbname=vertex_test` désigne bien
    # `vertex_test` — libpq honore la query — alors qu'un `rsplit("/")` y lit
    # une chaîne vide et laissait passer le garde-fou.
    database = database_name(url)
    looks_like_test = any(marker in database for marker in _TEST_DATABASE_MARKERS)
    if looks_like_test and os.environ.get("VERTEX_ALLOW_TEST_DB") != "1":
        raise SystemExit(
            f"La base « {database} » ressemble à une base de test. Pour l'utiliser "
            "volontairement, définir VERTEX_ALLOW_TEST_DB=1."
        )
    return url


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("VERTEX_LOG_LEVEL", "INFO"),
        # Journal structuré minimal : ni secret, ni DSN, ni charge utile.
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    url = _require_database_url()

    try:
        profil = resolve_profile(os.environ)
    except ProfileError as erreur:
        raise SystemExit(f"profil de fusion refusé : {erreur}") from erreur
    registry = build_registry(
        clock=_utc_now,
        fusion_config=profil.fusion,
        markets_config=profil.markets,
        options_config=profil.options,
        analysis_config=profil.analysis,
        calendar_config=profil.calendar,
        opportunities_config=profil.opportunities,
        risk_config=profil.risk,
    )
    engine = create_engine(url, pool_pre_ping=True)
    runner = WorkerRunner(
        session_factory=lambda: Session(engine),
        registry=registry,
        clock=_utc_now,
    )

    # ADR-006 : NOTIFY réveille, il ne livre pas. Sa perte est tolérée parce que
    # le sondage de la table outbox reste la garantie de livraison.
    listener: PostgresNotifyListener | None = None
    try:
        listener = PostgresNotifyListener(
            conninfo=sqlalchemy_url_to_conninfo(url),
            channel=OUTBOX_NOTIFY_CHANNEL,
            on_notify=runner.wake,
        )
        listener.start()
    except Exception as error:
        log.warning(
            "réveil LISTEN indisponible (%s) — le worker continue en sondage seul",
            type(error).__name__,
        )
        listener = None

    def _request_stop(signum: int, _frame: FrameType | None) -> None:
        log.info("signal %s reçu — arrêt après le lot en cours", signal.Signals(signum).name)
        runner.request_stop()

    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)

    if profil.is_real:
        log.warning(
            "profil de fusion RÉEL actif — sources autorisées: %s, droits: %s, "
            "%d instrument(s) déclaré(s). Les snapshots porteront population=REAL "
            "dès qu'une observation réelle sera fusionnée.",
            sorted(profil.fusion.allowed_sources),
            sorted(profil.fusion.usable_rights),
            len(profil.analysis.instruments),
        )
    else:
        log.warning(
            "configuration DÉVELOPPEMENT SYNTHETIC active : aucune source réelle "
            "n'est connectée ; tout snapshot publié porte population=SYNTHETIC"
        )
    log.info("worker démarré — %d topics surveillés", len(registry.topics))
    try:
        runner.run()
    finally:
        if listener is not None:
            listener.stop()
        stats = runner.stats()
        log.info(
            "arrêt — lots=%d réclamés=%d acquittés=%d échoués=%d morts=%d baux perdus=%d",
            stats.batches,
            stats.claimed,
            stats.acked,
            stats.failed,
            stats.dead,
            stats.lease_lost,
        )
        engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(main())
