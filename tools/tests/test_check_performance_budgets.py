"""Preuve d'exécution de la porte `tools/check_performance_budgets.py`.

Chaque règle est prouvée par injection : on construit un dépôt minimal, on y
introduit exactement le défaut visé, et on vérifie que la porte le signale. Une
porte de performance qui ne signalerait rien laisserait passer précisément ce
qu'elle est censée empêcher — un budget « satisfait » sans mesure.

Le contrôle symétrique compte autant : un rapport complet et conforme doit
passer. Sans lui, la porte pourrait bloquer par accident et son verdict ne
voudrait rien dire.

Périmètre prouvé ici : les règles de la porte. Ces tests ne prouvent PAS que
les mesures elles-mêmes sont justes ; c'est le rôle de
`test_measure_web_bundle.py` pour le bundle, et d'une campagne de mesure encore
absente pour la latence API (voir `required_measurements`, statut
`NOT_YET_MEASURED`).
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_GATE = _REPO_ROOT / "tools" / "check_performance_budgets.py"


def _load_gate() -> Any:
    spec = importlib.util.spec_from_file_location("check_performance_budgets_gate", _GATE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = _load_gate()

TODAY = dt.date(2026, 8, 30)

# Manifeste minimal : uniquement ce que la porte lit. Les valeurs sont
# arbitraires et SYNTHETIC ; elles ne décrivent aucune machine réelle.
BASE_MANIFEST: dict[str, Any] = {
    "policy": {"missing_measurement_is_pass": False},
    "enforcement": {"absolute_targets_block_pr": False},
    "measurement": {"minimum_samples": {"p95": 1000, "p99": 10000}},
    "profiles": {
        "P-CI": {"absolute_release_gate": False, "required_metadata": ["cpu", "os_kernel"]},
        "P-LOCAL": {"absolute_release_gate": True, "required_metadata": ["cpu"]},
    },
    "regression": {
        "warning_fraction": 0.10,
        "block_fraction": 0.20,
        "block_after_comparable_repetitions": 3,
    },
    "observability": {"forbidden_metric_labels": ["ticker", "portfolio_id", "trace_id"]},
    "hard_failures": ["durable_event_loss"],
    "frontend": {"bundles": {"initial_gzip_recommended_max_bytes": 1000}},
    "hot_paths": {
        "HP-03": {
            "segments": [
                {"id": "hot_api_snapshot_server", "objective_p95_ms": 150},
            ]
        }
    },
    "required_measurements": [
        {
            "metric_id": "frontend.bundles.initial_gzip_bytes",
            "kind": "max",
            "budget_path": "frontend.bundles.initial_gzip_recommended_max_bytes",
            "unit": "byte",
            "status": "MEASURED",
            "machine_independent": True,
        }
    ],
}

#: Budget SENSIBLE À LA MACHINE : une latence mesurée sur un coureur partagé ne
#: dit pas grand-chose de la machine cible. C'est le seul cas où un profil sans
#: autorité absolue a le droit de rétrograder un dépassement.
LATENCE_SPEC: dict[str, Any] = {
    "metric_id": "api.page_snapshot.hot_api_snapshot_server.latency_ms.p95",
    "kind": "max",
    "budget_path": "hot_paths.HP-03.segments#hot_api_snapshot_server.objective_p95_ms",
    "unit": "ms",
    "status": "MEASURED",
    "machine_independent": False,
}

BASE_REPORT: dict[str, Any] = {
    "profile_id": "P-CI",
    "runner_metadata": {"cpu": "x86_64 x2", "os_kernel": "Linux 6.0"},
    "measurements": [
        {"metric_id": "frontend.bundles.initial_gzip_bytes", "value": 500, "samples": 1}
    ],
    "hard_failures_observed": [],
}


def _write(tmp_path: Path, manifest: dict[str, Any], report: dict[str, Any]) -> tuple[Path, Path]:
    """Écrit manifeste et rapport, et recale le hash de provenance du rapport.

    Le hash est recalculé APRÈS écriture du manifeste : un test qui figerait un
    hash constant ne testerait plus que sa propre constante.
    """
    manifest_path = tmp_path / "manifests" / "performance-budgets.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")

    report_path = tmp_path / "report.json"
    if "manifest_hash" not in report:
        report = {**report, "manifest_hash": gate.manifest_hash(manifest_path)}
    report_path.write_text(json.dumps(report), encoding="utf-8")
    return tmp_path, report_path


def _codes(tmp_path: Path, manifest: dict[str, Any], report: dict[str, Any]) -> set[str]:
    root, report_path = _write(tmp_path, manifest, report)
    result = gate.check(root, report_path, TODAY)
    return {finding["code"] for finding in result["findings"]}


def _run(tmp_path: Path, manifest: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    root, report_path = _write(tmp_path, manifest, report)
    return gate.check(root, report_path, TODAY)


# ── contrôle symétrique : un rapport conforme passe ──────────────────────────


def test_un_rapport_complet_et_conforme_passe(tmp_path: Path) -> None:
    result = _run(tmp_path, BASE_MANIFEST, BASE_REPORT)
    assert result["ok"], result["findings"]
    assert result["findings"] == []


# ── règle 5 : la règle qui justifie la porte ─────────────────────────────────


def test_un_budget_exige_sans_mesure_echoue(tmp_path: Path) -> None:
    """`policy.missing_measurement_is_pass: false`, rendu exécutable."""
    report = {**BASE_REPORT, "measurements": []}
    assert "missing_measurement" in _codes(tmp_path, BASE_MANIFEST, report)


def test_un_rapport_vide_ne_passe_pas_par_absence(tmp_path: Path) -> None:
    """Le périmètre vient du manifeste, jamais du rapport.

    Si le rapport déclarait son propre périmètre, livrer un rapport vide
    rendrait la porte verte. Ce test fige l'inverse.
    """
    report = {**BASE_REPORT, "measurements": []}
    result = _run(tmp_path, BASE_MANIFEST, report)
    assert not result["ok"]


def test_un_manifeste_sans_mesure_exigee_est_refuse(tmp_path: Path) -> None:
    """Vider `required_measurements` est l'autre façon de vider la porte."""
    manifest = {**BASE_MANIFEST, "required_measurements": []}
    root, report_path = _write(tmp_path, manifest, BASE_REPORT)
    with pytest.raises(gate.DocumentError):
        gate.check(root, report_path, TODAY)


