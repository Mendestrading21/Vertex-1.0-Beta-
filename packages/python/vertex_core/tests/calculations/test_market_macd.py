"""``market.macd`` — convergence/divergence de moyennes mobiles : vecteurs, portes,
propriétés, oracle.

Convention déclarée : ``MACD = EMA(fast) - EMA(slow)`` des prix ; ligne de
signal = EMA(signal) de la ligne MACD ; histogramme = MACD - signal. Les EMA
sont celles de ``market.ema`` (amorce = moyenne arithmétique). Toutes les
séries sont SYNTHÉTIQUES.
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
    MacdSeries,
    exponential_moving_average,
    macd,
)

NON_FINITE = [float("nan"), float("inf"), float("-inf"), Decimal("NaN"), Decimal("-Infinity")]

prix = st.lists(
    st.floats(min_value=1e-2, max_value=1e4, allow_nan=False, allow_infinity=False),
    min_size=3,
    max_size=60,
)


def ema_reference(serie: np.ndarray, fenetre: int) -> np.ndarray:
    alpha = 2.0 / (fenetre + 1.0)
    amorce = float(np.mean(serie[:fenetre]))
    reste = serie[fenetre:]
    if reste.size == 0:
        return np.array([amorce])
    b = [alpha]
    a = [1.0, -(1.0 - alpha)]
    suite, _ = lfilter(b, a, reste, zi=lfiltic(b, a, y=[amorce]))
    return np.concatenate([[amorce], suite])


def macd_reference(
    serie: list[float], fast: int, slow: int, signal: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Oracle indépendant écrit DANS ce test : composition de trois filtres
    IIR ``scipy.signal.lfilter``."""
    x = np.array(serie, dtype=np.float64)
    rapide = ema_reference(x, fast)
    lente = ema_reference(x, slow)
    ligne = rapide[slow - fast :] - lente
    sig = ema_reference(ligne, signal)
    histogramme = ligne[len(ligne) - len(sig) :] - sig
    return ligne, sig, histogramme


class TestMacd:
    def test_vecteur_derive_a_la_main(self):
        # Série linéaire 1..6, fast = 1 (EMA(1) = prix), slow = 2 :
        # EMA(2) amorce 1.5 puis alpha 2/3 : 2.5, 3.5, 4.5, 5.5.
        # MACD = prix aligné - EMA(2) = 0.5 partout ; signal EMA(2) de 0.5 = 0.5 ;
        # histogramme 0.
        resultat = macd([1, 2, 3, 4, 5, 6], fast=1, slow=2, signal=2)
        assert isinstance(resultat, MacdSeries)
        assert resultat.macd == pytest.approx((0.5,) * 5, rel=FLOAT64_REL_TOL)
        assert resultat.signal == pytest.approx((0.5,) * 4, rel=FLOAT64_REL_TOL)
        assert resultat.histogram == pytest.approx((0.0,) * 4, abs=1e-12)

    def test_longueurs_alignees_sur_le_dernier_prix(self):
        # 40 prix, slow 26 -> 15 points MACD ; signal 9 -> 7 points de signal.
        resultat = macd([100.0 + i for i in range(40)], fast=12, slow=26, signal=9)
        assert len(resultat.macd) == 40 - 26 + 1
        assert len(resultat.signal) == len(resultat.histogram) == 40 - 26 - 9 + 2

    def test_juste_assez_de_prix_donne_un_seul_point_de_signal(self):
        resultat = macd([100.0 + i for i in range(34)], fast=12, slow=26, signal=9)
        assert len(resultat.signal) == 1

    def test_la_ligne_macd_redit_les_deux_ema_deja_approuvees(self):
        serie = [100.0 + 7.0 * math.sin(i / 3.0) + 0.1 * i for i in range(40)]
        resultat = macd(serie, fast=5, slow=12, signal=4)
        rapide = exponential_moving_average(serie, 5)
        lente = exponential_moving_average(serie, 12)
        attendu = [rapide[i + 12 - 5] - lente[i] for i in range(len(lente))]
        assert resultat.macd == pytest.approx(tuple(attendu), rel=FLOAT64_REL_TOL, abs=1e-12)

    def test_l_histogramme_est_la_difference_macd_moins_signal(self):
        serie = [100.0 + 7.0 * math.sin(i / 3.0) + 0.1 * i for i in range(40)]
        resultat = macd(serie, fast=5, slow=12, signal=4)
        queue = resultat.macd[len(resultat.macd) - len(resultat.signal) :]
        attendu = [m - s for m, s in zip(queue, resultat.signal, strict=True)]
        assert resultat.histogram == pytest.approx(tuple(attendu), rel=FLOAT64_REL_TOL, abs=1e-12)

    def test_entrees_decimales_converties_explicitement(self):
        resultat = macd(
            [Decimal("1"), Decimal("2"), Decimal("3"), Decimal("4")], fast=1, slow=2, signal=1
        )
        assert resultat.macd == pytest.approx((0.5, 0.5, 0.5), rel=FLOAT64_REL_TOL)

    def test_deterministe(self):
        serie = [100.0 + 7.0 * math.sin(i / 3.0) for i in range(40)]
        assert macd(serie, fast=3, slow=6, signal=2) == macd(serie, fast=3, slow=6, signal=2)

    # -- portes -----------------------------------------------------------

    @pytest.mark.parametrize(("fast", "slow"), [(26, 12), (12, 12)])
    def test_fenetre_rapide_non_strictement_plus_courte_refusee(self, fast, slow):
        with pytest.raises(CalculationInputError) as capture:
            macd([100.0 + i for i in range(60)], fast=fast, slow=slow, signal=9)
        assert capture.value.reason == "unordered_windows"

    def test_serie_trop_courte_refusee(self):
        # slow 26 + signal 9 - 1 = 34 prix requis.
        with pytest.raises(CalculationInputError) as capture:
            macd([100.0 + i for i in range(33)], fast=12, slow=26, signal=9)
        assert capture.value.reason == "minimum_sample"

    @pytest.mark.parametrize(
        "fenetres",
        [
            {"fast": 0, "slow": 26, "signal": 9},
            {"fast": 12, "slow": -1, "signal": 9},
            {"fast": 12, "slow": 26, "signal": 0},
        ],
    )
    def test_fenetre_invalide_refusee(self, fenetres):
        with pytest.raises(CalculationInputError) as capture:
            macd([100.0 + i for i in range(60)], **fenetres)
        assert capture.value.reason == "invalid_window"

    def test_fenetre_booleenne_refusee(self):
        with pytest.raises(CalculationInputError) as capture:
            macd([100.0 + i for i in range(60)], fast=True, slow=26, signal=9)
        assert capture.value.reason == "invalid_type"

    @pytest.mark.parametrize("mauvais", [0, -1, Decimal("0")])
    def test_prix_non_positif_refuse(self, mauvais):
        with pytest.raises(CalculationInputError) as capture:
            macd([1, mauvais, 3, 4], fast=1, slow=2, signal=1)
        assert capture.value.reason == "non_positive_price"

    @pytest.mark.parametrize("mauvais", NON_FINITE)
    def test_prix_non_fini_refuse(self, mauvais):
        with pytest.raises(CalculationInputError) as capture:
            macd([1, mauvais, 3, 4], fast=1, slow=2, signal=1)
        assert capture.value.reason == "non_finite_input"

    def test_serie_non_sequence_refusee(self):
        with pytest.raises(CalculationInputError) as capture:
            macd("1,2,3", fast=1, slow=2, signal=1)
        assert capture.value.reason == "invalid_type"


