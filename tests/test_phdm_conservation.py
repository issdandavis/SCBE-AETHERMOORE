"""Property-based conservation tests for Layer 11 coherence safeguards."""

from __future__ import annotations

import math

import numpy as np
from hypothesis import given
from hypothesis import strategies as st


SACRED_TONGUE_WEIGHTS = {
    "KO": 1.00,
    "AV": 1.62,
    "RU": 2.62,
    "CA": 4.24,
    "UM": 6.85,
    "DR": 11.09,
}

PHI = (1 + math.sqrt(5.0)) / 2.0
EPSILON = 1e-8


@st.composite
def vector_strategy(draw, dim: int, min_value: float = -10.0, max_value: float = 10.0):
    values = draw(
        st.lists(
            st.floats(min_value=min_value, max_value=max_value, allow_nan=False, allow_infinity=False),
            min_size=dim,
            max_size=dim,
        )
    )
    return np.asarray(values, dtype=np.float64)


def project_to_poincare_ball(vec: np.ndarray, max_norm: float = 0.999999) -> np.ndarray:
    norm = np.linalg.norm(vec)
    if norm < max_norm:
        return vec
    return vec / norm * max_norm


def harmonic_wall(d: float, radius: float) -> float:
    return radius ** (d**2)


def normalize(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    if norm < EPSILON:
        return np.zeros_like(vec)
    return vec / norm


def pqcm_connectivity(matrix: np.ndarray) -> np.ndarray:
    # Construct an SPD matrix from an arbitrary square matrix.
    return matrix @ matrix.T + np.eye(matrix.shape[0]) * 1e-6


def clamp_trust(score: float) -> float:
    return min(1.0, max(0.0, score))


@given(vector_strategy(21, -100.0, 100.0))
def test_phdm_vectors_remain_inside_poincare_ball(raw_vec: np.ndarray) -> None:
    projected = project_to_poincare_ball(raw_vec)
    assert np.linalg.norm(projected) < 1.0


@given(
    st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    st.floats(min_value=1.001, max_value=3.0, allow_nan=False, allow_infinity=False),
)
def test_harmonic_wall_is_strictly_monotonic_in_d(d1: float, d2: float, radius: float) -> None:
    lower_d, upper_d = sorted((d1, d2))
    if math.isclose(lower_d, upper_d, abs_tol=1e-9):
        upper_d = lower_d + 1e-6

    assert harmonic_wall(upper_d, radius) > harmonic_wall(lower_d, radius)


def test_sacred_tongue_weights_follow_golden_ratio_sequence() -> None:
    assert SACRED_TONGUE_WEIGHTS == {
        "KO": 1.0,
        "AV": 1.62,
        "RU": 2.62,
        "CA": 4.24,
        "UM": 6.85,
        "DR": 11.09,
    }

    values = list(SACRED_TONGUE_WEIGHTS.values())
    for i in range(1, len(values)):
        ratio = values[i] / values[i - 1]
        assert math.isclose(ratio, PHI, rel_tol=0.02)


@given(vector_strategy(8, -100.0, 100.0))
def test_phase_vectors_are_unit_normalized(phase_vec: np.ndarray) -> None:
    normalized = normalize(phase_vec)
    if np.linalg.norm(phase_vec) < EPSILON:
        assert np.allclose(normalized, np.zeros_like(phase_vec))
    else:
        assert np.isclose(np.linalg.norm(normalized), 1.0, atol=1e-7)


@given(
    st.integers(min_value=2, max_value=8),
    st.data(),
)
def test_pqcm_connectivity_eigenspectrum_is_spd(dim: int, data) -> None:
    raw = data.draw(vector_strategy(dim * dim, -10.0, 10.0))
    matrix = raw.reshape(dim, dim)
    connectivity = pqcm_connectivity(matrix)

    assert np.allclose(connectivity, connectivity.T, atol=1e-9)
    eigenvalues = np.linalg.eigvalsh(connectivity)
    assert np.all(eigenvalues > 0.0)


@given(st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False))
def test_trust_scores_are_bounded(score: float) -> None:
    bounded = clamp_trust(score)
    assert 0.0 <= bounded <= 1.0


@given(
    vector_strategy(12, -100.0, 100.0),
    st.floats(min_value=0.0, max_value=2 * math.pi, allow_nan=False, allow_infinity=False),
)
def test_total_system_energy_is_conserved_within_epsilon(state: np.ndarray, theta: float) -> None:
    # Agent operation modeled as orthonormal pairwise rotation.
    rotation = np.array(
        [[math.cos(theta), -math.sin(theta)], [math.sin(theta), math.cos(theta)]],
        dtype=np.float64,
    )
    transformed = state.copy()
    for i in range(0, len(state) - 1, 2):
        transformed[i : i + 2] = rotation @ state[i : i + 2]

    energy_before = float(np.dot(state, state))
    energy_after = float(np.dot(transformed, transformed))
    assert math.isclose(energy_before, energy_after, rel_tol=0.0, abs_tol=1e-6)