# ── règles 6 et 7 : la dette non mesurée reste datée ─────────────────────────


@pytest.mark.parametrize("champ", ["owner", "reason", "expires_at", "closure_criterion"])
def test_une_mesure_absente_sans_exception_complete_echoue(tmp_path: Path, champ: str) -> None:
    entry = {
        "metric_id": "api.latence.p95",
        "kind": "max",
        "budget_path": "hot_paths.HP-03.segments#hot_api_snapshot_server.objective_p95_ms",
        "status": "NOT_YET_MEASURED",
        "owner": "équipe",
        "reason": "motif écrit",
        "expires_at": "2026-12-31",
        "closure_criterion": "critère écrit",
    }
    del entry[champ]
    manifest = {
        **BASE_MANIFEST,
        "required_measurements": [*BASE_MANIFEST["required_measurements"], entry],
    }
    assert "unmeasured_without_exception" in _codes(tmp_path, manifest, BASE_REPORT)


def test_une_exception_perimee_echoue(tmp_path: Path) -> None:
    entry = {
        "metric_id": "api.latence.p95",
        "kind": "max",
        "budget_path": "hot_paths.HP-03.segments#hot_api_snapshot_server.objective_p95_ms",
        "status": "NOT_YET_MEASURED",
        "owner": "équipe",
        "reason": "motif écrit",
        "expires_at": "2026-08-29",  # la veille de TODAY
        "closure_criterion": "critère écrit",
    }
    manifest = {
        **BASE_MANIFEST,
        "required_measurements": [*BASE_MANIFEST["required_measurements"], entry],
    }
    assert "expired_exception" in _codes(tmp_path, manifest, BASE_REPORT)


