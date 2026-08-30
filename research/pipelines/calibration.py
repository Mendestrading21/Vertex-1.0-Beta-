"""Évaluation de calibration et RÈGLE D'ABSTENTION.

Une probabilité prédictive n'a de sens que si elle est calibrée : quand le
modèle annonce 30 %, l'événement doit survenir environ trois fois sur dix. Ce
module mesure cela et, surtout, **décide de s'abstenir**.

Le contrat d'interface (``docs/03-domain/PROBABILITY_CALIBRATION.md``) est
strict : une valeur ne peut être affichée comme probabilité prédictive que si
``calibration_status == VALID``. Toute autre issue masque la valeur et affiche
la cause. :func:`assess_calibration` produit exactement ce statut.

Rappel de périmètre : `probability.calibration` est `NOT_IMPLEMENTED` au
registre des calculs. Ce module fournit l'outil d'évaluation ; il n'autorise
rien par lui-même et n'est appelé par aucun code de production.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum
from typing import Sequence

__all__ = [
    "CalibrationStatus",
    "CalibrationReport",
    "ReliabilityBin",
    "brier_score",
    "log_loss",
    "reliability_diagram",
    "block_bootstrap_interval",
    "assess_calibration",
]

# Bornes de sécurité numérique : une probabilité exactement 0 ou 1 rend la
# log-loss infinie. On borne au lieu de laisser passer un infini, et le
# document de calibration exige que ce traitement soit explicite.
_EPSILON = 1e-15


class CalibrationStatus(str, Enum):
    """Issue de l'évaluation. Seul ``VALID`` autoriserait un affichage."""

    VALID = "VALID"
    INSUFFICIENT_SAMPLE = "INSUFFICIENT_SAMPLE"
    MISCALIBRATED = "MISCALIBRATED"
    UNSTABLE = "UNSTABLE"


@dataclass(frozen=True)
class ReliabilityBin:
    lower: float
    upper: float
    count: int
    mean_predicted: float
    observed_frequency: float


@dataclass(frozen=True)
class CalibrationReport:
    status: CalibrationStatus
    reason: str
    """Cause en clair — affichée à la place de la valeur quand le statut n'est
    pas ``VALID``. Jamais vide."""
    sample_size: int
    brier: float
    log_loss: float
    expected_calibration_error: float
    brier_interval: tuple[float, float]
    bins: tuple[ReliabilityBin, ...]


def _validate(predicted: Sequence[float], observed: Sequence[int]) -> None:
    if len(predicted) != len(observed):
        raise ValueError("predicted et observed: longueurs différentes")
    if not predicted:
        raise ValueError("predicted: séquence vide")
    for position, probability in enumerate(predicted):
        if not isinstance(probability, (int, float)) or isinstance(probability, bool):
            raise TypeError(f"predicted[{position}]: nombre requis")
        if math.isnan(probability) or math.isinf(probability):
            raise ValueError(f"predicted[{position}]: NaN ou infini interdit")
        if not (0.0 <= probability <= 1.0):
            raise ValueError(f"predicted[{position}]: hors [0, 1] ({probability})")
    for position, outcome in enumerate(observed):
        if outcome not in (0, 1):
            raise ValueError(f"observed[{position}]: 0 ou 1 requis ({outcome!r})")


def brier_score(predicted: Sequence[float], observed: Sequence[int]) -> float:
    """Erreur quadratique moyenne. 0 = parfait, 0.25 = pièce non biaisée."""
    _validate(predicted, observed)
    return sum((p - o) ** 2 for p, o in zip(predicted, observed)) / len(predicted)


def log_loss(predicted: Sequence[float], observed: Sequence[int]) -> float:
    """Log-loss, bornée pour rester finie sur les probabilités extrêmes."""
    _validate(predicted, observed)
    total = 0.0
    for probability, outcome in zip(predicted, observed):
        bounded = min(max(probability, _EPSILON), 1.0 - _EPSILON)
        total -= math.log(bounded) if outcome == 1 else math.log(1.0 - bounded)
    return total / len(predicted)


def reliability_diagram(
    predicted: Sequence[float], observed: Sequence[int], *, bins: int = 10
) -> tuple[ReliabilityBin, ...]:
    """Fréquence observée par tranche de probabilité annoncée.

    Les tranches VIDES sont omises : inventer une fréquence observée pour une
    tranche sans observation reviendrait à afficher un zéro là où il n'y a pas
    de donnée — absent n'est pas zéro.
    """
    _validate(predicted, observed)
    if not isinstance(bins, int) or bins < 2:
        raise ValueError("bins: entier >= 2 requis")

    buckets: list[list[tuple[float, int]]] = [[] for _ in range(bins)]
    for probability, outcome in zip(predicted, observed):
        # La borne haute 1.0 appartient à la dernière tranche.
        position = min(int(probability * bins), bins - 1)
        buckets[position].append((probability, outcome))

    result: list[ReliabilityBin] = []
    for index, bucket in enumerate(buckets):
        if not bucket:
            continue
        result.append(
            ReliabilityBin(
                lower=index / bins,
                upper=(index + 1) / bins,
                count=len(bucket),
                mean_predicted=sum(p for p, _ in bucket) / len(bucket),
                observed_frequency=sum(o for _, o in bucket) / len(bucket),
            )
        )
    return tuple(result)


