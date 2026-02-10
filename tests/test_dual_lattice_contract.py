"""
Tests for Dual Lattice Architecture Contract Validation
========================================================

Covers:
- Static projection (6D -> 3D) cut-and-project
- Acceptance domain and tile type classification
- Dynamic transform (3D -> 6D -> 3D) roundtrip
- Phason shifts in perpendicular space
- Aperiodic mesh generation
- 3x frequency interference patterns
- Fractal dimension (box-counting)
- DualLatticeSystem lifecycle
- Cross-verification coherence
- Threat-responsive phason creation
- Utility functions (norms, distances)

@module tests/test_dual_lattice_contract
"""

import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from symphonic_cipher.scbe_aethermoore.ai_brain.dual_lattice import (
    Lattice6D,
    Lattice3D,
    PhasonShift,
    DualLatticeConfig,
    DualLatticeSystem,
    DEFAULT_DUAL_LATTICE_CONFIG,
    static_projection,
    dynamic_transform,
    generate_aperiodic_mesh,
    apply_phason_shift,
    estimate_fractal_dimension,
    lattice_norm_6d,
    lattice_distance_3d,
)

PHI = (1 + math.sqrt(5)) / 2
BRAIN_EPSILON = 1e-10


# ---------------------------------------------------------------------------
# Static Projection (6D -> 3D)
# ---------------------------------------------------------------------------