def test_une_exception_valide_et_datee_passe(tmp_path: Path) -> None:
    entry = {
        "metric_id": "api.latence.p95",
        "kind": "max",
        "budget_path": "hot_paths.HP-03.segments#hot_api_snapshot_server.objective_p95_ms",
        "status": "NOT_YET_MEASURED",
        "owner": "équipe",
        "reason": "motif écrit",
        "expires_at": "2026-12-31",
        "closure_criterion": "critère écrit",
    }
    manifest = {
        **BASE_MANIFEST,
        "required_measurements": [*BASE_MANIFEST["required_measurements"], entry],
    }
    assert _run(tmp_path, manifest, BASE_REPORT)["ok"]


# ── règles 2, 3, 4 : provenance ──────────────────────────────────────────────


def test_un_rapport_mesure_contre_un_autre_manifeste_echoue(tmp_path: Path) -> None:
    report = {**BASE_REPORT, "manifest_hash": "0" * 64}
    assert "manifest_drift" in _codes(tmp_path, BASE_MANIFEST, report)


def test_un_profil_inconnu_echoue(tmp_path: Path) -> None:
    report = {**BASE_REPORT, "profile_id": "P-INVENTE"}
    assert "unknown_profile" in _codes(tmp_path, BASE_MANIFEST, report)


def test_une_metadonnee_de_profil_absente_echoue(tmp_path: Path) -> None:
    report = {**BASE_REPORT, "runner_metadata": {"cpu": "x86_64 x2"}}
    assert "missing_profile_metadata" in _codes(tmp_path, BASE_MANIFEST, report)


def test_une_metadonnee_vide_ne_compte_pas_comme_presente(tmp_path: Path) -> None:
    """Une chaîne vide décrit une machine aussi mal qu'un champ absent."""
    report = {**BASE_REPORT, "runner_metadata": {"cpu": "x86_64 x2", "os_kernel": ""}}
    assert "missing_profile_metadata" in _codes(tmp_path, BASE_MANIFEST, report)


# ── règle 8 : un budget introuvable n'est pas un budget tenu ─────────────────


def test_un_budget_path_qui_ne_resout_pas_echoue(tmp_path: Path) -> None:
    manifest = {
        **BASE_MANIFEST,
        "required_measurements": [
            {**BASE_MANIFEST["required_measurements"][0], "budget_path": "frontend.absent.valeur"}
        ],
    }
    assert "unresolvable_budget_path" in _codes(tmp_path, manifest, BASE_REPORT)


def test_un_segment_est_adresse_par_identifiant_pas_par_position(tmp_path: Path) -> None:
    """`segments#id` doit suivre l'identifiant même si l'ordre change."""
    manifest = json.loads(json.dumps(BASE_MANIFEST))
    manifest["hot_paths"]["HP-03"]["segments"].insert(0, {"id": "autre", "objective_p95_ms": 1})
    manifest["required_measurements"] = [
        {
            "metric_id": "api.latence.p95",
            "kind": "max",
            "budget_path": "hot_paths.HP-03.segments#hot_api_snapshot_server.objective_p95_ms",
            "status": "MEASURED",
            "machine_independent": False,
        }
    ]
    report = {
        **BASE_REPORT,
        "measurements": [{"metric_id": "api.latence.p95", "value": 100, "samples": 1000}],
    }
    result = _run(tmp_path, manifest, report)
    # 100 ms est sous le budget 150 ms du bon segment ; il dépasserait le
    # budget 1 ms du segment inséré en tête. Un verdict vert prouve que la
    # résolution suit l'identifiant.
    assert result["ok"], result["findings"]


