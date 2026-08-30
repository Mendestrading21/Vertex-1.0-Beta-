"""Découpage walk-forward purgé pour l'évaluation hors échantillon.

Le défaut classique d'une évaluation temporelle n'est pas le sur-apprentissage,
c'est la **fuite** : une observation d'entraînement dont le label se résout
APRÈS le début du test partage l'information du test. Un simple découpage
chronologique ne suffit donc pas.

Ce module implémente le protocole minimal exigé par
``docs/03-domain/PROBABILITY_CALIBRATION.md`` :

* découpage **strictement chronologique**, jamais aléatoire ;
* **purge** : la fenêtre d'entraînement est contiguë au test, et toute
  observation dont la fenêtre de label ``[t, t + horizon]`` empiète sur le test
  est retirée. C'est la purge qui garantit la non-fuite — pas un écart
  arbitraire. Un écart fixe suffisamment grand rendrait la purge inutile ; il
  masquerait surtout le fait qu'on jette des données sans savoir combien ;
* **embargo** : une quarantaine des observations DÉJÀ ÉVALUÉES. Dans un
  walk-forward, la fenêtre de test d'un pli devient de la donnée
  d'entraînement pour les plis suivants ; l'estimation agrégée hors
  échantillon suppose pourtant des plis peu redondants. Une observation
  évaluée par un pli dont le test se termine à ``test_end`` ne redevient donc
  entraînable qu'à partir de ``test_end + embargo``. Avec ``embargo = 0``
  (défaut) rien n'est mis en quarantaine et seule la purge agit ;
* **holdout final** séparé et intouchable.

Aucune dépendance au runtime : ce module ne connaît ni base, ni API, ni
worker. Il travaille sur des instants et des indices, rien d'autre.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterator, Sequence

__all__ = ["Fold", "WalkForwardConfig", "purged_walk_forward", "final_holdout"]


@dataclass(frozen=True)
class WalkForwardConfig:
    """Paramètres du découpage. Tous obligatoires : aucun défaut implicite.

    ``label_horizon`` est l'horizon du label : le délai au bout duquel le
    résultat qu'on cherche à prédire est connu. La fenêtre d'entraînement est
    contiguë au test ; la non-fuite vient de la purge, qui retire les
    observations dont le label se résout pendant le test.

    ``embargo`` est le délai de quarantaine appliqué APRÈS la fin d'un test :
    une observation évaluée par un pli ne peut réintégrer un entraînement
    qu'une fois ce délai écoulé. Il ne remplace pas la purge et ne la relâche
    jamais : les deux filtres s'appliquent, la purge répondant à la fuite de
    label et l'embargo à la redondance entre plis. ``embargo = 0`` laisse le
    walk-forward réutiliser immédiatement chaque test, ce qui est le
    comportement classique et reste le défaut.
    """

    train_span: timedelta
    test_span: timedelta
    label_horizon: timedelta
    embargo: timedelta = timedelta(0)

    def __post_init__(self) -> None:
        for name in ("train_span", "test_span", "label_horizon", "embargo"):
            value = getattr(self, name)
            if not isinstance(value, timedelta):
                raise TypeError(f"{name}: timedelta requis")
        if self.train_span <= timedelta(0):
            raise ValueError("train_span: durée strictement positive requise")
        if self.test_span <= timedelta(0):
            raise ValueError("test_span: durée strictement positive requise")
        if self.label_horizon < timedelta(0):
            raise ValueError("label_horizon: durée négative interdite")
        if self.embargo < timedelta(0):
            raise ValueError("embargo: durée négative interdite")


@dataclass(frozen=True)
class Fold:
    """Un pli : les indices d'entraînement et de test, et leurs bornes."""

    index: int
    train: tuple[int, ...]
    test: tuple[int, ...]
    train_end: datetime
    test_start: datetime
    test_end: datetime
    purged: tuple[int, ...]
    """Indices qui étaient dans la fenêtre d'entraînement et en ont été
    RETIRÉS, par purge de label ou par embargo. Rendus explicitement : un
    retrait muet empêche de vérifier qu'il a eu lieu. N'y figure jamais une
    observation postérieure au début du test : elle n'était pas candidate,
    l'inscrire gonflerait le compte sans rien retirer."""


