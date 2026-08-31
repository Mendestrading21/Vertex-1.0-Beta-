"""Découverte par scanner : la largeur de marché, sans univers déclaré.

POURQUOI CE FICHIER EXISTE. `runner.py` (temps réel) et `history.py`
(profondeur) exigent tous deux un univers de `con_id` connus d'avance. Or la
question « quoi regarder aujourd'hui ? » ne se répond pas depuis une liste
figée : elle se répond en interrogeant le marché entier. C'est exactement ce
que fait `reqScannerData` — le calcul a lieu chez IBKR, et seul le classement
revient.

CE QUE CE RÉGIME COÛTE, ET CE QU'IL NE COÛTE PAS
------------------------------------------------
Un scan ne maintient AUCUN abonnement durable : il ouvre une ligne le temps de
la requête, puis la relâche. Le plafond structurel est donc d'UNE ligne à la
fois, et la cadence est volontairement limitée à un scan par seconde — IBKR
refuse les demandes de scanner trop rapprochées.

CE QU'UN SCAN N'EST PAS
-----------------------
Un classement de scanner est un **déclencheur**, jamais un verdict. Il ne
porte ni prix canonique, ni décision : il dit seulement « ces candidats
méritent d'être regardés ». La revalidation appartient aux deux autres
régimes. Cette frontière est la même que celle imposée aux alertes
TradingView (ADR-005), et pour la même raison.

FRONTIÈRE FINANCIÈRE. `scanner_run` est le seul appel utilisé. Aucune capacité
compte, position, P&L, ordre ou exécution.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vertex_edge_ibkr.pacing import LineBudget, SlidingWindowPacer
from vertex_edge_ibkr.port import (
    EdgeIbkrError,
    IbkrInformationPort,
    ProviderError,
    ScannerDefinition,
)
from vertex_edge_ibkr.probe import is_informational_code
from vertex_edge_ibkr.runner import ObservationSink

__all__ = [
    "DEFAULT_SCANS_PER_WINDOW",
    "DEFAULT_SCAN_WINDOW_SECONDS",
    "MAX_SCAN_DEFINITIONS",
    "DiscoveryStats",
    "ScanDefinitionError",
    "ScannerDiscovery",
    "load_scan_definitions",
    "parse_scan_definitions",
]

log = logging.getLogger("vertex_edge_ibkr.discovery")

#: IBKR refuse des demandes de scanner trop rapprochées : un scan par seconde.
DEFAULT_SCANS_PER_WINDOW = 1
DEFAULT_SCAN_WINDOW_SECONDS = 1.0

_COUNTER_NAMES = (
    "scans",
    "ingested",
    "duplicates",
    "deferred",
    "provider_errors",
    "transport_errors",
    "notices",
)


@dataclass(frozen=True)
class DiscoveryStats:
    """Compteurs observables. Une attente et un refus restent visibles."""

    scans: int = 0
    ingested: int = 0
    duplicates: int = 0
    deferred: int = 0
    provider_errors: int = 0
    transport_errors: int = 0
    notices: int = 0
    waited_seconds: float = 0.0


class ScannerDiscovery:
    """Exécute une série de scans bornés et ingère leurs classements.

    Tout est injecté — port, puits, pacer, budget de lignes, sommeil — donc
    aucun test n'ouvre de socket. ``max_scans`` borne l'exécution.
    """

    def __init__(
        self,
        *,
        port: IbkrInformationPort,
        definitions: Sequence[ScannerDefinition],
        sink: ObservationSink,
        pacer: SlidingWindowPacer,
        line_budget: LineBudget,
        sleep: Callable[[float], Awaitable[None]],
        max_scans: int | None = None,
    ) -> None:
        if not definitions:
            raise ValueError("aucune définition de scan : la découverte n'en invente pas")
        if max_scans is not None and max_scans < 1:
            raise ValueError("max_scans doit être >= 1 quand il est fourni")
        self._port = port
        self._definitions = tuple(definitions)
        self._sink = sink
        self._pacer = pacer
        self._lines = line_budget
        self._sleep = sleep
        self._max_scans = max_scans
        self._stop_requested = False
        self._waited = 0.0
        self._c: dict[str, int] = dict.fromkeys(_COUNTER_NAMES, 0)

    # -- pilotage ----------------------------------------------------------

    def request_stop(self) -> None:
        self._stop_requested = True

    def stats(self) -> DiscoveryStats:
        return DiscoveryStats(waited_seconds=self._waited, **self._c)

    @staticmethod
    def scan_key(definition: ScannerDefinition) -> str:
        return f"{definition.instrument}:{definition.location_code}:{definition.scan_code}"

    # -- boucle ------------------------------------------------------------

    async def run(self) -> DiscoveryStats:
        for definition in self._definitions:
            if self._stop_requested or self._limit_reached():
                break
            if not await self._await_slot(definition):
                break
            await self._scan_and_ingest(definition)
        log.info(
            "découverte terminée — scans=%d insérés=%d doublons=%d attentes=%d",
            self._c["scans"],
            self._c["ingested"],
            self._c["duplicates"],
            self._c["deferred"],
        )
        return self.stats()

    def _limit_reached(self) -> bool:
        return self._max_scans is not None and self._c["scans"] >= self._max_scans

    async def _await_slot(self, definition: ScannerDefinition) -> bool:
        cle = self.scan_key(definition)
        attente = self._pacer.seconds_until_allowed(cle)
        while attente > 0.0:
            if self._stop_requested:
                return False
            self._c["deferred"] += 1
            self._waited += attente
            await self._sleep(attente)
            attente = self._pacer.seconds_until_allowed(cle)
        if self._stop_requested:
            return False
        return self._pacer.try_acquire(cle)

    async def _scan_and_ingest(self, definition: ScannerDefinition) -> None:
        if not self._lines.try_acquire():
            # Structurellement impossible avec un plafond de 1 et des scans
            # séquentiels ; compté quand même plutôt que supposé impossible.
            self._c["deferred"] += 1
            log.warning(
                "plafond de lignes atteint (%d/%d) — scan %s reporté",
                self._lines.in_use,
                self._lines.max_usable,
                self.scan_key(definition),
            )
            return
        try:
            self._c["scans"] += 1
            enveloppe = await self._port.scanner_run(definition)
        except ProviderError as erreur:
            if is_informational_code(erreur.code):
                self._c["notices"] += 1
                log.info("notice fournisseur %d sur %s", erreur.code, self.scan_key(definition))
                return
            self._c["provider_errors"] += 1
            log.warning(
                "erreur fournisseur %d sur le scan %s — jamais convertie en "
                "« aucun candidat »",
                erreur.code,
                self.scan_key(definition),
            )
            return
        except (EdgeIbkrError, OSError, TimeoutError) as erreur:
            self._c["transport_errors"] += 1
            log.warning(
                "erreur de transport (%s) sur le scan %s",
                type(erreur).__name__,
                self.scan_key(definition),
            )
            return
        finally:
            # La ligne est TOUJOURS relâchée, quoi qu'il arrive au-dessus.
            self._lines.release()
        inserees, doublons = self._sink((enveloppe,))
        self._c["ingested"] += inserees
        self._c["duplicates"] += doublons


#: Borne du nombre de scans par passe. Un scan par seconde : au-dela, la passe
#: durerait plus longtemps que la pertinence de son classement.
MAX_SCAN_DEFINITIONS = 32

_SCAN_KEYS = frozenset({"instrument", "location_code", "scan_code", "number_of_rows"})


class ScanDefinitionError(ValueError):
    """Fichier de scans absent, illisible, incomplet ou hors borne."""


def parse_scan_definitions(
    document: Any, *, max_definitions: int = MAX_SCAN_DEFINITIONS
) -> tuple[ScannerDefinition, ...]:
    """Valide un document de scans deja decode.

    Refuse : racine non-objet, `scans` absent ou vide, cle inconnue, borne
    depassee, doublon exact. Un fichier vide n'est pas une passe neutre :
    c'est une configuration incomplete, donc un refus.
    """
    if max_definitions < 1 or max_definitions > MAX_SCAN_DEFINITIONS:
        raise ScanDefinitionError(
            f"max_definitions doit rester dans [1, {MAX_SCAN_DEFINITIONS}]."
        )
    if not isinstance(document, dict):
        raise ScanDefinitionError("scans : objet JSON attendu a la racine.")
    entrees = document.get("scans")
    if not isinstance(entrees, list) or not entrees:
        raise ScanDefinitionError("scans : `scans` doit etre une liste non vide.")
    if len(entrees) > max_definitions:
        raise ScanDefinitionError(
            f"scans : {len(entrees)} demandes, maximum {max_definitions}."
        )
    definitions: list[ScannerDefinition] = []
    for index, entree in enumerate(entrees):
        if not isinstance(entree, dict):
            raise ScanDefinitionError(f"scan #{index} : objet JSON attendu.")
        inconnues = sorted(set(entree) - _SCAN_KEYS)
        if inconnues:
            raise ScanDefinitionError(
                f"scan #{index} : cles inconnues {inconnues}. "
                f"Cles reconnues : {sorted(_SCAN_KEYS)}."
            )
        try:
            definitions.append(
                ScannerDefinition(
                    instrument=str(entree.get("instrument", "")),
                    location_code=str(entree.get("location_code", "")),
                    scan_code=str(entree.get("scan_code", "")),
                    number_of_rows=int(entree.get("number_of_rows", 50)),
                )
            )
        except (TypeError, ValueError) as erreur:
            raise ScanDefinitionError(f"scan #{index} : {erreur}") from erreur
    cles = [ScannerDiscovery.scan_key(d) for d in definitions]
    doublons = sorted({c for c in cles if cles.count(c) > 1})
    if doublons:
        raise ScanDefinitionError(f"scans : definitions dupliquees {doublons}.")
    return tuple(definitions)


def load_scan_definitions(
    path: Path, *, max_definitions: int = MAX_SCAN_DEFINITIONS
) -> tuple[ScannerDefinition, ...]:
    """Lit et valide le fichier de scans. Toute anomalie arrete la decouverte."""
    try:
        texte = path.read_text(encoding="utf-8")
    except OSError as erreur:
        raise ScanDefinitionError(f"scans illisibles ({path}) : {erreur}") from erreur
    try:
        document = json.loads(texte)
    except json.JSONDecodeError as erreur:
        raise ScanDefinitionError(f"scans : JSON invalide ({path}) : {erreur}") from erreur
    return parse_scan_definitions(document, max_definitions=max_definitions)
