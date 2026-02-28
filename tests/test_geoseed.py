"""
GeoSeed Network — First-Principles Validation Tests
=====================================================

Tests organized by mathematical invariant:
1. Cl(6,0) algebraic properties (anticommutation, bivector count)
2. Icosahedral grid geometry (vertex count, edge connectivity, sphere coverage)
3. Poincaré ball operations (Möbius addition closure, distance positivity)
4. Geometric bit dressing (14-layer traversal, governance gating)
5. Geometric composition (bivector interactions, convergence)
6. M6 layer (simplified dressing + composition)
7. M6 SphereMesh runtime
8. End-to-end numpy model

@tier L2-unit, L4-property
@component GeoSeed
"""

import sys
import os
import math

import numpy as np
import pytest

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.geoseed.sphere_grid import (
    CliffordAlgebra,
    CL6,
    SphereGrid,
    SphereGridNetwork,
    TONGUE_NAMES,
    TONGUE_PHASES,
    PHI_WEIGHTS,
    LWS_WEIGHTS,
    TONGUE_BASIS,
    icosahedral_subdivide,
    poincare_project,
    mobius_add,
    hyperbolic_distance,
    cross_tongue_convolve,
)
from src.geoseed.dressing_geometric import (
    GeometricBitDresser,
    GeometricDressedBit,
    DressingTier,
    GovernanceDecision,
)
from src.geoseed.composition_geometric import (
    GeometricComposer,
    GeometricSemanticUnit,
    CrossTerm,
)
from src.geoseed.dressing import BitDresser, DressedBit
from src.geoseed.composition import DressedBitComposer, SemanticUnit
from src.geoseed.m6_spheremesh import M6Event, M6SphereMesh, SacredEgg
from src.geoseed.model import GeoSeedConfig, GeoSeedModelNumpy


# ============================================================
# 1. Cl(6,0) Algebraic Properties
# ============================================================


class TestCliffordAlgebra:
    """Verify Cl(6,0) satisfies the Clifford algebra axioms."""

    def test_algebra_dimension(self):
        """Cl(6,0) should have 2^6 = 64 components."""
        assert CL6.total_components == 64

    def test_grade_dimensions(self):
        """Grade dimensions should be C(6,k) for k=0..6."""
        expected = [1, 6, 15, 20, 15, 6, 1]
        assert CL6.grade_dims == expected
        assert sum(expected) == 64

    def test_basis_vector_count(self):
        """Should have exactly 6 basis vectors (one per tongue)."""
        assert len(TONGUE_BASIS) == 6

    def test_basis_vectors_orthonormal(self):
        """e_i and e_j should be orthogonal for i != j."""
        for i in range(6):
            for j in range(6):
                ei = CL6.basis_vector(i)
                ej = CL6.basis_vector(j)
                vi = ei[1:7]
                vj = ej[1:7]
                dot = np.dot(vi, vj)
                if i == j:
                    assert abs(dot - 1.0) < 1e-10
                else:
                    assert abs(dot) < 1e-10

    def test_bivector_count(self):
        """C(6,2) = 15 bivectors."""
        assert len(CL6._bivector_map) == 15

    def test_geometric_product_anticommutation(self):
        """For distinct basis vectors: e_i * e_j = -e_j * e_i."""
        for i in range(6):
            for j in range(i + 1, 6):
                ei = CL6.basis_vector(i)
                ej = CL6.basis_vector(j)
                prod_ij = CL6.geometric_product(ei, ej)
                prod_ji = CL6.geometric_product(ej, ei)
                assert abs(prod_ij[0]) < 1e-10
                assert abs(prod_ji[0]) < 1e-10
                bv_ij = prod_ij[7:22]
                bv_ji = prod_ji[7:22]
                np.testing.assert_allclose(bv_ij, -bv_ji, atol=1e-10)

    def test_geometric_product_self(self):
        """e_i * e_i should give scalar = 1 (positive-definite signature)."""
        for i in range(6):
            ei = CL6.basis_vector(i)
            prod = CL6.geometric_product(ei, ei)
            assert abs(prod[0] - 1.0) < 1e-10
            assert np.max(np.abs(prod[7:22])) < 1e-10

    def test_bivector_strength_symmetry(self):
        """Bivector strength should be symmetric."""
        for t1 in TONGUE_NAMES:
            for t2 in TONGUE_NAMES:
                if t1 != t2:
                    s1 = CL6.bivector_strength(t1, t2)
                    s2 = CL6.bivector_strength(t2, t1)
                    assert abs(s1 - s2) < 1e-10