def _require_sorted_aware(timestamps: Sequence[datetime]) -> None:
    if not timestamps:
        raise ValueError("timestamps: séquence vide")
    for position, moment in enumerate(timestamps):
        if moment.tzinfo is None or moment.utcoffset() is None:
            raise ValueError(f"timestamps[{position}]: instant naïf interdit (UTC requis)")
    for position in range(1, len(timestamps)):
        if timestamps[position] < timestamps[position - 1]:
            raise ValueError(
                f"timestamps[{position}]: séquence non triée — le découpage "
                "temporel exige un ordre chronologique explicite"
            )


def purged_walk_forward(
    timestamps: Sequence[datetime], config: WalkForwardConfig
) -> Iterator[Fold]:
    """Produit les plis walk-forward purgés, du plus ancien au plus récent.

    ``timestamps[i]`` est l'instant de DÉCISION de l'observation ``i`` : le
    moment où ses variables sont connues. Le label correspondant se résout à
    ``timestamps[i] + label_horizon``.

    Un pli n'est produit que s'il a au moins une observation d'entraînement ET
    une observation de test : un pli vide n'est pas une évaluation.
    """
    _require_sorted_aware(timestamps)

    start = timestamps[0]
    last = timestamps[-1]
    fold_index = 0

    # Fenêtres de test des plis DÉJÀ PRODUITS. Seules celles-là comptent : une
    # fenêtre qu'aucun pli n'a évaluée n'a contaminé aucune mesure, la mettre
    # en quarantaine jetterait des données sans motif.
    evaluated: list[tuple[datetime, datetime]] = []

    train_start = start
    while True:
        train_end = train_start + config.train_span
        # Contiguïté délibérée : c'est la purge qui sépare, et elle rend compte
        # de ce qu'elle retire.
        test_start = train_end
        test_end = test_start + config.test_span
        if test_start > last:
            return

        test = tuple(
            position
            for position, moment in enumerate(timestamps)
            if test_start <= moment < test_end
        )
        # Embargo encore actif à l'instant où commence ce test : la quarantaine
        # d'une fenêtre évaluée court jusqu'à `fin du test + embargo`.
        quarantine = [
            window
            for window in evaluated
            if window[1] + config.embargo > test_start
        ]

        candidate_train: list[int] = []
        purged: list[int] = []
        for position, moment in enumerate(timestamps):
            if not (train_start <= moment < train_end):
                continue
            # Embargo : cette observation a-t-elle déjà été évaluée par un pli
            # dont la quarantaine n'est pas expirée ? Si oui, l'entraîner
            # dessus rendrait ce pli redondant avec le précédent.
            if any(
                window_start <= moment < window_end
                for window_start, window_end in quarantine
            ):
                purged.append(position)
                continue
            # Purge : le label de cette observation se résout-il pendant ou
            # après le début du test ? Si oui, elle partage l'information du
            # test et ne peut pas servir à l'entraîner.
            if moment + config.label_horizon > test_start:
                purged.append(position)
                continue
            candidate_train.append(position)

        if candidate_train and test:
            yield Fold(
                index=fold_index,
                train=tuple(candidate_train),
                test=test,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                purged=tuple(purged),
            )
            fold_index += 1
            evaluated.append((test_start, test_end))

        train_start = train_start + config.test_span
        if train_start >= last:
            return


def final_holdout(
    timestamps: Sequence[datetime], holdout_span: timedelta, label_horizon: timedelta
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Sépare un holdout final intouchable de tout le reste.

    Retourne ``(développement, holdout)``. Les observations de développement
    dont le label empiète sur le holdout sont retirées du développement ET
    absentes du holdout : elles n'appartiennent à personne, ce qui est la seule
    réponse honnête.
    """
    _require_sorted_aware(timestamps)
    if holdout_span <= timedelta(0):
        raise ValueError("holdout_span: durée strictement positive requise")
    if label_horizon < timedelta(0):
        raise ValueError("label_horizon: durée négative interdite")

    holdout_start = timestamps[-1] - holdout_span
    development = tuple(
        position
        for position, moment in enumerate(timestamps)
        if moment + label_horizon <= holdout_start
    )
    holdout = tuple(
        position for position, moment in enumerate(timestamps) if moment >= holdout_start
    )
    return development, holdout
