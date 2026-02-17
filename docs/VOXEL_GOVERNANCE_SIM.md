# Voxel Governance Simulator (SCBE)

## Purpose

Implements a deterministic sparse voxel simulation that bridges:
1. Spectral channels (six Sacred Tongues)
2. Voxel addressing (quantized cubic space)
3. Quasicrystal projection/validation
4. Governance routing using Poincaré distance and Layer 12 costs

Canonical wall formula is preserved:

`H(d*,R) = R * pi^(phi * d*)`

## Files

- Script: `scripts/voxel_governance_sim.py`
- Sample input: `examples/voxel_inputs.sample.json`
- Output (default): `artifacts/voxel_governance_run.json`

## Run

```powershell
python scripts/voxel_governance_sim.py `
  --input-json examples/voxel_inputs.sample.json `
  --count 12 `
  --output artifacts/voxel_governance_run.json
```

## Output contract

Top-level output includes:
1. `state_vector` (coherence, energy, drift)
2. `decision_record` (action, signature, timestamp, reason, confidence)
3. `route` (geodesic-style shortest path and total cost)
4. `voxels[]` (per-voxel metrics and decision details)

## Layer mapping

1. Layer 4/5: Poincaré embedding + hyperbolic distance via `poincare_dist_3d`.
2. Layer 9/12: coherence + Layer 12 cost from `src/scbe_governance_math.py`.
3. Layer 13: consensus decision from six local votes.
4. QC lattice: projection and acceptance window checks from `qc_lattice/quasicrystal.py`.

## Notes

1. The simulator is deterministic for a given input seed list.
2. If quasicrystal validity fails, decision severity is escalated.
3. This is an engineering bridge artifact for runtime experimentation, not a replacement for canonical spec/tests.

