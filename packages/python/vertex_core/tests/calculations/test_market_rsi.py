"""``market.rsi`` — indice de force relative de Wilder : vecteurs, portes, propriétés, oracle.

Convention déclarée : gains et pertes moyens amorcés par la moyenne
arithmétique des ``window`` premières variations, puis lissage de Wilder
(``AG_t = (AG_{t-1} * (window - 1) + gain_t) / window``) ;
``RSI = 100 * AG / (AG + AL)``. Une fenêtre sans aucune variation ne rend
PAS une valeur de convention : elle est REFUSÉE (``flat_series``).
Toutes les séries sont SYNTHÉTIQUES.
"""

from __future__ import annotations

import math
from decimal import Decimal

import numpy as np
import pytest
from hypothesis import assume, given
from hypothesis import strategies as st
from scipy.signal import lfilter, lfiltic

from vertex_core.calculations.market import (
    FLOAT64_REL_TOL,
    CalculationInputError,
    relative_strength_index,
)

NON_FINITE = [float("nan"), float("inf"), float("-inf"), Decimal("NaN"), Decimal("-Infinity")]

prix = st.lists(
    st.floats(min_value=1e-2, max_value=1e4, allow_nan=False, allow_infinity=False),
    min_size=2,
    max_size=60,
)


def _wilder(valeurs: np.ndarray, fenetre: int) -> np.ndarray:
    """Lissage de Wilder = filtre IIR du premier ordre d'``alpha = 1/window``,
    amorcé par la moyenne arithmétique des ``window`` premières valeurs."""
    alpha = 1.0 / fenetre
    amorce = float(np.mean(valeurs[:fenetre]))
    reste = valeurs[fenetre:]
    if reste.size == 0:
        return np.array([amorce])
    b = [alpha]
    a = [1.0, -(1.0 - alpha)]
    suite, _ = lfilter(b, a, reste, zi=lfiltic(b, a, y=[amorce]))
    return np.concatenate([[amorce], suite])


def rsi_reference(serie: list[float], fenetre: int) -> np.ndarray:
    """Oracle indépendant écrit DANS ce test, sous la forme classique
    ``100 - 100 / (1 + RS)`` avec ``RS = AG / AL`` (``100`` quand ``AL = 0``)."""
    variations = np.diff(np.array(serie, dtype=np.float64))
    gains = np.where(variations > 0.0, variations, 0.0)
    pertes = np.where(variations < 0.0, -variations, 0.0)
    ag = _wilder(gains, fenetre)
    al = _wilder(pertes, fenetre)
    sortie = []
    for gain, perte in zip(ag, al, strict=True):
        sortie.append(100.0 if perte == 0.0 else 100.0 - 100.0 / (1.0 + gain / perte))
    return np.array(sortie)


def _rapport_defini(serie: list[float], fenetre: int) -> bool:
    """``AG + AL > 0`` en chaque point publié : fenêtre >= 2, le lissage garde
    la mémoire d'une variation de la fenêtre d'amorce ; fenêtre 1, sans
    mémoire, chaque variation doit être non nulle."""
    if fenetre == 1:
        return all(serie[i] != serie[i - 1] for i in range(1, len(serie)))
    return any(serie[i] != serie[i - 1] for i in range(1, fenetre + 1))


