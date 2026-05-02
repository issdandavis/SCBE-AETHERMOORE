from __future__ import annotations

from src.storage.spin_voxel import (
    SpinVoxelConfig,
    apply_phason,
    build_ring_edges,
    harmonic_scaling_spin_voxel,
    normalize_spin,
    spin_coherence,
    spin_disorder,
)


def test_spin_coherence_alignment_vs_disorder() -> None:
    aligned = [normalize_spin((1.0, 0.0, 0.0)) for _ in range(24)]
    disordered = [normalize_spin((1.0, 0.0, 0.0)), normalize_spin((-1.0, 0.0, 0.0))] * 12
    assert spin_coherence(aligned) > spin_coherence(disordered)


def test_phason_rotation_preserves_norm() -> None:
    spins = [normalize_spin((0.1, 0.4, 0.7)), normalize_spin((-0.3, 0.5, 0.2))]
    rotated = apply_phason(spins, n=2)
    for before, after in zip(spins, rotated):
        b = (before[0] ** 2 + before[1] ** 2 + before[2] ** 2) ** 0.5
        a = (after[0] ** 2 + after[1] ** 2 + after[2] ** 2) ** 0.5
        assert abs(a - b) < 1e-9


def test_harmonic_cost_increases_with_disorder() -> None:
    edges = build_ring_edges(32)
    cfg = SpinVoxelConfig(alpha=0.5, spin_reference=2.0, external_field=(0.0, 0.0, 0.0))
    aligned = [normalize_spin((1.0, 0.0, 0.0)) for _ in range(32)]
    disordered = [normalize_spin((1.0, 0.0, 0.0)), normalize_spin((-1.0, 0.0, 0.0))] * 16

    assert spin_disorder(disordered, edges=edges) >= spin_disorder(aligned, edges=edges)

    cost_aligned = harmonic_scaling_spin_voxel(
        d=6.0,
        r=1.35,
        intent_norm=1.0,
        spins=aligned,
        phase="fast",
        edges=edges,
        config=cfg,
    )
    cost_disordered = harmonic_scaling_spin_voxel(
        d=6.0,
        r=1.35,
        intent_norm=1.0,
        spins=disordered,
        phase="fast",
        edges=edges,
        config=cfg,
    )
    assert cost_disordered >= cost_aligned
