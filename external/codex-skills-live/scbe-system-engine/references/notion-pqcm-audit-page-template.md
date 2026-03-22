---
title: PQCM kappa_eff Audit — Feb 2026
parent: SCBE-AETHERMOORE
status: draft
---

# PQCM κ_eff Audit — Feb 2026

## Verdict

- Result: `FAIL: growth risk`
- Formula: `kappa_eff = (E/N) * log(1 + det(L_reduced))`
- Issue: `det(L_reduced)` scales rapidly with graph size (`N^(N-2)` for complete graph), so log-term can re-scale stiffness.

## Evidence

- `references/dimensional-analysis.md` updated with Common Error #5.
- `references/scbe-pqcm-audit-log.md` dataset metadata added.
- `scripts/pqcm_audit.py --max-n 10` output captured and stored in audit trace.

## Required follow-up

- Replace determinant-based factor with a normalized finite-size-safe scalar.
- Keep the dual-output audit contract in place (`StateVector`, `DecisionRecord`).

