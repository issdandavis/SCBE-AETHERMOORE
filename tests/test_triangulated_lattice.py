"""Tests for Triangulated PHDM Lattice — governance-as-geometry vertices."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from lattice import (
    TriangulatedPHDMLattice,
    Triangle,
    TONGUE_DIMS,
)


class TestConstruction:
    def test_21_phdm_nodes(self):
        lattice = TriangulatedPHDMLattice()
        assert len(lattice.nodes) == 21

    def test_has_edges(self):
        lattice = TriangulatedPHDMLattice()
        assert len(lattice.edges) > 0

    def test_has_triangles(self):
        lattice = TriangulatedPHDMLattice()
        assert len(lattice.triangles) > 0

    def test_has_governance_vertices(self):
        lattice = TriangulatedPHDMLattice()
        assert len(lattice.governance_vertices) > 0

    def test_node_types(self):
        lattice = TriangulatedPHDMLattice()
        types = [n.dim_type for n in lattice.nodes]
        assert types.count("tongue") == 6
        assert types.count("phase") == 6
        assert types.count("telemetry") == 9

    def test_tongue_names(self):
        lattice = TriangulatedPHDMLattice()
        names = [n.name for n in lattice.nodes if n.dim_type == "tongue"]
        assert names == TONGUE_DIMS

    def test_governance_vertices_are_marked(self):
        lattice = TriangulatedPHDMLattice()
        for gov in lattice.governance_vertices:
            assert gov.is_governance is True
            assert gov.dim_type == "governance"


class TestGovernanceIndependence:
    """Core property: governance changes do NOT affect tokenizer values."""

    def test_changing_governance_preserves_node_values(self):
        lattice = TriangulatedPHDMLattice()
        state = np.random.randn(21)
        lattice.set_node_values(state)
        vals_before = [n.value for n in lattice.nodes]
        lattice.set_all_governance(0.01)
        vals_after = [n.value for n in lattice.nodes]
        assert vals_before == vals_after

    def test_governance_only_affects_blend(self):
        state = np.random.randn(21)
        l1 = TriangulatedPHDMLattice(governance_default=1.0)
        l2 = TriangulatedPHDMLattice(governance_default=0.5)
        r1 = l1.evaluate(state)
        r2 = l2.evaluate(state)
        # Blends differ
        assert r1["average_blend"] != r2["average_blend"]
        # But the triangle corner values come from the same state
        for t1, t2 in zip(r1["triangle_results"], r2["triangle_results"]):
            assert t1["val_a"] == t2["val_a"]
            assert t1["val_b"] == t2["val_b"]


class TestBarycentricInterpolation:
    def test_weights_sum_to_one(self):
        tri = Triangle(corner_a=0, corner_b=1, corner_c=100, governance_weight=1.0)
        # Should not raise
        tri.interpolate(0.33, 0.33, 0.34, 1.0, 2.0)

    def test_weights_not_summing_raises(self):
        tri = Triangle(corner_a=0, corner_b=1, corner_c=100, governance_weight=1.0)
        with pytest.raises(ValueError, match="must sum to 1"):
            tri.interpolate(0.5, 0.5, 0.5, 1.0, 2.0)

    def test_pure_corner_a(self):
        tri = Triangle(corner_a=0, corner_b=1, corner_c=100, governance_weight=1.0)
        result = tri.interpolate(1.0, 0.0, 0.0, 10.0, 20.0)
        assert abs(result - 10.0) < 1e-6

    def test_pure_corner_b(self):
        tri = Triangle(corner_a=0, corner_b=1, corner_c=100, governance_weight=1.0)
        result = tri.interpolate(0.0, 1.0, 0.0, 10.0, 20.0)
        assert abs(result - 20.0) < 1e-6

    def test_governance_compression(self):
        tri = Triangle(corner_a=0, corner_b=1, corner_c=100, governance_weight=0.0)
        result = tri.interpolate(0.4, 0.4, 0.2, 10.0, 20.0)
        # governance_weight=0 means governance_factor = 1 + 0.2*(0-1) = 0.8
        expected = (0.4 * 10.0 + 0.4 * 20.0) * 0.8
        assert abs(result - expected) < 1e-6

    def test_governance_expansion(self):
        tri = Triangle(corner_a=0, corner_b=1, corner_c=100, governance_weight=3.0)
        result = tri.interpolate(0.4, 0.4, 0.2, 10.0, 20.0)
        # governance_factor = 1 + 0.2*(3-1) = 1.4
        expected = (0.4 * 10.0 + 0.4 * 20.0) * 1.4
        assert abs(result - expected) < 1e-6


class TestEvaluation:
    def test_evaluate_returns_dict(self):
        lattice = TriangulatedPHDMLattice()
        result = lattice.evaluate(np.random.randn(21))
        assert "total_triangles" in result
        assert "average_blend" in result
        assert "governance_range" in result

    def test_different_states_different_results(self):
        lattice = TriangulatedPHDMLattice()
        r1 = lattice.evaluate(np.ones(21))
        r2 = lattice.evaluate(-np.ones(21))
        assert r1["average_blend"] != r2["average_blend"]

    def test_per_triangle_governance(self):
        lattice = TriangulatedPHDMLattice()
        lattice.set_governance(0, 10.0)
        lattice.set_governance(1, 0.01)
        result = lattice.evaluate(np.random.randn(21))
        gmin, gmax = result["governance_range"]
        assert gmax >= 10.0 or gmin <= 0.01

    def test_zero_state(self):
        lattice = TriangulatedPHDMLattice()
        result = lattice.evaluate(np.zeros(21))
        assert result["average_blend"] == 0.0


class TestThreeStringOverlay:
    """Test that the lattice supports the 3-string architecture:
    String 1: Tokenizer edges (semantic)
    String 2: Governance vertices (authority)
    String 3: Temporal (via triadic weights — simulated here)
    """

    def test_semantic_string_independent(self):
        """Changing tokenizer input changes blend but not governance."""
        lattice = TriangulatedPHDMLattice(governance_default=1.5)
        r1 = lattice.evaluate(np.ones(21))
        r2 = lattice.evaluate(np.ones(21) * 2)
        assert r1["average_blend"] != r2["average_blend"]
        assert r1["governance_range"] == r2["governance_range"]

    def test_governance_string_independent(self):
        """Changing governance changes blend but not tokenizer values."""
        state = np.random.randn(21)
        lattice = TriangulatedPHDMLattice()
        lattice.set_node_values(state)
        vals1 = [n.value for n in lattice.nodes[:6]]  # Tongue values
        lattice.set_all_governance(0.1)
        vals2 = [n.value for n in lattice.nodes[:6]]
        assert vals1 == vals2

    def test_temporal_can_modulate(self):
        """Simulated temporal modulation via governance weight cycling."""
        lattice = TriangulatedPHDMLattice()
        state = np.random.randn(21)
        results = []
        for t in range(10):
            # Simulate temporal breathing: governance oscillates
            gov = 1.0 + 0.5 * np.sin(t * 0.5)
            lattice.set_all_governance(gov)
            r = lattice.evaluate(state)
            results.append(r["average_blend"])
        # Results should vary over time
        assert len(set(f"{r:.6f}" for r in results)) > 1