class TestRelativeStrengthIndex:
    def test_vecteur_derive_a_la_main(self):
        # variations +1, +1, -1, +1 ; fenêtre 2.
        # amorce : AG = 1, AL = 0            -> 100
        # puis -1 : AG = 0.5, AL = 0.5       -> 50
        # puis +1 : AG = 0.75, AL = 0.25     -> 75
        serie = relative_strength_index([10, 11, 12, 11, 12], 2)
        assert serie == pytest.approx((100.0, 50.0, 75.0), rel=FLOAT64_REL_TOL)

    def test_une_serie_strictement_croissante_vaut_100(self):
        assert relative_strength_index([1, 2, 3, 4, 5, 6], 3) == (100.0, 100.0, 100.0)

    def test_une_serie_strictement_decroissante_vaut_0(self):
        assert relative_strength_index([6, 5, 4, 3, 2, 1], 3) == (0.0, 0.0, 0.0)

    def test_une_valeur_par_variation_au_dela_de_la_fenetre(self):
        # 7 prix = 6 variations ; fenêtre 4 -> 3 points.
        assert len(relative_strength_index([1, 2, 3, 2, 3, 4, 3], 4)) == 3

    def test_un_plateau_apres_un_mouvement_reste_defini(self):
        """Le lissage garde la mémoire du mouvement : le plateau ne
        ramène pas à 0/0."""
        serie = relative_strength_index([10, 11, 11, 11, 11, 11], 2)
        assert len(serie) == 4
        assert all(0.0 <= point <= 100.0 for point in serie)

    def test_entrees_decimales_converties_explicitement(self):
        serie = relative_strength_index([Decimal("10"), Decimal("11"), Decimal("12")], 2)
        assert serie == (100.0,)

    def test_deterministe(self):
        serie = [100.0, 101.3, 99.8, 102.1, 101.0]
        assert relative_strength_index(serie, 2) == relative_strength_index(serie, 2)

    # -- portes -----------------------------------------------------------

    def test_une_fenetre_sans_variation_est_REFUSEE_jamais_conventionnelle(self):
        """AG = AL = 0 : le rapport n'existe pas. Publier 0, 50 ou 100 serait
        une valeur inventée."""
        with pytest.raises(CalculationInputError) as capture:
            relative_strength_index([7, 7, 7, 7], 3)
        assert capture.value.reason == "flat_series"

    def test_un_pas_plat_en_fenetre_1_est_REFUSE_sans_memoire(self):
        """Fenêtre 1 : ``AG_t = gain_t`` et ``AL_t = perte_t`` exactement, le
        lissage n'a aucune mémoire. Un pas plat rend 0 / 0 : refusé, la série
        entière — aucun point n'est remplacé par une convention."""
        with pytest.raises(CalculationInputError) as capture:
            relative_strength_index([10, 11, 11, 12], 1)
        assert capture.value.reason == "flat_series"

    def test_serie_trop_courte_refusee(self):
        # fenêtre 3 exige 3 variations, donc 4 prix.
        with pytest.raises(CalculationInputError) as capture:
            relative_strength_index([1, 2, 3], 3)
        assert capture.value.reason == "minimum_sample"

    @pytest.mark.parametrize("mauvaise", [0, -1])
    def test_fenetre_invalide_refusee(self, mauvaise):
        with pytest.raises(CalculationInputError) as capture:
            relative_strength_index([1, 2, 3], mauvaise)
        assert capture.value.reason == "invalid_window"

    def test_fenetre_booleenne_refusee(self):
        with pytest.raises(CalculationInputError) as capture:
            relative_strength_index([1, 2, 3], True)
        assert capture.value.reason == "invalid_type"

    @pytest.mark.parametrize("mauvais", [0, -1, Decimal("0")])
    def test_prix_non_positif_refuse(self, mauvais):
        with pytest.raises(CalculationInputError) as capture:
            relative_strength_index([1, mauvais, 3], 1)
        assert capture.value.reason == "non_positive_price"

    @pytest.mark.parametrize("mauvais", NON_FINITE)
    def test_prix_non_fini_refuse(self, mauvais):
        with pytest.raises(CalculationInputError) as capture:
            relative_strength_index([1, mauvais, 3], 1)
        assert capture.value.reason == "non_finite_input"

    @pytest.mark.parametrize("mauvaise", ["1,2,3", 5, None])
    def test_serie_non_sequence_refusee(self, mauvaise):
        with pytest.raises(CalculationInputError) as capture:
            relative_strength_index(mauvaise, 1)
        assert capture.value.reason == "invalid_type"


@pytest.mark.oracle
class TestOracleScipy:
    @pytest.mark.parametrize("fenetre", [1, 2, 7, 14, 30])
    def test_oracle_lfilter(self, fenetre):
        serie = [100.0 + 7.0 * math.sin(i / 3.0) + 0.1 * i for i in range(40)]
        attendu = rsi_reference(serie, fenetre)
        obtenu = relative_strength_index(serie, fenetre)
        assert len(obtenu) == len(attendu) == 40 - fenetre
        assert np.allclose(np.array(obtenu), attendu, rtol=FLOAT64_REL_TOL, atol=1e-9)


@pytest.mark.property
class TestProprietes:
    @given(serie=prix, data=st.data())
    def test_borne_entre_0_et_100_et_longueur(self, serie, data):
        fenetre = data.draw(st.integers(min_value=1, max_value=len(serie) - 1))
        # La porte flat_series est testée à part : ici, le rapport existe en
        # chaque point publié (voir _rapport_defini).
        assume(_rapport_defini(serie, fenetre))
        obtenu = relative_strength_index(serie, fenetre)
        assert len(obtenu) == len(serie) - fenetre
        for point in obtenu:
            assert math.isfinite(point)
            assert 0.0 <= point <= 100.0

    @given(
        depart=st.floats(min_value=1.0, max_value=1e3, allow_nan=False, allow_infinity=False),
        pas=st.floats(min_value=1e-3, max_value=10.0, allow_nan=False, allow_infinity=False),
        n=st.integers(min_value=2, max_value=40),
    )
    def test_une_serie_croissante_sature_a_100(self, depart, pas, n):
        serie = [depart + pas * i for i in range(n)]
        assume(all(serie[i] > serie[i - 1] for i in range(1, n)))
        assert all(point == 100.0 for point in relative_strength_index(serie, 1))
