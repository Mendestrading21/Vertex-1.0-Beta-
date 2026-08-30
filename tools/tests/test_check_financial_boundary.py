"""Preuve d'exécution de la porte de frontière financière.

C'est la porte la plus critique du programme : elle garde l'interdiction
absolue des capacités IBKR de compte, ordre, position, P&L et exécution.

Le 6e audit adversarial a montré qu'elle était contournable de quatre façons
en code de PRODUCTION, et qu'elle n'inspectait même pas les tests alors que
`manifests/forbidden-capabilities.yaml` déclare
`scope: [runtime, tests, dependencies, routes, permissions, ai_tools]`.

Ces tests figent la fermeture. Ils ne prouvent PAS l'exhaustivité : un nom
construit à l'exécution reste hors de portée d'une analyse statique.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_GATE = _REPO_ROOT / "tools" / "check_financial_boundary.py"


def _load_gate():
    spec = importlib.util.spec_from_file_location("financial_boundary_gate", _GATE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = _load_gate()
FORBIDDEN = gate.FALLBACK_CALLS


def _scan(tmp_path: Path, source: str, name: str = "module.py") -> set[tuple[str, str]]:
    target = tmp_path / name
    target.write_text(source, encoding="utf-8")
    return {
        (str(f["symbol"]), str(f["kind"])) for f in gate.scan_python(target, FORBIDDEN)
    }


# ── Les quatre contournements de code de production ───────────────────────

@pytest.mark.parametrize(
    ("label", "source", "expected"),
    [
        ("appel direct (témoin)", "def f(ib):\n    return ib.placeOrder(1, 2)\n", ("placeOrder", "call")),
        ("méthode liée", "def f(ib):\n    send = ib.placeOrder\n    return send\n", ("placeOrder", "attribute")),
        ("nom en chaîne", 'def f(ib):\n    return getattr(ib, "reqPositions")\n', ("reqPositions", "string")),
        ("valeur de dictionnaire", 'def f(ib):\n    return {"p": ib.reqAccountSummary}["p"]\n', ("reqAccountSummary", "attribute")),
        ("alias", "def f(ib):\n    g = ib.reqPnL\n    return g\n", ("reqPnL", "attribute")),
    ],
)
def test_une_capacite_interdite_est_vue_meme_sans_appel(
    tmp_path: Path, label: str, source: str, expected: tuple[str, str]
) -> None:
    """Obtenir la RÉFÉRENCE suffit à appeler la capacité ailleurs."""
    assert expected in _scan(tmp_path, source), label


def test_les_symboles_ambigus_ne_sont_signales_qu_en_appel_ou_attribut(
    tmp_path: Path,
) -> None:
    """`portfolio` et `positions` sont aussi le vocabulaire métier de Vertex.

    Le portefeuille MANUEL de l'utilisateur a des « positions » : les signaler
    en tant que chaîne produirait 29 faux positifs et rendrait la porte
    illisible, donc inappliquée. Les formes dangereuses restent vues.
    """
    assert _scan(tmp_path, 'x = {"positions": [], "portfolio": 1}\n') == set()
    assert ("positions", "attribute") in _scan(tmp_path, "def f(ib):\n    return ib.positions\n")
    assert ("portfolio", "call") in _scan(tmp_path, "def f(ib):\n    return ib.portfolio()\n")


def test_un_module_sain_ne_declenche_rien(tmp_path: Path) -> None:
    """Anti-vacuité : la porte n'est pas un refus systématique."""
    assert _scan(tmp_path, "def f(ib):\n    return ib.reqMktData(1)\n") == set()


# ── Portée : les tests ne sont plus écartés ───────────────────────────────

def test_les_tests_sont_desormais_inspectes(tmp_path: Path) -> None:
    """`SKIP_PARTS` écartait `tests` : un appel interdit y passait la porte."""
    assert "tests" not in gate.SKIP_PARTS
    assert "tools" not in gate.SKIP_PARTS


def test_la_porte_est_verte_sur_le_depot() -> None:
    """Exécution réelle sur le dépôt tel qu'il est."""
    completed = subprocess.run(
        [sys.executable, str(_GATE)], cwd=_REPO_ROOT, capture_output=True, text=True
    )
    payload = json.loads(completed.stdout)
    assert payload["ok"] is True, payload["findings"][:10]
    assert completed.returncode == 0


# ── Allowlist ─────────────────────────────────────────────────────────────

def test_l_allowlist_exige_un_motif_ecrit(tmp_path: Path) -> None:
    (tmp_path / "manifests").mkdir()
    (tmp_path / "manifests" / gate.ALLOWLIST_FILENAME).write_text(
        "allow:\n  - path: a.py\n    symbol: placeOrder\n", encoding="utf-8"
    )
    with pytest.raises(SystemExit) as raised:
        gate.load_allowlist(tmp_path)
    assert "reason" in str(raised.value)


