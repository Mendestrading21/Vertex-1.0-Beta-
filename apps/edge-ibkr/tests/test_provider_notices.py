"""Une NOTICE fournisseur ne doit jamais masquer la raison honnête d'un champ.

DÉFAUT QUE CES TESTS EMPÊCHENT DE REVENIR. Sonde réelle du 2026-08-31 contre TWS
Live, GOOG 20260918 C 200, marché US fermé : `option_top_of_book.bid/ask/last`
sont ressortis en `ERROR / UNMAPPED_PROVIDER_ERROR_2104`. Or le code IBKR 2104
signifie « Market data farm connection is OK » — une notification de BON
fonctionnement. Elle avait été classée comme une erreur, et comme « ERROR
l'emporte pour les champs non observés », elle a remplacé la vraie raison
(`NO_OBSERVATION`, aucun tick parce que le marché était fermé).

Aucun faux `NOT_ENTITLED` n'avait été produit — la conception l'interdit déjà —
mais une raison trompeuse dans une matrice de droits reste un défaut : elle
ferait chercher une panne de connexion là où il n'y avait qu'un marché fermé.
"""

from __future__ import annotations

import asyncio

import pytest
from fakes import (
    FakeInformationPort,
    SteppingMonotonic,
    fixed_clock,
    full_greeks,
    full_quote,
    make_envelope,
    make_snapshot_result,
)

from vertex_core.contracts import SourceCapabilityStatus
from vertex_edge_ibkr.port import ContractSpec, ProviderErrorInfo
from vertex_edge_ibkr.probe import (
    INFORMATIONAL_CODE_RANGE,
    OPTION_TOP,
    PROVIDER_ERROR_MAPPING,
    EntitlementProbe,
    ProbeConfig,
    ProbeGate,
    is_informational_code,
    map_provider_error,
)

_STATUS = SourceCapabilityStatus

UNDERLYING = ContractSpec(sec_type="STK", con_id=1001, symbol="AAA", exchange="SMART")
OPTION = ContractSpec(
    sec_type="OPT",
    con_id=2002,
    symbol="AAA",
    exchange="SMART",
    trading_class="AAA",
    multiplier="100",
)


def make_probe(port: FakeInformationPort) -> EntitlementProbe:
    return EntitlementProbe(
        port,
        ProbeConfig(underlying=UNDERLYING, option=OPTION),
        gate=ProbeGate(),
        clock=fixed_clock(),
        monotonic=SteppingMonotonic(),
        epoch_provider=lambda: 5,
        probe_id_factory=lambda: "probe-notices-1",
    )


# -- classification --------------------------------------------------------


@pytest.mark.parametrize("code", [2100, 2104, 2106, 2158, 2200])
def test_la_plage_2100_2200_est_une_notice(code: int) -> None:
    assert is_informational_code(code) is True
    mapping = map_provider_error(code)
    assert mapping.informational is True
    assert mapping.reason_code == f"PROVIDER_NOTICE_{code}"


@pytest.mark.parametrize("code", [2099, 2201, 9999, 502])
def test_hors_plage_reste_une_erreur_non_concluante(code: int) -> None:
    assert is_informational_code(code) is False
    mapping = map_provider_error(code)
    assert mapping.informational is False
    assert mapping.status is _STATUS.ERROR
    assert mapping.reason_code == f"UNMAPPED_PROVIDER_ERROR_{code}"


@pytest.mark.parametrize("code", sorted(PROVIDER_ERROR_MAPPING))
def test_un_code_du_manifeste_garde_son_sens(code: int) -> None:
    """Le mapping exact reste l'autorité, la plage ne le recouvre jamais."""
    assert is_informational_code(code) is False
    assert map_provider_error(code) is PROVIDER_ERROR_MAPPING[code]


def test_la_plage_declaree_correspond_au_manifeste() -> None:
    assert INFORMATIONAL_CODE_RANGE == (2100, 2200)


# -- le défaut lui-même ----------------------------------------------------


def _port_avec_notice_et_sans_tick_option() -> FakeInformationPort:
    """Sous-jacent observé, option muette, plus une NOTICE 2104.

    C'est exactement la situation mesurée le 2026-08-31 : la connexion aux
    serveurs de données va bien (2104), mais l'option ne cote pas parce que le
    marché est fermé.
    """
    return FakeInformationPort(
        snapshot_behaviors={
            (1001, 1): make_snapshot_result(
                (make_envelope(full_quote(1001, with_generics=True), con_id=1001),)
            ),
            (2002, 1): make_snapshot_result(
                (make_envelope(full_greeks(2002, tick_type=13), con_id=2002),),
                errors=(ProviderErrorInfo(code=2104, message="Market data farm OK"),),
            ),
        }
    )


def test_une_notice_ne_remplace_pas_no_observation() -> None:
    """LE test de non-régression : la raison doit rester honnête."""
    snapshot = asyncio.run(make_probe(_port_avec_notice_et_sans_tick_option()).run())
    for champ in ("bid", "ask", "last"):
        preuve = snapshot.field_evidence(OPTION_TOP, champ)
        assert preuve is not None
        assert preuve.status is _STATUS.ERROR
        # AVANT le correctif : "UNMAPPED_PROVIDER_ERROR_2104" — trompeur.
        assert preuve.reason_code == "NO_OBSERVATION"
        assert preuve.provider_error_code is None


def test_une_notice_ne_produit_jamais_not_entitled() -> None:
    snapshot = asyncio.run(make_probe(_port_avec_notice_et_sans_tick_option()).run())
    statuts = {preuve.status for preuve in snapshot.fields}
    assert _STATUS.NOT_ENTITLED not in statuts


def test_une_notice_n_empeche_pas_une_preuve_positive() -> None:
    """Les Greeks observés restent AVAILABLE malgré la notice."""
    snapshot = asyncio.run(make_probe(_port_avec_notice_et_sans_tick_option()).run())
    assert snapshot.status_of("option_computations_live", "delta") is _STATUS.AVAILABLE


def test_une_VRAIE_erreur_l_emporte_toujours_sur_no_observation() -> None:
    """Le correctif ne doit pas avoir affaibli la règle « ERROR gagne »."""
    port = FakeInformationPort(
        snapshot_behaviors={
            (1001, 1): make_snapshot_result(
                (make_envelope(full_quote(1001, with_generics=True), con_id=1001),)
            ),
            (2002, 1): make_snapshot_result(
                (),
                errors=(
                    ProviderErrorInfo(code=2104, message="notice"),
                    ProviderErrorInfo(code=100, message="rate exceeded"),
                ),
            ),
        }
    )
    snapshot = asyncio.run(make_probe(port).run())
    preuve = snapshot.field_evidence(OPTION_TOP, "bid")
    assert preuve is not None
    assert preuve.status is _STATUS.ERROR
    assert preuve.reason_code == "MESSAGE_RATE_EXCEEDED"
    assert preuve.provider_error_code == 100
