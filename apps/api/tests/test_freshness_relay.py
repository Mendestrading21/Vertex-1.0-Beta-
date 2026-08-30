"""Le propriétaire unique de la fraîcheur au relais.

Le défaut que ce module ferme est mesuré, pas supposé : un dossier publié
conserve `snapshot_fresh_and_coherent = PASS` à +47 h ET à +71 h parce
qu'aucune relecture ne recalcule son âge. `.claude/rules/financial-safety.md`
appelle cela « conserver SILENCIEUSEMENT un ancien verdict ».

Une sonde a montré que resserrer le budget ne corrigeait rien : le TTL déclaré
de `daily_bar` en séance fermée vaut 72 h, donc +71 h reste DANS le budget. Le
correctif est de publier l'âge dans tous les cas — c'est ce que ces tests
vérifient, budget ou pas.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from vertex_api.freshness import (
    REASON_CLOCK_INCONSISTENT,
    REASON_SNAPSHOT_STALE,
    closed_session_budget,
    evaluate_relay_freshness,
)
from vertex_core.data.freshness import get_freshness_policy

NOW = datetime(2026, 8, 30, 14, 0, tzinfo=UTC)
DAILY_BAR = get_freshness_policy("daily_bar")
NEWS = get_freshness_policy("news_attention")


def _at(age: timedelta):
    return evaluate_relay_freshness(NOW - age, now=NOW, policy=DAILY_BAR)


def test_le_budget_est_celui_du_registre_jamais_un_nombre_local() -> None:
    """Un TTL inventé ici serait la valeur non justifiée que ce dépôt refuse."""
    assert closed_session_budget(DAILY_BAR) == timedelta(
        seconds=DAILY_BAR.ttl_closed_seconds
    )
    assert closed_session_budget(DAILY_BAR) == timedelta(hours=72)
    assert closed_session_budget(NEWS) == timedelta(hours=1)


def test_l_age_est_publie_meme_quand_l_instantane_est_dans_le_budget() -> None:
    """LE correctif du P0 : à +71 h le dossier est servi AVEC ses secondes.

    Il n'est pas `stale` — 71 h tiennent dans les 72 h déclarées — et c'est
    précisément pourquoi resserrer le budget ne réglait rien. Ce qui règle le
    défaut, c'est que l'âge ne soit plus absent.
    """
    mesure = _at(timedelta(hours=71))
    assert mesure.stale is False
    assert mesure.age_seconds == 255_600
    assert mesure.stale_reason is None


def test_au_dela_du_budget_l_etat_bascule_et_la_raison_nomme_la_politique() -> None:
    mesure = _at(timedelta(hours=73))
    assert mesure.stale is True
    assert mesure.age_seconds == 262_800
    assert mesure.stale_reason == REASON_SNAPSHOT_STALE.format(
        age=262_800, budget=259_200, policy="daily_bar", version="1.0.0"
    )


def test_la_bascule_se_fait_a_la_seconde_pres() -> None:
    """Exactement au budget, l'instantané est encore servi `ok` : `>` et non `>=`."""
    assert _at(timedelta(seconds=DAILY_BAR.ttl_closed_seconds)).stale is False
    assert _at(timedelta(seconds=DAILY_BAR.ttl_closed_seconds + 1)).stale is True


def test_sans_tolerance_declaree_toute_avance_est_une_incoherence_d_horloge() -> None:
    """La tolérance par défaut est ZÉRO : un relais qui tolère une dérive la DÉCLARE."""
    mesure = evaluate_relay_freshness(
        NOW + timedelta(seconds=1), now=NOW, policy=DAILY_BAR
    )
    assert mesure.clock_inconsistent is True
    assert mesure.drift_seconds == 1
    assert mesure.age_seconds == 0
    assert mesure.clock_reason == REASON_CLOCK_INCONSISTENT.format(
        drift=1, tolerance=0
    )


def test_une_derive_toleree_est_absorbee_et_l_age_borne_a_zero() -> None:
    """Deux processus horodatent chacun leur lecture : ce n'est pas un défaut
    de contenu, et l'âge n'est JAMAIS publié négatif."""
    mesure = evaluate_relay_freshness(
        NOW + timedelta(seconds=4),
        now=NOW,
        policy=DAILY_BAR,
        drift_tolerance=timedelta(seconds=5),
    )
    assert mesure.clock_inconsistent is False
    assert mesure.age_seconds == 0
    assert mesure.age == timedelta(0)


def test_au_dela_de_la_tolerance_l_horloge_est_nommee_pas_le_contenu() -> None:
    mesure = evaluate_relay_freshness(
        NOW + timedelta(seconds=9),
        now=NOW,
        policy=DAILY_BAR,
        drift_tolerance=timedelta(seconds=5),
    )
    assert mesure.clock_inconsistent is True
    assert mesure.drift_seconds == 9
    assert "CLOCK problem" in (mesure.clock_reason or "")
    assert "invalid snapshot content" in (mesure.clock_reason or "")


def test_une_horloge_naive_est_refusee_des_deux_cotes() -> None:
    """Une horloge naïve serait lue en heure locale et décalerait tous les âges."""
    # DTZ001 est justement la règle testée ici : on FABRIQUE l'instant naïf
    # que le module doit refuser.
    naive = NOW.replace(tzinfo=None)
    with pytest.raises(ValueError, match="naive"):
        evaluate_relay_freshness(naive, now=NOW, policy=DAILY_BAR)
    with pytest.raises(ValueError, match="naive"):
        evaluate_relay_freshness(NOW, now=naive, policy=DAILY_BAR)


def test_une_tolerance_negative_est_refusee() -> None:
    with pytest.raises(ValueError, match="negative"):
        evaluate_relay_freshness(
            NOW, now=NOW, policy=DAILY_BAR, drift_tolerance=timedelta(seconds=-1)
        )


def test_l_age_ne_depend_pas_du_fuseau_d_entree() -> None:
    """Le stockage est UTC ; un instant équivalent dans un autre décalage donne
    le MÊME âge, sinon un fuseau changerait silencieusement une fraîcheur."""
    from datetime import timezone

    ailleurs = (NOW - timedelta(hours=2)).astimezone(timezone(timedelta(hours=9)))
    assert (
        evaluate_relay_freshness(ailleurs, now=NOW, policy=DAILY_BAR).age_seconds
        == 7_200
    )
