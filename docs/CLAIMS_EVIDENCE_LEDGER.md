# Claims Evidence Ledger

Last updated: February 19, 2026
Scope: Provisional claim tracking mapped to reproducible evidence status.

## Status labels
- `PROVEN`: reproduced with artifacts and baseline comparisons.
- `PROVEN_PARTIAL`: one sub-claim validated, at least one key sub-claim still open.
- `CODE_EXISTS_UNTESTED`: implementation exists, no claim-grade benchmark yet.
- `THEORETICAL_ONLY`: formal argument exists, no implementation-grade validation.
- `REFRAMED`: claim retained with corrected technical framing.

## Portfolio summary (21 claims)
- `PROVEN`: 8/21 (38%)
- `PROVEN_PARTIAL`: 1/21 (5%)
- `CODE_EXISTS_UNTESTED`: 10/21 (48%)
- `THEORETICAL_ONLY`: 1/21 (5%)
- `REFRAMED`: 1/21 (5%)

## Claim matrix

| Claim | Status | Evidence anchor | Next gate |
|---|---|---|---|
| 1 | PROVEN | `experiments/three_mechanism_results.json` | external reproducibility rerun |
| 2 | PROVEN | `tests/test_sacred_eggs.py`, `tests/test_sacred_eggs_ref.py` | TS/Python parity vectors |
| 3 | REFRAMED | `docs/CLAIMS_AUDIT_V4.md` | maintain as cost-function framing only |
| 4 | PROVEN | `experiments/sacred_eggs_results.json` | side-channel profile report |
| 5 | CODE_EXISTS_UNTESTED | `src/symphonic_cipher/scbe_aethermoore/layers/fourteen_layer_pipeline.py` | benchmark on frozen corpus |
| 6 | CODE_EXISTS_UNTESTED | `hydra/`, `src/ai_brain/unified-kernel.ts` | byzantine adversary simulation suite |
| 7 | CODE_EXISTS_UNTESTED | `scripts/`, training automation paths | end-to-end data lineage benchmark |
| 8 | CODE_EXISTS_UNTESTED | `packages/kernel/src/harmonicScaling.ts` | bounded-vs-unbounded comparative test |
| 9 | PROVEN | `experiments/three_mechanism_results.json` | held-out attack family rerun |
| 10 | PROVEN | `experiments/three_mechanism_results.json` | ablation proof for GeoSeal contribution |
| 11 | PROVEN | deployment/config artifacts + integration tests | environment-independent perf envelope |
| 12 | CODE_EXISTS_UNTESTED | `packages/kernel/src/pqc.ts`, python pqc modules | conformance and interop vectors |
| 13 | THEORETICAL_ONLY | ordering rationale in design docs | implement and measure reject-cost ordering |
| 14 | PROVEN | model/package artifacts and integration traces | reproducible release pinning |
| 15 | CODE_EXISTS_UNTESTED | spectral identity modules | benchmark vs simpler spectral thresholds |
| 16 | CODE_EXISTS_UNTESTED | voxel + quasicrystal modules | robustness and scaling test suite |
| 17 | CODE_EXISTS_UNTESTED | automated training connectors | failure-mode and rollback validation |
| 18 | CODE_EXISTS_UNTESTED | harmonic/temporal modules | long-horizon drift and calibration test |
| 19 | PROVEN_PARTIAL | trust-tier behavior observed in runtime paths | prove swarm classification lift vs baseline |
| 20 | CODE_EXISTS_UNTESTED | provenance and lineage components | tamper and replay audit challenge tests |
| 21 | PROVEN | combined defense-in-depth evidence in `experiments/three_mechanism_results.json` | independent third-run reproducibility |

## Conflict register

### C-1: Hyperbolic baseline mismatch
- `docs/CLAIMS_AUDIT_V4.md` and `experiments/hyperbolic_experiment_results.json` reflect different protocols.
- Action: lock one canonical protocol before any status promotion.

### C-2: Pipeline superiority mismatch
- `experiments/pipeline_vs_baseline_results.json` disagrees with broad superiority framing.
- Action: publish adjudicated run with confidence intervals and fixed seeds.

### C-3: Formula family drift
- Multiple active formula families appear in code/docs.
- Action: require regime tags (`WALL_ENFORCEMENT`, `PATROL_MONITORING`, `BOUNDED_SCORING`) in all claim docs.

## Promotion policy
1. Fixed dataset version and seed file.
2. One canonical script per claim experiment.
3. JSON metrics artifact + CI log hash.
4. Baseline included in same run.
5. Reviewer sign-off row appended below.

## Sign-off log

| Date | Claim | Decision | Reviewer | Notes |
|---|---|---|---|---|
| 2026-02-19 | Portfolio | Updated | Codex | Migrated to 21-claim ledger structure requested by user |
