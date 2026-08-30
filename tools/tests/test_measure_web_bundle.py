"""Preuve d'exécution du mesureur `tools/measure_web_bundle.py`.

Le budget de bundle initial ne vaut que si la mesure distingue réellement un
import statique d'un `import()` dynamique. Ces tests construisent des sorties
de build synthétiques minimales et vérifient cette distinction, plus les deux
façons de rendre le budget faussement vert : mesurer sans manifeste, et
supprimer les modules de graphes pour que « aucun moteur n'est dans la charge
initiale » devienne vrai par disparition.
"""

from __future__ import annotations

import gzip
import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TOOL = _REPO_ROOT / "tools" / "measure_web_bundle.py"


def _load() -> Any:
    spec = importlib.util.spec_from_file_location("measure_web_bundle_tool", _TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tool = _load()


def _dist(tmp_path: Path, manifest: dict[str, Any], files: dict[str, bytes]) -> Path:
    dist = tmp_path / "dist"
    (dist / ".vite").mkdir(parents=True)
    (dist / ".vite" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    for relative, payload in files.items():
        path = dist / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return dist


ENTRY_ONLY = {
    "index.html": {"isEntry": True, "file": "assets/entry.js", "css": ["assets/entry.css"]},
    "src/charts/echartsLoader.ts": {"file": "assets/echarts.js"},
}
FILES = {
    "assets/entry.js": b"a" * 4000,
    "assets/entry.css": b"b" * 2000,
    "assets/echarts.js": b"c" * 900000,
}


def test_un_chunk_atteint_seulement_par_import_dynamique_est_hors_charge_initiale(
    tmp_path: Path,
) -> None:
    manifest = json.loads(json.dumps(ENTRY_ONLY))
    manifest["index.html"]["dynamicImports"] = ["src/charts/echartsLoader.ts"]
    result = tool.measure(_dist(tmp_path, manifest, FILES))
    assert result["chart_engines_route_chunked"] is True
    assert result["chart_engines_in_initial_closure"] == []
    # 900 ko de graphe ne doivent pas apparaître dans la charge initiale.
    assert result["initial_gzip_bytes"] < 5000


def test_un_moteur_de_graphe_importe_statiquement_est_detecte(tmp_path: Path) -> None:
    manifest = json.loads(json.dumps(ENTRY_ONLY))
    manifest["index.html"]["imports"] = ["src/charts/echartsLoader.ts"]
    result = tool.measure(_dist(tmp_path, manifest, FILES))
    assert result["chart_engines_route_chunked"] is False
    assert result["chart_engines_in_initial_closure"] == ["src/charts/echartsLoader.ts"]


def test_la_fermeture_statique_est_transitive(tmp_path: Path) -> None:
    manifest = {
        "index.html": {"isEntry": True, "file": "assets/entry.js", "imports": ["_a.js"]},
        "_a.js": {"file": "assets/a.js", "imports": ["_b.js"]},
        "_b.js": {"file": "assets/b.js"},
        "src/charts/echartsLoader.ts": {"file": "assets/echarts.js"},
    }
    files = {
        "assets/entry.js": b"a" * 100,
        "assets/a.js": b"b" * 100,
        "assets/b.js": b"c" * 100,
        "assets/echarts.js": b"d" * 100,
    }
    result = tool.measure(_dist(tmp_path, manifest, files))
    assert result["initial_chunk_count"] == 3


def test_un_cycle_d_imports_ne_boucle_pas(tmp_path: Path) -> None:
    manifest = {
        "index.html": {"isEntry": True, "file": "assets/entry.js", "imports": ["_a.js"]},
        "_a.js": {"file": "assets/a.js", "imports": ["index.html"]},
        "src/charts/echartsLoader.ts": {"file": "assets/echarts.js"},
    }
    files = {
        "assets/entry.js": b"a" * 100,
        "assets/a.js": b"b" * 100,
        "assets/echarts.js": b"c" * 100,
    }
    assert tool.measure(_dist(tmp_path, manifest, files))["initial_chunk_count"] == 2


def test_la_taille_est_bien_le_gzip_du_fichier(tmp_path: Path) -> None:
    """La mesure ne relaie pas un chiffre imprimé par l'outil de build."""
    manifest = {
        "index.html": {"isEntry": True, "file": "assets/entry.js"},
        "src/charts/echartsLoader.ts": {"file": "assets/echarts.js"},
    }
    payload = bytes(range(256)) * 40
    files = {"assets/entry.js": payload, "assets/echarts.js": b"x"}
    result = tool.measure(_dist(tmp_path, manifest, files))
    attendu = len(gzip.compress(payload, compresslevel=tool.GZIP_LEVEL, mtime=0))
    assert result["initial_gzip_bytes"] == attendu


def test_un_manifeste_absent_interdit_toute_mesure(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    with pytest.raises(tool.BundleError):
        tool.measure(dist)


def test_un_manifeste_sans_entree_interdit_toute_mesure(tmp_path: Path) -> None:
    manifest = {"src/charts/echartsLoader.ts": {"file": "assets/echarts.js"}}
    with pytest.raises(tool.BundleError):
        tool.measure(_dist(tmp_path, manifest, {"assets/echarts.js": b"x"}))


def test_supprimer_les_modules_de_graphes_ne_rend_pas_le_budget_vrai(tmp_path: Path) -> None:
    """Sinon le budget de découpage se satisferait en supprimant les graphes."""
    manifest = {"index.html": {"isEntry": True, "file": "assets/entry.js"}}
    with pytest.raises(tool.BundleError):
        tool.measure(_dist(tmp_path, manifest, {"assets/entry.js": b"x"}))


def test_un_chunk_reference_mais_non_defini_interdit_toute_mesure(tmp_path: Path) -> None:
    """Mesurer le reste sous-estimerait la charge initiale."""
    manifest = {
        "index.html": {"isEntry": True, "file": "assets/entry.js", "imports": ["_absent.js"]},
        "src/charts/echartsLoader.ts": {"file": "assets/echarts.js"},
    }
    files = {"assets/entry.js": b"a", "assets/echarts.js": b"b"}
    with pytest.raises(tool.BundleError):
        tool.measure(_dist(tmp_path, manifest, files))


def test_un_fichier_manquant_sur_disque_interdit_toute_mesure(tmp_path: Path) -> None:
    manifest = {
        "index.html": {"isEntry": True, "file": "assets/entry.js"},
        "src/charts/echartsLoader.ts": {"file": "assets/echarts.js"},
    }
    with pytest.raises(tool.BundleError):
        tool.measure(_dist(tmp_path, manifest, {"assets/echarts.js": b"b"}))


# ── 9e audit : le CSS pouvait sortir de la charge initiale sans rougir ───────
#
# Mutant survivant mesuré : remplacer `[record["file"], *record.get("css", ())]`
# par `[record["file"]]` ne faisait rougir AUCUN test, alors que le chiffre
# publié tombait de 118 291 à 110 433 octets — 6,6 % du budget qui disparaît
# d'un coup. Un budget qui rétrécit tout seul est un budget qui ment.


def test_le_css_de_l_entree_compte_dans_la_charge_initiale(tmp_path: Path) -> None:
    """Le CSS est TÉLÉCHARGÉ avec l'entrée : il est dans la charge initiale.

    Ce test tue le mutant : sans le CSS, la mesure vaudrait la seule taille de
    `entry.js`.
    """
    js = b"const a = 1;\n" * 40
    css = b".vx { color: #fff; }\n" * 40
    dist = _dist(tmp_path, ENTRY_ONLY, {"assets/entry.js": js, "assets/entry.css": css})

    mesure = tool.measure(dist)
    fichiers = mesure["initial_files"]

    assert "assets/entry.css" in fichiers, (
        "le CSS de l'entrée est absent de la charge initiale : le navigateur le "
        "télécharge pourtant avant le premier rendu"
    )
    attendu = fichiers["assets/entry.js"] + fichiers["assets/entry.css"]
    assert mesure["initial_gzip_bytes"] == attendu
    # Anti-vacuité : sans cette borne, un CSS vide rendrait l'égalité vraie
    # même si le CSS était retiré du calcul.
    assert fichiers["assets/entry.css"] > 0


def test_retirer_le_css_du_calcul_ferait_chuter_la_mesure(tmp_path: Path) -> None:
    """Le test précédent ne vaut que si le CSS pèse assez pour être vu.

    On mesure l'écart réel : c'est lui que le mutant faisait disparaître en
    silence sur le dépôt réel (118 291 → 110 433 octets).
    """
    js = b"const a = 1;\n" * 40
    css = b".vx { color: #fff; }\n" * 200
    dist = _dist(tmp_path, ENTRY_ONLY, {"assets/entry.js": js, "assets/entry.css": css})

    mesure = tool.measure(dist)
    sans_css = mesure["initial_files"]["assets/entry.js"]
    assert mesure["initial_gzip_bytes"] > sans_css, (
        "la mesure avec et sans CSS est identique : ce test ne prouverait rien"
    )