# ============================================================
# 2. Icosahedral Grid Geometry
# ============================================================


class TestIcosahedralGrid:

    def test_resolution_0_counts(self):
        verts, edges = icosahedral_subdivide(0)
        assert len(verts) == 12
        assert len(edges) == 30

    def test_resolution_1_counts(self):
        verts, edges = icosahedral_subdivide(1)
        assert len(verts) == 42

    def test_resolution_3_counts(self):
        verts, edges = icosahedral_subdivide(3)
        assert len(verts) == 642

    def test_vertices_on_unit_sphere(self):
        verts, _ = icosahedral_subdivide(2)
        norms = np.linalg.norm(verts, axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-10)

    def test_edges_connect_valid_vertices(self):
        verts, edges = icosahedral_subdivide(2)
        n = len(verts)
        for u, v in edges:
            assert 0 <= u < n
            assert 0 <= v < n
            assert u != v

    def test_sphere_grid_creation(self):
        grid = SphereGrid(tongue="KO", resolution=2)
        assert grid.tongue == "KO"
        assert grid.n_vertices == 162
        assert grid.basis_index == 0
        assert grid.signals.shape == (162, 64)

    def test_sphere_grid_adjacency_symmetric(self):
        grid = SphereGrid(tongue="AV", resolution=1)
        adj = grid.adjacency
        for v, neighbors in adj.items():
            for u in neighbors:
                assert v in adj[u]

    def test_geodesic_weight_range(self):
        grid = SphereGrid(tongue="RU", resolution=1)
        for u, v in grid.edges[:20]:
            w = grid.geodesic_weight(u, v)
            assert 0 < w <= 1.0

    def test_deposit_and_read(self):
        grid = SphereGrid(tongue="CA", resolution=1, signal_dim=8)
        pos = np.array([0.0, 0.0, 1.0])
        sig = np.ones(8) * 5.0
        grid.deposit_signal(pos, sig)
        readback = grid.read_signal(pos)
        assert np.any(readback > 0)


# ============================================================
# 3. Poincaré Ball Operations
# ============================================================


class TestPoincareBall:

    def test_poincare_project_stays_in_ball(self):
        for _ in range(100):
            v = np.random.randn(6) * 10
            p = poincare_project(v)
            assert np.linalg.norm(p) < 1.0

    def test_poincare_project_origin(self):
        p = poincare_project(np.zeros(6))
        np.testing.assert_allclose(p, 0, atol=1e-12)

    def test_mobius_add_closure(self):
        for _ in range(100):
            x = poincare_project(np.random.randn(6) * 0.3)
            y = poincare_project(np.random.randn(6) * 0.3)
            result = mobius_add(x, y)
            assert np.linalg.norm(result) < 1.0

    def test_mobius_add_identity(self):
        x = poincare_project(np.array([0.3, 0.1, 0.0, 0.2, -0.1, 0.0]))
        result = mobius_add(x, np.zeros(6))
        np.testing.assert_allclose(result, x, atol=1e-8)

    def test_hyperbolic_distance_positive(self):
        for _ in range(50):
            u = poincare_project(np.random.randn(6) * 0.5)
            v = poincare_project(np.random.randn(6) * 0.5)
            d = hyperbolic_distance(u, v)
            assert d >= 0

    def test_hyperbolic_distance_zero_self(self):
        x = poincare_project(np.array([0.2, 0.1, 0.0, 0.1, 0.0, 0.0]))
        d = hyperbolic_distance(x, x)
        assert d < 1e-6

    def test_hyperbolic_distance_triangle_inequality(self):
        for _ in range(50):
            x = poincare_project(np.random.randn(6) * 0.3)
            y = poincare_project(np.random.randn(6) * 0.3)
            z = poincare_project(np.random.randn(6) * 0.3)
            dxz = hyperbolic_distance(x, z)
            dxy = hyperbolic_distance(x, y)
            dyz = hyperbolic_distance(y, z)
            assert dxz <= dxy + dyz + 1e-6


