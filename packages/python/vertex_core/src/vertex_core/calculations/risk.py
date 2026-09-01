"""Risk calculations: covariance estimation over aligned return series.

Implements the calculation registry entry ``risk.covariance``.

Alignment contract
------------------
``aligned_returns`` is a complete rectangular matrix: one row per synchronous
observation date, one column per asset, aligned point-in-time by the caller
(the upstream owner of the ``point_in_time_universe`` gate). A missing return
must be resolved upstream — a hole is rejected here and is never replaced by
zero.

Population rule: one population per call — one real universe snapshot OR one
hypothetical scenario set, never mixed.

Numeric policy
--------------
float64 core (numpy). Sample estimator with ``ddof=1``:
``S = centered.T @ centered / (n - 1)``. Documented tolerances:

- ``COVARIANCE_SYMMETRY_TOLERANCE`` (1e-12, relative to ``max(1, max|S|)``)
  bounds the floating-point asymmetry of the raw product before the exact
  symmetrization ``(S + S.T) / 2``;
- ``COVARIANCE_PSD_TOLERANCE`` (1e-10, relative to ``max(1, max|eig|)``)
  bounds the admissible negative eigenvalue computed with
  ``numpy.linalg.eigvalsh``.

Deterministic: no randomness, fixed estimator, fixed tolerances. Fail-closed:
every invalid input raises a typed :class:`RiskCalculationError` subclass, and
an estimator without a real implementation raises
:class:`EstimatorNotImplementedError` (NOT_IMPLEMENTED — never presented as a
pending capability).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from decimal import Decimal
from typing import Annotated

import numpy as np
from pydantic import AfterValidator, model_validator

from vertex_core.contracts.types import ContractModel, NonEmptyStr, PositiveInt

__all__ = [
    "CORRELATION_BOUND_TOLERANCE",
    "COVARIANCE_PSD_TOLERANCE",
    "COVARIANCE_SYMMETRY_TOLERANCE",
    "CorrelationResult",
    "CovarianceResult",
    "EstimatorNotImplementedError",
    "MinimumSampleError",
    "RiskCalculationError",
    "correlation",
    "covariance",
]

COVARIANCE_SYMMETRY_TOLERANCE = 1e-12
"""Max admissible |S - S.T| relative to max(1, max|S|) before symmetrization."""

CORRELATION_BOUND_TOLERANCE = 1e-9
"""Depassement admissible de |rho| au-dela de 1, du seul fait du float64.