# ── règle 9 : un percentile sans échantillons n'est pas une mesure ───────────


def test_un_p95_sous_le_minimum_d_echantillons_echoue(tmp_path: Path) -> None:
    manifest = {
        **BASE_MANIFEST,
        "required_measurements": [
            {
                "metric_id": "api.latence.p95",
                "kind": "max",
                "budget_path": "hot_paths.HP-03.segments#hot_api_snapshot_server.objective_p95_ms",
                "status": "MEASURED",
            }
        ],
    }
    report = {
        **BASE_REPORT,
        "measurements": [{"metric_id": "api.latence.p95", "value": 12, "samples": 12}],
    }
    assert "insufficient_samples" in _codes(tmp_path, manifest, report)


def test_un_percentile_sans_champ_samples_echoue(tmp_path: Path) -> None:
    manifest = {
        **BASE_MANIFEST,
        "required_measurements": [
            {
                "metric_id": "api.latence.p95",
                "kind": "max",
                "budget_path": "hot_paths.HP-03.segments#hot_api_snapshot_server.objective_p95_ms",
                "status": "MEASURED",
            }
        ],
    }
    report = {**BASE_REPORT, "measurements": [{"metric_id": "api.latence.p95", "value": 12}]}
    assert "insufficient_samples" in _codes(tmp_path, manifest, report)


# ── règle 10 : aucun second canal de chiffres ────────────────────────────────


def test_une_mesure_non_declaree_echoue(tmp_path: Path) -> None:
    report = {
        **BASE_REPORT,
        "measurements": [
            *BASE_REPORT["measurements"],
            {"metric_id": "frontend.bundles.une_metrique_flatteuse", "value": 1, "samples": 1},
        ],
    }
    assert "undeclared_measurement" in _codes(tmp_path, BASE_MANIFEST, report)


# ── règle 11 : dépassement, selon l'autorité du profil ───────────────────────


def test_un_depassement_bloque_sous_un_profil_a_autorite_absolue(tmp_path: Path) -> None:
    report = {
        **BASE_REPORT,
        "profile_id": "P-LOCAL",
        "runner_metadata": {"cpu": "x86_64 x2"},
        "measurements": [
            {"metric_id": "frontend.bundles.initial_gzip_bytes", "value": 5000, "samples": 1}
        ],
    }
    result = _run(tmp_path, BASE_MANIFEST, report)
    assert "budget_exceeded" in {f["code"] for f in result["findings"]}
    assert not result["ok"]


def test_un_depassement_sensible_a_la_machine_est_enregistre_sans_bloquer(
    tmp_path: Path,
) -> None:
    """`enforcement.absolute_targets_block_pr: false` — enregistré, pas perdu.

    Ce report vaut UNIQUEMENT pour un budget dont la valeur dépend de la
    machine. Une latence p95 mesurée sur un coureur GitHub partagé ne dit rien
    de la machine cible ; la rendre bloquante ferait rougir la CI pour du bruit
    d'ordonnancement. Le dépassement est enregistré, jamais perdu.
    """
    manifest = json.loads(json.dumps(BASE_MANIFEST))
    manifest["required_measurements"] = [LATENCE_SPEC]
    report = {
        **BASE_REPORT,
        "measurements": [
            {
                "metric_id": "api.page_snapshot.hot_api_snapshot_server.latency_ms.p95",
                "value": 900,
                "samples": 5000,
            }
        ],
    }
    result = _run(tmp_path, manifest, report)
    assert result["ok"], result["findings"]
    assert [w["code"] for w in result["warnings"]] == ["budget_exceeded"]


