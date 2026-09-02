"""risk calculations: sample covariance over aligned return series."""

import math
from decimal import Decimal

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from vertex_core.calculations.risk import (
    CORRELATION_BOUND_TOLERANCE,
    COVARIANCE_PSD_TOLERANCE,
    CorrelationResult,
    CovarianceResult,
    EstimatorNotImplementedError,
    MinimumSampleError,
    RiskCalculationError,
    correlation,
    covariance,
)


class TestGates:
    def test_unknown_estimator_is_not_implemented(self):
        with pytest.raises(EstimatorNotImplementedError, match="NOT_IMPLEMENTED"):
            covariance([[0.1, 0.2], [0.2, 0.1]], estimator="ledoit_wolf")

    def test_non_string_estimator_rejected(self):
        with pytest.raises(RiskCalculationError, match="string"):
            covariance([[0.1], [0.2]], estimator=42)

    def test_single_observation_rejected(self):
        with pytest.raises(MinimumSampleError):
            covariance([[0.1, 0.2]])

    def test_empty_input_rejected(self):
        with pytest.raises(MinimumSampleError):
            covariance([])

    def test_explicit_minimum_sample_enforced(self):
        with pytest.raises(MinimumSampleError, match="minimum_sample 5"):
            covariance([[0.1], [0.2], [0.3]], minimum_sample=5)

    def test_minimum_sample_below_two_rejected(self):
        with pytest.raises(RiskCalculationError, match="minimum_sample"):
            covariance([[0.1], [0.2]], minimum_sample=1)

    def test_nan_return_rejected(self):
        with pytest.raises(RiskCalculationError, match="non-finite"):
            covariance([[0.1, float("nan")], [0.2, 0.1]])

    def test_infinite_return_rejected(self):
        with pytest.raises(RiskCalculationError, match="non-finite"):
            covariance([[0.1, float("inf")], [0.2, 0.1]])

    def test_ragged_rows_rejected(self):
        with pytest.raises(RiskCalculationError, match="ragged"):
            covariance([[0.1, 0.2], [0.3]])

    def test_zero_asset_columns_rejected(self):
        with pytest.raises(RiskCalculationError, match="at least one asset"):
            covariance([[], []])

    def test_non_numeric_cell_rejected(self):
        with pytest.raises(RiskCalculationError, match="real number"):
            covariance([[0.1, "0.2"], [0.2, 0.1]])

    def test_bool_cell_rejected(self):
        with pytest.raises(RiskCalculationError, match="real number"):
            covariance([[0.1, True], [0.2, 0.1]])


