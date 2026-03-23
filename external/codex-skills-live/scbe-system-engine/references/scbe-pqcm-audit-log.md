---
dataset_id: scbe-pqcm-audit-log
title: SCBE PQCM Formula Audit Log
license: mit
language: en
multilingual_support: false
pipeline: scbe-system-engine
version: 0.1.0
---

# SCBE PQCM Audit Log

Use this dataset to store deterministic formula-audit records for
`kappa_eff = (E/N) * log(1 + det(L))` and related PQCM stiffness proposal checks.

- SCBE Layers referenced: 1, 5, 8, 12
- Sacred Tongue affinity: KO, CA, DR
- Dual-output schema:
  - `StateVector`: n, E, det_L, kappa, kappa_eff
  - `DecisionRecord`: decision, signature, timestamp, rationale

## Record Schema

Each row should be JSON with:

- `record_id` (string): deterministic run hash or version tag
- `timestamp` (string): RFC3339 UTC
- `dataset` (string): fixed `"pqcm_audit"`
- `n` (integer): graph size
- `E` (integer): edge count
- `det_reduced_l` (integer): reduced Laplacian determinant proxy (`n^(n-2)` for K_n)
- `kappa` (number): baseline stiffness `E/N`
- `kappa_eff` (number): proposed stiffness `(E/N) * log(1 + det)`
- `ratio_to_baseline` (number)
- `risk` (enum): `PASS | WARN | FAIL`
- `notes` (string): dimensional and behavioral findings

## Canonical Notes

- `det(L_reduced)` is dimensionless but can exhibit super-polynomial growth with N.
- For complete graph probes, `det(K_n) = N^(N-2)` → growth in `log(1 + det)` is unbounded.
- This dataset exists to preserve audit history and prevent reintroducing scaling traps.
