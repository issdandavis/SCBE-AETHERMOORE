"""
Tests for src/training/topological_loss.py
==========================================

Covers:
- Symmetry group generators (A4, S4, A5)
- Friction Laplacian construction
- TopologicalLoss (numpy) three-term computation
- topological_training_step convenience function
- Generator alignment loss
"""

import sys
import math
from pathlib import Path

import pytest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from training.topological_loss import (
    PHI,
    tetrahedral_generators_A4,
    octahedral_generators_S4,
    icosahedral_generators_A5,
    SYMMETRY_GENERATORS,
    FrictionLaplacian,
    _natural_frequency,
    _PHDM_POLYHEDRA,
    build_default_friction_laplacian,
    TopologicalLossConfig,
    TopologicalLoss,
    topological_training_step,
)

# ============================================================
# Symmetry group generators
# ============================================================


@pytest.mark.unit
class TestSymmetryGenerators:
    def test_a4_generators_count(self):
        gens = tetrahedral_generators_A4()
        assert len(gens) == 2

    def test_a4_generator_shapes(self):
        gens = tetrahedral_generators_A4()
        for g in gens:
            assert g.shape == (4, 4)

    def test_a4_generators_are_permutation_matrices(self):
        """Each row and column of a permutation matrix sums to 1."""
        gens = tetrahedral_generators_A4()
        for g in gens:
            for i in range(4):
                assert abs(g[i].sum() - 1.0) < 1e-10
                assert abs(g[:, i].sum() - 1.0) < 1e-10

    def test_s4_generators_count(self):
        gens = octahedral_generators_S4()
        assert len(gens) == 2

    def test_s4_generator_shapes(self):
        gens = octahedral_generators_S4()
        for g in gens:
            assert g.shape == (3, 3)

    def test_s4_generators_orthogonal(self):
        """Rotation matrices should be orthogonal: R^T R = I."""
        gens = octahedral_generators_S4()
        for g in gens:
            product = g.T @ g
            np.testing.assert_allclose(product, np.eye(3), atol=1e-10)

    def test_s4_generators_det_one(self):
        """Rotation matrices have determinant +1."""
        gens = octahedral_generators_S4()
        for g in gens:
            assert abs(np.linalg.det(g) - 1.0) < 1e-10

    def test_a5_generators_count(self):
        gens = icosahedral_generators_A5()
        assert len(gens) == 2

    def test_a5_generator_shapes(self):
        gens = icosahedral_generators_A5()
        for g in gens:
            assert g.shape == (3, 3)

    def test_a5_generators_orthogonal(self):
        gens = icosahedral_generators_A5()
        for g in gens:
            product = g.T @ g
            np.testing.assert_allclose(product, np.eye(3), atol=1e-10)

    def test_a5_generators_det_one(self):
        gens = icosahedral_generators_A5()
        for g in gens:
            assert abs(np.linalg.det(g) - 1.0) < 1e-10

    def test_a5_first_generator_order_5(self):
        """72-degree rotation should have order 5: R^5 = I."""
        r = icosahedral_generators_A5()[0]
        power = np.eye(3)
        for _ in range(5):
            power = power @ r
        np.testing.assert_allclose(power, np.eye(3), atol=1e-10)

    def test_symmetry_generators_registry(self):
        assert set(SYMMETRY_GENERATORS.keys()) == {"A4", "S4", "A5"}
        for _key, fn in SYMMETRY_GENERATORS.items():
            gens = fn()
            assert len(gens) >= 2


# ============================================================
# Friction Laplacian
# ============================================================


@pytest.mark.unit
class TestNaturalFrequency:
    def test_positive_for_all_polyhedra(self):
        for poly in _PHDM_POLYHEDRA:
            freq = _natural_frequency(poly)
            assert freq > 0, f"{poly['name']} has non-positive frequency"

    def test_zero_euler_handled(self):
        """Toroidal polyhedra have euler_chi=0; should not crash."""
        toroidal = {"faces": 14, "edges": 21, "vertices": 7, "euler_chi": 0, "depth": 0.8}
        freq = _natural_frequency(toroidal)
        assert freq > 0 and math.isfinite(freq)