class TestSampleCovariance:
    @pytest.mark.golden
    def test_golden_two_assets_hand_computed(self):
        # Provenance — hand computation (documented 2026-08-28), ddof=1:
        #   A = (0.01, 0.03, 0.02) mean 0.02 -> deviations (-0.01, 0.01, 0)
        #   B = (0.02, 0.06, 0.04) mean 0.04 -> deviations (-0.02, 0.02, 0)
        #   var(A) = (1e-4 + 1e-4 + 0) / 2 = 1e-4
        #   var(B) = (4e-4 + 4e-4 + 0) / 2 = 4e-4
        #   cov(A,B) = (2e-4 + 2e-4 + 0) / 2 = 2e-4  (B = 2A: exact comovement)
        result = covariance([[0.01, 0.02], [0.03, 0.06], [0.02, 0.04]])
        expected = ((1e-4, 2e-4), (2e-4, 4e-4))
        for row, expected_row in zip(result.matrix, expected, strict=True):
            for cell, expected_cell in zip(row, expected_row, strict=True):
                assert cell == pytest.approx(expected_cell, abs=1e-18)
        assert result.n_observations == 3
        assert result.n_assets == 2
        assert result.ddof == 1
        # Perfectly dependent columns: the smallest eigenvalue sits at the
        # PSD boundary, within the documented tolerance of zero.
        assert abs(result.min_eigenvalue) <= COVARIANCE_PSD_TOLERANCE * 1.0

    @pytest.mark.oracle
    def test_oracle_matches_numpy_cov(self):
        # Oracle: numpy.cov (rowvar=False, ddof=1), an independent
        # implementation of the same estimator.
        data = [
            [0.011, -0.004, 0.021],
            [0.002, 0.007, -0.013],
            [0.005, 0.009, 0.004],
            [-0.008, 0.012, 0.006],
            [0.010, -0.002, 0.001],
        ]
        expected = np.cov(np.array(data, dtype=np.float64), rowvar=False, ddof=1)
        result = covariance(data)
        assert np.allclose(np.array(result.matrix), expected, rtol=0.0, atol=1e-15)

    def test_single_asset_variance(self):
        result = covariance([[0.01], [0.03]])
        # var = ((0.01-0.02)^2 + (0.03-0.02)^2) / 1 = 2e-4
        assert result.matrix[0][0] == pytest.approx(2e-4, abs=1e-18)
        assert result.n_assets == 1

    def test_constant_column_gives_zero_row(self):
        # Not exact 0.0: the float64 column mean of three 0.05 values differs
        # from 0.05 by ~7e-18, so the variance is ~1e-35 (documented float64
        # core tolerance), indistinguishable from zero at any useful scale.
        result = covariance([[0.05, 0.01], [0.05, 0.02], [0.05, 0.03]])
        assert result.matrix[0][0] == pytest.approx(0.0, abs=1e-30)
        assert result.matrix[0][1] == pytest.approx(0.0, abs=1e-30)

    def test_decimal_input_accepted(self):
        result = covariance([[Decimal("0.01")], [Decimal("0.03")]])
        assert result.matrix[0][0] == pytest.approx(2e-4, abs=1e-18)

    def test_deterministic(self):
        data = [[0.011, -0.004], [0.002, 0.007], [0.005, 0.009]]
        assert covariance(data) == covariance(data)

    def test_result_matrix_exactly_symmetric(self):
        result = covariance([[0.011, -0.004, 0.02], [0.002, 0.007, -0.01], [0.005, 0.009, 0.0]])
        n = result.n_assets
        for i in range(n):
            for j in range(n):
                assert result.matrix[i][j] == result.matrix[j][i]

    def test_result_model_rejects_asymmetric_matrix(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="symmetric"):
            CovarianceResult(
                estimator="sample",
                n_observations=3,
                n_assets=2,
                ddof=1,
                matrix=((1.0, 0.5), (0.4, 1.0)),
                min_eigenvalue=0.1,
            )


@st.composite
def return_matrices(draw):
    n_assets = draw(st.integers(min_value=1, max_value=4))
    n_obs = draw(st.integers(min_value=2, max_value=8))
    row = st.lists(
        st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
        min_size=n_assets,
        max_size=n_assets,
    )
    return draw(st.lists(row, min_size=n_obs, max_size=n_obs))


class TestProperties:
    @pytest.mark.property
    @settings(max_examples=150, deadline=None)
    @given(matrix=return_matrices())
    def test_symmetric_and_psd_within_tolerance(self, matrix):
        result = covariance(matrix)
        n = result.n_assets
        for i in range(n):
            for j in range(n):
                assert result.matrix[i][j] == result.matrix[j][i]
                assert math.isfinite(result.matrix[i][j])
        # Independent PSD re-check through numpy.linalg.eigvalsh.
        eigenvalues = np.linalg.eigvalsh(np.array(result.matrix, dtype=np.float64))
        scale = max(1.0, float(np.abs(eigenvalues).max()))
        assert float(eigenvalues[0]) >= -COVARIANCE_PSD_TOLERANCE * scale

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(matrix=return_matrices())
    def test_diagonal_is_non_negative_variance(self, matrix):
        result = covariance(matrix)
        for i in range(result.n_assets):
            assert result.matrix[i][i] >= -1e-12


