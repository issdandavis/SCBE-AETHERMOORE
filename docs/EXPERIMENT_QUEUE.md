# Experiment Queue

Last updated: February 19, 2026
Scope: 24 claim-promotion experiments across 6 priority tiers.

## Global protocol
- Pre-register objective, metric, and pass criteria before running.
- Freeze dataset and seed set per run.
- Run baseline and candidate in same harness.
- Emit JSON metrics, confidence intervals, and failure slices.

## Tier Q0 - Reproducibility gate (3)

### Q0-1 Hyperbolic baseline adjudication
- Goal: reconcile `d_H` vs Euclidean conflicting artifacts.
- Pass: protocol and rerun artifacts agree within tolerance.

### Q0-2 Pipeline-vs-baseline adjudication
- Goal: reconcile `pipeline_vs_baseline` vs combined-defense claims.
- Pass: single adjudicated report with CI hash.

### Q0-3 Sacred Eggs rerun lock
- Goal: rerun SE-1/2/3 on pinned environment.
- Pass: same pass/fail outcomes with seed lock.

## Tier Q1 - Core claim promotion (5)

### Q1-1 Claim 5 promotion
- Measure full pipeline detection quality on frozen corpus.
- Pass: meets pre-stated AUC and latency gates.

### Q1-2 Claim 6 promotion
- Measure swarm governance under adversarial nodes.
- Pass: quorum integrity and safety actions hold under attack.

### Q1-3 Claim 7 promotion
- Measure data pipeline integrity and rollback safety.
- Pass: no silent corruption, deterministic recoverability.

### Q1-4 Claim 8 promotion
- Measure bounded harmonic scoring utility.
- Pass: better stability without unacceptable recall loss.

### Q1-5 Claim 12 promotion
- Measure PQC module conformance and interop.
- Pass: vector conformance and deterministic decode success.

## Tier Q2 - Comparative novelty tests (4)

### Q2-1 LWS vs uniform weighting
- Pass: statistically significant lift over best baseline.

### Q2-2 Spectral vs threshold detectors
- Pass: improved recall at fixed low FPR.

### Q2-3 Tri-mechanism ablation
- Pass: each mechanism demonstrates non-zero marginal value.

### Q2-4 Trust-ring policy vs flat RBAC
- Pass: fewer high-risk false allows at comparable throughput.

## Tier Q3 - Extension tests (6)

### Q3-1 PHDM traceability
- Pass: faster anomaly localization than non-PHDM logging.

### Q3-2 Flux-state recovery
- Pass: lower drift slope and faster recovery after stress.

### Q3-3 Sacred Tongue IPC robustness
- Pass: envelope integrity under packet loss/reorder.

### Q3-4 Dual-lattice runtime stress
- Pass: stable decisions under large topology perturbations.

### Q3-5 Provenance lineage tamper test
- Pass: tamper/replay attempts flagged with no silent pass.

### Q3-6 Multi-model modal matrix
- Pass: reducer improves decision quality vs single-model multimodal baseline.

## Tier Q4 - Research (3)

### Q4-1 Chladni eigenmode storage hypothesis
- Pass: measurable benefit under defined storage threat model.

### Q4-2 Spin voxel governance signal
- Pass: added predictive signal beyond existing features.

### Q4-3 Multi-model consensus topology
- Pass: consensus quality gain with bounded latency overhead.

## Tier Q5 - Nice-to-have (3)

### Q5-1 Cross-language parity suite
- Pass: TS/Python parity vectors match 100%.

### Q5-2 End-to-end perf benchmark pack
- Pass: reproducible benchmark with environment manifest.

### Q5-3 Visualization and audit UX pack
- Pass: operator can trace decision lineage in one dashboard flow.

## Experiment template (mandatory)

```md
Experiment ID:
Claim linkage:
Objective:
Dataset + seed:
Baselines:
Primary metric:
Secondary metrics:
Pre-stated pass criteria:
Pre-stated fail criteria:
Reproduce command:
Artifact paths:
```

## State machine
- `OPEN -> RUNNING -> PASS`
- `OPEN -> RUNNING -> FAIL`
- Promotion only occurs after `PASS` with reproducibility checks satisfied.
