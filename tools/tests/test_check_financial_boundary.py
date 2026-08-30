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
        (
            "appel direct (témoin)",
            "def f(ib):\n    return ib.placeOrder(1, 2)\n",
            ("placeOrder", "call"),
        ),
        (
            "méthode liée",
            "def f(ib):\n    send = ib.placeOrder\n    return send\n",
            ("placeOrder", "attribute"),
        ),
        (
            "nom en chaîne",
            'def f(ib):\n    return getattr(ib, "reqPositions")\n',
            ("reqPositions", "string"),
        ),
        (
            "valeur de dictionnaire",
            'def f(ib):\n    return {"p": ib.reqAccountSummary}["p"]\n',
            ("reqAccountSummary", "attribute"),
        ),
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
    completed = subprocess.run(  # noqa: S603 (argv littéral, sans shell)
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


EXEMPTABLE_KINDS = {"string", "reference", "fragment", "binding"}


def test_la_cle_d_exemption_porte_la_forme_d_acces() -> None:
    """Sans le `kind` dans la clé, une exemption de chaîne couvrait un appel."""
    for key in gate.load_allowlist(_REPO_ROOT):
        kind = key.rsplit(":", 1)[-1]
        assert kind not in gate.NEVER_EXEMPTABLE_KINDS, key
        assert kind in EXEMPTABLE_KINDS, key


def test_les_deux_ensembles_de_formes_sont_disjoints_et_complets() -> None:
    """Aucune forme ne doit tomber entre les deux ensembles.

    Une forme inconnue des deux listes serait exemptable par défaut sans que
    personne l'ait décidé — c'est exactement le genre de trou que les audits
    précédents ont trouvé.
    """
    assert not (EXEMPTABLE_KINDS & gate.NEVER_EXEMPTABLE_KINDS)
    produced = {
        str(f["kind"])
        for f in gate.scan_python(_GATE, FORBIDDEN)
        + gate.scan_python_fragments(_GATE, gate.FALLBACK_FRAGMENTS)
    }
    assert produced <= EXEMPTABLE_KINDS | gate.NEVER_EXEMPTABLE_KINDS


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
    completed = subprocess.run(  # noqa: S603 (argv littéral, sans shell)
        [sys.executable, str(_GATE), str(tmp_path)], capture_output=True, text=True
    )
    payload = json.loads(completed.stdout)
    assert payload["ok"] is False, label
    assert any(f["kind"] == "call" for f in payload["findings"]), label


def test_les_repertoires_ecartes_sont_seulement_generes_ou_vendus() -> None:
    """Un nom qui peut désigner du code de production ne s'écarte pas.

    `.mypy_cache` et `.ruff_cache` sont des caches d'OUTIL : ignorés par Git,
    jamais livrés, régénérés à chaque exécution. Le cache de mypy sérialise
    les types des bibliothèques analysées — dont `ib_async`, donc les NOMS des
    capacités interdites : sans cet écart, la porte `python-quality` rendrait
    la porte `frontière financière` rouge à la deuxième exécution locale.
    C'est la même décision que pour `.venv`, qui contient déjà le code source
    d'`ib_async`. La porte protège ce que le dépôt CONTIENT.
    """
    assert gate.SKIP_PARTS == {
        ".git",
        ".venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
        ".vite",
    }


# ── 8e audit : l'IMPORT, la surface d'analyse et l'asymétrie TS/Python ────
#
# Trois familles reproduites :
#   1. `scan_python` ne visitait que `Call`, `Attribute` et `Constant`. Les
#      nœuds `ast.alias` — donc TOUTES les instructions `import` — n'étaient
#      jamais examinés : `from ib_insync.ib import placeOrder as _send` puis
#      `_send(ib, c, o)` passait la porte. Un `import … as` EST l'obtention
#      de la référence, sous forme statique et littérale.
#   2. Le manifeste déclare `scope: [runtime, tests, dependencies, routes,
#      permissions, ai_tools]` mais `CODE_SUFFIXES` ne couvrait ni `.sh`
#      (3 fichiers suivis, dont `tools/run_checks.sh`), ni les formats
#      déclaratifs qui portent routes, permissions et outils IA.
#   3. `scan_text` n'avait qu'un motif `symbole\s*\(` : `ib.placeOrder` et
#      `ib["reqPositions"]` échappaient en TypeScript alors que les MÊMES
#      formes étaient vues en Python.


def _scan_ts(tmp_path: Path, source: str, name: str = "module.ts") -> set[tuple[str, str]]:
    target = tmp_path / name
    target.write_text(source, encoding="utf-8")
    return {
        (str(f["symbol"]), str(f["kind"]))
        for f in gate.scan_text(target, FORBIDDEN, gate.FALLBACK_FRAGMENTS)
    }


def _run_gate_on(root: Path) -> dict[str, object]:
    completed = subprocess.run(  # noqa: S603 (argv littéral, sans shell)
        [sys.executable, str(_GATE), str(root)], capture_output=True, text=True
    )
    return json.loads(completed.stdout)


@pytest.mark.parametrize(
    ("label", "source", "expected"),
    [
        (
            "import avec alias",
            "from ib_insync.ib import placeOrder as _send\n\n\n"
            "def go(ib, c, o):\n    return _send(ib, c, o)\n",
            ("placeOrder", "import"),
        ),
        (
            "import nu jamais appelé",
            "from ib_insync.ib import reqPositions\n",
            ("reqPositions", "import"),
        ),
        (
            "module pointé",
            "import ib_insync.cancelOrder as _m\n",
            ("cancelOrder", "import"),
        ),
        (
            "module d'origine pointé",
            "from ib_insync.whatIfOrder import helper\n",
            ("whatIfOrder", "import"),
        ),
        (
            "renommage VERS un nom interdit",
            "import ib_insync as reqPnL\n",
            ("reqPnL", "import"),
        ),
    ],
)
def test_un_import_est_une_obtention_de_reference(
    tmp_path: Path, label: str, source: str, expected: tuple[str, str]
) -> None:
    """`import … as` est statique et littéral : la porte doit le voir."""
    assert expected in _scan(tmp_path, source), label


@pytest.mark.parametrize(
    ("label", "source", "expected"),
    [
        (
            "concaténation littérale",
            'def go(ib):\n    return getattr(ib, "place" + "Order")\n',
            "placeOrder",
        ),
        (
            "f-string entièrement littérale",
            'def go(ib):\n    return getattr(ib, f"reqPositions")\n',
            "reqPositions",
        ),
        (
            "littéral d'octets décodé",
            'def go(ib):\n    return getattr(ib, b"cancelOrder".decode())\n',
            "cancelOrder",
        ),
        (
            "chemin pointé en chaîne",
            'import importlib\n\n\ndef go():\n'
            '    return importlib.import_module("ib_insync.placeOrder")\n',
            "placeOrder",
        ),
    ],
)
def test_les_litteraux_composes_sont_resolus(
    tmp_path: Path, label: str, source: str, expected: str
) -> None:
    """Ce qui est STATIQUE et LITTÉRAL doit être résolu, même découpé."""
    assert expected in {symbol for symbol, _ in _scan(tmp_path, source)}, label


@pytest.mark.parametrize(
    ("label", "source", "expected"),
    [
        (
            "appel (témoin)",
            "export const f = (ib: any) => ib.placeOrder(1);\n",
            ("placeOrder", "call"),
        ),
        (
            "accès d'attribut",
            "export const f = (ib: any) => ib.placeOrder;\n",
            ("placeOrder", "attribute"),
        ),
        (
            "chaînage optionnel",
            "export const f = (ib: any) => ib?.reqAccountSummary;\n",
            ("reqAccountSummary", "attribute"),
        ),
        (
            "indexation par nom",
            'export const f = (ib: any) => ib["reqPositions"];\n',
            ("reqPositions", "reference"),
        ),
        (
            "destructuration",
            "export const f = (ib: any) => { const { placeOrder } = ib; return placeOrder; };\n",
            ("placeOrder", "reference"),
        ),
        (
            "destructuration avec alias",
            "export const f = (ib: any) => { const { reqPnL: r } = ib; return r; };\n",
            ("reqPnL", "reference"),
        ),
        (
            "import nommé",
            'import { cancelOrder } from "./ib";\nexport const f = cancelOrder;\n',
            ("cancelOrder", "import"),
        ),
        (
            "import avec alias",
            'import { reqPositions as read } from "./ib";\nexport const f = read;\n',
            ("reqPositions", "import"),
        ),
        (
            "import dynamique",
            'export const f = async () => (await import("./ib")).whatIfOrder;\n',
            ("whatIfOrder", "attribute"),
        ),
        ("require", 'const { reqExecutions } = require("./ib");\n', ("reqExecutions", "import")),
    ],
)
def test_l_analyseur_texte_est_aligne_sur_l_analyseur_python(
    tmp_path: Path, label: str, source: str, expected: tuple[str, str]
) -> None:
    """Les mêmes formes doivent être vues en TypeScript et en Python."""
    assert expected in _scan_ts(tmp_path, source), label


@pytest.mark.parametrize(
    ("label", "relative", "source"),
    [
        (
            "script shell — route courtier",
            "deploy.sh",
            '#!/usr/bin/env bash\n'
            'curl -s "https://localhost:5000/v1/api/iserver/account/orders" -X POST\n',
        ),
        (
            "script shell — symbole appelé",
            "infra/publish.sh",
            '#!/usr/bin/env bash\npython3 -c "import x; x.placeOrder(1, 2)"\n',
        ),
        (
            "OpenAPI — route",
            "apps/api/openapi.json",
            '{"paths": {"/v1/api/iserver/account/orders": {"post": {}}}}\n',
        ),
        (
            "YAML — permission",
            "manifests/tooling.yaml",
            "tools:\n  - name: broker\n    allowed_methods: [placeOrder]\n",
        ),
        (
            "TOML — route de worker",
            "worker/wrangler.toml",
            'routes = ["https://x/v1/api/iserver/account/orders"]\n',
        ),
        (
            "HTML — script en ligne",
            "apps/web/index.html",
            '<script>fetch("/v1/api/iserver/account/orders");</script>\n',
        ),
        (
            "Dockerfile — appel réseau",
            "infra/Dockerfile.python",
            'RUN curl "https://x/v1/api/iserver/account/orders"\n',
        ),
        (
            "workflow CI — étape shell",
            ".github/workflows/deploy.yml",
            'jobs:\n  a:\n    steps:\n      - run: curl "https://x/v1/api/iserver/account/orders"\n',
        ),
    ],
)
def test_la_surface_couvre_le_perimetre_declare(
    tmp_path: Path, label: str, relative: str, source: str
) -> None:
    """`scope: [runtime, tests, dependencies, routes, permissions, ai_tools]`.

    Routes et permissions vivent dans des fichiers shell et déclaratifs ; les
    ignorer laissait le périmètre déclaré plus large que le périmètre analysé.
    """
    target = tmp_path / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")
    assert _run_gate_on(tmp_path)["ok"] is False, label


def test_un_import_n_est_pas_exemptable(tmp_path: Path) -> None:
    """Un renommage est une obtention de référence, pas une mention."""
    assert "import" in gate.NEVER_EXEMPTABLE_KINDS
    _write_allowlist(tmp_path, "import")
    with pytest.raises(SystemExit) as raised:
        gate.load_allowlist(tmp_path)
    assert "jamais exemptables" in str(raised.value)


def test_le_vocabulaire_metier_ne_produit_pas_de_faux_positif(tmp_path: Path) -> None:
    """`portfolio` et `positions` sont le portefeuille MANUEL de Vertex.

    Le dépôt les emploie plus de 400 fois : module `vertex_api.portfolio`,
    clés de contenu, champs de DTO. Élargir la porte sans les traiter la
    rendrait illisible — donc inappliquée.
    """
    assert _scan(tmp_path, "from vertex_api.portfolio import build\n") == set()
    assert _scan(tmp_path, 'x = {"positions": [], "portfolio": 1}\n') == set()
    assert _scan_ts(tmp_path, "const id = data.portfolio.id;\n") == set()
    assert _scan_ts(tmp_path, "for (const p of record['positions']) void p;\n") == set()
    # …mais un contexte courtier explicite les fait ressortir.
    assert _scan_ts(
        tmp_path, 'const r = await fetch("/iserver/portfolio").then((x) => x.positions);\n'
    ) != set()


def test_les_formes_dynamiques_restent_hors_de_portee(tmp_path: Path) -> None:
    """Limite ASSUMÉE d'une analyse statique — elle est nommée, pas cachée.

    Un nom assemblé à l'exécution n'est pas littéral : aucun scanner statique
    ne le voit. Ce test fige la frontière pour qu'elle ne soit jamais
    présentée comme couverte.
    """
    assert _scan(tmp_path, 'def go(ib, part):\n    return getattr(ib, "place" + part)\n') == set()
    assert _scan(tmp_path, 'def go(ib, n):\n    return getattr(ib, f"req{n}")\n') == set()
    assert _scan(tmp_path, "def go(ib, name):\n    return ib.__getattribute__(name)\n") == set()


def test_le_docstring_ne_sur_promet_pas() -> None:
    """Le 8e audit a relevé une affirmation fausse : « couvre `getattr` ».

    La mention en chaîne couvre `getattr` avec un nom LITTÉRAL, jamais un nom
    construit. Une porte qui se décrit plus large qu'elle n'est fait échouer
    la revue suivante.
    """
    doc = gate.scan_python.__doc__ or ""
    assert "littéral" in doc.lower() or "litteral" in doc.lower()
    assert "construit" in doc.lower()


# ── Forme liste de l'allowlist : lisibilité sans relâchement ──────────────
#
# L'élargissement de la surface au 8e audit a fait passer les exemptions de 33
# à 76 clés. À cinq lignes chacune, l'allowlist devenait illisible — et une
# allowlist qu'on ne relit plus est exactement ce qui a permis au 7e audit d'y
# trouver une exemption couvrant autre chose que ce qu'elle annonçait.

def _write_allowlist_entry(root: Path, body: str) -> None:
    (root / "manifests").mkdir(exist_ok=True)
    (root / "manifests" / gate.ALLOWLIST_FILENAME).write_text(
        "allow:\n" + body, encoding="utf-8"
    )


def test_la_forme_liste_nomme_chaque_symbole(tmp_path: Path) -> None:
    _write_allowlist_entry(
        tmp_path,
        "  - path: a.py\n"
        "    symbols: [placeOrder, reqPositions]\n"
        "    kind: string\n"
        "    reason: motif suffisamment long pour passer le contrôle de longueur\n",
    )
    assert set(gate.load_allowlist(tmp_path)) == {
        "a.py:placeOrder:string",
        "a.py:reqPositions:string",
    }


def test_la_forme_liste_n_introduit_aucun_joker(tmp_path: Path) -> None:
    """`*` n'exempte que le symbole littéral `*`, jamais un fichier entier."""
    _write_allowlist_entry(
        tmp_path,
        '  - path: a.py\n'
        '    symbols: ["*"]\n'
        "    kind: string\n"
        "    reason: motif suffisamment long pour passer le contrôle de longueur\n",
    )
    assert set(gate.load_allowlist(tmp_path)) == {"a.py:*:string"}
    (tmp_path / "a.py").write_text('X = "placeOrder"\n', encoding="utf-8")
    assert _run_gate_on(tmp_path)["ok"] is False


def test_la_forme_liste_reste_soumise_aux_formes_non_exemptables(tmp_path: Path) -> None:
    _write_allowlist_entry(
        tmp_path,
        "  - path: a.py\n"
        "    symbols: [placeOrder]\n"
        "    kind: import\n"
        "    reason: motif suffisamment long pour passer le contrôle de longueur\n",
    )
    with pytest.raises(SystemExit) as raised:
        gate.load_allowlist(tmp_path)
    assert "jamais exemptables" in str(raised.value)


def test_une_entree_sans_aucun_symbole_est_refusee(tmp_path: Path) -> None:
    _write_allowlist_entry(
        tmp_path,
        "  - path: a.py\n"
        "    symbols: []\n"
        "    kind: string\n"
        "    reason: motif suffisamment long pour passer le contrôle de longueur\n",
    )
    with pytest.raises(SystemExit) as raised:
        gate.load_allowlist(tmp_path)
    assert "symbol" in str(raised.value)


def test_une_exemption_de_liste_sans_occurrence_est_dette_morte(tmp_path: Path) -> None:
    """La détection de dette morte reste par SYMBOLE, pas par entrée."""
    _write_allowlist_entry(
        tmp_path,
        "  - path: a.py\n"
        "    symbols: [placeOrder, reqPositions]\n"
        "    kind: string\n"
        "    reason: motif suffisamment long pour passer le contrôle de longueur\n",
    )
    (tmp_path / "a.py").write_text('X = "placeOrder"\n', encoding="utf-8")
    payload = _run_gate_on(tmp_path)
    assert payload["ok"] is False
    assert any(
        f["symbol"] == "STALE_ALLOWLIST_ENTRY" and "reqPositions" in str(f["path"])
        for f in payload["findings"]
    )


def test_les_limites_de_la_porte_sont_ecrites_dans_la_porte() -> None:
    """Une porte qui ne dit pas où elle s'arrête sera crue exhaustive."""
    assert len(gate.OUT_OF_STATIC_REACH) >= 6
    joined = " ".join(gate.OUT_OF_STATIC_REACH).lower()
    for expected in ("getattr", "__getattr__", "import *", "markdown"):
        assert expected in joined, expected


# ── Fabriquer le nom, pas seulement l'atteindre ───────────────────────────
#
# Énumération poursuivie au-delà des vecteurs signalés : une capacité interdite
# peut aussi être RECRÉÉE sous le toit de Vertex. Si le corps de la fonction
# atteint IBKR par un nom construit — hors de portée d'une analyse statique —,
# la définition est la SEULE trace visible.

@pytest.mark.parametrize(
    ("label", "source", "expected"),
    [
        ("fonction", "def placeOrder(ib, c, o):\n    return None\n", ("placeOrder", "definition")),
        (
            "fonction asynchrone",
            "async def reqPositions(ib):\n    return None\n",
            ("reqPositions", "definition"),
        ),
        ("classe", "class whatIfOrder:\n    pass\n", ("whatIfOrder", "definition")),
        ("affectation", "def f(x):\n    reqPnL = x\n    return reqPnL\n", ("reqPnL", "binding")),
        ("paramètre", "def f(cancelOrder):\n    return cancelOrder\n", ("cancelOrder", "binding")),
        (
            "boucle",
            "def f(xs):\n    for reqExecutions in xs:\n        return reqExecutions\n",
            ("reqExecutions", "binding"),
        ),
        (
            "gestionnaire d'exception",
            "def f():\n    try:\n        pass\n"
            "    except ValueError as reqIds:\n        return reqIds\n",
            ("reqIds", "binding"),
        ),
        (
            "global",
            "def f():\n    global reqGlobalCancel\n    return 1\n",
            ("reqGlobalCancel", "binding"),
        ),
    ],
)
def test_recreer_la_capacite_sous_un_autre_toit_est_vu(
    tmp_path: Path, label: str, source: str, expected: tuple[str, str]
) -> None:
    assert expected in _scan(tmp_path, source), label


def test_une_definition_n_est_pas_exemptable(tmp_path: Path) -> None:
    """`financial-safety.md` interdit d'AJOUTER la commande, pas seulement de
    l'appeler. Aucun motif ne rend légitime un `def placeOrder` chez Vertex."""
    assert "definition" in gate.NEVER_EXEMPTABLE_KINDS
    _write_allowlist(tmp_path, "definition")
    with pytest.raises(SystemExit) as raised:
        gate.load_allowlist(tmp_path)
    assert "jamais exemptables" in str(raised.value)


def test_une_liaison_reste_exemptable(tmp_path: Path) -> None:
    """Anti-vacuité : « executions » est aussi un mot anglais courant.

    Une variable locale n'est pas un point d'entrée ; la rendre non exemptable
    rendrait la porte inapplicable sans rien fermer.
    """
    assert "binding" not in gate.NEVER_EXEMPTABLE_KINDS
    _write_allowlist_entry(
        tmp_path,
        "  - path: a.py\n"
        "    symbol: executions\n"
        "    kind: binding\n"
        "    reason: motif suffisamment long pour passer le contrôle de longueur\n",
    )
    assert set(gate.load_allowlist(tmp_path)) == {"a.py:executions:binding"}


def test_le_vocabulaire_metier_echappe_aussi_a_ces_formes(tmp_path: Path) -> None:
    """`portfolio = ...` et `def positions(...)` sont partout dans Vertex."""
    assert _scan(tmp_path, "def f(row):\n    portfolio = row\n    return portfolio\n") == set()
    assert _scan(tmp_path, "def positions(ledger):\n    return ledger\n") == set()


def test_une_definition_typescript_est_vue(tmp_path: Path) -> None:
    assert ("placeOrder", "definition") in _scan_ts(
        tmp_path, "export function placeOrder(ib: any) { return ib; }\n"
    )
    assert ("reqPositions", "definition") in _scan_ts(
        tmp_path, "class reqPositions {}\n"
    )


def test_la_concatenation_litterale_est_repliee_aussi_en_texte(tmp_path: Path) -> None:
    """Dernière asymétrie relevée : Python repliait, TypeScript non."""
    assert ("placeOrder", "reference") in _scan_ts(
        tmp_path, 'export const f = (ib: any) => ib["place" + "Order"];\n'
    )
    assert ("reqPositions", "reference") in _scan_ts(
        tmp_path, "export const f = (ib: any) => ib['req' + 'Positions'];\n"
    )
    # …mais un morceau non littéral ne se replie pas : c'est un nom construit.
    assert _scan_ts(
        tmp_path, 'export const f = (ib: any, s: string) => ib["place" + s];\n'
    ) == set()


def test_les_deux_analyseurs_voient_les_memes_formes(tmp_path: Path) -> None:
    """Anti-régression d'asymétrie : la même source, deux langages.

    L'analyseur texte n'avait qu'un motif `symbole\\s*\\(` ; `ib.placeOrder` et
    `ib["reqPositions"]` passaient en TypeScript alors qu'ils étaient vus en
    Python. Ce test compare les deux analyseurs sur les formes communes.
    """
    cases = [
        ("appel", "x = ib.placeOrder(1)\n", "const x = ib.placeOrder(1);\n"),
        ("attribut", "x = ib.placeOrder\n", "const x = ib.placeOrder;\n"),
        ("indexation", 'x = ib["reqPositions"]\n', 'const x = ib["reqPositions"];\n'),
        ("définition", "def placeOrder():\n    pass\n", "function placeOrder() {}\n"),
        ("concaténation", 'x = ib["place" + "Order"]\n', 'const x = ib["place" + "Order"];\n'),
    ]
    for label, python_source, text_source in cases:
        seen_py = {symbol for symbol, _ in _scan(tmp_path, python_source)}
        seen_ts = {symbol for symbol, _ in _scan_ts(tmp_path, text_source)}
        assert seen_py == seen_ts != set(), f"{label} : {seen_py} vs {seen_ts}"


# ── La surface analysée doit suivre le dépôt ──────────────────────────────

#: Formats délibérément HORS de l'analyse, avec le motif de la décision.
#: Toute autre extension présente dans le dépôt doit être analysée : c'est
#: ainsi que `.sh` a pu manquer pendant huit audits.
DELIBERATELY_UNSCANNED = {
    ".md": "documentation — le manifeste la classe `comment_or_documentation: "
           "review_required`, pas `deny`",
    ".svg": "icône vectorielle — aucune exécution, aucune route",
    ".png": "image binaire",
    ".lock": "verrou de dépendances généré",
    ".gitkeep": "marqueur de répertoire vide",
    ".gitignore": "règles d'ignorance Git",
    ".gitattributes": "attributs Git",
    ".editorconfig": "réglages d'éditeur",
    ".css": "feuille de style — aucune capacité atteignable",
    ".pyc": "octet-code généré",
}


def test_aucun_format_du_depot_n_echappe_sans_decision_ecrite() -> None:
    """Le périmètre analysé doit couvrir tout ce que le dépôt contient.

    `CODE_SUFFIXES` ignorait `.sh` alors que trois scripts shell sont suivis,
    dont `tools/run_checks.sh` : `deploy.sh` appelant une route d'ordre par
    `curl` n'était vu par personne (8e audit). Ce test échoue dès qu'un format
    nouveau apparaît sans avoir été soit analysé, soit écarté par écrit.
    """
    tracked = subprocess.run(
        ["git", "ls-files", "-z"],  # noqa: S607 (git résolu par PATH, argv littéral)
        cwd=_REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout.split("\0")
    undecided: dict[str, str] = {}
    for name in tracked:
        if not name:
            continue
        path = _REPO_ROOT / name
        if any(part in gate.SKIP_PARTS for part in Path(name).parts):
            continue
        if gate.is_scanned(path):
            continue
        if path.suffix in DELIBERATELY_UNSCANNED or path.name in DELIBERATELY_UNSCANNED:
            continue
        undecided.setdefault(path.suffix or path.name, name)
    assert not undecided, (
        "format ni analysé ni écarté par écrit — décider, puis inscrire la "
        f"décision : {undecided}"
    )


def test_les_scripts_shell_du_depot_sont_bien_analyses() -> None:
    """Anti-vacuité du test précédent : le dépôt contient bien des `.sh`."""
    shell = [
        _REPO_ROOT / n
        for n in subprocess.run(
            ["git", "ls-files", "*.sh"],  # noqa: S607 (git résolu par PATH, argv littéral)
            cwd=_REPO_ROOT, capture_output=True, text=True, check=True,
        ).stdout.split()
    ]
    assert shell, "aucun script shell : le test ne prouverait rien"
    assert all(gate.is_scanned(p) for p in shell)
    assert ".sh" in gate.CODE_SUFFIXES


def test_les_repertoires_ecartes_restent_seulement_generes_ou_vendus() -> None:
    assert gate.SKIP_PARTS == {
        ".git", ".venv", "node_modules", "__pycache__", ".pytest_cache",
        ".mypy_cache", ".ruff_cache", "dist", ".vite",
    }
