#!/usr/bin/env python3
"""Sonde exécutable des droits et capacités IBKR — la commande qui manquait.

POURQUOI CE FICHIER EXISTE. `apps/edge-ibkr/src/vertex_edge_ibkr/probe.py`
implémente déjà la sonde complète décrite par
`docs/04-integrations/IBKR_ENTITLEMENT_PROBE.md` : six étapes bornées, une
seule sonde active, deux lignes de données au maximum, mapping d'erreurs exact
et `ERROR` jamais converti en `NOT_ENTITLED`. Elle est testée. Mais AUCUNE
commande ne permettait de la lancer : au premier allumage de TWS, on aurait
découvert les droits au hasard, page par page.

Ce fichier n'est qu'un ASSEMBLEUR. Il ne réimplémente ni la sonde, ni les
gardes de connexion, ni l'interprétation des ticks : il résout un contrat
exact, appelle `EntitlementProbe.run()` et imprime la matrice obtenue.

CE QU'IL NE FAIT JAMAIS
-----------------------
- Aucune capacité de compte, position, P&L, ordre ou exécution. Le port
  `IbkrInformationPort` ne les expose pas et `tools/check_financial_boundary.py`
  balaie ce fichier comme tous les autres.
- Aucun hôte configurable : il n'existe pas d'option `--host`. L'adaptateur
  refuse déjà tout hôte autre que `127.0.0.1` ; ne pas offrir le réglage est
  plus fort que de le valider.
- Aucun symbole « populaire » codé en dur. L'identité vient entièrement de la
  ligne de commande, et toute ambiguïté arrête la sonde (spécification :
  « Si l'identité ou la session est ambiguë, la sonde s'arrête »).
- Aucune écriture en base sans `--persist`.

USAGE
-----
Étape 1 — résolution, AUCUNE ligne de données de marché ouverte ::

    python3 tools/probe_entitlements.py --symbol XYZ --dry-run

Elle se connecte, qualifie le sous-jacent et imprime les définitions de chaîne
réellement renvoyées : exchanges, `trading_class`, multiplicateurs, échéances
et strikes. C'est ce qui permet de choisir l'option exacte de l'étape 2.

Étape 2 — sonde réelle ::

    python3 tools/probe_entitlements.py --symbol XYZ \
        --option-expiry 20261218 --option-strike 100 --option-right C \
        --option-trading-class XYZ --option-exchange SMART [--persist]

Codes de sortie : ``0`` succès, ``1`` échec de transport ou de fournisseur,
``2`` configuration invalide ou refus délibéré.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import random
import secrets
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import TYPE_CHECKING, Any

REPO_ROOT = Path(__file__).resolve().parents[1]

# src-layout : sans cela, aucun paquet du dépôt n'est importable depuis un
# script de `tools/` exécuté par `python3` nu (le cas du runbook).
for _package in (
    "packages/python/vertex_core/src",
    "packages/python/vertex_persistence/src",
    "apps/edge-ibkr/src",
    "apps/worker/src",
):
    _path = str(REPO_ROOT / _package)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from vertex_edge_ibkr.port import (  # noqa: E402 - après l'amorçage du sys.path
    ContractSpec,
    EdgeIbkrError,
    IbkrInformationPort,
    OptionChainDefinition,
)
from vertex_edge_ibkr.probe import (  # noqa: E402
    EntitlementProbe,
    ProbeConfig,
    SourceCapabilitySnapshot,
)

if TYPE_CHECKING:  # pragma: no cover - typage seulement
    from vertex_edge_ibkr.state import ConnectionStateMachine

#: Habilitation publiée par l'edge IBKR. Identique à l'argument par défaut de
#: `IbAsyncInformationAdapter` : une sonde réelle n'est ni `SYNTHETIC` ni
#: `DEMO`, et ne doit surtout pas emprunter ces marqueurs.
REAL_RIGHTS = "IBKR_MARKET_DATA_DISPLAY_ONLY"

#: Le worker publie `capabilities` à partir des observations persistées.
CAPABILITY_SCHEMA_VERSION = "source-capability/1.0"


class ProbeRefusal(Exception):
    """Refus délibéré : configuration ambiguë, absente ou incohérente."""


# ---------------------------------------------------------------------------
# 1. Résolution d'identité — l'ambiguïté arrête la sonde
# ---------------------------------------------------------------------------


async def resolve_exactly_one(
    port: IbkrInformationPort, spec: ContractSpec, *, what: str
) -> ContractSpec:
    """Qualifie ``spec`` et exige une identité UNIQUE et porteuse de ``con_id``.

    `reqContractDetails` peut renvoyer plusieurs contrats pour un symbole
    (plusieurs bourses, plusieurs devises). Choisir « le premier » fabriquerait
    une identité : la sonde s'arrête et rend la main à l'utilisateur.
    """
    resolved = await port.qualify_contracts(spec)
    if not resolved:
        raise ProbeRefusal(
            f"{what} : aucun contrat qualifié pour {_describe(spec)}. "
            "Préciser exchange, currency ou sec_type."
        )
    if len(resolved) > 1:
        lignes = "\n".join(f"    - {_describe(candidat)}" for candidat in resolved)
        raise ProbeRefusal(
            f"{what} : identité AMBIGUË — {len(resolved)} contrats qualifiés.\n"
            f"{lignes}\n"
            "Préciser exchange et currency jusqu'à n'en garder qu'un."
        )
    unique = resolved[0]
    if unique.con_id is None:
        raise ProbeRefusal(
            f"{what} : le contrat qualifié ne porte pas de con_id. "
            "Une sonde exige une identité exacte, jamais un symbole seul."
        )
    return unique


def _describe(spec: ContractSpec) -> str:
    """Description lisible d'un contrat, sans jamais inventer un champ absent."""
    parts = [spec.sec_type]
    for name, value in (
        ("con_id", spec.con_id),
        ("symbol", spec.symbol),
        ("exchange", spec.exchange),
        ("currency", spec.currency),
        ("expiry", spec.last_trade_date),
        ("strike", spec.strike),
        ("right", spec.right),
        ("trading_class", spec.trading_class),
        ("multiplier", spec.multiplier),
    ):
        if value is not None:
            parts.append(f"{name}={value}")
    return " ".join(parts)