def expected_calibration_error(bins: Sequence[ReliabilityBin]) -> float:
    """Écart moyen |annoncé - observé|, pondéré par l'effectif de la tranche."""
    total = sum(b.count for b in bins)
    if total == 0:
        raise ValueError("bins: aucun effectif")
    return sum(b.count * abs(b.mean_predicted - b.observed_frequency) for b in bins) / total


def block_bootstrap_interval(
    predicted: Sequence[float],
    observed: Sequence[int],
    *,
    block_size: int,
    resamples: int = 1000,
    confidence: float = 0.95,
    seed: int,
) -> tuple[float, float]:
    """Intervalle du Brier score par bootstrap EN BLOCS.

    Les observations financières voisines ne sont pas indépendantes : un
    bootstrap i.i.d. produirait un intervalle faussement étroit. On rééchantillonne
    des blocs contigus. ``seed`` est OBLIGATOIRE — un intervalle non reproductible
    n'est pas une preuve.
    """
    _validate(predicted, observed)
    if not isinstance(block_size, int) or block_size < 1:
        raise ValueError("block_size: entier >= 1 requis")
    if block_size > len(predicted):
        raise ValueError("block_size: supérieur à la taille de l'échantillon")
    if not isinstance(resamples, int) or resamples < 100:
        raise ValueError("resamples: entier >= 100 requis")
    if not (0.5 < confidence < 1.0):
        raise ValueError("confidence: strictement entre 0.5 et 1.0")

    size = len(predicted)
    blocks = max(1, size // block_size)
    generator = random.Random(seed)
    scores: list[float] = []
    for _ in range(resamples):
        sample_p: list[float] = []
        sample_o: list[int] = []
        for _ in range(blocks):
            start = generator.randrange(0, size - block_size + 1)
            sample_p.extend(predicted[start : start + block_size])
            sample_o.extend(observed[start : start + block_size])
        scores.append(brier_score(sample_p, sample_o))
    scores.sort()
    tail = (1.0 - confidence) / 2.0
    low = scores[int(tail * (len(scores) - 1))]
    high = scores[int((1.0 - tail) * (len(scores) - 1))]
    return (low, high)


def assess_calibration(
    predicted: Sequence[float],
    observed: Sequence[int],
    *,
    minimum_sample: int = 250,
    maximum_calibration_error: float = 0.05,
    block_size: int = 5,
    seed: int,
    bins: int = 10,
) -> CalibrationReport:
    """Évalue, et **s'abstient** dès qu'une condition n'est pas tenue.

    L'ordre des refus est délibéré : on ne juge pas la calibration d'un
    échantillon trop petit, et on ne juge pas la stabilité d'un modèle déjà
    mal calibré. Le premier refus rencontré est celui qui est rendu, avec sa
    cause en clair.
    """
    _validate(predicted, observed)
    size = len(predicted)

    diagram = reliability_diagram(predicted, observed, bins=bins)
    score = brier_score(predicted, observed)
    loss = log_loss(predicted, observed)

    if size < minimum_sample:
        return CalibrationReport(
            status=CalibrationStatus.INSUFFICIENT_SAMPLE,
            reason=(
                f"échantillon de {size} observations pour un minimum de "
                f"{minimum_sample} — aucune probabilité n'est affichable"
            ),
            sample_size=size,
            brier=score,
            log_loss=loss,
            expected_calibration_error=expected_calibration_error(diagram),
            brier_interval=(float("nan"), float("nan")),
            bins=diagram,
        )

    error = expected_calibration_error(diagram)
    interval = block_bootstrap_interval(
        predicted, observed, block_size=block_size, seed=seed
    )

    if error > maximum_calibration_error:
        return CalibrationReport(
            status=CalibrationStatus.MISCALIBRATED,
            reason=(
                f"écart de calibration de {error:.4f} pour un maximum de "
                f"{maximum_calibration_error:.4f}"
            ),
            sample_size=size,
            brier=score,
            log_loss=loss,
            expected_calibration_error=error,
            brier_interval=interval,
            bins=diagram,
        )

    # Instabilité : un intervalle de confiance qui englobe le Brier d'une
    # prédiction constante à la fréquence de base signifie qu'on ne peut pas
    # distinguer le modèle de l'absence de modèle.
    base_rate = sum(observed) / size
    naive = base_rate * (1.0 - base_rate)
    if interval[1] >= naive:
        return CalibrationReport(
            status=CalibrationStatus.UNSTABLE,
            reason=(
                f"la borne haute du Brier ({interval[1]:.4f}) atteint celui d'une "
                f"prédiction constante ({naive:.4f}) — le modèle n'est pas "
                "distinguable de l'absence de modèle"
            ),
            sample_size=size,
            brier=score,
            log_loss=loss,
            expected_calibration_error=error,
            brier_interval=interval,
            bins=diagram,
        )

    return CalibrationReport(
        status=CalibrationStatus.VALID,
        reason=(
            f"calibrée sur {size} observations hors échantillon, écart "
            f"{error:.4f}, Brier {score:.4f} dans [{interval[0]:.4f}, {interval[1]:.4f}]"
        ),
        sample_size=size,
        brier=score,
        log_loss=loss,
        expected_calibration_error=error,
        brier_interval=interval,
        bins=diagram,
    )
