"""Preuves de l'évaluation de calibration et de la règle d'abstention.

Ce qui compte ici n'est pas qu'un score soit calculé : c'est que le module
REFUSE dans les cas où une probabilité ne doit pas être affichée.
"""

from __future__ import annotations

import math
import random

import pytest
from pipelines.calibration import (
    CalibrationStatus,
    assess_calibration,
    block_bootstrap_interval,
    brier_score,
    log_loss,
    reliability_diagram,
)


def well_calibrated(size: int, seed: int) -> tuple[list[float], list[int]]:
    """Échantillon dont la fréquence observée suit la probabilité annoncée."""
    generator = random.Random(seed)
    predicted: list[float] = []
    observed: list[int] = []
    for _ in range(size):
        probability = generator.uniform(0.05, 0.95)
        predicted.append(probability)
        observed.append(1 if generator.random() < probability else 0)
    return predicted, observed


# ── Refus d'entrée ────────────────────────────────────────────────────────

@pytest.mark.parametrize("bad", [1.5, -0.1, float("nan"), float("inf")])
def test_une_probabilite_invalide_est_refusee(bad: float) -> None:
    with pytest.raises(ValueError):
        brier_score([0.5, bad], [1, 0])


def test_un_resultat_non_binaire_est_refuse() -> None:
    with pytest.raises(ValueError, match="0 ou 1"):
        brier_score([0.5, 0.5], [1, 2])


def test_des_longueurs_differentes_sont_refusees() -> None:
    with pytest.raises(ValueError, match="longueurs"):
        brier_score([0.5], [1, 0])


def test_un_booleen_n_est_pas_une_probabilite() -> None:
    with pytest.raises(TypeError):
        brier_score([True, 0.5], [1, 0])


# ── Scores ────────────────────────────────────────────────────────────────

def test_une_prediction_parfaite_donne_un_brier_nul() -> None:
    assert brier_score([1.0, 0.0, 1.0], [1, 0, 1]) == 0.0


def test_une_piece_non_biaisee_donne_le_brier_attendu() -> None:
    assert brier_score([0.5] * 4, [1, 0, 1, 0]) == pytest.approx(0.25)


def test_la_log_loss_reste_finie_sur_une_probabilite_extreme() -> None:
    """Une certitude démentie ne doit pas produire un infini silencieux."""
    value = log_loss([1.0], [0])
    assert math.isfinite(value)
    assert value > 30.0  # bornée, mais massivement pénalisée


def test_une_tranche_vide_n_est_pas_inventee() -> None:
    """Absent n'est pas zéro : une tranche sans observation est omise."""
    bins = reliability_diagram([0.05, 0.06, 0.95], [0, 0, 1], bins=10)
    assert {(b.lower, b.upper) for b in bins} == {(0.0, 0.1), (0.9, 1.0)}
    assert all(b.count > 0 for b in bins)


def test_la_borne_haute_appartient_a_la_derniere_tranche() -> None:
    (only,) = reliability_diagram([1.0], [1], bins=10)
    assert (only.lower, only.upper) == (0.9, 1.0)


# ── Bootstrap ─────────────────────────────────────────────────────────────

def test_l_intervalle_est_reproductible_a_graine_egale() -> None:
    predicted, observed = well_calibrated(400, seed=7)
    first = block_bootstrap_interval(predicted, observed, block_size=5, seed=11)
    second = block_bootstrap_interval(predicted, observed, block_size=5, seed=11)
    assert first == second


def test_la_graine_est_obligatoire() -> None:
    predicted, observed = well_calibrated(300, seed=3)
    with pytest.raises(TypeError):
        block_bootstrap_interval(predicted, observed, block_size=5)  # type: ignore[call-arg]


def test_l_intervalle_encadre_le_score_observe() -> None:
    predicted, observed = well_calibrated(600, seed=5)
    low, high = block_bootstrap_interval(predicted, observed, block_size=10, seed=2)
    assert low <= brier_score(predicted, observed) <= high


# ── Règle d'abstention ────────────────────────────────────────────────────

def test_un_echantillon_trop_petit_fait_abstention() -> None:
    predicted, observed = well_calibrated(50, seed=1)
    report = assess_calibration(predicted, observed, seed=1)
    assert report.status is CalibrationStatus.INSUFFICIENT_SAMPLE
    assert "50 observations" in report.reason


def test_un_modele_mal_calibre_est_refuse() -> None:
    """Le modèle annonce 90 % partout alors que l'événement arrive 10 % du temps."""
    generator = random.Random(4)
    predicted = [0.9] * 400
    observed = [1 if generator.random() < 0.1 else 0 for _ in range(400)]
    report = assess_calibration(predicted, observed, seed=4)
    assert report.status is CalibrationStatus.MISCALIBRATED
    assert "écart de calibration" in report.reason


def test_un_modele_indistinguable_du_hasard_est_refuse() -> None:
    """Bien calibré mais sans pouvoir discriminant : la constante fait aussi
    bien, donc rien ne doit être affiché."""
    generator = random.Random(9)
    predicted = [0.5] * 500
    observed = [1 if generator.random() < 0.5 else 0 for _ in range(500)]
    report = assess_calibration(predicted, observed, seed=9)
    assert report.status is CalibrationStatus.UNSTABLE
    assert "distinguable de l'absence de modèle" in report.reason


def test_un_modele_calibre_et_discriminant_est_valide() -> None:
    """Anti-vacuité : la règle n'est pas un refus systématique."""
    predicted, observed = well_calibrated(2000, seed=21)
    report = assess_calibration(predicted, observed, seed=21)
    assert report.status is CalibrationStatus.VALID, report.reason
    assert report.expected_calibration_error <= 0.05


def test_toute_issue_porte_une_cause_en_clair() -> None:
    """Le contrat d'interface exige d'afficher la cause à la place de la valeur."""
    for size, seed in ((50, 1), (2000, 21)):
        predicted, observed = well_calibrated(size, seed=seed)
        report = assess_calibration(predicted, observed, seed=seed)
        assert report.reason.strip()
        assert report.sample_size == size