# ============================================================
# 4. Geometric Bit Dressing (F1 pipeline)
# ============================================================


class TestGeometricDressing:

    def test_dress_single_bit(self):
        dresser = GeometricBitDresser(tier=DressingTier.F1)
        bit = dresser.dress(0x42, 0)
        assert bit.raw_value == 0x42
        assert bit.position == 0
        assert bit.tongue == "KO"
        assert bit.complex_state is not None
        assert bit.poincare_pos is not None
        assert bit.multivector is not None
        assert len(bit.multivector) == 64

    def test_tongue_assignment_round_robin(self):
        dresser = GeometricBitDresser()
        for i in range(12):
            bit = dresser.dress(0, i)
            assert bit.tongue == TONGUE_NAMES[i % 6]

    def test_different_values_different_fingerprints(self):
        dresser = GeometricBitDresser()
        bit0 = dresser.dress(0, 0)
        bit255 = dresser.dress(255, 0)
        dist = np.linalg.norm(bit0.poincare_pos - bit255.poincare_pos)
        assert dist > 1e-6

    def test_poincare_pos_in_ball(self):
        dresser = GeometricBitDresser()
        for val in [0, 1, 127, 128, 255]:
            for pos in range(6):
                bit = dresser.dress(val, pos)
                norm = np.linalg.norm(bit.poincare_pos)
                assert norm < 1.0

    def test_governance_scoring_ranges(self):
        dresser = GeometricBitDresser()
        bit = dresser.dress(100, 3)
        assert 0 <= bit.spectral_score <= 1
        assert 0 <= bit.spin_score <= 1
        assert 0 <= bit.temporal_score <= 1
        assert 0 < bit.harmonic_score <= 1
        assert bit.decision in GovernanceDecision

    def test_multivector_signal_structure(self):
        dresser = GeometricBitDresser()
        bit = dresser.dress(50, 0)
        sig = bit.multivector
        if bit.is_allowed:
            assert sig[0] > 0
        grade1 = sig[1:7]
        assert np.any(grade1 != 0)

    def test_f2_lightweight(self):
        dresser = GeometricBitDresser(tier=DressingTier.F2)
        bit = dresser.dress(100, 0)
        assert bit.harmonic_score == 1.0
        assert bit.decision == GovernanceDecision.ALLOW
        assert bit.poincare_pos is not None

    def test_dress_bytes(self):
        dresser = GeometricBitDresser()
        dressed = dresser.dress_bytes(b"Hello!")
        assert len(dressed) == 6
        assert dressed[0].raw_value == ord("H")

    def test_dress_string(self):
        dresser = GeometricBitDresser()
        dressed = dresser.dress_string("OK")
        assert len(dressed) == 2


# ============================================================
# 5. Geometric Composition
# ============================================================


class TestGeometricComposition:

    def test_compose_basic(self):
        dresser = GeometricBitDresser()
        bits = dresser.dress_bytes(b"ABCDEF")
        composer = GeometricComposer(resolution=1, n_propagation_steps=1)
        unit = composer.compose(bits)
        assert isinstance(unit, GeometricSemanticUnit)
        assert unit.n_bits > 0
        assert len(unit.tongue_signals) == 6
        assert len(unit.cross_terms) == 15
        assert unit.convergence_point is not None

    def test_cross_terms_count(self):
        dresser = GeometricBitDresser()
        bits = dresser.dress_bytes(b"ABCDEF")
        composer = GeometricComposer(resolution=1, n_propagation_steps=1)
        unit = composer.compose(bits)
        assert len(unit.cross_terms) == 15

    def test_cross_term_pairs(self):
        dresser = GeometricBitDresser()
        bits = dresser.dress_bytes(b"ABCDEF")
        composer = GeometricComposer(resolution=1, n_propagation_steps=1)
        unit = composer.compose(bits)
        pairs = {(ct.tongue_a, ct.tongue_b) for ct in unit.cross_terms}
        expected = set()
        for i, t1 in enumerate(TONGUE_NAMES):
            for t2 in TONGUE_NAMES[i + 1:]:
                expected.add((t1, t2))
        assert pairs == expected

    def test_governance_ratio(self):
        dresser = GeometricBitDresser()
        bits = dresser.dress_bytes(b"test")
        composer = GeometricComposer(resolution=1, n_propagation_steps=1)
        unit = composer.compose(bits)
        assert 0 <= unit.governance_ratio <= 1

    def test_to_embedding_dimension(self):
        dresser = GeometricBitDresser()
        bits = dresser.dress_bytes(b"ABCDEF")
        composer = GeometricComposer(resolution=1, n_propagation_steps=1)
        unit = composer.compose(bits)
        for dim in [128, 256, 384, 512]:
            emb = unit.to_embedding(dim=dim)
            assert len(emb) == dim

    def test_convergence_in_ball(self):
        dresser = GeometricBitDresser()
        bits = dresser.dress_bytes(b"test data")
        composer = GeometricComposer(resolution=1, n_propagation_steps=1)
        unit = composer.compose(bits)
        norm = np.linalg.norm(unit.convergence_point)
        assert norm < 1.0