# Une ligne par date, une colonne par actif : l'orientation de `covariance`.
def _par_dates(*series: list[float]) -> list[list[float]]:
    return [list(ligne) for ligne in zip(*series, strict=True)]


_SERIE_A = [0.011, -0.023, 0.031, -0.014, 0.022, 0.005, 0.017, -0.009]
_SERIE_C = [-0.008, 0.030, -0.021, 0.012, -0.033, 0.019, -0.004, 0.006]


class TestCorrelation:
    """`risk.correlation` — renormalisation d'une covariance approuvee."""

    @pytest.mark.golden
    def test_golden_perfect_and_inverse(self):
        """Deux coefficients connus par construction, a l arrondi float64 pres.

        Une serie et son double portent la meme information : leur correlation
        vaut mathematiquement +1. Une serie et son opposee, -1.

        MAIS PAS EXACTEMENT EN float64. Mesure le 2026-09-01, ce cas rend
        0.9999999999999999 — un ULP sous 1.0. La cause est connue :
        `S_ab / sqrt(S_aa * S_bb)` vaut 1 en arithmetique exacte, et la racine
        carree y introduit un arrondi. Affirmer l egalite exacte serait
        s inventer une precision que la machine n a pas.

        La borne est donc declaree : quelques ULP, jamais plus. Un ecart plus
        grand ne serait plus un arrondi mais une erreur de methode.

        C est aussi, precisement, pourquoi la diagonale est POSEE et non
        calculee : elle subirait exactement le meme arrondi.
        """
        tolerance = 4 * math.ulp(1.0)  # ~8.9e-16
        double = [2.0 * x for x in _SERIE_A]
        oppose = [-x for x in _SERIE_A]
        result = correlation(covariance(_par_dates(_SERIE_A, double, oppose)))

        assert result.matrix[0][1] == pytest.approx(1.0, rel=0.0, abs=tolerance)
        assert result.matrix[0][2] == pytest.approx(-1.0, rel=0.0, abs=tolerance)
        assert result.matrix[1][2] == pytest.approx(-1.0, rel=0.0, abs=tolerance)

        # La diagonale, elle, est exacte — parce qu elle n est pas calculee.
        assert result.matrix[0][0] == 1.0

    @pytest.mark.oracle
    def test_oracle_matches_numpy_corrcoef(self):
        """Comparaison a une implementation independante.

        `numpy.corrcoef` n'est pas derivee de notre code. Si les deux
        divergent au-dela de 1e-12, c'est la notre qui est en cause.
        """
        dates = _par_dates(
            _SERIE_A, _SERIE_C, [x - y for x, y in zip(_SERIE_A, _SERIE_C, strict=True)]
        )
        nous = np.array(correlation(covariance(dates)).matrix)
        eux = np.corrcoef(np.array(dates), rowvar=False)
        np.testing.assert_allclose(nous, eux, rtol=0.0, atol=1e-12)

    def test_diagonal_is_posed_exactly(self):
        """La diagonale vaut 1.0 au bit pres — posee, jamais calculee.

        Un actif est parfaitement correle a lui-meme. Calculer S_ii/S_ii
        laisserait un arrondi l'en eloigner ; la valeur est donc posee.
        """
        result = correlation(covariance(_par_dates(_SERIE_A, _SERIE_C)))
        for index in range(result.n_assets):
            assert result.matrix[index][index] == 1.0

    def test_matrix_is_exactly_symmetric(self):
        result = correlation(covariance(_par_dates(_SERIE_A, _SERIE_C)))
        for i in range(result.n_assets):
            for j in range(result.n_assets):
                assert result.matrix[i][j] == result.matrix[j][i]

    def test_coefficients_are_the_renormalised_covariances(self):
        """Le calcul n'ajoute AUCUNE information : il renormalise.

        C'est ce qui le rend verifiable — chaque coefficient doit tomber
        exactement sur sa covariance divisee par le produit des ecarts-types.
        """
        cov = covariance(_par_dates(_SERIE_A, _SERIE_C))
        cor = correlation(cov)
        for i in range(cor.n_assets):
            for j in range(cor.n_assets):
                if i == j:
                    continue
                attendu = cov.matrix[i][j] / math.sqrt(cov.matrix[i][i] * cov.matrix[j][j])
                assert cor.matrix[i][j] == pytest.approx(attendu, rel=0.0, abs=1e-12)

    def test_shape_is_carried_from_the_covariance(self):
        cov = covariance(_par_dates(_SERIE_A, _SERIE_C))
        cor = correlation(cov)
        assert isinstance(cor, CorrelationResult)
        assert cor.n_assets == cov.n_assets == 2
        assert cor.n_observations == cov.n_observations == len(_SERIE_A)