@pytest.mark.unit
class TestFrictionLaplacianConstruction:
    def test_build_default(self):
        lap = build_default_friction_laplacian()
        assert isinstance(lap, FrictionLaplacian)

    def test_matrix_shape(self):
        lap = build_default_friction_laplacian()
        assert lap.matrix.shape == (16, 16)

    def test_matrix_symmetric(self):
        lap = build_default_friction_laplacian()
        np.testing.assert_allclose(lap.matrix, lap.matrix.T, atol=1e-10)

    def test_row_sums_near_zero(self):
        """Laplacian row sums should be zero (L = D - W)."""
        lap = build_default_friction_laplacian()
        row_sums = lap.matrix.sum(axis=1)
        np.testing.assert_allclose(row_sums, 0, atol=1e-10)

    def test_trace_positive(self):
        lap = build_default_friction_laplacian()
        assert lap.total_friction > 0

    def test_fiedler_value_positive(self):
        """Connected graph should have positive Fiedler value."""
        lap = build_default_friction_laplacian()
        assert lap.fiedler_value > 0

    def test_node_count(self):
        lap = build_default_friction_laplacian()
        assert lap.n_nodes == 16

    def test_edge_count_positive(self):
        lap = build_default_friction_laplacian()
        assert lap.n_edges > 0


# ============================================================
# TopologicalLossConfig
# ============================================================


@pytest.mark.unit
class TestTopologicalLossConfig:
    def test_defaults(self):
        cfg = TopologicalLossConfig()
        assert cfg.gamma == 1.0
        assert cfg.lambda_torsion == 0.1
        assert cfg.phi == PHI
        assert cfg.normalize_laplacian is True

    def test_custom_values(self):
        cfg = TopologicalLossConfig(gamma=2.0, lambda_torsion=0.5, normalize_laplacian=False)
        assert cfg.gamma == 2.0
        assert cfg.lambda_torsion == 0.5
        assert cfg.normalize_laplacian is False


# ============================================================
# TopologicalLoss (numpy)
# ============================================================


@pytest.mark.unit
class TestTopologicalLoss:
    def test_internalization_penalty_zero_when_equal(self):
        loss = TopologicalLoss()
        penalty = loss.internalization_penalty(0.95, 0.95)
        assert abs(penalty) < 1e-10

    def test_internalization_penalty_positive_when_different(self):
        loss = TopologicalLoss()
        penalty = loss.internalization_penalty(0.5, 0.95)
        assert penalty > 0

    def test_internalization_scales_with_gamma(self):
        loss1 = TopologicalLoss(config=TopologicalLossConfig(gamma=1.0))
        loss2 = TopologicalLoss(config=TopologicalLossConfig(gamma=2.0))
        p1 = loss1.internalization_penalty(0.5, 0.9)
        p2 = loss2.internalization_penalty(0.5, 0.9)
        assert abs(p2 - 2.0 * p1) < 1e-10

    def test_torsional_penalty_returns_float(self):
        loss = TopologicalLoss()
        W = np.random.randn(16, 4) * 0.01
        penalty = loss.torsional_penalty(W)
        assert isinstance(penalty, float)

    def test_torsional_penalty_scales_with_lambda(self):
        cfg1 = TopologicalLossConfig(lambda_torsion=0.1)
        cfg2 = TopologicalLossConfig(lambda_torsion=0.5)
        loss1 = TopologicalLoss(config=cfg1)
        loss2 = TopologicalLoss(config=cfg2)
        W = np.random.randn(16, 4) * 0.1
        p1 = loss1.torsional_penalty(W)
        p2 = loss2.torsional_penalty(W)
        assert abs(p2 / p1 - 5.0) < 0.01

    def test_torsional_handles_dimension_mismatch(self):
        """Weight matrix with different rows than Laplacian should still work."""
        loss = TopologicalLoss()
        W_small = np.random.randn(8, 4)
        penalty = loss.torsional_penalty(W_small)
        assert math.isfinite(penalty)

        W_large = np.random.randn(32, 4)
        penalty2 = loss.torsional_penalty(W_large)
        assert math.isfinite(penalty2)

    def test_torsional_handles_1d(self):
        loss = TopologicalLoss()
        W = np.random.randn(16)
        penalty = loss.torsional_penalty(W)
        assert math.isfinite(penalty)

    def test_compute_full_loss(self):
        loss = TopologicalLoss()
        W = np.random.randn(16, 4) * 0.01
        result = loss.compute(l_task=0.5, h_predicted=0.9, h_true=0.95, W=W)

        assert "l_total" in result
        assert "l_task" in result
        assert "l_internalization" in result
        assert "l_torsion" in result
        assert result["l_task"] == 0.5
        assert result["l_internalization"] > 0  # h_pred != h_true

    def test_compute_no_weights(self):
        loss = TopologicalLoss()
        result = loss.compute(l_task=0.3, h_predicted=0.9, h_true=0.9, W=None)
        assert result["l_torsion"] == 0.0
        assert result["l_total"] == result["l_task"]  # h_pred == h_true, no W

    def test_total_equals_sum(self):
        loss = TopologicalLoss()
        W = np.random.randn(16, 4) * 0.1
        result = loss.compute(l_task=0.5, h_predicted=0.8, h_true=0.95, W=W)
        expected = result["l_task"] + result["l_internalization"] + result["l_torsion"]
        assert abs(result["l_total"] - expected) < 1e-10

    def test_adversary_higher_loss_than_legitimate(self):
        loss = TopologicalLoss()
        W_legit = np.random.randn(16, 4) * 0.01
        W_adv = np.random.randn(16, 4) * 1.0

        legit = loss.compute(l_task=0.5, h_predicted=0.99, h_true=0.995, W=W_legit)
        adv = loss.compute(l_task=0.5, h_predicted=0.3, h_true=0.15, W=W_adv)
        assert adv["l_total"] > legit["l_total"]


