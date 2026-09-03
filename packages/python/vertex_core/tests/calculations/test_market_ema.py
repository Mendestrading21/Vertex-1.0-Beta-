"""``market.ema`` — moyenne mobile exponentielle : vecteurs, portes, propriétés, oracle.

Convention déclarée : amorce = moyenne arithmétique des ``window`` premiers
prix, puis ``EMA_t = alpha * p_t + (1 - alpha) * EMA_{t-1}`` avec
``alpha = 2 / (window + 1)``. Toutes les séries sont SYNTHÉTIQUES.
"""

from __future__ import annotations

import math
from decimal import Decimal

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st
from scipy.signal import lfilter, lfiltic

from vertex_core.calculations.market import (
    FLOAT64_REL_TOL,
    CalculationInputError,
    exponential_moving_average,
)

NON_FINITE = [float("nan"), float("inf"), float("-inf"), Decimal("NaN"), Decimal("-Infinity")]
RANGE_REL_TOL = 1e-12

prix = st.lists(
    st.floats(min_value=1e-2, max_value=1e4, allow_nan=False, allow_infinity=False),
    min_size=1,
    max_size=60,
)


def ema_reference(serie: list[float], fenetre: int) -> np.ndarray:
    """Oracle indépendant écrit DANS ce test : la récurrence est un filtre IIR
    du premier ordre, ``y[n] = alpha x[n] + (1 - alpha) y[n-1]``, résolu par
    ``scipy.signal.lfilter`` avec l'amorce posée par ``lfiltic``."""
    alpha = 2.0 / (fenetre + 1.0)
    amorce = float(np.mean(np.array(serie[:fenetre], dtype=np.float64)))
    b = [alpha]
    a = [1.0, -(1.0 - alpha)]
    reste = np.array(serie[fenetre:], dtype=np.float64)
    if reste.size == 0:
        return np.array([amorce])
    zi = lfiltic(b, a, y=[amorce])
    suite, _ = lfilter(b, a, reste, zi=zi)
    return np.concatenate([[amorce], suite])


class TestExponentialMovingAverage:
    def test_vecteur_derive_a_la_main(self):
        # amorce (1+2+3)/3 = 2 ; alpha = 2/4 = 0.5 ;
        # 0.5*4 + 0.5*2 = 3 ; 0.5*5 + 0.5*3 = 4
        serie = exponential_moving_average([1, 2, 3, 4, 5], 3)
        assert serie == pytest.approx((2.0, 3.0, 4.0), rel=FLOAT64_REL_TOL)

    def test_le_premier_point_est_la_moyenne_arithmetique_d_amorce(self):
        serie = exponential_moving_average([10, 20, 30, 40], 4)
        assert serie == (25.0,)

    def test_une_valeur_par_fenetre_complete(self):
        assert len(exponential_moving_average([1, 2, 3, 4, 5, 6], 4)) == 3

    def test_fenetre_1_rend_les_prix_eux_memes(self):
        assert exponential_moving_average([1.5, 2.5, 0.75], 1) == (1.5, 2.5, 0.75)

    def test_entrees_decimales_converties_explicitement(self):
        serie = exponential_moving_average([Decimal("100.00"), Decimal("101.50")], 2)
        assert serie == pytest.approx((100.75,), rel=FLOAT64_REL_TOL)

    def test_deterministe(self):
        serie = [100.0, 101.3, 99.8, 102.1, 101.0]
        assert exponential_moving_average(serie, 3) == exponential_moving_average(serie, 3)

    # -- portes -----------------------------------------------------------

    def test_serie_trop_courte_refusee(self):
        with pytest.raises(CalculationInputError) as capture:
            exponential_moving_average([1, 2], 3)
        assert capture.value.reason == "minimum_sample"

    @pytest.mark.parametrize("mauvaise", [0, -1])
    def test_fenetre_invalide_refusee(self, mauvaise):
        with pytest.raises(CalculationInputError) as capture:
            exponential_moving_average([1, 2, 3], mauvaise)
        assert capture.value.reason == "invalid_window"

    def test_fenetre_booleenne_refusee(self):
        with pytest.raises(CalculationInputError) as capture:
            exponential_moving_average([1, 2, 3], True)
        assert capture.value.reason == "invalid_type"

    @pytest.mark.parametrize("mauvais", [0, -1, Decimal("0")])
    def test_prix_non_positif_refuse(self, mauvais):
        with pytest.raises(CalculationInputError) as capture:
            exponential_moving_average([1, mauvais, 3], 2)
        assert capture.value.reason == "non_positive_price"

    @pytest.mark.parametrize("mauvais", NON_FINITE)
    def test_prix_non_fini_refuse(self, mauvais):
        with pytest.raises(CalculationInputError) as capture:
            exponential_moving_average([1, mauvais, 3], 2)
        assert capture.value.reason == "non_finite_input"

    @pytest.mark.parametrize("mauvaise", ["1,2,3", 5, None])
    def test_serie_non_sequence_refusee(self, mauvaise):
        with pytest.raises(CalculationInputError) as capture:
            exponential_moving_average(mauvaise, 1)
        assert capture.value.reason == "invalid_type"


@pytest.mark.oracle
class TestOracleScipy:
    @pytest.mark.parametrize("fenetre", [1, 2, 5, 12, 26, 39])
    def test_oracle_lfilter(self, fenetre):
        serie = [100.0 + 7.0 * math.sin(i / 3.0) + 0.1 * i for i in range(40)]
        attendu = ema_reference(serie, fenetre)
        obtenu = exponential_moving_average(serie, fenetre)
        assert len(obtenu) == len(attendu) == 40 - fenetre + 1
        assert np.allclose(np.array(obtenu), attendu, rtol=FLOAT64_REL_TOL, atol=0.0)


@pytest.mark.property
class TestProprietes:
    @given(serie=prix, data=st.data())
    def test_longueur_et_combinaison_convexe_des_prix_passes(self, serie, data):
        """Chaque point est une combinaison convexe des prix vus jusque-là :
        il reste dans leur intervalle (à l'arrondi float64 près)."""
        fenetre = data.draw(st.integers(min_value=1, max_value=len(serie)))
        obtenu = exponential_moving_average(serie, fenetre)
        assert len(obtenu) == len(serie) - fenetre + 1
        for index, valeur in enumerate(obtenu):
            vus = serie[: index + fenetre]
            assert math.isfinite(valeur)
            assert min(vus) * (1.0 - RANGE_REL_TOL) <= valeur <= max(vus) * (1.0 + RANGE_REL_TOL)

    @given(
        valeur=st.floats(min_value=1e-2, max_value=1e4, allow_nan=False, allow_infinity=False),
        n=st.integers(min_value=1, max_value=30),
        data=st.data(),
    )
    def test_serie_constante_donne_une_moyenne_constante(self, valeur, n, data):
        fenetre = data.draw(st.integers(min_value=1, max_value=n))
        for point in exponential_moving_average([valeur] * n, fenetre):
            assert point == pytest.approx(valeur, rel=RANGE_REL_TOL)

    @given(serie=prix)
    def test_fenetre_1_est_l_identite(self, serie):
        assert exponential_moving_average(serie, 1) == tuple(serie)