class TestCorrelationGates:
    """Les deux refus, et le motif de chacun."""

    def test_constant_series_is_rejected(self):
        """Variance nulle : la correlation n'existe pas, on ne l'invente pas.

        Un titre suspendu a la cote ne bouge pas. Diviser par son ecart-type
        nul produirait un nombre sans signification ; le refus le dit.
        """
        constante = [0.0] * len(_SERIE_A)
        with pytest.raises(RiskCalculationError, match="variance nulle"):
            correlation(covariance(_par_dates(_SERIE_A, constante)))

    def test_out_of_bounds_coefficient_is_rejected_not_clamped(self):
        """Une matrice incoherente est REFUSEE, jamais ramenee dans [-1, 1].

        La construction contourne `covariance` volontairement : aucune vraie
        covariance ne produit cela. C'est precisement le point — si une telle
        matrice atteignait ce calcul, la ramener de force dans les bornes
        masquerait le defaut au lieu de le montrer.
        """
        incoherente = CovarianceResult(
            estimator="sample",
            n_observations=8,
            n_assets=2,
            ddof=1,
            matrix=((1.0, 2.0), (2.0, 1.0)),  # |rho| = 2 : impossible
            min_eigenvalue=-1.0,
        )
        with pytest.raises(RiskCalculationError, match="hors bornes"):
            correlation(incoherente)

    def test_float64_overshoot_is_clipped_within_tolerance(self):
        """Le seul recadrage admis : celui du float64, dans sa tolerance.

        Un depassement de l'ordre de CORRELATION_BOUND_TOLERANCE est un
        arrondi, pas une incoherence — il est ramene a la borne plutot que
        refuse. La frontiere entre les deux est declaree, pas implicite.
        """
        depassement = 1.0 + CORRELATION_BOUND_TOLERANCE / 2.0
        limite = CovarianceResult(
            estimator="sample",
            n_observations=8,
            n_assets=2,
            ddof=1,
            matrix=((1.0, depassement), (depassement, 1.0)),
            min_eigenvalue=0.0,
        )
        result = correlation(limite)
        assert result.matrix[0][1] == 1.0

    @pytest.mark.property
    @settings(max_examples=50, deadline=None)
    @given(
        st.lists(
            st.lists(
                st.floats(min_value=-0.5, max_value=0.5, allow_nan=False, allow_infinity=False),
                min_size=3,
                max_size=3,
            ),
            min_size=6,
            max_size=20,
        )
    )
    def test_property_bounds_and_symmetry_always_hold(self, dates):
        """Sur des series tirees au hasard, les invariants tiennent toujours.

        Une serie plate peut sortir du tirage : son refus est un comportement
        correct, pas un echec, et le test le reconnait comme tel.
        """
        try:
            result = correlation(covariance(dates))
        except RiskCalculationError:
            return  # variance nulle : refus attendu, pas un defaut
        for i in range(result.n_assets):
            assert result.matrix[i][i] == 1.0
            for j in range(result.n_assets):
                assert -1.0 <= result.matrix[i][j] <= 1.0
                assert result.matrix[i][j] == result.matrix[j][i]
