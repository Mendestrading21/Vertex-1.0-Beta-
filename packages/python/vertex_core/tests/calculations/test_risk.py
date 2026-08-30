"""risk calculations: sample covariance over aligned return series."""

import math
from decimal import Decimal

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from vertex_core.calculations.risk import (
    COVARIANCE_PSD_TOLERANCE,
    CovarianceResult,
    EstimatorNotImplementedError,
    MinimumSampleError,
    RiskCalculationError,
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
