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


def test_harmonic_cost_is_scale_free() -> None:
    # Regression for the extensivity bug: the spin penalty is now the intensive
    # per-edge disorder density, so a configuration with the same per-edge disorder
    # yields the same cost regardless of how many voxels it spans. The earlier
    # extensive Hamiltonian term made cost grow with size (and go negative at 16^3).
    cfg = SpinVoxelConfig(alpha=0.5, spin_reference=2.0)
    kwargs = {"d": 6.0, "r": 1.35, "intent_norm": 1.0, "phase": "fast", "config": cfg}

    def alternating(n: int) -> list[tuple[float, float, float]]:
        return [normalize_spin((1.0, 0.0, 0.0)), normalize_spin((-1.0, 0.0, 0.0))] * (n // 2)

    cost_small = harmonic_scaling_spin_voxel(spins=alternating(16), edges=build_ring_edges(16), **kwargs)
    cost_large = harmonic_scaling_spin_voxel(spins=alternating(256), edges=build_ring_edges(256), **kwargs)
    # Intensive => costs match to ~11 sig-figs (residual is the epsilon guard in the
    # disorder denominator, not size growth). The old extensive term differed by ~16x.
    assert abs(cost_large - cost_small) / cost_small < 1e-6