def test_un_budget_booleen_faux_bloque_a_tout_profil(tmp_path: Path) -> None:
    manifest = json.loads(json.dumps(BASE_MANIFEST))
    manifest["frontend"]["bundles"]["chart_engines_route_chunked"] = True
    manifest["required_measurements"] = [
        {
            "metric_id": "frontend.bundles.chart_engines_route_chunked",
            "kind": "boolean_true",
            "budget_path": "frontend.bundles.chart_engines_route_chunked",
            "status": "MEASURED",
        }
    ]
    report = {
        **BASE_REPORT,
        "measurements": [
            {"metric_id": "frontend.bundles.chart_engines_route_chunked", "value": False}
        ],
    }
    result = _run(tmp_path, manifest, report)
    assert not result["ok"]
    assert result["findings"][0]["code"] == "budget_exceeded"


def test_une_valeur_non_numerique_pour_un_budget_max_echoue(tmp_path: Path) -> None:
    report = {
        **BASE_REPORT,
        "measurements": [
            {"metric_id": "frontend.bundles.initial_gzip_bytes", "value": "petit", "samples": 1}
        ],
    }
    assert "report_unusable" in _codes(tmp_path, BASE_MANIFEST, report)


def test_un_booleen_ne_satisfait_pas_un_budget_numerique(tmp_path: Path) -> None:
    """`True` vaut 1 en Python ; il ne doit pas passer pour une mesure d'octets."""
    report = {
        **BASE_REPORT,
        "measurements": [
            {"metric_id": "frontend.bundles.initial_gzip_bytes", "value": True, "samples": 1}
        ],
    }
    assert "report_unusable" in _codes(tmp_path, BASE_MANIFEST, report)


# ── règle 12 : régression relative ───────────────────────────────────────────


def test_une_regression_repetee_bloque_meme_sous_p_ci(tmp_path: Path) -> None:
    """`enforcement.relative_regressions_block_pr_when_repeated: true`."""
    report = {
        **BASE_REPORT,
        "measurements": [
            {
                "metric_id": "frontend.bundles.initial_gzip_bytes",
                "value": 600,
                "samples": 1,
                "baseline_value": 400,  # +50 %
                "consecutive_comparable_regressions": 3,
            }
        ],
    }
    result = _run(tmp_path, BASE_MANIFEST, report)
    assert "regression_blocked" in {f["code"] for f in result["findings"]}


def test_une_regression_non_repetee_avertit_sans_bloquer(tmp_path: Path) -> None:
    report = {
        **BASE_REPORT,
        "measurements": [
            {
                "metric_id": "frontend.bundles.initial_gzip_bytes",
                "value": 600,
                "samples": 1,
                "baseline_value": 400,
                "consecutive_comparable_regressions": 1,
            }
        ],
    }
    result = _run(tmp_path, BASE_MANIFEST, report)
    assert result["ok"]
    assert [w["code"] for w in result["warnings"]] == ["regression_warning"]


def test_une_amelioration_n_est_ni_bloquante_ni_avertissement(tmp_path: Path) -> None:
    report = {
        **BASE_REPORT,
        "measurements": [
            {
                "metric_id": "frontend.bundles.initial_gzip_bytes",
                "value": 300,
                "samples": 1,
                "baseline_value": 400,
                "consecutive_comparable_regressions": 5,
            }
        ],
    }
    result = _run(tmp_path, BASE_MANIFEST, report)
    assert result["ok"] and result["warnings"] == []


# ── règles 13 et 14 : échecs durs et étiquettes interdites ───────────────────


def test_un_echec_dur_bloque_quel_que_soit_le_profil(tmp_path: Path) -> None:
    report = {**BASE_REPORT, "hard_failures_observed": ["durable_event_loss"]}
    result = _run(tmp_path, BASE_MANIFEST, report)
    assert "hard_failure_observed" in {f["code"] for f in result["findings"]}
    assert not result["ok"]