# ============================================================
# 6. M6 Layer (simplified dressing + composition)
# ============================================================


class TestM6Layer:
    """Test the M6-compatible simplified dressing/composition."""

    def test_m6_dresser_tokens(self):
        dresser = BitDresser(layer_count=14)
        bits = dresser.dress_tokens({"KO": ["hello", "world"], "AV": ["test"]})
        assert len(bits) == 3
        assert all(isinstance(b, DressedBit) for b in bits)
        assert bits[0].tongue == "KO"
        assert bits[2].tongue == "AV"

    def test_m6_dresser_text(self):
        dresser = BitDresser()
        bits = dresser.dress_text("hello world", tongue="RU")
        assert len(bits) == 2
        assert all(b.tongue == "RU" for b in bits)

    def test_m6_dressed_bit_deterministic(self):
        dresser = BitDresser()
        bits1 = dresser.dress_text("hello", run_id="run1")
        bits2 = dresser.dress_text("hello", run_id="run1")
        assert bits1[0].state21d == bits2[0].state21d

    def test_m6_state21d_dimensions(self):
        dresser = BitDresser()
        bits = dresser.dress_text("test")
        assert len(bits[0].state21d) == 21

    def test_m6_state21d_bounded(self):
        dresser = BitDresser()
        bits = dresser.dress_text("many words in a sentence here")
        for bit in bits:
            for val in bit.state21d:
                assert -1.0 <= val <= 1.0

    def test_m6_composer(self):
        dresser = BitDresser()
        bits = dresser.dress_tokens({"KO": ["a", "b"], "DR": ["c"]})
        composer = DressedBitComposer()
        unit = composer.compose(bits)
        assert isinstance(unit, SemanticUnit)
        assert len(unit.tongues) == 2  # KO and DR
        assert len(unit.state21d) == 21
        assert 0 < unit.confidence <= 1.0

    def test_m6_composer_empty(self):
        composer = DressedBitComposer()
        unit = composer.compose([])
        assert unit.confidence == 0.0
        assert unit.state21d == [0.0] * 21


# ============================================================
# 7. M6 SphereMesh Runtime
# ============================================================


class TestM6SphereMesh:

    def test_creation(self):
        mesh = M6SphereMesh(resolution=1, signal_dim=8)
        assert len(mesh.network.grids) == 6
        assert len(mesh.history) == 0

    def test_ingest_event(self):
        mesh = M6SphereMesh(resolution=1, signal_dim=8)
        event = M6Event(
            record_id="evt-1",
            summary="Test event for KO tongue",
            tongue_vector={"KO": 0.8, "AV": 0.2},
            metadata={"source": "test"},
        )
        record = mesh.ingest_event(event)
        assert record["record_id"] == "evt-1"
        assert "state21d" in record
        assert len(record["state21d"]) == 21
        assert len(mesh.history) == 1

    def test_score_transition(self):
        mesh = M6SphereMesh(resolution=1)
        scores = mesh.score_transition("KO", "AV")
        assert "compatibility" in scores
        assert "harmonic_cost" in scores
        assert 0 <= scores["compatibility"] <= 1

    def test_sacred_egg_lifecycle(self):
        mesh = M6SphereMesh(resolution=1)
        egg = mesh.register_egg(
            egg_id="egg-1",
            required_tongues=["KO", "AV"],
            min_phi_weight=2.0,
            ttl_seconds=3600,
        )
        assert not egg.hatched

        # Should fail — missing DR
        ok, reason = mesh.hatch_egg("egg-1", ["KO", "AV"])
        assert ok  # KO(1.0) + AV(1.618) = 2.618 >= 2.0, and both required tongues present
        assert reason == "hatched"

    def test_sacred_egg_insufficient_weight(self):
        mesh = M6SphereMesh(resolution=1)
        mesh.register_egg(
            egg_id="egg-2",
            required_tongues=["KO"],
            min_phi_weight=999.0,
        )
        ok, reason = mesh.hatch_egg("egg-2", ["KO"])
        assert not ok
        assert "insufficient_phi_weight" in reason

    def test_snapshot(self):
        mesh = M6SphereMesh(resolution=1)
        snap = mesh.snapshot()
        assert snap["history_count"] == 0
        assert snap["last_record"] is None


