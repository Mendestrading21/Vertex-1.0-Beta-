"""Preuve de la commande de sonde d'entitlements.

`tools/probe_entitlements.py` est le chemin par lequel Vertex verra pour la
PREMIÈRE fois des droits IBKR réels. Ce qui compte ici n'est pas qu'il
« marche » : c'est qu'il ne puisse pas mentir. Trois familles de tests :

1. il n'offre AUCUN chemin vers une capacité interdite ni vers un hôte non
   loopback ;
2. il refuse toute identité ambiguë au lieu d'en choisir une ;
3. un échec — timeout, erreur fournisseur, transport — ne devient jamais une
   preuve d'absence de droit, et n'écrit rien.

Le port IBKR est un faux local : aucun réseau, aucun TWS. Les gardes de
connexion réelles sont vérifiées directement sur l'adaptateur.
"""

from __future__ import annotations

import importlib.util
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import yaml

from vertex_core.contracts import SourceCapabilityStatus
from vertex_edge_ibkr.port import (
    CancellationOutcome,
    ContractSpec,
    EdgeIbkrError,
    MarketDataSnapshotResult,
    OperationToken,
    OptionChainDefinition,
    ProviderError,
    ProviderSessionStateError,
    ProviderStatusEvent,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TOOL = _REPO_ROOT / "tools" / "probe_entitlements.py"


def _load_tool() -> Any:
    spec = importlib.util.spec_from_file_location("probe_entitlements_tool", _TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tool = _load_tool()

T0 = datetime(2026, 8, 30, 14, 0, tzinfo=UTC)

UNDERLYING = ContractSpec(
    sec_type="STK", con_id=1001, symbol="SYN", exchange="SMART", currency="USD"
)
OPTION = ContractSpec(
    sec_type="OPT",
    con_id=2002,
    symbol="SYN",
    exchange="SMART",
    currency="USD",
    last_trade_date="20261218",
    strike=Decimal("100"),
    right="C",
    trading_class="SYN",
    multiplier="100",
)

CHAIN_SYN = OptionChainDefinition(
    exchange="SMART",
    underlying_con_id=1001,
    trading_class="SYN",
    multiplier="100",
    expirations=("20261218", "20270115"),
    strikes=(Decimal("95"), Decimal("100"), Decimal("105")),
)
#: Même échéance, autre `trading_class` ET autre multiplicateur : la
#: spécification interdit de les fusionner (mini-contrats, ajustements).
CHAIN_SYN1 = OptionChainDefinition(
    exchange="SMART",
    underlying_con_id=1001,
    trading_class="SYN1",
    multiplier="10",
    expirations=("20261218",),
    strikes=(Decimal("100"),),
)


class FauxPort:
    """Port IBKR minimal : enregistre CE QUI a été demandé, sans réseau."""

    def __init__(
        self,
        *,
        qualified: dict[str, tuple[ContractSpec, ...]] | None = None,
        chains: tuple[OptionChainDefinition, ...] = (CHAIN_SYN,),
        qualify_error: Exception | None = None,
        snapshot_error: Exception | None = None,
    ) -> None:
        self._qualified = qualified or {"STK": (UNDERLYING,), "OPT": (OPTION,)}
        self._chains = chains
        self._qualify_error = qualify_error
        self._snapshot_error = snapshot_error
        self.connected = False
        self.disconnected = False
        self.snapshot_calls: list[ContractSpec] = []
        self.cancelled: list[str] = []

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.disconnected = True

    async def server_time(self) -> datetime:
        return T0

    async def qualify_contracts(self, *specs: ContractSpec) -> tuple[ContractSpec, ...]:
        if self._qualify_error is not None:
            raise self._qualify_error
        return self._qualified.get(specs[0].sec_type, ())

    async def sec_def_opt_params(
        self, underlying: ContractSpec
    ) -> tuple[OptionChainDefinition, ...]:
        return self._chains

    async def market_data_snapshot(
        self,
        spec: ContractSpec,
        *,
        generic_ticks: tuple[int, ...] = (),
        market_data_type: int = 1,
        timeout_seconds: float | None = None,
    ) -> MarketDataSnapshotResult:
        self.snapshot_calls.append(spec)
        if self._snapshot_error is not None:
            raise self._snapshot_error
        return MarketDataSnapshotResult(
            envelopes=(),
            provider_errors=(),
            requested_market_data_type=market_data_type,
            reported_market_data_type=None,
            generic_ticks=generic_ticks,
            subscription_id=f"sub-{spec.con_id}",
            operation=OperationToken(
                journal_id="probe-journal",
                connection_epoch_at_start=7,
                provider_sequence_at_start=0,
                market_update_sequence_at_start=0,
            ),
            market_update_sequence_at_end=0,
            cancellation_outcome=CancellationOutcome.NOT_FOUND,
        )

    async def cancel_subscription(
        self, subscription_id: str
    ) -> CancellationOutcome:
        self.cancelled.append(subscription_id)
        return CancellationOutcome.CANCELLED

    def drain_provider_status_events(self) -> tuple[ProviderStatusEvent, ...]:
        return ()

    @property
    def pending_subscription_count(self) -> int:
        return 0


def _run(argv: list[str], port: FauxPort) -> int:
    return tool.main(
        argv,
        port_factory=lambda _arguments: (port, lambda: 7),
        clock=lambda: T0,
    )


_OPTION_ARGV = [
    "--option-expiry",
    "20261218",
    "--option-strike",
    "100",
    "--option-right",
    "C",
    "--option-trading-class",
    "SYN",
    "--option-exchange",
    "SMART",
]


# ── 1. Aucun chemin vers l'interdit ──────────────────────────────────────────


def _lignes_de_code(chemin: Path) -> list[str]:
    """Lignes exécutables : commentaires et docstrings écartés.

    Sans cela le balayage lirait la docstring qui EXPLIQUE l'absence de
    `--host`, et échouerait sur sa propre documentation.
    """
    lignes: list[str] = []
    dans_docstring = False
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        nue = ligne.strip()
        if nue.count('"""') == 1:
            dans_docstring = not dans_docstring
            continue
        if dans_docstring or nue.startswith("#") or not nue:
            continue
        lignes.append(ligne.split("  #")[0])
    return lignes


def test_aucune_option_host_n_est_offerte() -> None:
    """Ne PAS offrir le réglage est plus fort que le valider.

    L'adaptateur refuse déjà tout hôte ≠ 127.0.0.1 ; si la commande exposait
    `--host`, un futur contributeur pourrait croire ce réglage légitime.
    """
    parser = tool.build_parser()
    options = {
        chaine for action in parser._actions for chaine in action.option_strings
    }
    assert "--host" not in options
    code = _lignes_de_code(_TOOL)
    assert len(code) > 100, "le découpage ne voit presque rien : balayage aveugle"
    assert [ligne for ligne in code if "--host" in ligne] == []


def test_l_adaptateur_reel_refuse_un_client_id_nul() -> None:
    """La garde n'est pas réécrite ici : elle est LAISSÉE s'appliquer."""
    with pytest.raises(ValueError, match="client_id"):
        tool.build_adapter(port=7497, client_id=0)


def test_un_client_id_nul_sort_en_refus_et_ne_sonde_rien(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = tool.main(["--symbol", "SYN", "--dry-run", "--client-id", "0"])
    assert code == 2
    assert "client_id" in capsys.readouterr().err


def test_aucune_capacite_interdite_dans_le_fichier() -> None:
    """Balayage direct contre le manifeste, en plus de la porte CI globale."""
    manifeste = yaml.safe_load(
        (_REPO_ROOT / "manifests" / "forbidden-capabilities.yaml").read_text(encoding="utf-8")
    )
    interdits = {
        symbole
        for groupe in manifeste["forbidden_groups"]
        for symbole in groupe.get("symbols", ())
    }
    # 19 symboles au SHA courant ; le seuil garde le balayage honnête sans
    # se casser à chaque ajout au manifeste.
    assert len(interdits) >= 15, "le manifeste n'a presque rien livré : balayage aveugle"
    source = _TOOL.read_text(encoding="utf-8")
    trouves = sorted(s for s in interdits if re.search(rf"\b{re.escape(s)}\b", source))
    assert trouves == [], f"capacités interdites citées : {trouves}"


# ── 2. L'ambiguïté arrête la sonde ───────────────────────────────────────────


def test_dry_run_n_ouvre_aucune_ligne_de_donnees(capsys: pytest.CaptureFixture[str]) -> None:
    """Le mode à lancer en premier : il prouve la connexion et la chaîne, rien de plus."""
    port = FauxPort()
    assert _run(["--symbol", "SYN", "--dry-run"], port) == 0
    assert port.snapshot_calls == [], "une ligne de données a été ouverte en --dry-run"
    sortie = capsys.readouterr().out
    assert "con_id=1001" in sortie
    assert "trading_class=SYN" in sortie


def test_une_identite_ambigue_arrete_la_sonde(capsys: pytest.CaptureFixture[str]) -> None:
    """Deux contrats qualifiés : choisir « le premier » fabriquerait une identité."""
    autre = ContractSpec(
        sec_type="STK", con_id=1002, symbol="SYN", exchange="ARCA", currency="CAD"
    )
    port = FauxPort(qualified={"STK": (UNDERLYING, autre)})
    assert _run(["--symbol", "SYN", "--dry-run"], port) == 2
    erreur = capsys.readouterr().err
    assert "AMBIGUË" in erreur
    assert "con_id=1002" in erreur


def test_une_option_incompletement_nommee_est_refusee(
    capsys: pytest.CaptureFixture[str],
) -> None:
    port = FauxPort()
    argv = ["--symbol", "SYN", "--option-expiry", "20261218"]
    assert _run(argv, port) == 2
    erreur = capsys.readouterr().err
    assert "--option-strike" in erreur
    assert port.snapshot_calls == []


def test_une_echeance_absente_de_la_chaine_est_refusee(
    capsys: pytest.CaptureFixture[str],
) -> None:
    port = FauxPort()
    argv = ["--symbol", "SYN", *_OPTION_ARGV]
    argv[argv.index("20261218")] = "20301220"
    assert _run(argv, port) == 2
    assert "20301220" in capsys.readouterr().err
    assert port.snapshot_calls == []


def test_un_strike_absent_de_la_chaine_est_refuse(capsys: pytest.CaptureFixture[str]) -> None:
    port = FauxPort()
    argv = ["--symbol", "SYN", *_OPTION_ARGV]
    argv[argv.index("100")] = "101"
    assert _run(argv, port) == 2
    erreur = capsys.readouterr().err
    assert "101" in erreur and "plus proches" in erreur
    assert port.snapshot_calls == []


def test_deux_trading_class_a_meme_echeance_ne_sont_jamais_fusionnees() -> None:
    """Critère de sortie explicite de IBKR_ENTITLEMENT_PROBE.md.

    Les deux lignes partagent l'échéance et le strike ; seul le couple
    (exchange, trading_class) les distingue, et le multiplicateur diffère.
    Fusionner produirait un contrat de multiplicateur faux.
    """
    ligne = tool.select_chain_row(
        (CHAIN_SYN, CHAIN_SYN1), exchange="SMART", trading_class="SYN1"
    )
    assert ligne.trading_class == "SYN1"
    assert ligne.multiplier == "10"

    with pytest.raises(tool.ProbeRefusal, match="SYN2"):
        tool.select_chain_row((CHAIN_SYN, CHAIN_SYN1), exchange="SMART", trading_class="SYN2")


# ── 3. Un échec ne devient jamais une preuve d'absence de droit ──────────────


def test_une_erreur_fournisseur_reste_error_et_jamais_not_entitled(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """10197 = session concurrente. C'est un ERROR, pas un manque de droit."""
    port = FauxPort(snapshot_error=ProviderError(10197, "competing live session"))
    assert _run(["--symbol", "SYN", *_OPTION_ARGV], port) == 0
    sortie = capsys.readouterr().out
    assert "COMPETING_SESSION" in sortie
    # Le rappel de fin cite volontairement NOT_ENTITLED : ne lire que la matrice.
    matrice = [
        ligne for ligne in sortie.splitlines() if ligne.startswith(("option_", "underlying_"))
    ]
    assert matrice, "aucune ligne de matrice imprimée"
    assert [ligne for ligne in matrice if "NOT_ENTITLED" in ligne] == []
    assert [ligne for ligne in matrice if "ERROR" in ligne] != []


def test_un_echec_de_transport_ne_conclut_rien(capsys: pytest.CaptureFixture[str]) -> None:
    """Aucune matrice n'est imprimée : on ne conclut pas sur une connexion morte."""
    port = FauxPort(qualify_error=EdgeIbkrError("socket closed"))
    assert _run(["--symbol", "SYN", *_OPTION_ARGV], port) == 1
    capture = capsys.readouterr()
    assert "ÉCHEC" in capture.err
    assert "capacité" not in capture.out
    assert port.disconnected is False  # aucun adaptateur réel n'a été construit


def test_un_fence_de_session_interdit_la_matrice_et_la_persistance(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Une réponse traversant 1100/502 reste une panne, jamais une preuve."""
    ecritures: list[Any] = []
    monkeypatch.setattr(
        tool, "persist_snapshot", lambda snapshot, *, now: ecritures.append(snapshot)
    )
    port = FauxPort(
        snapshot_error=ProviderSessionStateError("synthetic provider-status fence")
    )

    code = _run(["--symbol", "SYN", *_OPTION_ARGV, "--persist"], port)

    capture = capsys.readouterr()
    assert code == 1
    assert "ÉCHEC" in capture.err
    assert "probe_id=" not in capture.out
    assert ecritures == []


def test_sans_persist_rien_n_est_ecrit(monkeypatch: pytest.MonkeyPatch) -> None:
    ecritures: list[Any] = []
    monkeypatch.setattr(
        tool, "persist_snapshot", lambda snapshot, *, now: ecritures.append(snapshot)
    )
    port = FauxPort()
    assert _run(["--symbol", "SYN", *_OPTION_ARGV], port) == 0
    assert ecritures == []

    assert _run(["--symbol", "SYN", *_OPTION_ARGV, "--persist"], port) == 0
    assert len(ecritures) == 1
    assert ecritures[0].source == "ibkr"


def test_la_preuve_persistee_n_emprunte_ni_synthetic_ni_demo() -> None:
    """Une sonde réelle publiée en `DEMO` ferait passer du réel pour de la démo
    — et l'inverse serait pire. L'habilitation est celle de l'edge."""
    assert tool.REAL_RIGHTS == "IBKR_MARKET_DATA_DISPLAY_ONLY"
    source = _TOOL.read_text(encoding="utf-8")
    assert 'rights="DEMO"' not in source
    assert 'rights="SYNTHETIC"' not in source


def test_la_matrice_publie_un_statut_par_champ(capsys: pytest.CaptureFixture[str]) -> None:
    """100 % des capacités publiées portent statut, raison et instant."""
    port = FauxPort()
    assert _run(["--symbol", "SYN", *_OPTION_ARGV], port) == 0
    sortie = capsys.readouterr().out
    assert "probe_id=" in sortie and "epoch=7" in sortie
    connus = {statut.value for statut in SourceCapabilityStatus}
    lignes = [
        ligne
        for ligne in sortie.splitlines()
        if ligne.startswith(("option_", "underlying_"))
    ]
    assert len(lignes) >= 10, f"seulement {len(lignes)} champs imprimés"
    for ligne in lignes:
        colonnes = ligne.split()
        assert colonnes[2] in connus, f"statut inconnu dans : {ligne}"


def test_la_preuve_porte_une_expiration_bornee() -> None:
    """Une capacité périmée redevient inconnue pour les gates : le TTL est requis."""
    port = FauxPort()
    captures: list[Any] = []

    async def _capture() -> Any:
        instantane = await tool.run_probe_session(
            port,
            tool.build_parser().parse_args(["--symbol", "SYN", *_OPTION_ARGV]),
            clock=lambda: T0,
            epoch_provider=lambda: 7,
        )
        captures.append(instantane)
        return instantane

    import asyncio

    asyncio.run(_capture())
    instantane = captures[0]
    assert instantane.expires_at == T0 + timedelta(hours=6)
    assert instantane.is_valid_at(T0 + timedelta(hours=5)) is True
    assert instantane.is_valid_at(T0 + timedelta(hours=7)) is False
