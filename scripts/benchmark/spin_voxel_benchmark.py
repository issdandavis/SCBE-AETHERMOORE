#!/usr/bin/env python3
"""Benchmark spin-voxel coherence and harmonic amplification signals."""

from __future__ import annotations

import json
from pathlib import Path
import random
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.storage.spin_voxel import (
    SpinVoxelConfig,
    SpinVector,
    apply_phason,
    build_ring_edges,
    harmonic_scaling_spin_voxel,
    normalize_spin,
    spin_coherence,
    spin_disorder,
)


def random_spin(rng: random.Random) -> SpinVector:
    return normalize_spin((rng.uniform(-1.0, 1.0), rng.uniform(-1.0, 1.0), rng.uniform(-1.0, 1.0)))


def main() -> int:
    rng = random.Random(123)
    count = 256
    edges = build_ring_edges(count)
    cfg = SpinVoxelConfig(alpha=0.35, exchange_j=0.6, external_field=(0.0, 0.0, 0.05), spin_reference=2.0)

    aligned = [normalize_spin((1.0, 0.0, 0.0)) for _ in range(count)]
    disordered = [random_spin(rng) for _ in range(count)]

    c_aligned = spin_coherence(aligned)
    c_disordered = spin_coherence(disordered)
    disorder_aligned = spin_disorder(aligned, edges=edges)
    disorder_disordered = spin_disorder(disordered, edges=edges)

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

    phased = apply_phason(disordered, n=2, config=cfg)
    norm_drift_max = max(
        abs(
            ((s[0] ** 2 + s[1] ** 2 + s[2] ** 2) ** 0.5)
            - ((p[0] ** 2 + p[1] ** 2 + p[2] ** 2) ** 0.5)
        )
        for s, p in zip(disordered, phased)
    )

    payload = {
        "schema_version": "scbe_spin_voxel_benchmark_v1",
        "sample_size": count,
        "metrics": {
            "coherence_aligned": round(c_aligned, 6),
            "coherence_disordered": round(c_disordered, 6),
            "disorder_aligned": round(disorder_aligned, 6),
            "disorder_disordered": round(disorder_disordered, 6),
            "cost_aligned": round(cost_aligned, 6),
            "cost_disordered": round(cost_disordered, 6),
            "cost_ratio_disordered_over_aligned": round(cost_disordered / max(cost_aligned, 1e-9), 6),
            "phason_norm_drift_max": round(norm_drift_max, 12),
        },
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
