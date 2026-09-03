"""``market.bollinger_bands`` — bandes de Bollinger : vecteurs, portes, propriétés, oracle.

Convention déclarée : bande médiane = moyenne mobile simple ; bandes haute et
basse = médiane ± ``num_std`` × écart-type de POPULATION (ddof = 0) de la
fenêtre. Toutes les séries sont SYNTHÉTIQUES.
"""

from __future__ import annotations

import math
from decimal import Decimal

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st
from numpy.lib.stride_tricks import sliding_window_view

from vertex_core.calculations.market import (
    FLOAT64_ABS_TOL,
    FLOAT64_REL_TOL,
    BollingerBands,
    CalculationInputError,
    bollinger_bands,
    simple_moving_average,
)

NON_FINITE = [float("nan"), float("inf"), float("-inf"), Decimal("NaN"), Decimal("-Infinity")]

prix = st.lists(
    st.floats(min_value=1e-2, max_value=1e4, allow_nan=False, allow_infinity=False),
    min_size=2,
    max_size=60,
)
multiples = st.floats(min_value=1e-3, max_value=5.0, allow_nan=False, allow_infinity=False)


class TestBollingerBands:
    def test_vecteur_derive_a_la_main(self):
        # fenêtre 5 sur 1..5 : moyenne 3, variance de population
        # ((4+1+0+1+4)/5) = 2, écart-type sqrt(2) ; k = 2.
        bandes = bollinger_bands([1, 2, 3, 4, 5], 5, num_std=2)
        assert isinstance(bandes, BollingerBands)
        assert bandes.middle == pytest.approx((3.0,), rel=FLOAT64_REL_TOL)
        assert bandes.upper == pytest.approx((3.0 + 2.0 * math.sqrt(2.0),), rel=FLOAT64_REL_TOL)
        assert bandes.lower == pytest.approx((3.0 - 2.0 * math.sqrt(2.0),), rel=FLOAT64_REL_TOL)

    def test_fenetre_glissante_de_trois(self):
        # fenêtres (1,2,3), (2,3,4), (3,4,5) : moyennes 2, 3, 4 ;
        # variance de population 2/3 pour chacune ; k = 1.
        bandes = bollinger_bands([1, 2, 3, 4, 5], 3, num_std=1)
        ecart = math.sqrt(2.0 / 3.0)
        assert bandes.middle == pytest.approx((2.0, 3.0, 4.0), rel=FLOAT64_REL_TOL)
        assert bandes.upper == pytest.approx(
            (2.0 + ecart, 3.0 + ecart, 4.0 + ecart), rel=FLOAT64_REL_TOL
        )
        assert bandes.lower == pytest.approx(
            (2.0 - ecart, 3.0 - ecart, 4.0 - ecart), rel=FLOAT64_REL_TOL
        )

    def test_serie_constante_donne_trois_bandes_confondues(self):
        bandes = bollinger_bands([50, 50, 50], 2, num_std=2)
        assert bandes.middle == bandes.upper == bandes.lower == (50.0, 50.0)

    def test_entrees_decimales_converties_explicitement(self):
        bandes = bollinger_bands(
            [Decimal("100.00"), Decimal("101.00")], 2, num_std=Decimal("1.5")
        )
        # moyenne 100.5, écart-type de population 0.5, k = 1.5 -> ± 0.75
        assert bandes.upper == pytest.approx((101.25,), rel=FLOAT64_REL_TOL)
        assert bandes.lower == pytest.approx((99.75,), rel=FLOAT64_REL_TOL)

    def test_deterministe(self):
        serie = [100.0, 101.3, 99.8, 102.1, 101.0]
        assert bollinger_bands(serie, 3, num_std=2) == bollinger_bands(serie, 3, num_std=2)

    # -- portes -----------------------------------------------------------

    def test_serie_trop_courte_refusee(self):
        with pytest.raises(CalculationInputError) as capture:
            bollinger_bands([1, 2], 3, num_std=2)
        assert capture.value.reason == "minimum_sample"

    @pytest.mark.parametrize("mauvaise", [1, 0, -2])
    def test_fenetre_sans_dispersion_possible_refusee(self, mauvaise):
        """Un seul prix n'a pas de dispersion : la bande n'existe pas."""
        with pytest.raises(CalculationInputError) as capture:
            bollinger_bands([1, 2, 3], mauvaise, num_std=2)
        assert capture.value.reason == "invalid_window"

    @pytest.mark.parametrize("mauvais", [0, -1, 0.0, Decimal("-2")])
    def test_multiple_non_positif_refuse(self, mauvais):
        with pytest.raises(CalculationInputError) as capture:
            bollinger_bands([1, 2, 3], 2, num_std=mauvais)
        assert capture.value.reason == "invalid_num_std"

    @pytest.mark.parametrize("mauvais", NON_FINITE)
    def test_multiple_non_fini_refuse(self, mauvais):
        with pytest.raises(CalculationInputError) as capture:
            bollinger_bands([1, 2, 3], 2, num_std=mauvais)
        assert capture.value.reason == "non_finite_input"

    def test_multiple_booleen_refuse(self):
        with pytest.raises(CalculationInputError) as capture:
            bollinger_bands([1, 2, 3], 2, num_std=True)
        assert capture.value.reason == "invalid_type"

    @pytest.mark.parametrize("mauvais", [0, -1, Decimal("0")])
    def test_prix_non_positif_refuse(self, mauvais):
        with pytest.raises(CalculationInputError) as capture:
            bollinger_bands([1, mauvais, 3], 2, num_std=2)
        assert capture.value.reason == "non_positive_price"

    @pytest.mark.parametrize("mauvais", NON_FINITE)
    def test_prix_non_fini_refuse(self, mauvais):
        with pytest.raises(CalculationInputError) as capture:
            bollinger_bands([1, mauvais, 3], 2, num_std=2)
        assert capture.value.reason == "non_finite_input"