def select_chain_row(
    definitions: Sequence[OptionChainDefinition], *, exchange: str, trading_class: str
) -> OptionChainDefinition:
    """Retient la ligne de chaîne EXACTE demandée, sans fusionner.

    « Deux `tradingClass` à même échéance ne sont jamais fusionnées »
    (`IBKR_ENTITLEMENT_PROBE.md`) : on filtre sur le couple exact et on refuse
    aussi bien zéro que plusieurs correspondances.
    """
    matches = [
        row
        for row in definitions
        if row.exchange == exchange and row.trading_class == trading_class
    ]
    if not matches:
        disponibles = sorted({(row.exchange, row.trading_class) for row in definitions})
        lignes = "\n".join(f"    - exchange={e} trading_class={t}" for e, t in disponibles)
        raise ProbeRefusal(
            f"aucune définition de chaîne pour exchange={exchange} "
            f"trading_class={trading_class}. Couples RÉELLEMENT renvoyés :\n{lignes}"
        )
    if len(matches) > 1:
        raise ProbeRefusal(
            f"définition de chaîne ambiguë : {len(matches)} lignes pour "
            f"exchange={exchange} trading_class={trading_class}."
        )
    return matches[0]


def check_expiry_and_strike(
    row: OptionChainDefinition, *, expiry: str, strike: Decimal
) -> None:
    """Refuse une échéance ou un strike que la chaîne n'a PAS annoncés."""
    if expiry not in row.expirations:
        proches = ", ".join(sorted(row.expirations)[:12])
        raise ProbeRefusal(
            f"échéance {expiry} absente de cette chaîne "
            f"({len(row.expirations)} échéances). Premières : {proches}"
        )
    if strike not in row.strikes:
        ordonnes = sorted(row.strikes)
        voisins = sorted(ordonnes, key=lambda value: abs(value - strike))[:8]
        proches = ", ".join(str(value) for value in sorted(voisins))
        raise ProbeRefusal(
            f"strike {strike} absent de cette chaîne ({len(row.strikes)} strikes). "
            f"Les plus proches : {proches}"
        )


# ---------------------------------------------------------------------------
# 2. Impression — la matrice, champ par champ
# ---------------------------------------------------------------------------


def format_chain_definitions(definitions: Sequence[OptionChainDefinition]) -> str:
    """Ce que `reqSecDefOptParams` a RÉELLEMENT renvoyé, borné à l'utile."""
    if not definitions:
        return (
            "  (aucune définition de chaîne renvoyée — réponse vide, ce qui est\n"
            "   INCONCLUSIF et jamais une preuve d'absence de droit)"
        )
    lignes = []
    for row in definitions:
        echeances = sorted(row.expirations)
        strikes = sorted(row.strikes)
        lignes.append(
            f"  exchange={row.exchange} trading_class={row.trading_class} "
            f"multiplier={row.multiplier}\n"
            f"    {len(echeances)} échéance(s) — premières : "
            f"{', '.join(echeances[:8]) or '(aucune)'}\n"
            f"    {len(strikes)} strike(s) — "
            f"{f'de {strikes[0]} à {strikes[-1]}' if strikes else '(aucun)'}"
        )
    return "\n".join(lignes)