def test_une_allowlist_illisible_n_accorde_aucune_exemption(tmp_path: Path) -> None:
    """Fail-closed : un fichier d'exemptions cassé ne doit pas ouvrir la porte."""
    (tmp_path / "manifests").mkdir()
    (tmp_path / "manifests" / gate.ALLOWLIST_FILENAME).write_text(
        "allow: [ this is not: valid yaml\n", encoding="utf-8"
    )
    assert gate.load_allowlist(tmp_path) == {}


def test_le_depot_declare_ses_exemptions_avec_un_motif() -> None:
    allowlist = gate.load_allowlist(_REPO_ROOT)
    assert allowlist, "aucune exemption : le test ne prouverait rien"
    for key, reason in allowlist.items():
        assert len(reason.strip()) > 40, f"motif trop court pour {key}"


# ── 7e audit : l'allowlist ÉTAIT une cachette ─────────────────────────────
#
# La clé d'exemption était `path:symbol`, sans la FORME D'ACCÈS. Le motif écrit
# dans le manifeste — « il les nomme en CHAÎNES uniquement, jamais en appel ni
# en accès d'attribut » — était exact, mais n'était appliqué par RIEN : quatre
# capacités interdites réellement APPELÉES dans un fichier exempté
# franchissaient la porte.

def _write_allowlist(root: Path, kind: str) -> None:
    (root / "manifests").mkdir(exist_ok=True)
    (root / "manifests" / gate.ALLOWLIST_FILENAME).write_text(
        "allow:\n"
        "  - path: a.py\n"
        "    symbol: placeOrder\n"
        f"    kind: {kind}\n"
        "    reason: motif suffisamment long pour passer le contrôle de longueur\n",
        encoding="utf-8",
    )


@pytest.mark.parametrize("kind", sorted(gate.NEVER_EXEMPTABLE_KINDS))
def test_une_exemption_d_appel_ou_d_attribut_est_refusee(tmp_path: Path, kind: str) -> None:
    """Un appel et un accès d'attribut ATTEIGNENT la capacité.

    Ce n'est pas une exemption discutable : c'est exactement le chemin qu'on
    interdit. Le refus est au CHARGEMENT, pas au cas par cas.
    """
    _write_allowlist(tmp_path, kind)
    with pytest.raises(SystemExit) as raised:
        gate.load_allowlist(tmp_path)
    assert "jamais exemptables" in str(raised.value)


def test_une_exemption_de_chaine_reste_possible(tmp_path: Path) -> None:
    """Anti-vacuité : la mention en chaîne reste légitimement exemptable."""
    _write_allowlist(tmp_path, "string")
    assert gate.load_allowlist(tmp_path) == {
        "a.py:placeOrder:string": (
            "motif suffisamment long pour passer le contrôle de longueur"
        )
    }


def test_la_cle_d_exemption_porte_la_forme_d_acces() -> None:
    """Sans le `kind` dans la clé, une exemption de chaîne couvrait un appel."""
    for key in gate.load_allowlist(_REPO_ROOT):
        assert key.rsplit(":", 1)[-1] in {"string", "fragment"}


@pytest.mark.parametrize(
    ("label", "relative", "source"),
    [
        # `.mjs` n'était pas dans CODE_SUFFIXES — et le dépôt en contient déjà
        # (`worker/test/*.test.mjs`, `infra/compose/serve-static.mjs`).
        ("module ECMAScript", "apps/edge-ibkr/src/account.mjs",
         "export function a(ib){ return ib.reqPositions(); }\n"),
        # `build` et `fixtures` étaient écartés À TOUTE PROFONDEUR, donc aussi
        # à l'intérieur d'un `src/`.
        ("répertoire nommé build sous src", "apps/edge-ibkr/src/pkg/build/orders.py",
         "def a(ib):\n    return ib.placeOrder(1, 2)\n"),
        ("répertoire nommé fixtures sous src", "apps/api/src/pkg/fixtures/accounts.py",
         "def a(ib):\n    return ib.reqAccountSummary('All')\n"),
    ],
)
def test_les_angles_morts_structurels_sont_fermes(
    tmp_path: Path, label: str, relative: str, source: str
) -> None:
    target = tmp_path / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, str(_GATE), str(tmp_path)], capture_output=True, text=True
    )
    payload = json.loads(completed.stdout)
    assert payload["ok"] is False, label
    assert any(f["kind"] == "call" for f in payload["findings"]), label


def test_les_repertoires_ecartes_sont_seulement_generes_ou_vendus() -> None:
    """Un nom qui peut désigner du code de production ne s'écarte pas."""
    assert gate.SKIP_PARTS == {
        ".git",
        ".venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        "dist",
        ".vite",
    }