@pytest.mark.parametrize("etiquette", ["ticker", "portfolio_id", "trace_id"])
def test_une_etiquette_interdite_bloque(tmp_path: Path, etiquette: str) -> None:
    """Un rapport de performance n'est pas un endroit où une donnée
    personnelle ou de marché a le droit d'arriver."""
    report = {
        **BASE_REPORT,
        "measurements": [
            {
                "metric_id": "frontend.bundles.initial_gzip_bytes",
                "value": 500,
                "samples": 1,
                "labels": {etiquette: "valeur"},
            }
        ],
    }
    assert "forbidden_metric_label" in _codes(tmp_path, BASE_MANIFEST, report)


# ── documents inutilisables ──────────────────────────────────────────────────


def test_un_rapport_absent_echoue(tmp_path: Path) -> None:
    root, _ = _write(tmp_path, BASE_MANIFEST, BASE_REPORT)
    with pytest.raises(gate.DocumentError):
        gate.check(root, tmp_path / "absent.json", TODAY)


def test_un_manifeste_absent_echoue(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    report_path.write_text("{}", encoding="utf-8")
    with pytest.raises(gate.DocumentError):
        gate.check(tmp_path, report_path, TODAY)


def test_un_statut_inconnu_est_refuse(tmp_path: Path) -> None:
    """Un troisième statut inventé ne doit pas devenir une porte de sortie."""
    manifest = {
        **BASE_MANIFEST,
        "required_measurements": [
            {**BASE_MANIFEST["required_measurements"][0], "status": "PLUS_TARD"}
        ],
    }
    root, report_path = _write(tmp_path, manifest, BASE_REPORT)
    with pytest.raises(gate.DocumentError):
        gate.check(root, report_path, TODAY)


# ── le manifeste réel du dépôt reste lisible par la porte ────────────────────


def test_le_manifeste_reel_est_exploitable_par_la_porte() -> None:
    """Toute entrée réelle doit avoir un `budget_path` qui résout.

    Ce test lit le manifeste du dépôt, pas une copie : il échoue le jour où
    quelqu'un ajoute une entrée pointant vers un budget inexistant.
    """
    manifest_path = _REPO_ROOT / "manifests" / "performance-budgets.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    entries = manifest["required_measurements"]
    assert entries, "le manifeste réel doit exiger au moins une mesure"
    for entry in entries:
        budget = gate._resolve(manifest, entry["budget_path"])
        assert budget is not None, entry["metric_id"]
        if entry["kind"] == "max":
            assert isinstance(budget, (int, float)) and not isinstance(budget, bool)


# ── 9e audit : un bundle 32x au-dessus du budget passait la porte ────────────
#
# Mesuré sur le dépôt réel : un rapport portant `initial_gzip_bytes` à
# 10 000 000 octets (budget 307 200) rendait `ok: true` sous P-DEV, parce
# qu'aucun profil de développement ni de CI ne porte `absolute_release_gate`.
# Un compte d'octets gzip ne dépend pourtant pas de la machine qui l'a mesuré :
# il n'existe aucun coureur sur lequel 10 Mo soit acceptable.


def test_un_depassement_independant_de_la_machine_bloque_sans_autorite_absolue(
    tmp_path: Path,
) -> None:
    """LE reproducteur : 32x le budget, sous un profil sans autorité absolue."""
    report = {
        **BASE_REPORT,
        "profile_id": "P-CI",
        "measurements": [
            {"metric_id": "frontend.bundles.initial_gzip_bytes", "value": 32_000, "samples": 1}
        ],
    }
    assert BASE_MANIFEST["profiles"]["P-CI"]["absolute_release_gate"] is False, (
        "anti-vacuité : si P-CI avait l'autorité absolue, ce test passerait "
        "par l'ancienne branche et ne prouverait rien"
    )
    result = _run(tmp_path, BASE_MANIFEST, report)
    assert not result["ok"], "un dépassement de 32x ne peut pas rendre ok: true"
    bloquants = [
        f for f in result["findings"] if f["code"] == "budget_exceeded" and f.get("blocking")
    ]
    assert len(bloquants) == 1, result["findings"]
    assert bloquants[0]["machine_independent"] is True
    assert result["warnings"] == [], "un budget indépendant ne se rétrograde pas"


def test_un_budget_max_sans_declaration_d_independance_echoue(tmp_path: Path) -> None:
    """Fail-closed : omettre le champ achèterait silencieusement l'indulgence.

    C'est exactement ainsi que le dépassement de 32x est passé inaperçu — la
    branche permissive était le DÉFAUT, pas un choix écrit.
    """
    manifest = json.loads(json.dumps(BASE_MANIFEST))
    del manifest["required_measurements"][0]["machine_independent"]
    result = _run(tmp_path, manifest, BASE_REPORT)
    assert "machine_independence_undeclared" in {f["code"] for f in result["findings"]}
    assert not result["ok"]


def test_une_declaration_non_booleenne_ne_compte_pas(tmp_path: Path) -> None:
    """`machine_independent: "oui"` est une chaîne vraie en Python.

    Sans ce test, un manifeste mal typé passerait pour une déclaration valide
    et, pire, serait lu comme « indépendant » par vérité de chaîne non vide.
    """
    manifest = json.loads(json.dumps(BASE_MANIFEST))
    manifest["required_measurements"][0]["machine_independent"] = "oui"
    result = _run(tmp_path, manifest, BASE_REPORT)
    assert "machine_independence_undeclared" in {f["code"] for f in result["findings"]}


def test_le_manifeste_reel_declare_l_independance_de_chaque_budget_max() -> None:
    """La règle ne vaut que si le manifeste LIVRÉ la respecte.

    Un test qui ne vérifie que des fixtures laisse le vrai manifeste libre
    d'omettre le champ, et la porte n'aurait alors jamais rien à dire.
    """
    reel = yaml.safe_load(
        (_REPO_ROOT / "manifests" / "performance-budgets.yaml").read_text(encoding="utf-8")
    )
    maxima = [
        spec for spec in reel["required_measurements"] if spec.get("kind") == "max"
    ]
    assert len(maxima) >= 4, f"seulement {len(maxima)} budgets `max` : le balayage est aveugle"
    sans_declaration = [
        spec["metric_id"]
        for spec in maxima
        if not isinstance(spec.get("machine_independent"), bool)
    ]
    assert sans_declaration == [], (
        "ces budgets `max` ne disent pas s'ils dépendent de la machine : "
        f"{sans_declaration}"
    )
    # Le budget de bundle EST indépendant : c'est celui que l'audit a mesuré.
    bundle = next(s for s in maxima if s["metric_id"] == "frontend.bundles.initial_gzip_bytes")
    assert bundle["machine_independent"] is True


def test_aucun_profil_a_autorite_absolue_ne_se_passe_de_metadonnees() -> None:
    """`P-DESKTOP` portait `absolute_release_gate: true` sans `required_metadata`.

    Un verdict de release ABSOLU rendu depuis une machine entièrement non
    décrite n'est comparable à rien, pas même à lui-même — c'est exactement ce
    que `missing_profile_metadata` existe pour empêcher, et ce profil y
    échappait faute de champs à exiger.
    """
    reel = yaml.safe_load(
        (_REPO_ROOT / "manifests" / "performance-budgets.yaml").read_text(encoding="utf-8")
    )
    profils = reel["profiles"]
    absolus = [
        nom for nom, corps in profils.items() if corps.get("absolute_release_gate") is True
    ]
    assert absolus, "aucun profil absolu : ce test ne prouverait rien"
    sans_metadonnees = [
        nom for nom in absolus if not (profils[nom].get("required_metadata") or [])
    ]
    assert sans_metadonnees == [], (
        "ces profils rendent un verdict de release absolu sans exiger la "
        f"moindre description de la machine : {sans_metadonnees}"
    )