def format_matrix(snapshot: SourceCapabilitySnapshot) -> str:
    """Une ligne par champ sondé : statut, raison, tick, type de marché, code."""
    entetes = ("capacité", "champ", "statut", "raison", "tick", "type", "code")
    lignes: list[tuple[str, ...]] = [entetes]
    for evidence in snapshot.fields:
        lignes.append(
            (
                evidence.capability_id,
                evidence.field,
                str(evidence.status.value),
                evidence.reason_code or "—",
                "—" if evidence.tick_type is None else str(evidence.tick_type),
                "—" if evidence.market_data_type is None else str(evidence.market_data_type),
                "—" if evidence.provider_error_code is None else str(evidence.provider_error_code),
            )
        )
    largeurs = [max(len(ligne[i]) for ligne in lignes) for i in range(len(entetes))]
    rendu = []
    for index, ligne in enumerate(lignes):
        rendu.append("  ".join(cellule.ljust(largeurs[i]) for i, cellule in enumerate(ligne)))
        if index == 0:
            rendu.append("  ".join("-" * largeur for largeur in largeurs))
    return "\n".join(rendu)


# ---------------------------------------------------------------------------
# 3. Persistance — le MÊME chemin que le semis de démonstration
# ---------------------------------------------------------------------------


def persist_snapshot(snapshot: SourceCapabilitySnapshot, *, now: datetime) -> None:
    """Écrit l'observation de capacité et met la republication en file.

    Chemin identique à `vertex_worker.demo_seed`, à deux différences qui
    comptent : `source="ibkr"` (stampé par la sonde elle-même) et
    `rights=IBKR_MARKET_DATA_DISPLAY_ONLY` — jamais `DEMO`, jamais
    `SYNTHETIC`. `/system` cessera d'afficher `NEVER_TESTED` pour les
    capacités RÉELLEMENT sondées, et pour elles seules.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from vertex_persistence.dsn import resolve_migration_url
    from vertex_persistence.repository.observations import insert_observation
    from vertex_persistence.repository.outbox import enqueue_outbox
    from vertex_worker.handlers import TOPIC_CAPABILITIES_REFRESH

    url = resolve_migration_url(os.environ)
    engine = create_engine(url)
    try:
        with Session(engine) as session:
            insert_observation(
                session,
                event_id=f"ibkr:capability:{snapshot.probe_id}",
                schema_version=CAPABILITY_SCHEMA_VERSION,
                source=snapshot.source,
                received_at=now,
                as_of=snapshot.tested_at,
                stale_after=snapshot.expires_at,
                quality_status="VALID",
                delay_status="UNKNOWN",
                rights=REAL_RIGHTS,
                connection_epoch=snapshot.connection_epoch,
                payload=snapshot.model_dump(mode="json"),
            )
            enqueue_outbox(
                session, TOPIC_CAPABILITIES_REFRESH, {"reason": "entitlement-probe"}
            )
            session.commit()
    finally:
        engine.dispose()


# ---------------------------------------------------------------------------
# 4. Orchestration
# ---------------------------------------------------------------------------


def build_adapter(*, port: int, client_id: int) -> tuple[Any, ConnectionStateMachine]:
    """Construit l'adaptateur RÉEL. Aucun hôte n'est réglable ici.

    `IbAsyncInformationAdapter.__init__` refuse tout hôte autre que
    `127.0.0.1` et tout `client_id` nul ou négatif : cette fonction ne
    redéclare aucune de ces deux gardes, elle les laisse s'appliquer.
    """
    from vertex_edge_ibkr.adapter import IbAsyncInformationAdapter
    from vertex_edge_ibkr.state import ConnectionStateMachine

    # `SystemRandom` uniquement pour le jitter de backoff de la machine
    # d'état : aucune décision financière n'en dépend.
    jitter: random.Random = secrets.SystemRandom()
    state = ConnectionStateMachine(rng=jitter)
    adapter = IbAsyncInformationAdapter(port=port, client_id=client_id, state=state)
    return adapter, state


async def run_probe_session(
    port: IbkrInformationPort,
    arguments: argparse.Namespace,
    *,
    clock: Callable[[], datetime],
    epoch_provider: Callable[[], int],
) -> SourceCapabilitySnapshot | None:
    """Résout, imprime la chaîne, puis sonde. ``None`` en mode ``--dry-run``."""
    underlying = await resolve_exactly_one(
        port,
        ContractSpec(
            sec_type=arguments.sec_type,
            symbol=arguments.symbol,
            exchange=arguments.exchange,
            currency=arguments.currency,
        ),
        what="sous-jacent",
    )
    print(f"sous-jacent qualifié : {_describe(underlying)}")

    definitions = await port.sec_def_opt_params(underlying)
    print("définitions de chaîne RÉELLEMENT renvoyées :")
    print(format_chain_definitions(definitions))

    if arguments.dry_run:
        print(
            "\n--dry-run : AUCUNE ligne de données de marché n'a été ouverte.\n"
            "Choisir une échéance, un strike, un right, un trading_class et un\n"
            "exchange ci-dessus, puis relancer SANS --dry-run pour sonder."
        )
        return None

    row = select_chain_row(
        definitions,
        exchange=arguments.option_exchange,
        trading_class=arguments.option_trading_class,
    )
    check_expiry_and_strike(row, expiry=arguments.option_expiry, strike=arguments.option_strike)

    option = await resolve_exactly_one(
        port,
        ContractSpec(
            sec_type="OPT",
            symbol=underlying.symbol,
            exchange=row.exchange,
            currency=underlying.currency,
            last_trade_date=arguments.option_expiry,
            strike=arguments.option_strike,
            right=arguments.option_right,
            trading_class=row.trading_class,
            multiplier=row.multiplier,
        ),
        what="option",
    )
    print(f"option qualifiée   : {_describe(option)}")

    config = ProbeConfig(
        underlying=underlying,
        option=option,
        allow_delayed_fallback=arguments.allow_delayed_fallback,
        step_timeout_seconds=arguments.step_timeout,
        total_deadline_seconds=arguments.total_deadline,
        result_ttl_seconds=arguments.result_ttl,
    )
    probe = EntitlementProbe(port, config, clock=clock, epoch_provider=epoch_provider)
    return await probe.run()


def _positive(value: str, *, what: str) -> float:
    try:
        numeric = float(value)
    except ValueError as erreur:
        raise argparse.ArgumentTypeError(f"{what} : nombre attendu") from erreur
    if numeric <= 0:
        raise argparse.ArgumentTypeError(f"{what} : doit être strictement positif")
    return numeric


def _decimal(value: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as erreur:
        raise argparse.ArgumentTypeError(f"strike : décimal attendu, reçu {value!r}") from erreur


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sonde les droits IBKR RÉELS pour un sous-jacent et une option "
        "exacts, sur TWS/IB Gateway en lecture seule et sur la boucle locale.",
    )
    parser.add_argument("--symbol", required=True, help="symbole du sous-jacent (aucun défaut)")
    parser.add_argument("--sec-type", default="STK", help="type de contrat (défaut : STK)")
    parser.add_argument("--exchange", default=None, help="bourse du sous-jacent, si ambiguë")
    parser.add_argument("--currency", default=None, help="devise du sous-jacent, si ambiguë")
    parser.add_argument(
        "--tws-port",
        type=int,
        default=int(os.environ.get("VERTEX_IBKR_PORT", "7497")),
        help="port TWS/IB Gateway sur 127.0.0.1 (défaut : 7497 / VERTEX_IBKR_PORT)",
    )
    parser.add_argument(
        "--client-id",
        type=int,
        default=int(os.environ.get("VERTEX_IBKR_CLIENT_ID", "71")),
        help="client_id API, non nul (défaut : 71 / VERTEX_IBKR_CLIENT_ID)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="qualifier le sous-jacent et imprimer les chaînes, SANS ouvrir "
        "aucune ligne de données de marché",
    )
    parser.add_argument("--option-expiry", default=None, help="échéance AAAAMMJJ")
    parser.add_argument("--option-strike", type=_decimal, default=None, help="strike exact")
    parser.add_argument("--option-right", choices=("C", "P"), default=None, help="C ou P")
    parser.add_argument("--option-trading-class", default=None, help="trading_class exacte")
    parser.add_argument("--option-exchange", default=None, help="bourse de l'option")
    parser.add_argument(
        "--allow-delayed-fallback",
        action="store_true",
        help="autoriser l'étape 5 : re-demander en delayed si le live est REFUSÉ. "
        "Le résultat reste étiqueté DELAYED, jamais requalifié live.",
    )
    parser.add_argument(
        "--step-timeout",
        type=lambda value: _positive(value, what="--step-timeout"),
        default=12.0,
    )
    parser.add_argument(
        "--total-deadline",
        type=lambda value: _positive(value, what="--total-deadline"),
        default=60.0,
    )
    parser.add_argument(
        "--result-ttl",
        type=lambda value: _positive(value, what="--result-ttl"),
        default=21600.0,
        help="durée de validité de la preuve, en secondes (défaut : 6 h)",
    )
    parser.add_argument(
        "--persist",
        action="store_true",
        help="écrire l'observation de capacité en base pour que /system montre "
        "le RÉEL au lieu de NEVER_TESTED (exige VERTEX_DATABASE_URL)",
    )
    return parser


_OPTION_ARGUMENTS = (
    ("option_expiry", "--option-expiry"),
    ("option_strike", "--option-strike"),
    ("option_right", "--option-right"),
    ("option_trading_class", "--option-trading-class"),
    ("option_exchange", "--option-exchange"),
)


def validate_arguments(arguments: argparse.Namespace) -> None:
    """Fail-closed : hors ``--dry-run``, l'option doit être ENTIÈREMENT nommée."""
    if arguments.dry_run:
        return
    manquants = [
        flag for attribut, flag in _OPTION_ARGUMENTS if getattr(arguments, attribut) is None
    ]
    if manquants:
        raise ProbeRefusal(
            "l'option doit être décrite EXACTEMENT — manquant : "
            f"{', '.join(manquants)}.\n"
            "Lancer d'abord --dry-run : il imprime les échéances, strikes, "
            "trading_class et exchanges réellement disponibles."
        )


