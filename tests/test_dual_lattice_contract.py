"""
Dual lattice contract validation tests.
"""

from __future__ import annotations

import math

import pytest

from src.symphonic_cipher.scbe_aethermoore.ai_brain.dual_lattice import (
    DualLatticeConfig,
    DualLatticeSystem,
    Lattice3D,
    Lattice6D,
    PhasonShift,
    apply_phason_shift,
    dynamic_transform,
    estimate_fractal_dimension,
    generate_aperiodic_mesh,
    lattice_distance_3d,
    lattice_norm_6d,
    static_projection,
)


class TestStaticProjection:
    def test_origin_projects_to_origin(self):
        p6 = Lattice6D(components=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
        out = static_projection(p6)
        assert abs(out.point_3d.x) < 1e-10
        assert abs(out.point_3d.y) < 1e-10
        assert abs(out.point_3d.z) < 1e-10
        assert out.accepted
        assert out.tile_type in {"thick", "thin"}

    def test_far_point_rejected(self):
        p6 = Lattice6D(components=(10.0, 10.0, 10.0, 10.0, 10.0, 10.0))
        out = static_projection(p6)
        assert not out.accepted

    def test_projection_distance_changes_for_distinct_points(self):
        p1 = Lattice6D(components=(1.0, 0.0, 0.0, 0.0, 0.0, 0.0))
        p2 = Lattice6D(components=(0.0, 1.0, 0.0, 0.0, 0.0, 0.0))
        a = static_projection(p1).point_3d
        b = static_projection(p2).point_3d
        assert lattice_distance_3d(a, b) > 1e-6


class TestDynamicTransform:
    def test_zero_phason_nearly_preserves_point(self):
        p3 = Lattice3D(x=1.0, y=0.5, z=-0.3)
        ph = PhasonShift(perp_shift=(0.0, 0.0, 0.0), magnitude=0.0, phase=0.0)
        out = dynamic_transform(p3, ph)
        assert out.displacement < 1e-6

    def test_nonzero_phason_changes_state(self):
        p3 = Lattice3D(x=1.0, y=0.5, z=-0.3)
        ph = PhasonShift(perp_shift=(1.0, 0.0, 0.0), magnitude=0.5, phase=0.0)
        out = dynamic_transform(p3, ph)
        diff = sum(
            (out.shifted_6d.components[i] - out.lifted_6d.components[i]) ** 2
            for i in range(6)
        )
        assert diff > 0.01
        assert -1.0 <= out.interference_value <= 1.0

    def test_structure_preservation_threshold(self):
        p3 = Lattice3D(x=0.5, y=0.5, z=0.5)
        small = PhasonShift(perp_shift=(1.0, 0.0, 0.0), magnitude=0.1, phase=0.0)
        large = PhasonShift(perp_shift=(1.0, 0.0, 0.0), magnitude=1.0, phase=0.0)
        assert dynamic_transform(p3, small).structure_preserved
        assert not dynamic_transform(p3, large).structure_preserved


class TestPhasonShift:
    def test_identity_shift(self):
        p6 = Lattice6D(components=(1.0, 2.0, 3.0, 4.0, 5.0, 6.0))
        ph = PhasonShift(perp_shift=(0.0, 0.0, 0.0), magnitude=0.0, phase=0.0)
        shifted = apply_phason_shift(p6, ph)
        for i in range(6):
            assert abs(shifted.components[i] - p6.components[i]) < 1e-12

    def test_shift_magnitude_scaling(self):
        p6 = Lattice6D(components=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
        a = PhasonShift(perp_shift=(1.0, 0.0, 0.0), magnitude=0.1, phase=0.0)
        b = PhasonShift(perp_shift=(1.0, 0.0, 0.0), magnitude=1.0, phase=0.0)
        n1 = lattice_norm_6d(apply_phason_shift(p6, a))
        n2 = lattice_norm_6d(apply_phason_shift(p6, b))
        assert n2 > n1


class TestAperiodicMesh:
    def test_mesh_nonempty_and_accepted(self):
        mesh = generate_aperiodic_mesh(radius=2)
        assert len(mesh) > 0
        assert all(x.accepted for x in mesh)

    def test_larger_radius_yields_no_fewer_points(self):
        a = generate_aperiodic_mesh(radius=1)
        b = generate_aperiodic_mesh(radius=3)
        assert len(b) >= len(a)


class TestFractalDimension:
    def test_line_like_dimension(self):
        points = [Lattice3D(x=i * 0.07, y=0.0, z=0.0) for i in range(200)]
        d = estimate_fractal_dimension(points, scales=[1.0, 0.5, 0.25, 0.125, 0.0625])
        assert 0.5 < d < 1.5

    def test_plane_like_dimension(self):
        points = [Lattice3D(x=i * 0.07, y=j * 0.07, z=0.0) for i in range(30) for j in range(30)]
        d = estimate_fractal_dimension(points, scales=[1.0, 0.5, 0.25, 0.125, 0.0625])
        assert 1.5 < d < 2.5


class TestDualLatticeSystem:
    def test_process_and_step_counter(self):
        sys = DualLatticeSystem()
        ph = PhasonShift(perp_shift=(0.0, 0.0, 0.0), magnitude=0.0, phase=0.0)
        r1 = sys.process([0.1] * 21, ph)
        r2 = sys.process([0.2] * 21, ph)
        assert 0.0 <= r1.coherence <= 1.0
        assert 0.0 <= r2.coherence <= 1.0
        assert sys.step == 2

    def test_short_state_rejected(self):
        sys = DualLatticeSystem()
        ph = PhasonShift(perp_shift=(0.0, 0.0, 0.0), magnitude=0.0, phase=0.0)
        with pytest.raises(ValueError):
            sys.process([0.1] * 3, ph)

    def test_create_threat_phason_clamps_and_normalizes(self):
        sys = DualLatticeSystem(DualLatticeConfig(max_phason_amplitude=0.5))
        p0 = sys.create_threat_phason(-5.0)
        p1 = sys.create_threat_phason(10.0)
        assert p0.magnitude < 1e-10
        assert p1.magnitude == sys.create_threat_phason(1.0).magnitude
        pn = sys.create_threat_phason(0.5, anomaly_dimensions=[0, 3, 7])
        norm = math.sqrt(sum(c * c for c in pn.perp_shift))
        assert abs(norm - 1.0) < 1e-6