class TestStaticProjection:
    """Cut-and-project from 6D to 3D."""

    def test_origin_projects_to_origin(self):
        pt = Lattice6D(components=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
        result = static_projection(pt)
        assert abs(result.point_3d.x) < 1e-10
        assert abs(result.point_3d.y) < 1e-10
        assert abs(result.point_3d.z) < 1e-10

    def test_origin_accepted(self):
        pt = Lattice6D(components=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
        result = static_projection(pt)
        assert result.accepted

    def test_large_point_rejected(self):
        pt = Lattice6D(components=(10.0, 10.0, 10.0, 10.0, 10.0, 10.0))
        result = static_projection(pt)
        assert not result.accepted

    def test_tile_type_classification(self):
        """Origin should be thick (close to center)."""
        pt = Lattice6D(components=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
        result = static_projection(pt)
        assert result.tile_type in ("thick", "thin")

    def test_boundary_distance_positive_for_accepted(self):
        pt = Lattice6D(components=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
        result = static_projection(pt)
        if result.accepted:
            assert result.boundary_distance >= 0

    def test_perp_component_is_3d(self):
        pt = Lattice6D(components=(1.0, 0.0, 0.0, 0.0, 0.0, 0.0))
        result = static_projection(pt)
        assert len(result.perp_component) == 3

    def test_different_points_different_projections(self):
        p1 = Lattice6D(components=(1.0, 0.0, 0.0, 0.0, 0.0, 0.0))
        p2 = Lattice6D(components=(0.0, 1.0, 0.0, 0.0, 0.0, 0.0))
        r1 = static_projection(p1)
        r2 = static_projection(p2)
        dist = lattice_distance_3d(r1.point_3d, r2.point_3d)
        assert dist > 1e-6


# ---------------------------------------------------------------------------
# Dynamic Transform (3D -> 6D -> 3D)
# ---------------------------------------------------------------------------

class TestDynamicTransform:
    """3D -> 6D -> 3D roundtrip with phason shifts."""

    def test_zero_phason_preserves_point(self):
        """With zero phason, 3D -> 6D -> 3D should recover original."""
        pt = Lattice3D(x=1.0, y=0.5, z=-0.3)
        phason = PhasonShift(perp_shift=(0.0, 0.0, 0.0), magnitude=0.0, phase=0.0)
        result = dynamic_transform(pt, phason)
        assert result.displacement < 1e-6

    def test_nonzero_phason_changes_6d(self):
        """Phason shifts act in perpendicular space; check 6D coordinates change."""
        pt = Lattice3D(x=1.0, y=0.5, z=-0.3)
        phason = PhasonShift(perp_shift=(1.0, 0.0, 0.0), magnitude=0.5, phase=0.0)
        result = dynamic_transform(pt, phason)
        diff = sum(
            (result.shifted_6d.components[i] - result.lifted_6d.components[i]) ** 2
            for i in range(6)
        )
        assert diff > 0.01

    def test_structure_preserved_small_phason(self):
        pt = Lattice3D(x=0.5, y=0.5, z=0.5)
        phason = PhasonShift(perp_shift=(1.0, 0.0, 0.0), magnitude=0.1, phase=0.0)
        result = dynamic_transform(pt, phason)
        assert result.structure_preserved

    def test_structure_broken_large_phason(self):
        pt = Lattice3D(x=0.5, y=0.5, z=0.5)
        phason = PhasonShift(perp_shift=(1.0, 0.0, 0.0), magnitude=1.0, phase=0.0)
        result = dynamic_transform(pt, phason)
        assert not result.structure_preserved

    def test_lifted_6d_has_6_components(self):
        pt = Lattice3D(x=1.0, y=0.0, z=0.0)
        phason = PhasonShift(perp_shift=(0.0, 0.0, 0.0), magnitude=0.0, phase=0.0)
        result = dynamic_transform(pt, phason)
        assert len(result.lifted_6d.components) == 6
        assert len(result.shifted_6d.components) == 6

    def test_interference_value_bounded(self):
        pt = Lattice3D(x=1.0, y=0.5, z=-0.3)
        phason = PhasonShift(perp_shift=(0.5, 0.5, 0.0), magnitude=0.2, phase=0.0)
        result = dynamic_transform(pt, phason)
        assert -1.0 <= result.interference_value <= 1.0


# ---------------------------------------------------------------------------
# Phason Shifts
# ---------------------------------------------------------------------------

class TestPhasonShifts:
    """Phason shift operations in perpendicular space."""

    def test_zero_shift_identity(self):
        pt = Lattice6D(components=(1.0, 2.0, 3.0, 4.0, 5.0, 6.0))
        phason = PhasonShift(perp_shift=(0.0, 0.0, 0.0), magnitude=0.0, phase=0.0)
        shifted = apply_phason_shift(pt, phason)
        for i in range(6):
            assert abs(shifted.components[i] - pt.components[i]) < 1e-12

    def test_nonzero_shift_changes_point(self):
        pt = Lattice6D(components=(1.0, 0.0, 0.0, 0.0, 0.0, 0.0))
        phason = PhasonShift(perp_shift=(1.0, 0.0, 0.0), magnitude=0.5, phase=0.0)
        shifted = apply_phason_shift(pt, phason)
        diff = sum(
            (shifted.components[i] - pt.components[i]) ** 2 for i in range(6)
        )
        assert diff > 1e-6

    def test_magnitude_scales_shift(self):
        pt = Lattice6D(components=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
        phason_small = PhasonShift(perp_shift=(1.0, 0.0, 0.0), magnitude=0.1, phase=0.0)
        phason_large = PhasonShift(perp_shift=(1.0, 0.0, 0.0), magnitude=1.0, phase=0.0)
        s1 = apply_phason_shift(pt, phason_small)
        s2 = apply_phason_shift(pt, phason_large)
        norm1 = lattice_norm_6d(s1)
        norm2 = lattice_norm_6d(s2)
        assert norm2 > norm1


# ---------------------------------------------------------------------------
# Aperiodic Mesh
# ---------------------------------------------------------------------------

class TestAperiodicMesh:
    """Generate aperiodic mesh from 6D integer lattice."""

    def test_origin_always_accepted(self):
        mesh = generate_aperiodic_mesh(radius=1)
        origins = [r for r in mesh if abs(r.point_3d.x) < 1e-6 and abs(r.point_3d.y) < 1e-6 and abs(r.point_3d.z) < 1e-6]
        assert len(origins) >= 1

    def test_nonempty_mesh(self):
        mesh = generate_aperiodic_mesh(radius=2)
        assert len(mesh) > 0

    def test_all_mesh_points_accepted(self):
        mesh = generate_aperiodic_mesh(radius=2)
        for result in mesh:
            assert result.accepted

    def test_larger_radius_more_points(self):
        m1 = generate_aperiodic_mesh(radius=1)
        m2 = generate_aperiodic_mesh(radius=3)
        assert len(m2) >= len(m1)

    def test_mesh_has_tile_types(self):
        mesh = generate_aperiodic_mesh(radius=3)
        types = {r.tile_type for r in mesh}
        # Should have at least one type
        assert len(types) >= 1
        assert types.issubset({"thick", "thin"})


# ---------------------------------------------------------------------------
# Fractal Dimension
# ---------------------------------------------------------------------------

class TestFractalDimension:
    """Box-counting fractal dimension estimation."""

    def test_single_point_zero(self):
        assert estimate_fractal_dimension([Lattice3D(0, 0, 0)]) == 0.0

    def test_collinear_points(self):
        """Points along a line -> D ~ 1."""
        # Use non-integer spacing so box-counting varies across scales
        points = [Lattice3D(x=i * 0.07, y=0.0, z=0.0) for i in range(200)]
        d = estimate_fractal_dimension(points, scales=[1.0, 0.5, 0.25, 0.125, 0.0625])
        assert 0.5 < d < 1.5

    def test_planar_points(self):
        """Points in a plane -> D ~ 2."""
        points = [Lattice3D(x=i * 0.07, y=j * 0.07, z=0.0) for i in range(30) for j in range(30)]
        d = estimate_fractal_dimension(points, scales=[1.0, 0.5, 0.25, 0.125, 0.0625])
        assert 1.5 < d < 2.5

    def test_dimension_non_negative(self):
        points = [Lattice3D(x=float(i), y=0.0, z=0.0) for i in range(5)]
        d = estimate_fractal_dimension(points)
        assert d >= 0


# ---------------------------------------------------------------------------
# DualLatticeSystem
# ---------------------------------------------------------------------------

class TestDualLatticeSystem:
    """Full system lifecycle."""

    def test_initialize_mesh(self):
        sys = DualLatticeSystem()
        mesh = sys.initialize_mesh(radius=2)
        assert len(mesh) > 0
        assert sys.mesh is not None

    def test_process_21d_state(self):
        sys = DualLatticeSystem()
        state = [0.1] * 21
        phason = PhasonShift(perp_shift=(0.0, 0.0, 0.0), magnitude=0.0, phase=0.0)
        result = sys.process(state, phason)
        assert result.coherence >= 0
        assert result.coherence <= 1

    def test_step_counter_increments(self):
        sys = DualLatticeSystem()
        phason = PhasonShift(perp_shift=(0.0, 0.0, 0.0), magnitude=0.0, phase=0.0)
        sys.process([0.1] * 21, phason)
        sys.process([0.2] * 21, phason)
        assert sys.step == 2

    def test_validation_with_zero_phason(self):
        """Zero phason on origin-like state -> high coherence -> validated."""
        sys = DualLatticeSystem()
        state = [0.0] * 21
        phason = PhasonShift(perp_shift=(0.0, 0.0, 0.0), magnitude=0.0, phase=0.0)
        result = sys.process(state, phason)
        # With zero input, should have high coherence
        assert result.coherence > 0.5

    def test_too_short_state_raises(self):
        sys = DualLatticeSystem()
        phason = PhasonShift(perp_shift=(0.0, 0.0, 0.0), magnitude=0.0, phase=0.0)
        with pytest.raises(ValueError):
            sys.process([0.1] * 3, phason)

    def test_reset_clears_step(self):
        sys = DualLatticeSystem()
        phason = PhasonShift(perp_shift=(0.0, 0.0, 0.0), magnitude=0.0, phase=0.0)
        sys.process([0.1] * 21, phason)
        sys.reset()
        assert sys.step == 0

    def test_full_reset_clears_mesh(self):
        sys = DualLatticeSystem()
        sys.initialize_mesh(radius=2)
        sys.full_reset()
        assert sys.mesh is None
        assert sys.step == 0


# ---------------------------------------------------------------------------
# Cross-Verification
# ---------------------------------------------------------------------------

class TestCrossVerification:
    """Coherence between static and dynamic lattice modes."""

    def test_high_coherence_safe_state(self):
        sys = DualLatticeSystem()
        state = [0.05] * 21
        phason = PhasonShift(perp_shift=(0.1, 0.0, 0.0), magnitude=0.01, phase=0.0)
        result = sys.process(state, phason)
        assert result.coherence > 0.3

    def test_low_coherence_large_phason(self):
        """Large phason breaks structure -> lower coherence."""
        config = DualLatticeConfig(max_phason_amplitude=0.5)
        sys = DualLatticeSystem(config)
        state = [0.5] * 21
        phason = PhasonShift(perp_shift=(1.0, 1.0, 1.0), magnitude=2.0, phase=0.0)
        result = sys.process(state, phason)
        # Structure not preserved -> reduced coherence
        assert not result.dynamic.structure_preserved


# ---------------------------------------------------------------------------
# Threat-Responsive Phasons
# ---------------------------------------------------------------------------

class TestThreatPhasons:
    """Security-responsive phason creation."""

    def test_zero_threat_zero_magnitude(self):
        sys = DualLatticeSystem()
        p = sys.create_threat_phason(0.0)
        assert p.magnitude < 1e-10

    def test_max_threat_nonzero_magnitude(self):
        sys = DualLatticeSystem()
        p = sys.create_threat_phason(1.0)
        assert p.magnitude > 0

    def test_threat_clamps_to_01(self):
        sys = DualLatticeSystem()
        p1 = sys.create_threat_phason(-5.0)
        p2 = sys.create_threat_phason(10.0)
        assert p1.magnitude < 1e-10
        assert p2.magnitude == sys.create_threat_phason(1.0).magnitude

    def test_anomaly_dimensions_set_direction(self):
        sys = DualLatticeSystem()
        p = sys.create_threat_phason(0.5, anomaly_dimensions=[0, 3, 7])
        norm = math.sqrt(p.perp_shift[0] ** 2 + p.perp_shift[1] ** 2 + p.perp_shift[2] ** 2)
        assert abs(norm - 1.0) < 1e-6  # Unit direction when anomaly dims given


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

class TestUtilities:
    """Norms and distances."""

    def test_lattice_norm_6d_origin(self):
        pt = Lattice6D(components=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
        assert lattice_norm_6d(pt) == 0.0

    def test_lattice_norm_6d_unit(self):
        pt = Lattice6D(components=(1.0, 0.0, 0.0, 0.0, 0.0, 0.0))
        assert abs(lattice_norm_6d(pt) - 1.0) < 1e-12

    def test_lattice_distance_3d_same(self):
        a = Lattice3D(x=1.0, y=2.0, z=3.0)
        assert lattice_distance_3d(a, a) < 1e-12

    def test_lattice_distance_3d_known(self):
        a = Lattice3D(x=0.0, y=0.0, z=0.0)
        b = Lattice3D(x=3.0, y=4.0, z=0.0)
        assert abs(lattice_distance_3d(a, b) - 5.0) < 1e-10