@pytest.mark.oracle
class TestOracleScipy:
    @pytest.mark.parametrize(
        ("fast", "slow", "signal"), [(1, 2, 1), (3, 6, 2), (12, 26, 9), (5, 30, 10)]
    )
    def test_oracle_lfilter(self, fast, slow, signal):
        serie = [100.0 + 7.0 * math.sin(i / 3.0) + 0.1 * i for i in range(40)]
        ligne, sig, histogramme = macd_reference(serie, fast, slow, signal)
        obtenu = macd(serie, fast=fast, slow=slow, signal=signal)
        assert len(obtenu.macd) == len(ligne)
        assert len(obtenu.signal) == len(sig)
        assert np.allclose(np.array(obtenu.macd), ligne, rtol=FLOAT64_REL_TOL, atol=1e-12)
        assert np.allclose(np.array(obtenu.signal), sig, rtol=FLOAT64_REL_TOL, atol=1e-12)
        assert np.allclose(
            np.array(obtenu.histogram), histogramme, rtol=FLOAT64_REL_TOL, atol=1e-12
        )


@pytest.mark.property
class TestProprietes:
    @given(serie=prix, data=st.data())
    def test_longueurs_et_finitude(self, serie, data):
        slow = data.draw(st.integers(min_value=2, max_value=len(serie)))
        fast = data.draw(st.integers(min_value=1, max_value=slow - 1))
        signal = data.draw(st.integers(min_value=1, max_value=len(serie) - slow + 1))
        resultat = macd(serie, fast=fast, slow=slow, signal=signal)
        assert len(resultat.macd) == len(serie) - slow + 1
        assert len(resultat.signal) == len(resultat.histogram) == len(serie) - slow - signal + 2
        assert all(math.isfinite(v) for ligne in resultat for v in ligne)

    @given(
        valeur=st.floats(min_value=1e-2, max_value=1e4, allow_nan=False, allow_infinity=False),
        n=st.integers(min_value=3, max_value=40),
    )
    def test_serie_constante_donne_un_macd_nul(self, valeur, n):
        resultat = macd([valeur] * n, fast=1, slow=2, signal=1)
        for point in resultat.macd:
            assert point == pytest.approx(0.0, abs=1e-12 * valeur)