# ============================================================
# Generator alignment loss
# ============================================================


@pytest.mark.unit
class TestGeneratorAlignmentLoss:
    def test_aligned_matrix_low_distance(self):
        loss = TopologicalLoss()
        gen = icosahedral_generators_A5()[0]
        dist = loss.generator_alignment_loss(gen, "A5")
        assert dist < 1e-10

    def test_random_matrix_higher_distance(self):
        loss = TopologicalLoss()
        rng = np.random.RandomState(42)
        W = rng.randn(3, 3)
        dist = loss.generator_alignment_loss(W, "A5")
        assert dist > 0.1

    def test_unknown_group_returns_zero(self):
        loss = TopologicalLoss()
        dist = loss.generator_alignment_loss(np.eye(3), "UNKNOWN")
        assert dist == 0.0

    def test_a4_alignment(self):
        loss = TopologicalLoss()
        gen = tetrahedral_generators_A4()[0]
        dist = loss.generator_alignment_loss(gen, "A4")
        assert dist < 1e-10


# ============================================================
# Topological training step
# ============================================================


@pytest.mark.integration
class TestTopologicalTrainingStep:
    def test_returns_full_breakdown(self):
        result = topological_training_step(
            task_loss=0.3,
            h_predicted=0.92,
            polyhedral_distances={"tetrahedron": 0.01, "cube": 0.02},
            phase_deviation=0.0,
        )
        assert "l_total" in result
        assert "tier" in result
        assert "h_true" in result

    def test_legitimate_gets_allow(self):
        result = topological_training_step(
            task_loss=0.3,
            h_predicted=0.99,
            polyhedral_distances={
                "tetrahedron": 0.01,
                "cube": 0.02,
                "octahedron": 0.01,
                "dodecahedron": 0.03,
                "icosahedron": 0.02,
            },
            phase_deviation=0.0,
        )
        assert result["tier"] == "ALLOW"

    def test_adversarial_gets_deny(self):
        result = topological_training_step(
            task_loss=0.3,
            h_predicted=0.1,
            polyhedral_distances={
                "tetrahedron": 5.0,
                "cube": 5.0,
                "octahedron": 5.0,
                "dodecahedron": 5.0,
                "icosahedron": 5.0,
            },
            phase_deviation=10.0,
        )
        assert result["tier"] == "DENY"

    def test_with_weight_matrix(self):
        result = topological_training_step(
            task_loss=0.3,
            h_predicted=0.92,
            polyhedral_distances={"tetrahedron": 0.01},
            phase_deviation=0.0,
            weight_matrix=np.random.randn(16, 4) * 0.01,
        )
        assert result["l_torsion"] != 0.0

    def test_custom_config(self):
        cfg = TopologicalLossConfig(gamma=5.0)
        result = topological_training_step(
            task_loss=0.3,
            h_predicted=0.5,
            polyhedral_distances={"tetrahedron": 0.5},
            phase_deviation=0.0,
            config=cfg,
        )
        assert result["gamma"] == 5.0
