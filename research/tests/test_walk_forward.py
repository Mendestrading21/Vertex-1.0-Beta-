"""Preuves du découpage walk-forward purgé.

Le test central est celui de NON-FUITE : aucune observation d'entraînement ne
doit avoir un label qui se résout après le début du test. S'il passait sans la
purge, il ne prouverait rien — un test dédié vérifie donc qu'il échoue quand
la purge est neutralisée.
"""

from __future__ import annotations

import itertools
from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pipelines.walk_forward import (
    Fold,
    WalkForwardConfig,
    final_holdout,
    purged_walk_forward,
)

DAY = timedelta(days=1)


def daily(count: int, start: datetime | None = None) -> list[datetime]:
    origin = start or datetime(2024, 1, 1, tzinfo=UTC)
    return [origin + index * DAY for index in range(count)]


def config(**overrides: object) -> WalkForwardConfig:
    base = {
        "train_span": 60 * DAY,
        "test_span": 20 * DAY,
        "label_horizon": 5 * DAY,
    }
    base.update(overrides)
    return WalkForwardConfig(**base)  # type: ignore[arg-type]


# ── Refus de configuration ────────────────────────────────────────────────

@pytest.mark.parametrize("field", ["train_span", "test_span"])
def test_une_duree_nulle_est_refusee(field: str) -> None:
    with pytest.raises(ValueError, match="strictement positive"):
        config(**{field: timedelta(0)})


def test_un_instant_naif_est_refuse() -> None:
    naive = [datetime(2024, 1, 1) + index * DAY for index in range(200)]  # noqa: DTZ001 (naïf délibéré : rejet vérifié)
    with pytest.raises(ValueError, match="naïf"):
        list(purged_walk_forward(naive, config()))


def test_une_serie_non_triee_est_refusee() -> None:
    stamps = daily(200)
    stamps[100], stamps[50] = stamps[50], stamps[100]
    with pytest.raises(ValueError, match="non triée"):
        list(purged_walk_forward(stamps, config()))


# ── Non-fuite ─────────────────────────────────────────────────────────────

def test_aucune_observation_d_entrainement_ne_voit_le_test() -> None:
    stamps = daily(400)
    settings_ = config()
    folds = list(purged_walk_forward(stamps, settings_))
    assert folds, "aucun pli produit : le test ne prouverait rien"
    for fold in folds:
        for position in fold.train:
            resolution = stamps[position] + settings_.label_horizon
            assert resolution <= fold.test_start, (
                f"fuite : l'observation {position} se résout à {resolution}, "
                f"après le début du test {fold.test_start}"
            )


def test_le_test_de_fuite_echouerait_sans_la_purge() -> None:
    """Anti-vacuité : sans purge, des observations fuiraient réellement.

    On reconstruit l'entraînement SANS le filtre de purge et on vérifie qu'il
    contient bien des observations fautives — donc que la purge fait un travail
    réel et que le test précédent n'est pas trivialement vrai.
    """
    stamps = daily(400)
    settings_ = config()
    fold = next(iter(purged_walk_forward(stamps, settings_)))
    train_start = stamps[0]
    unpurged = [
        position
        for position, moment in enumerate(stamps)
        if train_start <= moment < fold.train_end
    ]
    leaking = [
        position
        for position in unpurged
        if stamps[position] + settings_.label_horizon > fold.test_start
    ]
    assert leaking, "sans purge aucune fuite : le jeu de test est mal choisi"
    assert set(leaking).isdisjoint(fold.train)
    assert set(leaking).issubset(set(fold.purged))


def test_les_plis_avancent_dans_le_temps_sans_se_chevaucher() -> None:
    folds = list(purged_walk_forward(daily(500), config()))
    assert len(folds) >= 3
    for previous, current in itertools.pairwise(folds):
        assert current.test_start > previous.test_start
        assert set(previous.test).isdisjoint(current.test)


def test_aucun_pli_vide_n_est_produit() -> None:
    for fold in purged_walk_forward(daily(400), config()):
        assert fold.train and fold.test


def test_une_serie_trop_courte_ne_produit_aucun_pli() -> None:
    """Refus honnête : pas de pli dégradé fabriqué pour en produire un."""
    assert list(purged_walk_forward(daily(10), config())) == []


@settings(max_examples=50, deadline=None)
@given(
    horizon_days=st.integers(min_value=0, max_value=30),
    extra_gap_days=st.integers(min_value=0, max_value=10),
)
def test_propriete_non_fuite_pour_tout_horizon(horizon_days: int, extra_gap_days: int) -> None:
    stamps = daily(400)
    settings_ = config(
        label_horizon=horizon_days * DAY,
        embargo=extra_gap_days * DAY,
    )
    for fold in purged_walk_forward(stamps, settings_):
        for position in fold.train:
            assert stamps[position] + settings_.label_horizon <= fold.test_start


# ── Holdout final ─────────────────────────────────────────────────────────

def test_le_holdout_est_disjoint_et_ne_partage_aucun_label() -> None:
    stamps = daily(400)
    development, holdout = final_holdout(stamps, 60 * DAY, 5 * DAY)
    assert development and holdout
    assert set(development).isdisjoint(holdout)
    holdout_start = stamps[holdout[0]]
    for position in development:
        assert stamps[position] + 5 * DAY <= holdout_start