def main(
    argv: list[str] | None = None,
    *,
    port_factory: Callable[[argparse.Namespace], tuple[IbkrInformationPort, Callable[[], int]]]
    | None = None,
    clock: Callable[[], datetime] | None = None,
) -> int:
    arguments = build_parser().parse_args(argv)
    now = clock if clock is not None else lambda: datetime.now(UTC)

    try:
        validate_arguments(arguments)
    except ProbeRefusal as refus:
        print(f"REFUS: {refus}", file=sys.stderr)
        return 2

    if port_factory is not None:
        port, epoch_provider = port_factory(arguments)
        closer: Callable[[], Any] | None = None
    else:
        try:
            adapter, state = build_adapter(
                port=arguments.tws_port, client_id=arguments.client_id
            )
        except ValueError as erreur:
            print(f"REFUS: {erreur}", file=sys.stderr)
            return 2
        port = adapter
        epoch_provider = lambda: state.connection_epoch  # noqa: E731
        closer = adapter.disconnect

    async def _session() -> SourceCapabilitySnapshot | None:
        connect = getattr(port, "connect", None)
        if connect is not None:
            await connect()
        try:
            return await run_probe_session(
                port, arguments, clock=now, epoch_provider=epoch_provider
            )
        finally:
            if closer is not None:
                await closer()

    try:
        snapshot = asyncio.run(_session())
    except ProbeRefusal as refus:
        print(f"REFUS: {refus}", file=sys.stderr)
        return 2
    except (EdgeIbkrError, OSError, TimeoutError) as erreur:
        # Un échec de transport n'est JAMAIS une preuve d'absence de droit :
        # on sort en erreur, sans publier ni conclure quoi que ce soit.
        print(f"ÉCHEC: {type(erreur).__name__}: {erreur}", file=sys.stderr)
        return 1

    if snapshot is None:
        return 0

    print()
    print(f"probe_id={snapshot.probe_id} epoch={snapshot.connection_epoch}")
    print(f"testé le {snapshot.tested_at.isoformat()}, valable jusqu'au "
          f"{snapshot.expires_at.isoformat()}")
    print()
    print(format_matrix(snapshot))
    print()
    print(
        "Rappel : ERROR et timeout ne signifient JAMAIS NOT_ENTITLED. Une preuve\n"
        "ne vaut que pour cet instrument, cette bourse, ce type de donnée, cet\n"
        "utilisateur technique et cet epoch de connexion."
    )

    if arguments.persist:
        persist_snapshot(snapshot, now=now())
        print("\nobservation de capacité écrite ; /system la publiera au prochain cycle.")
    else:
        print("\nRien n'a été écrit en base (--persist absent).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