# ============================================================
# 8. Sphere Grid Network
# ============================================================


class TestSphereGridNetwork:

    def test_network_creation(self):
        net = SphereGridNetwork(resolution=1, signal_dim=8)
        assert len(net.grids) == 6
        assert len(net.tongue_pairs) == 15

    def test_network_total_nodes(self):
        net = SphereGridNetwork(resolution=1)
        assert net.total_nodes == 6 * 42

    def test_network_forward(self):
        net = SphereGridNetwork(resolution=1, signal_dim=8)
        net.deposit("KO", np.array([0, 0, 1.0]), np.ones(8))
        net.deposit("DR", np.array([1, 0, 0.0]), np.ones(8) * 0.5)
        signals = net.forward(n_steps=1)
        assert len(signals) == 6
        for tongue, sig in signals.items():
            assert sig.shape[1] == 8

    def test_cross_tongue_convolve(self):
        g1 = SphereGrid(tongue="KO", resolution=1, signal_dim=8)
        g2 = SphereGrid(tongue="AV", resolution=1, signal_dim=8)
        g1.signals[0] = np.ones(8) * 3.0
        g2.signals[0] = np.ones(8) * 7.0
        before_g1 = g1.signals.copy()
        before_g2 = g2.signals.copy()
        cross_tongue_convolve(g1, g2)
        assert not np.allclose(g1.signals, before_g1)
        assert not np.allclose(g2.signals, before_g2)

    def test_global_state_dimension(self):
        net = SphereGridNetwork(resolution=1, signal_dim=16)
        state = net.read_global_state()
        assert len(state) == 6 * 16


# ============================================================
# 9. End-to-End Numpy Model
# ============================================================


class TestGeoSeedModelNumpy:

    def test_config_creation(self):
        config = GeoSeedConfig()
        assert config.resolution == 3
        assert config.signal_dim == 64
        assert config.n_tongues == 6
        assert config.output_dim == 384

    def test_numpy_model_forward(self):
        config = GeoSeedConfig(resolution=1, n_propagation_steps=1)
        model = GeoSeedModelNumpy(config)
        result = model.forward(b"Hello")
        assert "embedding" in result
        assert "tongue_signals" in result
        assert "convergence" in result
        assert "governance_ratio" in result
        assert len(result["embedding"]) == config.output_dim

    def test_numpy_model_text(self):
        config = GeoSeedConfig(resolution=1, n_propagation_steps=1)
        model = GeoSeedModelNumpy(config)
        result = model.forward_text("SCBE")
        assert result["n_bits"] > 0
        assert result["governance_ratio"] > 0

    def test_different_inputs_different_embeddings(self):
        config = GeoSeedConfig(resolution=1, n_propagation_steps=1)
        model = GeoSeedModelNumpy(config)
        r1 = model.forward_text("alpha")
        r2 = model.forward_text("omega")
        dist = np.linalg.norm(r1["embedding"] - r2["embedding"])
        assert dist > 1e-6

    def test_config_save_load(self, tmp_path):
        config = GeoSeedConfig(resolution=2, hidden_dim=128)
        save_dir = str(tmp_path / "test_config")
        config.save_pretrained(save_dir)
        loaded = GeoSeedConfig.from_pretrained(save_dir)
        assert loaded.resolution == 2
        assert loaded.hidden_dim == 128


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