def test_les_observations_a_cheval_n_appartiennent_a_personne() -> None:
    """Une observation dont le label empiète sur le holdout est retirée des
    deux côtés — c'est la seule réponse honnête, pas un arbitrage."""
    stamps = daily(400)
    development, holdout = final_holdout(stamps, 60 * DAY, 5 * DAY)
    orphans = set(range(len(stamps))) - set(development) - set(holdout)
    assert orphans, "aucune observation à cheval : le cas n'est pas exercé"
    for position in orphans:
        assert stamps[position] + 5 * DAY > stamps[holdout[0]]
        assert stamps[position] < stamps[holdout[0]]


def test_le_pli_expose_ce_qu_il_a_purge() -> None:
    """Une purge muette ne serait pas vérifiable."""
    fold: Fold = next(iter(purged_walk_forward(daily(400), config())))
    assert fold.purged
    assert set(fold.purged).isdisjoint(fold.train)


# ── Embargo ───────────────────────────────────────────────────────────────
#
# L'embargo n'a de sens que s'il RETIRE des observations d'un entraînement.
# Un embargo qui ne change rien est une garantie décorative : les tests qui
# suivent comparent donc deux exécutions et exigent une différence, au lieu de
# se contenter de constater que le paramètre est accepté.

def _embargo_stamps() -> list[datetime]:
    return daily(120)


def _embargo_config(embargo_days: int) -> WalkForwardConfig:
    return WalkForwardConfig(
        train_span=30 * DAY,
        test_span=10 * DAY,
        label_horizon=3 * DAY,
        embargo=embargo_days * DAY,
    )


def _folds(embargo_days: int) -> list[Fold]:
    return list(purged_walk_forward(_embargo_stamps(), _embargo_config(embargo_days)))


def test_sans_embargo_le_pli_suivant_reutilise_le_test_du_pli_precedent() -> None:
    """Anti-vacuité : le cas que l'embargo doit corriger existe réellement."""
    folds = _folds(0)
    assert len(folds) >= 2
    reuse = set(folds[0].test) & set(folds[1].train)
    assert reuse, (
        "sans embargo le pli 1 devrait réutiliser le test du pli 0 ; "
        "si ce n'est pas le cas le jeu de test est mal choisi"
    )


def test_l_embargo_modifie_reellement_les_entrainements() -> None:
    """L'embargo doit CHANGER les entraînements, pas seulement être accepté."""
    sans = [fold.train for fold in _folds(0)]
    avec = [fold.train for fold in _folds(365)]
    assert sans, "aucun pli produit : la comparaison ne prouverait rien"
    assert avec != sans, (
        "embargo inerte : les entraînements sont identiques avec embargo=0 "
        f"et embargo=365 jours ({sans!r})"
    )


def test_l_embargo_retire_le_test_precedent_de_l_entrainement_suivant() -> None:
    folds = _folds(365)
    assert len(folds) >= 2
    for previous, current in itertools.pairwise(folds):
        assert set(current.train).isdisjoint(previous.test), (
            f"le pli {current.index} entraîne sur "
            f"{sorted(set(current.train) & set(previous.test))} — observations "
            f"évaluées par le pli {previous.index}, encore sous embargo"
        )


def test_les_observations_sous_embargo_sont_declarees_purgees() -> None:
    """Un retrait muet ne serait pas vérifiable : `purged` doit le montrer."""
    folds = _folds(365)
    assert len(folds) >= 2
    fold = folds[1]
    quarantined = set(folds[0].test) & {
        position
        for position, moment in enumerate(_embargo_stamps())
        if moment < fold.test_start
    }
    assert quarantined
    assert quarantined.issubset(set(fold.purged))
    assert set(fold.purged).isdisjoint(fold.train)


def test_purged_ne_contient_que_des_observations_retirees_d_un_entrainement() -> None:
    """`purged` documente un RETRAIT : une observation postérieure au test,
    qui n'était de toute façon pas candidate, n'y a pas sa place."""
    stamps = daily(400)
    settings_ = config(embargo=30 * DAY)
    for fold in purged_walk_forward(stamps, settings_):
        for position in fold.purged:
            assert stamps[position] < fold.test_start, (
                f"l'observation {position} est postérieure au début du test : "
                "elle n'a jamais été candidate à l'entraînement"
            )


@settings(max_examples=50, deadline=None)
@given(embargo_days=st.integers(min_value=0, max_value=40))
def test_propriete_embargo_aucune_reutilisation_avant_expiration(embargo_days: int) -> None:
    """Invariant : tant que `embargo` n'est pas écoulé depuis la fin d'un test,
    les observations de ce test ne peuvent pas servir à entraîner."""
    stamps = daily(300)
    settings_ = WalkForwardConfig(
        train_span=40 * DAY,
        test_span=15 * DAY,
        label_horizon=4 * DAY,
        embargo=embargo_days * DAY,
    )
    folds = list(purged_walk_forward(stamps, settings_))
    for earlier in folds:
        for later in folds:
            if later.index <= earlier.index:
                continue
            if earlier.test_end + settings_.embargo > later.test_start:
                assert set(later.train).isdisjoint(earlier.test)
