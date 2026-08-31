"""Découverte par scanner : cadence tenue, ligne toujours relâchée, rien inventé.

Aucun test n'ouvre de socket ni n'attend le temps réel : port, puits, pacer,
budget de lignes et sommeil sont injectés, et l'horloge est pilotée à la main.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fakes import make_envelope

from vertex_edge_ibkr.discovery import ScannerDiscovery
from vertex_edge_ibkr.pacing import LineBudget, SlidingWindowPacer
from vertex_edge_ibkr.port import EdgeIbkrError, ProviderError, ScannerDefinition

SCAN_A = ScannerDefinition(
    instrument="STK", location_code="STK.US.MAJOR", scan_code="TOP_PERC_GAIN"
)
SCAN_B = ScannerDefinition(instrument="STK", location_code="STK.US.MAJOR", scan_code="MOST_ACTIVE")


class Horloge:
    def __init__(self) -> None:
        self.maintenant = 0.0

    def __call__(self) -> float:
        return self.maintenant

    def avancer(self, secondes: float) -> None:
        self.maintenant += secondes


class FauxPort:
    def __init__(self, resultats: dict[str, Any] | None = None) -> None:
        self.resultats = resultats or {}
        self.appels: list[str] = []

    async def scanner_run(self, definition: ScannerDefinition) -> Any:
        cle = definition.scan_code
        self.appels.append(cle)
        comportement = self.resultats.get(cle)
        if isinstance(comportement, BaseException):
            raise comportement
        if comportement is None:
            return make_envelope({"scan": cle})
        return comportement


class Puits:
    def __init__(self, *, duplicates: int = 0) -> None:
        self.lots: list[tuple[Any, ...]] = []
        self._duplicates = duplicates

    def __call__(self, envelopes: Any) -> tuple[int, int]:
        lot = tuple(envelopes)
        self.lots.append(lot)
        doublons = min(self._duplicates, len(lot))
        return len(lot) - doublons, doublons


class Sommeil:
    def __init__(self, horloge: Horloge) -> None:
        self.horloge = horloge
        self.delais: list[float] = []

    async def __call__(self, delai: float) -> None:
        self.delais.append(delai)
        self.horloge.avancer(delai)


def monter(
    port: FauxPort,
    *,
    definitions: tuple[ScannerDefinition, ...] = (SCAN_A,),
    max_scans: int | None = None,
    lignes: int = 1,
) -> tuple[ScannerDiscovery, Puits, Sommeil, LineBudget]:
    horloge = Horloge()
    sommeil = Sommeil(horloge)
    puits = Puits()
    budget = LineBudget(lignes * 2, hard_cap=lignes)
    d = ScannerDiscovery(
        port=port,
        definitions=definitions,
        sink=puits,
        pacer=SlidingWindowPacer(max_requests=1, window_seconds=1.0, clock=horloge),
        line_budget=budget,
        sleep=sommeil,
        max_scans=max_scans,
    )
    return d, puits, sommeil, budget


# -- chemin nominal --------------------------------------------------------


def test_chaque_definition_est_scannee_et_ingeree() -> None:
    port = FauxPort()
    d, puits, _, _ = monter(port, definitions=(SCAN_A, SCAN_B))
    stats = asyncio.run(d.run())
    assert port.appels == ["TOP_PERC_GAIN", "MOST_ACTIVE"]
    assert stats.scans == 2
    assert stats.ingested == 2
    assert len(puits.lots) == 2


def test_la_cle_de_scan_distingue_les_definitions() -> None:
    assert ScannerDiscovery.scan_key(SCAN_A) != ScannerDiscovery.scan_key(SCAN_B)


def test_un_doublon_n_est_pas_compte_comme_insere() -> None:
    port = FauxPort()
    horloge = Horloge()
    d = ScannerDiscovery(
        port=port,
        definitions=(SCAN_A,),
        sink=Puits(duplicates=1),
        pacer=SlidingWindowPacer(max_requests=1, window_seconds=1.0, clock=horloge),
        line_budget=LineBudget(2, hard_cap=1),
        sleep=Sommeil(horloge),
    )
    stats = asyncio.run(d.run())
    assert stats.ingested == 0
    assert stats.duplicates == 1


# -- cadence ---------------------------------------------------------------


def test_la_cadence_d_un_scan_par_seconde_est_tenue() -> None:
    """IBKR refuse les demandes de scanner trop rapprochées."""
    port = FauxPort()
    d, _, sommeil, _ = monter(port, definitions=(SCAN_A, SCAN_B))
    stats = asyncio.run(d.run())
    assert stats.scans == 2
    assert stats.deferred == 1
    assert sommeil.delais == [pytest.approx(1.0)]


# -- la ligne est TOUJOURS relâchée ---------------------------------------


def test_la_ligne_est_relachee_apres_un_scan_reussi() -> None:
    port = FauxPort()
    d, _, _, budget = monter(port)
    asyncio.run(d.run())
    assert budget.in_use == 0


def test_la_ligne_est_relachee_meme_apres_une_erreur() -> None:
    """Une ligne fuitée bloquerait toute la découverte en silence."""
    port = FauxPort(resultats={"TOP_PERC_GAIN": EdgeIbkrError("panne")})
    d, _, _, budget = monter(port)
    asyncio.run(d.run())
    assert budget.in_use == 0


# -- erreurs : jamais converties en « aucun candidat » --------------------


def test_une_erreur_fournisseur_n_est_pas_une_absence_de_candidats() -> None:
    port = FauxPort(resultats={"TOP_PERC_GAIN": ProviderError(162, "scanner refusé")})
    d, puits, _, _ = monter(port, definitions=(SCAN_A, SCAN_B))
    stats = asyncio.run(d.run())
    assert stats.provider_errors == 1
    assert stats.ingested == 1  # SCAN_B a bien abouti
    assert len(puits.lots) == 1


def test_une_NOTICE_fournisseur_n_est_pas_une_erreur() -> None:
    port = FauxPort(resultats={"TOP_PERC_GAIN": ProviderError(2104, "farm OK")})
    d, _, _, _ = monter(port)
    stats = asyncio.run(d.run())
    assert stats.notices == 1
    assert stats.provider_errors == 0


def test_une_erreur_de_transport_est_comptee_a_part() -> None:
    port = FauxPort(resultats={"TOP_PERC_GAIN": EdgeIbkrError("EOF")})
    d, _, _, _ = monter(port)
    stats = asyncio.run(d.run())
    assert stats.transport_errors == 1
    assert stats.ingested == 0


# -- bornes et arrêt -------------------------------------------------------


def test_max_scans_borne_l_execution() -> None:
    port = FauxPort()
    d, _, _, _ = monter(port, definitions=(SCAN_A, SCAN_B), max_scans=1)
    stats = asyncio.run(d.run())
    assert stats.scans == 1
    assert len(port.appels) == 1


def test_request_stop_interrompt_avant_tout_scan() -> None:
    port = FauxPort()
    d, _, _, _ = monter(port, definitions=(SCAN_A, SCAN_B))
    d.request_stop()
    stats = asyncio.run(d.run())
    assert stats.scans == 0
    assert port.appels == []


# -- refus de configuration ------------------------------------------------


def test_aucune_definition_est_refuse() -> None:
    """La découverte n'invente aucun scan par défaut."""
    horloge = Horloge()
    with pytest.raises(ValueError, match="définition"):
        ScannerDiscovery(
            port=FauxPort(),
            definitions=(),
            sink=Puits(),
            pacer=SlidingWindowPacer(clock=horloge),
            line_budget=LineBudget(2, hard_cap=1),
            sleep=Sommeil(horloge),
        )


def test_max_scans_invalide_est_refuse() -> None:
    horloge = Horloge()
    with pytest.raises(ValueError, match="max_scans"):
        ScannerDiscovery(
            port=FauxPort(),
            definitions=(SCAN_A,),
            sink=Puits(),
            pacer=SlidingWindowPacer(clock=horloge),
            line_budget=LineBudget(2, hard_cap=1),
            sleep=Sommeil(horloge),
            max_scans=0,
        )


def test_un_scan_ne_peut_pas_demander_plus_de_50_lignes() -> None:
    """Borne du contrat IBKR, portée par ScannerDefinition elle-même."""
    with pytest.raises(ValueError, match="number_of_rows"):
        ScannerDefinition(
            instrument="STK", location_code="STK.US.MAJOR", scan_code="X", number_of_rows=51
        )
