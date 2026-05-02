# Quasi-Vector Spin Voxels for MAZE (R&D)

Status: Research and development (not production-integrated).

This note operationalizes a subset of the spin-voxel concept as a measurable
prototype layer for MAZE (Multi-geometry Adaptive Zonal Expert-router).

## Goal

Model intent-bearing storage states as spin vectors and test whether spin
disorder can serve as a governance/routing signal that amplifies harmonic cost.

## Scope of v0

- Implemented in `src/storage/spin_voxel.py`.
- Benchmarked by `scripts/benchmark/spin_voxel_benchmark.py`.
- Covered by `tests/test_spin_voxel.py`.
- No production wiring yet; this is shadow-mode R&D only.

## v0 Mathematical Mapping

- Spins: `S_i in R^3` (normalized vectors).
- Coherence:
  - `C_spin = |sum_i S_i| / (sum_i |S_i| + eps)`.
- Exchange-style Hamiltonian:
  - `H_spin = -J * sum_(i,j in E) (S_i dot S_j) - B dot sum_i S_i`.
- Disorder proxy:
  - `D_spin = mean_(i,j in E) (1 - S_i dot S_j)`.
- Harmonic coupling:
  - `H_sv = R^(d^2) * (T_phase / ||I||) * (1 + alpha * penalty_spin)`.
  - `penalty_spin = max(0, D_spin + H_spin / spin_reference)`.

## T-Phase Support in v0

Implemented phase factors:

- `fast = 1.0`
- `memory = 4.0`
- `governance = 12.0`
- `day = 0.85`
- `night = 1.15`
- `set = 8.0`

## Phason Dynamics (v0)

Golden-ratio-inspired z-axis rotation:

- `theta = 2*pi / phi^n`
- rotation matrix preserves spin norms.

## Integration Path (recommended)

1. Keep spin-voxel as read-side signal only (no write-path dependency).
2. Feed `C_spin` and `D_spin` into MAZE fusion as a reranking channel.
3. Compare MAZE with/without spin channel in benchmark harness.
4. Promote only if quality gains are stable and p95 latency stays bounded.