Un coefficient qui sort de [-1, 1] au-dela de cette marge n'est pas un
arrondi : c'est une matrice incoherente, et elle est REFUSEE plutot que
ramenee de force dans les bornes."""

COVARIANCE_PSD_TOLERANCE = 1e-10
"""Min admissible eigenvalue: >= -tolerance * max(1, max|eigenvalue|)."""


class RiskCalculationError(ValueError):
    """Base typed error for every invalid risk-calculation input (fail-closed)."""


class MinimumSampleError(RiskCalculationError):
    """Fewer synchronous observations than the required minimum sample."""


class EstimatorNotImplementedError(RiskCalculationError):
    """The requested estimator is NOT_IMPLEMENTED; only real implementations run."""


def _ensure_finite_float(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError(
            "non-finite float rejected: NaN and infinities are not valid contract values"
        )
    return value


FiniteFloat = Annotated[float, AfterValidator(_ensure_finite_float)]
"""Float64 result value with NaN/infinity rejected at the DTO boundary."""


class CovarianceResult(ContractModel):
    """Symmetric, PSD-within-tolerance sample covariance matrix with its lineage facts.

    ``matrix`` is exactly symmetric (validated), square ``n_assets`` x
    ``n_assets`` in the column order of the input; ``min_eigenvalue`` is the
    smallest eigenvalue observed by ``numpy.linalg.eigvalsh`` (may be a tiny
    negative within ``COVARIANCE_PSD_TOLERANCE``).
    """

    estimator: NonEmptyStr
    n_observations: PositiveInt
    n_assets: PositiveInt
    ddof: PositiveInt
    matrix: tuple[tuple[FiniteFloat, ...], ...]
    min_eigenvalue: FiniteFloat

    @model_validator(mode="after")
    def _check_shape_and_symmetry(self) -> CovarianceResult:
        if len(self.matrix) != self.n_assets:
            raise ValueError("matrix row count must equal n_assets")
        for row in self.matrix:
            if len(row) != self.n_assets:
                raise ValueError("matrix must be square (n_assets x n_assets)")
        for i in range(self.n_assets):
            for j in range(i):
                if self.matrix[i][j] != self.matrix[j][i]:
                    raise ValueError("matrix must be exactly symmetric")
        if self.n_observations <= self.ddof:
            raise ValueError("n_observations must exceed ddof")
        return self


def _validate_matrix(aligned_returns: Sequence[Sequence[float]]) -> list[list[float]]:
    if isinstance(aligned_returns, (str, bytes)):
        raise RiskCalculationError("aligned_returns must be a sequence of observation rows")
    rows = tuple(aligned_returns)
    converted: list[list[float]] = []
    width = None
    for i, row in enumerate(rows):
        if isinstance(row, (str, bytes)) or not isinstance(row, Sequence):
            raise RiskCalculationError(f"observation row {i} must be a sequence of returns")
        cells = tuple(row)
        if width is None:
            width = len(cells)
        elif len(cells) != width:
            raise RiskCalculationError(
                f"ragged input: row {i} has {len(cells)} cells, expected {width} "
                "(a missing return must be resolved upstream, never dropped or zero-filled here)"
            )
        converted_row: list[float] = []
        for j, cell in enumerate(cells):
            if isinstance(cell, bool) or not isinstance(cell, (int, float, Decimal)):
                raise RiskCalculationError(
                    f"cell [{i}][{j}] must be a real number, got {type(cell).__name__}"
                )
            value = float(cell)
            if not math.isfinite(value):
                raise RiskCalculationError(
                    f"non-finite return at [{i}][{j}] rejected (fail-closed)"
                )
            converted_row.append(value)
        converted.append(converted_row)
    if width == 0:
        raise RiskCalculationError("aligned_returns needs at least one asset column")
    return converted


class CorrelationResult(ContractModel):
    """Matrice de correlation, derivee d'une covariance deja validee.

    ``matrix`` est exactement symetrique et sa diagonale vaut exactement
    ``1.0`` — elle n'est pas calculee mais posee : un actif est parfaitement
    correle a lui-meme, et laisser un arrondi la deplacer serait absurde.
    """

    n_observations: PositiveInt
    n_assets: PositiveInt
    matrix: tuple[tuple[FiniteFloat, ...], ...]


def correlation(result: CovarianceResult) -> CorrelationResult:
    """``risk.correlation`` — correlation de Pearson depuis une covariance.

    Methode : ``rho_ij = S_ij / sqrt(S_ii * S_jj)``, sur une matrice deja
    validee par :func:`covariance` (symetrique, PSD dans sa tolerance).

    Gates :

    - ``positive_variances`` : chaque variance diagonale strictement positive.
      Une serie constante a une variance nulle et n'a AUCUNE correlation
      definie — la division serait une invention, pas un calcul ;
    - ``bounded_coefficients`` : ``|rho| <= 1 + CORRELATION_BOUND_TOLERANCE``.
      Au-dela, la matrice est incoherente et REFUSEE ; la ramener de force
      dans les bornes masquerait le defaut.

    Invariants (testes) : diagonale exactement ``1.0``, matrice exactement
    symetrique, et chaque coefficient egal a sa covariance renormalisee.
    """
    matrice = result.matrix
    n = result.n_assets
    variances = [matrice[i][i] for i in range(n)]
    for index, variance in enumerate(variances):
        if not (variance > 0.0):
            raise RiskCalculationError(
                f"risk.correlation : variance nulle ou negative pour l'actif "
                f"#{index} ({variance}). Une serie constante n'a pas de "
                "correlation definie ; l'inventer serait une falsification."
            )

    ecarts = [math.sqrt(variance) for variance in variances]
    lignes: list[tuple[float, ...]] = []
    for i in range(n):
        ligne: list[float] = []
        for j in range(n):
            if i == j:
                # Posee, jamais calculee : un actif est parfaitement correle a
                # lui-meme, et un arrondi ne doit pas l'en eloigner.
                ligne.append(1.0)
                continue
            rho = matrice[i][j] / (ecarts[i] * ecarts[j])
            if abs(rho) > 1.0 + CORRELATION_BOUND_TOLERANCE:
                raise RiskCalculationError(
                    f"risk.correlation : coefficient hors bornes ({rho}) pour "
                    f"({i}, {j}). La matrice est incoherente ; la ramener de "
                    "force dans [-1, 1] masquerait le defaut."
                )
            # Le seul recadrage admis : celui du float64, dans sa tolerance.
            ligne.append(_ensure_finite_float(max(-1.0, min(1.0, rho))))
        lignes.append(tuple(ligne))

    # Symetrie exacte : `(M + M.T) / 2` sur des valeurs deja quasi symetriques.
    symetrique = tuple(
        tuple(1.0 if i == j else (lignes[i][j] + lignes[j][i]) / 2.0 for j in range(n))
        for i in range(n)
    )
    return CorrelationResult(n_observations=result.n_observations, n_assets=n, matrix=symetrique)


def covariance(
    aligned_returns: Sequence[Sequence[float]],
    estimator: str = "sample",
    minimum_sample: int = 2,
) -> CovarianceResult:
    """Sample covariance matrix of aligned per-asset return series.

    Registry: ``risk.covariance``. Gates:

    - ``minimum_sample``: at least ``minimum_sample`` (>= 2, because
      ``ddof=1``) synchronous observations, otherwise
      :class:`MinimumSampleError`;
    - ``point_in_time_universe``: alignment is the caller's upstream duty;
      here the matrix must be rectangular and complete (finite real numbers
      only — ``Decimal`` input is converted to float64 with a relative error
      <= 2**-52).

    Only ``estimator="sample"`` has a real implementation; any other name
    raises :class:`EstimatorNotImplementedError` (NOT_IMPLEMENTED).

    Invariants (tested): the returned matrix is exactly symmetric (built as
    ``(S + S.T) / 2`` after checking the raw asymmetry against
    ``COVARIANCE_SYMMETRY_TOLERANCE``) and positive semi-definite within
    ``COVARIANCE_PSD_TOLERANCE`` via ``numpy.linalg.eigvalsh``; both checks
    fail closed with :class:`RiskCalculationError` when violated.
    """
    if not isinstance(estimator, str):
        raise RiskCalculationError(f"estimator must be a string, got {type(estimator).__name__}")
    if estimator != "sample":
        raise EstimatorNotImplementedError(
            f"estimator {estimator!r} is NOT_IMPLEMENTED: only 'sample' has a real implementation"
        )
    if (
        isinstance(minimum_sample, bool)
        or not isinstance(minimum_sample, int)
        or minimum_sample < 2
    ):
        raise RiskCalculationError(
            "minimum_sample must be an int >= 2 (ddof=1 needs two observations)"
        )

    converted = _validate_matrix(aligned_returns)
    n_observations = len(converted)
    if n_observations < minimum_sample:
        raise MinimumSampleError(
            f"{n_observations} synchronous observations < required minimum_sample {minimum_sample}"
        )
    n_assets = len(converted[0])

    data = np.array(converted, dtype=np.float64)
    centered = data - data.mean(axis=0)
    raw = centered.T @ centered / float(n_observations - 1)

    scale = max(1.0, float(np.abs(raw).max()))
    asymmetry = float(np.abs(raw - raw.T).max())
    if asymmetry > COVARIANCE_SYMMETRY_TOLERANCE * scale:
        raise RiskCalculationError(
            f"raw covariance asymmetry {asymmetry} exceeds the documented tolerance"
        )
    symmetric = (raw + raw.T) / 2.0

    eigenvalues = np.linalg.eigvalsh(symmetric)
    min_eigenvalue = float(eigenvalues[0])
    eigen_scale = max(1.0, float(np.abs(eigenvalues).max()))
    if min_eigenvalue < -COVARIANCE_PSD_TOLERANCE * eigen_scale:
        raise RiskCalculationError(
            f"covariance matrix is not positive semi-definite within tolerance "
            f"(min eigenvalue {min_eigenvalue})"
        )

    matrix = tuple(tuple(float(cell) for cell in row) for row in symmetric)
    return CovarianceResult(
        estimator=estimator,
        n_observations=n_observations,
        n_assets=n_assets,
        ddof=1,
        matrix=matrix,
        min_eigenvalue=min_eigenvalue,
    )