@pytest.mark.oracle
class TestOracleNumpy:
    """Oracle indépendant : moyenne et écart-type de population (ddof = 0)
    de chaque fenêtre par ``numpy`` sur une vue glissante."""

    @pytest.mark.parametrize(("fenetre", "k"), [(2, 1.0), (5, 2.0), (20, 2.0), (40, 0.5)])
    def test_oracle_sliding_window(self, fenetre, k):
        serie = np.array(
            [100.0 + 7.0 * math.sin(i / 3.0) + 0.1 * i for i in range(40)], dtype=np.float64
        )
        vues = sliding_window_view(serie, fenetre)
        moyennes = vues.mean(axis=1)
        ecarts = vues.std(axis=1, ddof=0)
        obtenu = bollinger_bands(list(serie), fenetre, num_std=k)
        assert len(obtenu.middle) == len(moyennes) == 40 - fenetre + 1
        assert np.allclose(np.array(obtenu.middle), moyennes, rtol=FLOAT64_REL_TOL, atol=0.0)
        assert np.allclose(
            np.array(obtenu.upper), moyennes + k * ecarts, rtol=FLOAT64_REL_TOL, atol=0.0
        )
        assert np.allclose(
            np.array(obtenu.lower), moyennes - k * ecarts, rtol=FLOAT64_REL_TOL, atol=0.0
        )


@pytest.mark.property
class TestProprietes:
    @given(serie=prix, k=multiples, data=st.data())
    def test_bandes_ordonnees_et_symetriques(self, serie, k, data):
        fenetre = data.draw(st.integers(min_value=2, max_value=len(serie)))
        bandes = bollinger_bands(serie, fenetre, num_std=k)
        assert len(bandes.middle) == len(bandes.upper) == len(bandes.lower)
        assert len(bandes.middle) == len(serie) - fenetre + 1
        for bas, milieu, haut in zip(bandes.lower, bandes.middle, bandes.upper, strict=True):
            assert math.isfinite(bas) and math.isfinite(haut)
            assert bas <= milieu <= haut
            # Deux arrondis float64 (m + h puis m - h), chacun d'au plus
            # ulp(m) / 2 : la symétrie tient à un ulp de la médiane près, ce
            # qui dépasse FLOAT64_ABS_TOL dès que m approche 1e4.
            assert math.isclose(
                haut - milieu,
                milieu - bas,
                rel_tol=FLOAT64_REL_TOL,
                abs_tol=max(FLOAT64_ABS_TOL, 2.0 * math.ulp(milieu)),
            )

    @given(serie=prix, data=st.data())
    def test_la_mediane_est_la_moyenne_mobile_simple_deja_approuvee(self, serie, data):
        """La bande médiane redit exactement ``market.sma`` : aucune
        information nouvelle, une présentation d'un calcul approuvé."""
        fenetre = data.draw(st.integers(min_value=2, max_value=len(serie)))
        bandes = bollinger_bands(serie, fenetre, num_std=2)
        assert bandes.middle == simple_moving_average(serie, fenetre)
