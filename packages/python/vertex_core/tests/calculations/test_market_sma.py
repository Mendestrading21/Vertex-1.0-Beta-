"""``market.sma`` — moyenne mobile simple : vecteurs, portes, propriétés, oracle.

Toutes les séries sont SYNTHÉTIQUES et déterministes ; aucune donnée de marché
réelle, aucun aléa non maîtrisé (Hypothesis gère sa propre reproductibilité).
"""

from __future__ import annotations

import math
from decimal import Decimal

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from vertex_core.calculations.market import (
    FLOAT64_REL_TOL,
    CalculationInputError,
    simple_moving_average,
)

NON_FINITE = [float("nan"), float("inf"), float("-inf"), Decimal("NaN"), Decimal("-Infinity")]

#: Tolérance relative de l'invariant « dans l'intervalle de la fenêtre » : la
#: somme exacte (fsum) divisée par la fenêtre s'arrondit d'au plus un ulp.
RANGE_REL_TOL = 1e-12

prix = st.lists(
    st.floats(min_value=1e-2, max_value=1e4, allow_nan=False, allow_infinity=False),
    min_size=1,
    max_size=60,
)


class TestSimpleMovingAverage:
    def test_vecteur_derive_a_la_main(self):
        # (1+2+3)/3 = 2 ; (2+3+4)/3 = 3 ; (3+4+5)/3 = 4
        serie = simple_moving_average([1, 2, 3, 4, 5], 3)
        assert serie == pytest.approx((2.0, 3.0, 4.0), rel=FLOAT64_REL_TOL)

    def test_une_valeur_par_fenetre_complete_alignee_sur_le_dernier_prix(self):
        serie = simple_moving_average([10, 20, 30, 40], 2)
        assert len(serie) == 3, "aucun remplissage en tête : 4 prix, fenêtre 2, 3 points"
        assert serie[-1] == pytest.approx(35.0, rel=FLOAT64_REL_TOL)

    def test_fenetre_egale_a_la_serie_donne_un_seul_point(self):
        assert simple_moving_average([2, 4], 2) == (3.0,)

    def test_fenetre_1_rend_les_prix_eux_memes(self):
        assert simple_moving_average([1.5, 2.5], 1) == (1.5, 2.5)

    def test_entrees_decimales_converties_explicitement(self):
        serie = simple_moving_average([Decimal("100.00"), Decimal("101.50")], 2)
        assert serie == pytest.approx((100.75,), rel=FLOAT64_REL_TOL)

    def test_deterministe(self):
        serie = [100.0, 101.3, 99.8, 102.1, 101.0]
        assert simple_moving_average(serie, 3) == simple_moving_average(serie, 3)

    # -- portes, chacune nommée par son code stable -----------------------

    def test_serie_trop_courte_refusee_jamais_moyennee_sur_ce_qu_on_a(self):
        with pytest.raises(CalculationInputError) as capture:
            simple_moving_average([1, 2], 3)
        assert capture.value.reason == "minimum_sample"

    def test_serie_vide_refusee(self):
        with pytest.raises(CalculationInputError) as capture:
            simple_moving_average([], 1)
        assert capture.value.reason == "minimum_sample"

    @pytest.mark.parametrize("mauvaise", [0, -1])
    def test_fenetre_invalide_refusee(self, mauvaise):
        with pytest.raises(CalculationInputError) as capture:
            simple_moving_average([1, 2, 3], mauvaise)
        assert capture.value.reason == "invalid_window"

    @pytest.mark.parametrize("mauvaise", [True, 2.0, "2", None])
    def test_fenetre_non_entiere_refusee(self, mauvaise):
        with pytest.raises(CalculationInputError) as capture:
            simple_moving_average([1, 2, 3], mauvaise)
        assert capture.value.reason == "invalid_type"

    @pytest.mark.parametrize("mauvais", [0, -1, Decimal("0"), -0.5])
    def test_prix_non_positif_refuse(self, mauvais):
        with pytest.raises(CalculationInputError) as capture:
            simple_moving_average([1, mauvais, 3], 2)
        assert capture.value.reason == "non_positive_price"

    @pytest.mark.parametrize("mauvais", NON_FINITE)
    def test_prix_non_fini_refuse(self, mauvais):
        with pytest.raises(CalculationInputError) as capture:
            simple_moving_average([1, mauvais, 3], 2)
        assert capture.value.reason == "non_finite_input"

    @pytest.mark.parametrize("mauvais", [True, "1", None, [1.0]])
    def test_prix_non_numerique_refuse(self, mauvais):
        with pytest.raises(CalculationInputError) as capture:
            simple_moving_average([1, mauvais, 3], 2)
        assert capture.value.reason == "invalid_type"

    @pytest.mark.parametrize("mauvaise", ["1,2,3", 5, None, {"a": 1}])
    def test_serie_non_sequence_refusee(self, mauvaise):
        with pytest.raises(CalculationInputError) as capture:
            simple_moving_average(mauvaise, 1)
        assert capture.value.reason == "invalid_type"


@pytest.mark.oracle
class TestOracleNumpy:
    """Oracle indépendant : ``numpy.convolve`` en mode ``valid`` calcule la
    même moyenne glissante par une autre arithmétique (produit de convolution
    en float64), écrite DANS ce test."""

    @pytest.mark.parametrize("fenetre", [1, 2, 5, 13, 40])
    def test_oracle_numpy_convolve(self, fenetre):
        serie = [100.0 + 7.0 * math.sin(i / 3.0) + 0.1 * i for i in range(40)]
        noyau = np.ones(fenetre, dtype=np.float64) / fenetre
        attendu = np.convolve(np.array(serie, dtype=np.float64), noyau, mode="valid")
        obtenu = simple_moving_average(serie, fenetre)
        assert len(obtenu) == len(attendu) == 40 - fenetre + 1
        assert np.allclose(np.array(obtenu), attendu, rtol=FLOAT64_REL_TOL, atol=0.0)


@pytest.mark.property
class TestProprietes:
    @given(serie=prix, data=st.data())
    def test_longueur_et_bornes_de_chaque_fenetre(self, serie, data):
        fenetre = data.draw(st.integers(min_value=1, max_value=len(serie)))
        obtenu = simple_moving_average(serie, fenetre)
        assert len(obtenu) == len(serie) - fenetre + 1
        for index, valeur in enumerate(obtenu):
            bloc = serie[index : index + fenetre]
            assert math.isfinite(valeur)
            assert min(bloc) * (1.0 - RANGE_REL_TOL) <= valeur <= max(bloc) * (1.0 + RANGE_REL_TOL)

    @given(
        valeur=st.floats(min_value=1e-2, max_value=1e4, allow_nan=False, allow_infinity=False),
        n=st.integers(min_value=1, max_value=30),
        data=st.data(),
    )
    def test_serie_constante_donne_une_moyenne_constante(self, valeur, n, data):
        fenetre = data.draw(st.integers(min_value=1, max_value=n))
        for point in simple_moving_average([valeur] * n, fenetre):
            assert point == pytest.approx(valeur, rel=RANGE_REL_TOL)

    @given(serie=prix)
    def test_fenetre_1_est_l_identite(self, serie):
        assert simple_moving_average(serie, 1) == tuple(serie)
